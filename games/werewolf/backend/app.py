from flask import Flask, request, jsonify
import os
import json
import random
import threading
import time
import uuid
from typing import List, Dict, Any, Optional

# Simple Werewolf game server (AI-driven players). Reads API key from project root.

def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    root = os.getcwd()
    f1 = os.path.join(root, "api_key")
    if os.path.exists(f1):
        return open(f1).read().strip()
    f2 = os.path.join(root, "api_keys.json")
    if os.path.exists(f2):
        try:
            data = json.load(open(f2))
            for k in ("OPENAI_API_KEY", "openai", "api_key", "apiKey"):
                if k in data:
                    return data[k]
        except Exception:
            pass
    f3 = os.path.join(root, "api_keys.example.json")
    if os.path.exists(f3):
        try:
            data = json.load(open(f3))
            for k in ("OPENAI_API_KEY", "openai", "api_key"):
                if k in data:
                    return data[k]
        except Exception:
            pass
    return ""

API_KEY = load_api_key()

# ai_client is implemented separately and is expected to provide:
# - decide_night_action(player, context, api_key)
# - decide_vote(player, context, api_key)
# Import robustly so tests that load this module by file path work in different contexts.
import importlib
import importlib.util

ai_client = None
try:
    # normal package-relative import (when running as package)
    from . import ai_client as _ai_client  # type: ignore
    ai_client = _ai_client
