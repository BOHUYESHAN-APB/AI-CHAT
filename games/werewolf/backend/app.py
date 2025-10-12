from flask import Flask, request, jsonify
import os
import json
import random
import threading
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

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
models = None
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

try:
    from . import models as _models  # type: ignore
    models = _models
except Exception:
    try:
        models = importlib.import_module("games.werewolf.backend.models")
    except Exception:
        try:
            spec_path = os.path.join(os.getcwd(), "games", "werewolf", "backend", "models.py")
            spec = importlib.util.spec_from_file_location("werewolf_models", spec_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            models = mod
        except Exception:
            models = None

app = Flask(__name__)

if models and hasattr(models, "Role"):
    ROLES = [r.value for r in models.Role]  # type: ignore[attr-defined]
else:
    ROLES = ["werewolf", "seer", "witch", "villager"]

class Game:
    def __init__(self, players: List[str] = None):
        self.players = players or [f"AI_{i}" for i in range(6)]
        self.num_players = len(self.players)
        self.roles: Dict[str, str] = {}
        self.alive = set(self.players)
        self.day = 0
        self.state = "lobby"  # lobby, night, day_morning, day_discussion, day_voting, vote_reveal, ended
        self.history: List[Dict[str, Any]] = []
        # Witch resources tracked on server (one-time save and poison)
        self.witch_save_available = True
        self.witch_poison_available = True
        # werewolf team coordination buffer (collect choices each night)
        self._werewolf_choices: List[str] = []
        # cached phase summaries for multi-stage day cycle
        self.last_night_result: Optional[Dict[str, Any]] = None
        self.morning_announcement: Optional[Dict[str, Any]] = None
        self.current_talks: List[Dict[str, Any]] = []
        self.current_votes: Dict[str, int] = {}
        self.current_votes_meta: List[Dict[str, Any]] = []
        self.guard_last_protected: Dict[str, Optional[str]] = {}
        self.gs = None
        self.assign_roles()

    def assign_roles(self):
        self.roles = {}
        self.gs = None
        if models and hasattr(models, "create_default_game"):
            try:
                self.gs = models.create_default_game(self.players)  # type: ignore[attr-defined]
                for player in getattr(self.gs, "players", []):
                    role_obj = getattr(player, "role", None)
                    role_value = getattr(role_obj, "value", None)
                    self.roles[player.name] = role_value or str(role_obj)
                try:
                    alive_players = self.gs.alive_players()  # type: ignore[attr-defined]
                except Exception:
                    alive_players = [player.name for player in getattr(self.gs, "players", [])]
                self.alive = set(alive_players)
                return
            except Exception:
                self.gs = None
        order = list(self.players)
        random.shuffle(order)
        fallback_roles: List[str] = []
        if models and hasattr(models, "default_roles_for"):
            try:
                distribution = models.default_roles_for(self.num_players)  # type: ignore[attr-defined]
                fallback_roles = [getattr(role, "value", str(role)) for role in distribution]
            except Exception:
                fallback_roles = []
        if not fallback_roles:
            fallback_roles = ["werewolf", "werewolf", "seer", "witch"] + ["villager"] * max(self.num_players - 4, 0)
        for p, r in zip(order, fallback_roles):
            self.roles[p] = r
        self.alive = set(self.roles.keys())

    def set_player_role(self, player: str, role: str):
        if role not in ROLES:
            return
        self.roles[player] = role
        if self.gs and hasattr(self.gs, "get_player"):
            try:
                target_player = self.gs.get_player(player)  # type: ignore[attr-defined]
                if target_player:
                    if hasattr(models, "Role"):
                        try:
                            target_player.role = models.Role(role)  # type: ignore[attr-defined]
                        except Exception:
                            target_player.role = role
                    else:
                        target_player.role = role
            except Exception:
                pass

    def _mark_dead(self, player: Optional[str], cause: str):
        if not player or player not in self.alive:
            return
        # remove player from alive set
        self.alive.remove(player)
        # annotate model state player as dead
        if self.gs and hasattr(self.gs, "get_player"):
            try:
                target_player = self.gs.get_player(player)  # type: ignore[attr-defined]
                if target_player:
                    target_player.alive = False
                    if hasattr(target_player, "meta") and isinstance(target_player.meta, dict):
                        target_player.meta["death_cause"] = cause
                        target_player.meta["death_day"] = self.day
            except Exception:
                pass
        # record history entry for this death
        self.history.append({"phase": "death_event", "day": self.day, "player": player, "cause": cause})
        # handle Cupid lover consequence: if player had a lover, that lover dies of heartbreak (if still alive)
        try:
            if self.gs and hasattr(self.gs, "get_player"):
                tp = self.gs.get_player(player)  # type: ignore[attr-defined]
                partner = getattr(tp, "lover_partner", None) if tp else None
                if partner and partner in self.alive:
                    # mark lover dead due to heartbreak
                    self.alive.remove(partner)
                    if self.gs:
                        p_obj = self.gs.get_player(partner)  # type: ignore[attr-defined]
                        if p_obj:
                            p_obj.alive = False
                            p_obj.meta["death_cause"] = "lover_heartbreak"
                            p_obj.meta["death_day"] = self.day
                    self.history.append({"phase": "death_event", "day": self.day, "player": partner, "cause": "lover_heartbreak", "linked_to": player})
        except Exception:
            pass

    def _reset_day_buffers(self):
        self.current_talks = []
        self.current_votes = {}
        self.current_votes_meta = []

    def _get_model_name(self, player: str) -> Optional[str]:
        try:
            return ai_client.get_model_for(player)
        except Exception:
            return None

    def _check_and_finalize_winner(self) -> bool:
        winner = self.check_win()
        if winner:
            self.state = "ended"
            self.history.append({"phase": "end", "winner": winner, "day": self.day})
            return True
        return False

    def to_dict(self):
        snapshot: Dict[str, Any] = {
            "players": self.players,
            "alive": list(self.alive),
            "roles_known_to_server": self.roles,
            "day": self.day,
            "state": self.state,
            "available_roles": ROLES,
            "history": self.history[-20:],
            "phase_context": {
                "last_night_result": self.last_night_result,
                "morning_announcement": self.morning_announcement,
                "current_talks": self.current_talks,
                "current_votes": self.current_votes,
                "current_votes_meta": self.current_votes_meta,
            },
            "resources": {
                "witch_save_available": self.witch_save_available,
                "witch_poison_available": self.witch_poison_available,
            },
        }
        if self.gs and hasattr(self.gs, "to_dict"):
            try:
                snapshot["model_state"] = self.gs.to_dict()  # type: ignore[call-arg]
            except Exception:
                pass
        return snapshot

    def check_win(self):
        # third-party lovers win: if exactly two alive players and they are lovers linked by Cupid
        try:
            if self.gs:
                alive_list = list(self.alive)
                if len(alive_list) == 2:
                    p0 = self.gs.get_player(alive_list[0])
                    p1 = self.gs.get_player(alive_list[1])
                    if p0 and p1 and getattr(p0, "lover_partner", None) == p1.name and getattr(p1, "lover_partner", None) == p0.name:
                        return "lovers"
        except Exception:
            pass
        wolves = [p for p in self.alive if self.roles.get(p) == "werewolf"]
        villagers = [p for p in self.alive if self.roles.get(p) != "werewolf"]
        if not wolves:
            return "villagers"
        if len(wolves) >= len(villagers):
            return "werewolves"
        return None

    def night_phase(self):
        """
        Night resolution with support for guard protection and hunter retaliation.
        Order of resolution:
          1. Collect night actions from werewolf/seer/witch/guard (guard cannot protect same player consecutively).
          2. Resolve werewolf collective kill target.
          3. Apply guard protections (may save the night victim).
          4. Apply witch save/poison.
          5. If final killed is a hunter, perform hunter's retaliation shot.
        """
        self.state = "night"
        self.day += 1
        actions: List[Dict[str, Any]] = []
        # reset werewolf buffer for this night
        self._werewolf_choices = []
        guard_actions: List[Dict[str, Any]] = []

        for p in list(self.alive):
            role = self.roles.get(p)
            model_used = self._get_model_name(p)
            start = time.time()
            api_key = get_api_key_for_player(p)
            if role == "werewolf":
                target = None
                try:
                    target = ai_client.decide_night_action(p, {"role": "werewolf", "state": self.to_dict()}, api_key)
                except Exception:
                    target = None
                latency = time.time() - start
                if target:
                    self._werewolf_choices.append(target)
                actions.append({"actor": p, "action": "vote_kill", "target": target, "meta": {"model": model_used, "latency": latency}})
            elif role == "seer":
                target = None
                try:
                    target = ai_client.decide_night_action(p, {"role": "seer", "state": self.to_dict()}, api_key)
                except Exception:
                    target = None
                latency = time.time() - start
                revealed = None
                if target in self.roles:
                    revealed = self.roles.get(target)
                actions.append({"actor": p, "action": "reveal", "target": target, "revealed_role": revealed, "meta": {"model": model_used, "latency": latency}})
            elif role == "witch":
                target = None
                try:
                    target = ai_client.decide_night_action(p, {"role": "witch", "state": self.to_dict()}, api_key)
                except Exception:
                    target = None
                latency = time.time() - start
                actions.append({"actor": p, "action": "witch_action", "target": target, "meta": {"model": model_used, "latency": latency}})
            elif role == "guard":
                target = None
                try:
                    target = ai_client.decide_night_action(p, {"role": "guard", "state": self.to_dict()}, api_key)
                except Exception:
                    target = None
                latency = time.time() - start
                last_protected = self.guard_last_protected.get(p)
                # enforce no consecutive protection of the same player
                if target and last_protected and target == last_protected:
                    # invalid repeat protection; record but mark invalid
                    actions.append({"actor": p, "action": "guard_protect", "target": target, "meta": {"model": model_used, "latency": latency}, "result": "invalid_repeat"})
                else:
                    guard_actions.append({"actor": p, "target": target, "meta": {"model": model_used, "latency": latency}})
                    actions.append({"actor": p, "action": "guard_protect", "target": target, "meta": {"model": model_used, "latency": latency}})
            elif role == "cupid":
                # Cupid chooses two players to link as lovers (format: "AI_1,AI_2" or JSON)
                choice = None
                try:
                    choice = ai_client.decide_night_action(p, {"role": "cupid", "state": self.to_dict()}, api_key)
                except Exception:
                    choice = None
                latency = time.time() - start
                linked = None
                if isinstance(choice, str):
                    parts = [s.strip() for s in choice.split(",") if s.strip()]
                    if len(parts) >= 2:
                        linked = (parts[0], parts[1])
                elif isinstance(choice, (list, tuple)) and len(choice) >= 2:
                    linked = (choice[0], choice[1])
                if linked and self.gs:
                    try:
                        self.gs.link_lovers(linked[0], linked[1])
                    except Exception:
                        pass
                actions.append({"actor": p, "action": "cupid_link", "target": linked, "meta": {"model": model_used, "latency": latency}})
            else:
                # roles without night actions (villager, hunter before death, etc.)
                continue

        # resolve werewolf collective decision (majority of proposed targets)
        killed: Optional[str] = None
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

        # process guard actions first: if any guard protected the killed target, the kill is prevented
        if killed and guard_actions:
            for g in guard_actions:
                tgt = g.get("target")
                actor = g.get("actor")
                if tgt and tgt == killed:
                    # save happens
                    killed = None
                    # mark that guard protected this target this night (prevent consecutive next night)
                    self.guard_last_protected[actor] = tgt
                    # annotate action record in actions list
                    for a in actions:
                        if a.get("actor") == actor and a.get("action") == "guard_protect" and a.get("target") == tgt:
                            a["result"] = "saved"
                            break
                    break
            # also update guard_last_protected for guards who protected someone (even if not saving)
            for g in guard_actions:
                actor = g.get("actor")
                tgt = g.get("target")
                if actor and tgt:
                    # only set when not invalid_repeat (invalid_repeat recorded earlier)
                    if self.guard_last_protected.get(actor) != tgt:
                        self.guard_last_protected[actor] = tgt

        # process witch actions: save if matches killed and save available; else poison if poison available
        for a in actions:
            if a.get("action") == "witch_action" and a.get("target"):
                tgt = a.get("target")
                if tgt == killed and self.witch_save_available:
                    killed = None
                    self.witch_save_available = False
                    a["result"] = "saved"
                elif tgt in self.alive and tgt != killed and self.witch_poison_available:
                    killed = tgt
                    self.witch_poison_available = False
                    a["result"] = "poisoned"

        # apply final kill (use _mark_dead to keep model state in sync)
        if killed:
            self._mark_dead(killed, "night")

        # if a hunter died this night, allow immediate retaliation shot
        hunter_shot_info: Optional[Dict[str, Any]] = None
        if killed and self.roles.get(killed) == "hunter":
            actor = killed
            model_used = self._get_model_name(actor)
            start = time.time()
            api_key = get_api_key_for_player(actor)
            shot_target = None
            try:
                shot_target = ai_client.decide_night_action(actor, {"role": "hunter", "state": self.to_dict(), "killed": actor}, api_key)
            except Exception:
                shot_target = None
            latency = time.time() - start
            if shot_target and shot_target in self.alive:
                self._mark_dead(shot_target, "hunter_shot")
                hunter_shot_info = {"actor": actor, "action": "hunter_shot", "target": shot_target, "meta": {"model": model_used, "latency": latency}, "result": "killed"}
            else:
                hunter_shot_info = {"actor": actor, "action": "hunter_shot", "target": shot_target, "meta": {"model": model_used, "latency": latency}, "result": "invalid_or_missed"}
            actions.append(hunter_shot_info)

        # record night with detailed context for auditing and reasoning
        self.history.append({
            "phase": "night",
            "day": self.day,
            "killed": killed,
            "actions": actions,
            "witch_save_available": self.witch_save_available,
            "witch_poison_available": self.witch_poison_available,
            "werewolf_choices": list(self._werewolf_choices),
            "guard_last_protected": dict(self.guard_last_protected),
        })

    def _run_discussion(self):
        """Run ordered talk round and populate self.current_talks."""
        talks: List[Dict[str, Any]] = []
        for p in list(self.players):
            if p not in self.alive:
                continue
            model_used = self._get_model_name(p)
            start = time.time()
            api_key = get_api_key_for_player(p)
            try:
                talk_result = ai_client.decide_talk(p, {"state": self.to_dict()}, talks, api_key)
            except TypeError:
                try:
                    talk_result = ai_client.decide_talk(p, {"state": self.to_dict()}, talks)
                except Exception:
                    talk_result = {"speech": f"{p} has nothing to add.", "meta": {"heuristic": True}}
            except Exception:
                talk_result = {"speech": f"{p} has nothing to add.", "meta": {"heuristic": True}}
            latency = time.time() - start
            if isinstance(talk_result, dict):
                speech = talk_result.get("speech") or ""
                meta = talk_result.get("meta") or {}
            else:
                speech = str(talk_result)
                meta = {}
            talks.append({"player": p, "speech": speech, "meta": meta, "model": model_used, "latency": latency})
        self.current_talks = talks

    def _run_voting(self):
        """Run voting round using self.current_talks as context and populate current_votes/current_votes_meta."""
        votes: Dict[str, int] = {}
        votes_meta: List[Dict[str, Any]] = []
        for p in list(self.alive):
            model_used = self._get_model_name(p)
            start = time.time()
            api_key = get_api_key_for_player(p)
            try:
                vote = ai_client.decide_vote(p, {"state": self.to_dict(), "talk_history": self.current_talks}, api_key)
            except TypeError:
                try:
                    vote = ai_client.decide_vote(p, {"state": self.to_dict(), "talk_history": self.current_talks})
                except Exception:
                    vote = ai_client.decide_vote(p, {"state": self.to_dict()})
            except Exception:
                vote = random.choice(list(self.alive))
            latency = time.time() - start
            if vote not in self.alive:
                vote = random.choice(list(self.alive))
            votes.setdefault(vote, 0)
            votes[vote] += 1
            votes_meta.append({"voter": p, "vote": vote, "model": model_used, "latency": latency})
        self.current_votes = votes
        self.current_votes_meta = votes_meta

    def _finalize_vote(self):
        """Tally current_votes, remove lynched if any, and append day history entry."""
        lynched = None
        if self.current_votes:
            max_votes = max(self.current_votes.values())
            top = [name for name, v in self.current_votes.items() if v == max_votes]
            lynched = random.choice(top)
            if lynched in self.alive:
                # if lynched player is idiot, they reveal but do not die
                if self.roles.get(lynched) == "idiot":
                    # mark idiot revealed in model state if available
                    if self.gs and hasattr(self.gs, "get_player"):
                        try:
                            p = self.gs.get_player(lynched)  # type: ignore[attr-defined]
                            if p:
                                p.idiot_revealed = True
                                # record event
                                self.history.append({"phase": "day", "day": self.day, "idiot_revealed": lynched})
                        except Exception:
                            pass
                    # do not kill the idiot; they lose voting rights (handled by idiot_revealed flag)
                else:
                    self._mark_dead(lynched, "vote")
        # record day with talks and votes metadata
        self.history.append({
            "phase": "day",
            "day": self.day,
            "lynched": lynched,
            "votes": dict(self.current_votes),
            "votes_meta": list(self.current_votes_meta),
            "talks": list(self.current_talks),
        })

    def day_phase(self):
        """
        Day phase runs discussion then voting, using helper methods to keep logic testable.
        """
        self.state = "day"
        self._reset_day_buffers()
        self._run_discussion()
        self._run_voting()
        self._finalize_vote()

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
    """
    Create a new room, but enforce a single active room policy:
      - If any existing room is in 'waiting' or 'running' state, return its id instead of creating a new one.
      - Only allow creation when no active (non-ended) room exists.
    This keeps frontend logic simple: there is at most one room to show at any time.
    """
    with rooms_lock:
        # If an active (non-ended) room exists, return it
        for rid, r in rooms.items():
            if r.get("state") and r.get("state") != "ended":
                return rid
        # Otherwise create a fresh room
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

# Resolve per-player API key using /config/api_keys providers and /config/players.player_map
def get_api_key_for_player(player: str) -> Optional[str]:
    """
    Resolve an API key for a given player:
      - read api keys file at API_KEYS_PATH; expected shape: { "providers": { name: { "api_key": "...", ... } }, ... }
      - read players config at PLAYERS_CONFIG_PATH; expected shape includes "player_map": { player: providerName }
      - if mapping exists and provider contains api_key, return it
      - otherwise return the first provider api_key if any, else fallback to global API_KEY
    """
    try:
        api_cfg = _read_json_file(API_KEYS_PATH) or {}
        # normalize providers object
        providers = {}
        if isinstance(api_cfg, dict):
            providers = api_cfg.get("providers") or {k: v for k, v in api_cfg.items() if isinstance(v, dict)}
        # players mapping
        players_cfg = _read_json_file(PLAYERS_CONFIG_PATH) or {}
        player_map = players_cfg.get("player_map", {}) if isinstance(players_cfg, dict) else {}

        provider_name = player_map.get(player)
        if provider_name and isinstance(providers, dict) and providers.get(provider_name):
            prov = providers.get(provider_name) or {}
            return prov.get("api_key") or prov.get("key") or prov.get("secret")
        # fallback: use first provider api_key if present
        if isinstance(providers, dict) and len(providers) > 0:
            first = next(iter(providers.values()))
            return first.get("api_key") or first.get("key") or first.get("secret")
    except Exception:
        pass
    # final fallback: legacy single-key in api_keys.json or env
    try:
        api_cfg = _read_json_file(API_KEYS_PATH) or {}
        if isinstance(api_cfg, dict):
            for k in ("OPENAI_API_KEY", "openai", "api_key", "apiKey"):
                if k in api_cfg:
                    return api_cfg[k]
    except Exception:
        pass
    return API_KEY or None

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
    # return both created room id and initial room state for convenience (201 Created)
    return jsonify({"room_id": rid, "room": get_room_state(rid)}), 201

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
                # apply preferences: for any player with a preferred role, sync role assignment across structures
                for p, pref in prefs.items():
                    if p in g.players and pref in ROLES:
                        g.set_player_role(p, pref)
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