except Exception:
    try:
        # absolute import by package name if available
        ai_client = importlib.import_module("games.werewolf.backend.ai_client")
    except Exception:
        # fallback: load module directly from file path
        try:
            spec_path = os.path.join(os.getcwd(), "games", "werewolf", "backend", "ai_client.py")
            spec = importlib.util.spec_from_file_location("werewolf_ai_client", spec_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            ai_client = mod
        except Exception:
            # final fallback: lightweight stub to allow tests to run without network
            class _StubAIClient:
                @staticmethod
                def decide_night_action(player, context, api_key):
                    alive = context.get("state", {}).get("alive", [])
                    alive = [p for p in alive if p != player]
                    return alive[0] if alive else None

                @staticmethod
                def decide_talk(player, context, talk_history, api_key):
                    # return a simple heuristic speech object expected by the server
                    alive = context.get("state", {}).get("alive", [])
                    if player not in alive:
                        return None
                    speech = f"I am {player}. I have nothing special to say."
                    return {"speech": speech, "meta": {"heuristic": True}}

                @staticmethod
                def decide_vote(player, context, api_key):
                    alive = context.get("state", {}).get("alive", [])
                    alive = [p for p in alive if p != player]
                    return alive[0] if alive else player

                @staticmethod
                def get_model_for(player):
                    return None
            ai_client = _StubAIClient()

app = Flask(__name__)

ROLES = ["werewolf", "seer", "witch", "villager"]

class Game:
    def __init__(self, players: List[str]=None):
        self.players = players or [f"AI_{i}" for i in range(6)]
        self.num_players = len(self.players)
        self.roles: Dict[str, str] = {}
        self.alive = set(self.players)
        self.day = 0
        self.state = "lobby"  # lobby, night, day, ended
        self.history: List[Dict[str, Any]] = []
        # Witch resources tracked on server (one-time save and poison)
        self.witch_save_available = True
        self.witch_poison_available = True
        # werewolf team coordination buffer (collect choices each night)
        self._werewolf_choices: List[str] = []
        self.assign_roles()

    def assign_roles(self):
        order = list(self.players)
        random.shuffle(order)
        roles = ["werewolf", "werewolf", "seer", "witch"] + ["villager"] * (self.num_players - 4)
        for p, r in zip(order, roles):
            self.roles[p] = r

    def to_dict(self):
        return {
            "players": self.players,
            "alive": list(self.alive),
            "roles_known_to_server": self.roles,
            "day": self.day,
            "state": self.state,
            "history": self.history[-20:],
        }

    def check_win(self):
        wolves = [p for p in self.alive if self.roles.get(p) == "werewolf"]
        villagers = [p for p in self.alive if self.roles.get(p) != "werewolf"]
        if not wolves:
            return "villagers"
        if len(wolves) >= len(villagers):
            return "werewolves"
        return None

    def night_phase(self):
        self.state = "night"
        self.day += 1
        actions = []
        # reset werewolf buffer for this night
        self._werewolf_choices = []
        for p in list(self.alive):
            role = self.roles.get(p)
            # determine model for logging if ai_client exposes it
            model_used = None
            try:
                model_used = ai_client.get_model_for(p)
            except Exception:
                model_used = None
            if role == "werewolf":
                # werewolves propose targets; server will aggregate; measure latency & record model
                start = time.time()
                target = ai_client.decide_night_action(p, {"role": "werewolf", "state": self.to_dict()}, API_KEY)
                latency = time.time() - start
                if target:
                    self._werewolf_choices.append(target)
                actions.append({"actor": p, "action": "vote_kill", "target": target, "meta": {"model": model_used, "latency": latency}})
            elif role == "seer":
                start = time.time()
                target = ai_client.decide_night_action(p, {"role": "seer", "state": self.to_dict()}, API_KEY)
                latency = time.time() - start
                revealed = None
                if target in self.roles:
                    revealed = self.roles.get(target)
                actions.append({"actor": p, "action": "reveal", "target": target, "revealed_role": revealed, "meta": {"model": model_used, "latency": latency}})
            elif role == "witch":
                start = time.time()
                target = ai_client.decide_night_action(p, {"role": "witch", "state": self.to_dict()}, API_KEY)
                latency = time.time() - start
                # target protocol: if equals night victim -> attempt save; otherwise poison target
                actions.append({"actor": p, "action": "witch_action", "target": target, "meta": {"model": model_used, "latency": latency}})
        # resolve werewolf collective decision (majority of proposed targets)
        killed = None
        if self._werewolf_choices:
            try:
                from collections import Counter
                cnt = Counter(self._werewolf_choices)
                most = cnt.most_common()
                maxv = most[0][1]
                candidates = [t for t, c in most if c == maxv]
                killed = random.choice(candidates)
                if killed not in self.alive:
                    killed = None
            except Exception:
                killed = None
        # process witch actions: save if matches killed and save available; else poison if poison available
        for a in actions:
            if a["action"] == "witch_action" and a.get("target"):
                if a["target"] == killed and self.witch_save_available:
                    killed = None
                    self.witch_save_available = False
                    a["result"] = "saved"
                elif a["target"] in self.alive and a["target"] != killed and self.witch_poison_available:
                    killed = a["target"]
                    self.witch_poison_available = False
                    a["result"] = "poisoned"
        if killed:
            self.alive.remove(killed)
        # record night with detailed context for auditing and reasoning
        self.history.append({
            "phase": "night",
            "day": self.day,
            "killed": killed,
            "actions": actions,
            "witch_save_available": self.witch_save_available,
            "witch_poison_available": self.witch_poison_available,
            "werewolf_choices": list(self._werewolf_choices),
        })

    def day_phase(self):
        """
        Day phase now includes:
         - Ordered talk round: players speak in self.players order (only alive players speak).
           Each speech is collected into talk_history and passed to subsequent speakers.
         - Voting: after talks, each alive player votes; the talk_history is provided in the vote context.
         - History records 'talks' (list of {"player","speech","meta","model","latency"}) and voting metadata.
        """
        self.state = "day"
        votes = {}
        votes_meta = []
        talks = []
        # Ordered talk round: use original player order so numbering 1..6 remains stable
        for p in list(self.players):
            if p not in self.alive:
                continue
            # determine model for logging if available
            model_used = None
            try:
                model_used = ai_client.get_model_for(p)
            except Exception:
                model_used = None
            start = time.time()
            try:
                talk_result = ai_client.decide_talk(p, {"state": self.to_dict()}, talks, API_KEY)
            except TypeError:
                # older ai_client may not support decide_talk signature; fallback to simple placeholder
                talk_result = {"speech": f"{p} has nothing to add.", "meta": {"heuristic": True}}
            latency = time.time() - start
            if isinstance(talk_result, dict):
                speech = talk_result.get("speech") or ""
                meta = talk_result.get("meta") or {}
            else:
                speech = str(talk_result)
                meta = {}
            talks.append({"player": p, "speech": speech, "meta": meta, "model": model_used, "latency": latency})
        # Voting round: provide talk history context to voters
        for p in list(self.alive):
            # determine model for logging if available
            model_used = None
            try:
                model_used = ai_client.get_model_for(p)
            except Exception:
                model_used = None
            start = time.time()
            vote = None
            try:
                vote = ai_client.decide_vote(p, {"state": self.to_dict(), "talk_history": talks}, API_KEY)
            except TypeError:
                vote = ai_client.decide_vote(p, {"state": self.to_dict()}, API_KEY)
            latency = time.time() - start
            if vote not in self.alive:
                vote = random.choice(list(self.alive))
            votes.setdefault(vote, 0)
            votes[vote] += 1
            votes_meta.append({"voter": p, "vote": vote, "model": model_used, "latency": latency})
        lynched = None
        if votes:
            # tie-breaker: random among top-voted
            max_votes = max(votes.values())
            top = [name for name, v in votes.items() if v == max_votes]
            lynched = random.choice(top)
            if lynched in self.alive:
                self.alive.remove(lynched)
        # record day with talks and votes metadata
        self.history.append({"phase": "day", "day": self.day, "lynched": lynched, "votes": votes, "votes_meta": votes_meta, "talks": talks})

    def step(self):
        if self.state in ("lobby", "day"):
            self.night_phase()
        elif self.state == "night":
            self.day_phase()
        winner = self.check_win()
        if winner:
            self.state = "ended"
            self.history.append({"phase": "end", "winner": winner})

# Rooms management
rooms_lock = threading.Lock()
rooms: Dict[str, Dict[str, Any]] = {}

def create_room(owner: str, max_players: int = 6) -> str:
    with rooms_lock:
        rid = str(uuid.uuid4())[:8]
        rooms[rid] = {
            "id": rid,
            "owner": owner,
            "players": [owner],
            "max_players": max_players,
            "game": None,
            "created_at": time.time(),
            "state": "waiting",  # waiting, running, ended
        }
        return rid

def join_room(room_id: str, player: str) -> Optional[str]:
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return "room_not_found"
        if r["state"] != "waiting":
            return "room_not_joinable"
        if player in r["players"]:
            return "already_in_room"
        if len(r["players"]) >= r["max_players"]:
            return "room_full"
        r["players"].append(player)
        return None

def leave_room(room_id: str, player: str) -> Optional[str]:
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return "room_not_found"
        if player in r["players"]:
            r["players"].remove(player)
            if r["owner"] == player and r["players"]:
                r["owner"] = r["players"][0]
            if not r["players"]:
                del rooms[room_id]
            return None
        return "not_in_room"

def start_room_game(room_id: str) -> Optional[str]:
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return "room_not_found"
        if r["state"] != "waiting":
            return "already_started"
        players = list(r["players"])
        g = Game(players)
        r["game"] = g
        r["state"] = "running"
        return None

def get_room_state(room_id: str) -> Optional[Dict[str, Any]]:
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return None
        g = r.get("game")
        # If the game object exists and has reached ended state, reflect that in the room state
        room_state = r.get("state", "waiting")
        if g and getattr(g, "state", None) == "ended":
            room_state = "ended"
        return {
            "id": r["id"],
            "owner": r["owner"],
            "players": list(r["players"]),
            "max_players": r["max_players"],
            "created_at": r["created_at"],
            "state": room_state,
            "game": g.to_dict() if g else None,
        }

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# Small helpers for reading/writing JSON config files in project root / game folder
def _read_json_file(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _write_json_file(path: str, data) -> bool:
    try:
        dirp = os.path.dirname(path)
        if dirp and not os.path.exists(dirp):
            os.makedirs(dirp, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

API_KEYS_PATH = os.path.join(os.getcwd(), "api_keys.json")
PLAYERS_CONFIG_PATH = os.path.join(os.getcwd(), "games", "werewolf", "config.json")

@app.route("/config/api_keys", methods=["GET", "POST"])
def api_keys_config():
    if request.method == "GET":
        data = _read_json_file(API_KEYS_PATH)
        if data is None:
            return jsonify({"error": "not_found"}), 404
        return jsonify(data)
    # POST - write file
    body = request.json
    if body is None:
        return jsonify({"error": "invalid_json"}), 400
    ok = _write_json_file(API_KEYS_PATH, body)
    if not ok:
        return jsonify({"error": "write_failed"}), 500
    return jsonify({"status": "ok"})

@app.route("/config/players", methods=["GET", "POST"])
def players_config():
    if request.method == "GET":
        data = _read_json_file(PLAYERS_CONFIG_PATH)
        if data is None:
            # return default structure if not present
            return jsonify({"players": [], "role_preferences": {}}), 200
        return jsonify(data)
    body = request.json
    if body is None:
        return jsonify({"error": "invalid_json"}), 400
    # basic validation: must include players list
    if not isinstance(body, dict) or "players" not in body or not isinstance(body.get("players"), list):
        return jsonify({"error": "invalid_schema"}), 400
    ok = _write_json_file(PLAYERS_CONFIG_PATH, body)
    if not ok:
        return jsonify({"error": "write_failed"}), 500
    return jsonify({"status": "ok"})

@app.route("/rooms", methods=["GET", "POST"])
def rooms_handler():
    if request.method == "GET":
        with rooms_lock:
            return jsonify({"rooms": [get_room_state(rid) for rid in rooms.keys()]})
    body = request.json or {}
    owner = body.get("owner", "AI_owner")
    max_players = int(body.get("max_players", 6))
    rid = create_room(owner, max_players)
    return jsonify({"room_id": rid})

@app.route("/rooms/<room_id>/join", methods=["POST"])
def join_handler(room_id: str):
    body = request.json or {}
    player = body.get("player")
    if not player:
        return jsonify({"error": "player required"}), 400
    err = join_room(room_id, player)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"status": "joined", "room": get_room_state(room_id)})

@app.route("/rooms/<room_id>/leave", methods=["POST"])
def leave_handler(room_id: str):
    body = request.json or {}
    player = body.get("player")
    if not player:
        return jsonify({"error": "player required"}), 400
    err = leave_room(room_id, player)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"status": "left", "room": get_room_state(room_id)})

@app.route("/rooms/<room_id>/start", methods=["POST"])
def start_handler(room_id: str):
    err = start_room_game(room_id)
    if err:
        return jsonify({"error": err}), 400
    # If players config exists, apply role_preferences to newly created game
    with rooms_lock:
        r = rooms.get(room_id)
        if r and r.get("game") and os.path.exists(PLAYERS_CONFIG_PATH):
            cfg = _read_json_file(PLAYERS_CONFIG_PATH) or {}
            prefs = cfg.get("role_preferences", {}) if isinstance(cfg, dict) else {}
            g: Optional[Game] = r.get("game")
            if g:
                # apply preferences: for any player with a preferred role, set it in g.roles (override random)
                for p, pref in prefs.items():
                    if p in g.players and pref in ROLES:
                        g.roles[p] = pref
    return jsonify({"status": "started", "room": get_room_state(room_id)})

@app.route("/rooms/<room_id>/state", methods=["GET"])
def room_state_handler(room_id: str):
    st = get_room_state(room_id)
    if not st:
        return jsonify({"error": "room_not_found"}), 404
    return jsonify(st)

@app.route("/rooms/<room_id>/step", methods=["POST"])
def room_step_handler(room_id: str):
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return jsonify({"error": "room_not_found"}), 404
        g: Optional[Game] = r.get("game")
    if not g:
        return jsonify({"error": "game_not_started"}), 400
    g.step()
    with rooms_lock:
        if g.state == "ended":
            r["state"] = "ended"
    return jsonify({"status": "ok", "room": get_room_state(room_id)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)