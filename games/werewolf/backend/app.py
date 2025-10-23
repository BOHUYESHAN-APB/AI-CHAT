from flask import Flask, request, jsonify
import os
import json
import random
import threading
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, "..", "..", ".."))

# Simple Werewolf game server (AI-driven players). Reads API key from project root.

def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    search_roots = [os.getcwd()]
    if PROJECT_ROOT not in search_roots:
        search_roots.append(PROJECT_ROOT)
    for root in search_roots:
        f1 = os.path.join(root, "api_key")
        if os.path.exists(f1):
            try:
                with open(f1, "r", encoding="utf-8") as fh:
                    return fh.read().strip()
            except Exception:
                continue
        f2 = os.path.join(root, "api_keys.json")
        if os.path.exists(f2):
            try:
                with open(f2, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for k in ("OPENAI_API_KEY", "openai", "api_key", "apiKey"):
                    if k in data:
                        return data[k]
            except Exception:
                pass
        f3 = os.path.join(root, "api_keys.example.json")
        if os.path.exists(f3):
            try:
                with open(f3, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
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
        self.role_metadata: Dict[str, Dict[str, Any]] = {}
        self.seer_reveals: Dict[str, List[Dict[str, Any]]] = {}
        self.witch_action_log: Dict[str, List[Dict[str, Any]]] = {}
        self.werewolf_discussion_log: List[Dict[str, Any]] = []
        self.day_discussion_rounds: int = 2
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
        self._refresh_role_metadata()
        self.seer_reveals = {p: [] for p in self.players if self.roles.get(p) == "seer"}
        self.witch_action_log = {p: [] for p in self.players if self.roles.get(p) == "witch"}

    def _refresh_role_metadata(self):
        """Recompute per-player role metadata used for context building."""
        metadata: Dict[str, Dict[str, Any]] = {}
        werewolves = [p for p in self.players if self.roles.get(p) == "werewolf"]
        for player in self.players:
            role = self.roles.get(player)
            meta: Dict[str, Any] = {}
            if role == "werewolf":
                meta["teammates"] = [w for w in werewolves if w != player]
            if role == "witch":
                meta["save_available"] = self.witch_save_available
                meta["poison_available"] = self.witch_poison_available
            metadata[player] = meta
        self.role_metadata = metadata

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
            "roles": self.roles,  # 前端组件需要这个字段名
            "roles_known_to_server": self.roles,  # 保持向后兼容
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
            # debug log
            print(f"[DEBUG] check_win -> no wolves alive. alive={list(self.alive)}, roles={self.roles}")
            return "villagers"
        if len(wolves) >= len(villagers):
            print(f"[DEBUG] check_win -> wolves >= villagers. wolves={wolves}, villagers={villagers}, roles={self.roles}")
            return "werewolves"
        return None

    def _role_monologue(self, player: str, role: str, action_result: Any) -> Dict[str, Any]:
        """
        生成职业角色的夜间独白/思考
        player: 玩家名
        role: 职业
        action_result: 行动结果（如预言家查验结果、女巫目标等）
        """
        model_used = self._get_model_name(player)
        creds = resolve_player_credentials(player)
        provider_name = creds.get("provider")
        api_token = provider_name or creds.get("api_key")
        start = time.time()
        
        # 构建独白提示
        context_desc = ""
        if role == "seer" and action_result:
            target = action_result.get("target")
            revealed = action_result.get("revealed_role", "unknown")
            context_desc = f"我查验了 {target}，发现他是 {revealed}"
        elif role == "witch":
            if action_result and action_result.get("result") == "saved":
                context_desc = f"我使用解药救了 {action_result.get('target')}"
            elif action_result and action_result.get("result") == "poisoned":
                context_desc = f"我使用毒药杀死了 {action_result.get('target')}"
            else:
                context_desc = "今晚我没有使用药水"
        elif role == "guard" and action_result:
            context_desc = f"我守护了 {action_result.get('target')}"
        else:
            context_desc = "今晚我执行了我的职业行动"
        
        # 生成简短独白
        speech = f"[{role}的思考] {context_desc}。"
        
        # 尝试调用AI生成更丰富的独白
        try:
            prompt_context = {
                "role": role,
                "state": self.to_dict(),
                "action_context": context_desc
            }
            prompt_context.update(
                {
                    "provider": provider_name,
                    "provider_model": (creds.get("provider_config") or {}).get("model"),
                    "provider_url": (creds.get("provider_config") or {}).get("model_url"),
                }
            )
            talk_result = ai_client.decide_talk(player, prompt_context, [], api_token)
            if isinstance(talk_result, dict) and talk_result.get("speech"):
                speech = f"[{role}独白] " + talk_result["speech"][:100]  # 限制长度
        except:
            pass  # 使用默认 speech
        
        latency = time.time() - start
        return {
            "player": player,
            "role": role,
            "speech": speech,
            "type": "monologue",
            "meta": {"heuristic": False, "provider": provider_name},
            "model": model_used,
            "latency": latency
        }

    def night_phase(self):
        """Night resolution aligning with reference logic."""
        self.state = "night"
        self.day += 1
        self._refresh_role_metadata()
        self.werewolf_discussion_log = []

        werewolf_outcome = self._resolve_werewolf_night()
        seer_outcome = self._resolve_seer_night()
        witch_outcome = self._resolve_witch_night(werewolf_outcome.get("target"))

        killed_players: List[str] = []
        saved_player = witch_outcome.get("saved_player")
        poisoned_player = witch_outcome.get("poisoned_player")
        final_wolf_target = werewolf_outcome.get("target")

        if final_wolf_target and final_wolf_target in self.alive and final_wolf_target != saved_player:
            killed_players.append(final_wolf_target)
        if poisoned_player and poisoned_player in self.alive:
            killed_players.append(poisoned_player)
        # remove duplicates while preserving order
        killed_players = list(dict.fromkeys(killed_players))

        night_talks: List[Dict[str, Any]] = list(self.werewolf_discussion_log)

        if seer_outcome.get("actor") and seer_outcome.get("actor") in self.alive:
            night_talks.append(
                self._role_monologue(
                    seer_outcome["actor"],
                    self.roles.get(seer_outcome["actor"], "seer"),
                    {"target": seer_outcome.get("target"), "revealed_role": seer_outcome.get("revealed_role")},
                )
            )

        if witch_outcome.get("actor") and witch_outcome.get("actor") in self.alive:
            witch_actor = witch_outcome["actor"]
            if witch_outcome.get("saved_player"):
                action_context = {"result": "saved", "target": witch_outcome.get("saved_player")}
            elif witch_outcome.get("poisoned_player"):
                action_context = {"result": "poisoned", "target": witch_outcome.get("poisoned_player")}
            else:
                action_context = {"result": "none"}
            night_talks.append(
                self._role_monologue(
                    witch_actor,
                    self.roles.get(witch_actor, "witch"),
                    action_context,
                )
            )

        for victim in killed_players:
            cause = "night"
            if victim == poisoned_player:
                cause = "witch_poison"
            self._mark_dead(victim, cause)

        announcement = {
            "werewolf_target": final_wolf_target,
            "killed": killed_players,
            "saved": saved_player if saved_player else None,
            "poisoned": poisoned_player if poisoned_player else None,
        }

        actions: List[Dict[str, Any]] = []
        actions.extend(werewolf_outcome.get("actions", []))
        if seer_outcome.get("actor"):
            actions.append(
                {
                    "actor": seer_outcome["actor"],
                    "action": "seer_reveal",
                    "target": seer_outcome.get("target"),
                    "revealed_role": seer_outcome.get("revealed_role"),
                    "meta": seer_outcome.get("meta"),
                }
            )
        actions.extend(witch_outcome.get("actions", []))

        night_event = {
            "phase": "night",
            "day": self.day,
            "killed": killed_players[0] if killed_players else None,
            "killed_players": killed_players,
            "actions": actions,
            "night_talks": night_talks,
            "announcement": announcement,
            "werewolf_choices": [entry.get("target") for entry in werewolf_outcome.get("actions", []) if entry.get("target")],
            "witch_save_available": self.witch_save_available,
            "witch_poison_available": self.witch_poison_available,
            "guard_last_protected": dict(self.guard_last_protected),
            "werewolf": werewolf_outcome,
            "seer": seer_outcome,
            "witch": witch_outcome,
        }

        self.last_night_result = night_event
        self.morning_announcement = announcement
        self.history.append(night_event)
        self._refresh_role_metadata()
        self._check_and_finalize_winner()

    def _call_ai_function(
        self,
        func_type: str,
        player: str,
        context: Dict[str, Any],
        fallback=None,
        talk_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        model_used = self._get_model_name(player)
        creds = resolve_player_credentials(player)
        provider_name = creds.get("provider")
        api_token = creds.get("api_key") or API_KEY
        if not api_token and provider_name:
            api_token = provider_name
        provider_cfg = creds.get("provider_config") or {}
        token = api_token or ""
        start = time.time()
        raw_result: Any = None
        try:
            if func_type == "talk":
                raw_result = ai_client.decide_talk(player, context, talk_history or [], token)
            elif func_type == "action":
                raw_result = ai_client.decide_night_action(player, context, token)
            elif func_type == "vote":
                raw_result = ai_client.decide_vote(player, context, token)
            else:
                raise ValueError(f"Unknown func_type: {func_type}")
        except TypeError:
            try:
                if func_type == "talk":
                    raw_result = ai_client.decide_talk(player, context, talk_history or [])
                elif func_type == "action":
                    raw_result = ai_client.decide_night_action(player, context)
                elif func_type == "vote":
                    raw_result = ai_client.decide_vote(player, context)
            except Exception:
                raw_result = None
        except Exception:
            raw_result = None

        latency = time.time() - start
        meta: Dict[str, Any] = {
            "model": model_used,
            "provider": provider_name,
            "latency": latency,
        }
        if provider_cfg.get("model"):
            meta["provider_model"] = provider_cfg.get("model")
        if provider_cfg.get("model_url"):
            meta["provider_url"] = provider_cfg.get("model_url")

        if raw_result is None and callable(fallback):
            raw_result = fallback()
            meta["heuristic"] = True

        return raw_result, meta

    def _normalize_speech(self, raw: Any, default_text: str) -> Tuple[str, Dict[str, Any]]:
        if isinstance(raw, dict):
            speech = raw.get("speech") or default_text
            meta = raw.get("meta") or {}
        elif isinstance(raw, str):
            speech = raw
            meta = {}
        else:
            speech = default_text
            meta = {"heuristic": True}
        return speech, meta

    def _normalize_target(self, raw: Any) -> Optional[str]:
        if isinstance(raw, dict):
            for key in ("target", "vote_target", "choice", "decision"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _normalize_vote_choice(self, raw: Any) -> Optional[str]:
        if isinstance(raw, dict):
            for key in ("vote", "vote_target", "target", "choice", "decision"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return None

    def _build_player_context(self, player: str, phase: str, extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "phase": phase,
            "day": self.day,
            "player": player,
            "your_role": self.roles.get(player),
            "players": list(self.players),
            "alive_players": sorted(self.alive),
            "role_info": self.role_metadata.get(player, {}),
            "history": self._get_visible_history_for(player),
            "morning_announcement": self.morning_announcement,
        }
        if extras:
            context.update(extras)
        return context

    def _get_visible_history_for(self, player: str) -> List[Dict[str, Any]]:
        role = self.roles.get(player)
        visible: List[Dict[str, Any]] = []
        for event in self.history[-8:]:
            phase = event.get("phase")
            entry: Dict[str, Any] = {"phase": phase, "day": event.get("day")}
            if phase == "night":
                entry["announcement"] = event.get("announcement")
                if role == "werewolf" and event.get("werewolf"):
                    entry["werewolf"] = {
                        "target": event["werewolf"].get("target"),
                        "votes": event["werewolf"].get("votes"),
                    }
                if role == "seer" and event.get("seer") and event["seer"].get("actor") == player:
                    entry["seer"] = {
                        "target": event["seer"].get("target"),
                        "revealed_role": event["seer"].get("revealed_role"),
                    }
                if role == "witch" and event.get("witch") and event["witch"].get("actor") == player:
                    entry["witch"] = {
                        "saved_player": event["witch"].get("saved_player"),
                        "poisoned_player": event["witch"].get("poisoned_player"),
                    }
            elif phase == "day":
                entry["talks"] = event.get("talks") or event.get("speeches")
                entry["votes"] = event.get("votes")
                entry["lynched"] = event.get("lynched")
                entry["announcement"] = event.get("announcement")
            elif phase == "end":
                entry["winner"] = event.get("winner")
            visible.append(entry)
        return visible

    def _resolve_werewolf_night(self) -> Dict[str, Any]:
        wolves = [p for p in self.alive if self.roles.get(p) == "werewolf"]
        if not wolves:
            self._werewolf_choices = []
            self.werewolf_discussion_log = []
            return {"target": None, "actions": [], "votes": {}, "discussions": []}

        discussions: List[Dict[str, Any]] = []
        action_logs: List[Dict[str, Any]] = []
        kill_votes: Dict[str, int] = {}

        for round_index in range(1, 4):
            for wolf in wolves:
                fallback_text = f"{wolf} 暂无明确目标，继续讨论。"
                fallback_payload = {"speech": fallback_text, "meta": {"heuristic": True}}
                context = self._build_player_context(
                    wolf,
                    "werewolf_discussion",
                    {
                        "round": round_index,
                        "previous_discussions": list(discussions),
                        "teammates": [w for w in wolves if w != wolf],
                        "alive_players": sorted(self.alive),
                    },
                )
                raw, meta = self._call_ai_function("talk", wolf, context, fallback=lambda: fallback_payload, talk_history=discussions)
                speech, speech_meta = self._normalize_speech(raw, fallback_text)
                if meta.get("heuristic"):
                    speech_meta["heuristic"] = True
                speech_meta.setdefault("provider", meta.get("provider"))
                discussions.append(
                    {
                        "player": wolf,
                        "round": round_index,
                        "speech": speech,
                        "meta": speech_meta,
                        "model": meta.get("model"),
                        "provider": meta.get("provider"),
                        "latency": meta.get("latency"),
                    }
                )

        self.werewolf_discussion_log = list(discussions)

        for wolf in wolves:
            fallback_choice = self._random_vote_choice(wolf, sorted(self.alive), allow_self=False, exclude=wolves)
            context = self._build_player_context(
                wolf,
                "werewolf_kill",
                {
                    "previous_discussions": list(discussions),
                    "teammates": [w for w in wolves if w != wolf],
                    "alive_players": sorted(self.alive),
                    "default_choice": fallback_choice,
                },
            )
            raw, meta = self._call_ai_function("action", wolf, context, fallback=lambda: {"target": fallback_choice} if fallback_choice else {"target": None})
            target = self._normalize_target(raw)
            if target and target in self.alive and target not in wolves:
                kill_votes[target] = kill_votes.get(target, 0) + 1
            action_logs.append({"actor": wolf, "action": "werewolf_vote", "target": target, "meta": meta})

        chosen_target: Optional[str] = None
        if kill_votes:
            max_votes = max(kill_votes.values())
            top_targets = [name for name, count in kill_votes.items() if count == max_votes]
            candidates = [p for p in top_targets if p in self.alive and p not in wolves]
            pool = candidates or [p for p in kill_votes if p in self.alive]
            if pool:
                chosen_target = random.choice(pool)
        if not chosen_target:
            non_wolf_players = [p for p in self.alive if p not in wolves]
            if non_wolf_players:
                chosen_target = random.choice(non_wolf_players)

        self._werewolf_choices = [entry.get("target") for entry in action_logs if entry.get("target")]

        return {
            "target": chosen_target,
            "votes": kill_votes,
            "actions": action_logs,
            "discussions": discussions,
        }

    def _resolve_seer_night(self) -> Dict[str, Any]:
        seer = next((p for p in self.alive if self.roles.get(p) == "seer"), None)
        if not seer:
            return {"actor": None, "target": None, "revealed_role": None, "meta": {}}

        available_targets = [p for p in self.alive if p != seer]
        context = self._build_player_context(
            seer,
            "seer_reveal",
            {
                "available_targets": available_targets,
                "seer_reveals": list(self.seer_reveals.get(seer, [])),
            },
        )

        def _fallback():
            if not available_targets:
                return {"target": None}
            return {"target": random.choice(available_targets)}

        raw, meta = self._call_ai_function("action", seer, context, fallback=_fallback)
        target = self._normalize_target(raw)
        if not target or target == seer or target not in self.players:
            target = None
        revealed_role = self.roles.get(target) if target else None
        if target:
            record = {"day": self.day, "target": target, "role": revealed_role}
            self.seer_reveals.setdefault(seer, []).append(record)
        return {"actor": seer, "target": target, "revealed_role": revealed_role, "meta": meta}

    def _resolve_witch_night(self, pending_target: Optional[str]) -> Dict[str, Any]:
        witch = next((p for p in self.alive if self.roles.get(p) == "witch"), None)
        actions: List[Dict[str, Any]] = []
        if not witch:
            return {"actor": None, "saved_player": None, "poisoned_player": None, "actions": actions, "meta": {}}

        available_targets = [p for p in self.alive if p != witch]
        context = self._build_player_context(
            witch,
            "witch_action",
            {
                "available_targets": available_targets,
                "werewolf_target": pending_target,
                "save_available": self.witch_save_available,
                "poison_available": self.witch_poison_available,
                "witch_actions": list(self.witch_action_log.get(witch, [])),
            },
        )

        raw, meta = self._call_ai_function("action", witch, context, fallback=lambda: {"decision": "none"})

        save_candidate: Optional[str] = None
        poison_candidate: Optional[str] = None

        if isinstance(raw, dict):
            save_candidate = raw.get("save_target")
            if raw.get("decision") == "save" and not save_candidate:
                save_candidate = pending_target
            poison_candidate = raw.get("poison_target")
            if raw.get("decision") == "poison" and not poison_candidate:
                choices = [p for p in available_targets if p != pending_target]
                if choices:
                    poison_candidate = random.choice(choices)
        elif isinstance(raw, str):
            lowered = raw.lower()
            if "save" in lowered and pending_target:
                save_candidate = pending_target
            if "poison" in lowered:
                for name in available_targets:
                    if name.lower() in lowered and name != pending_target:
                        poison_candidate = name
                        break

        saved_player: Optional[str] = None
        poisoned_player: Optional[str] = None

        if save_candidate and save_candidate == pending_target and self.witch_save_available:
            saved_player = save_candidate
            self.witch_save_available = False
            actions.append({"actor": witch, "action": "witch_save", "target": saved_player, "result": "saved", "meta": meta})
            self.witch_action_log.setdefault(witch, []).append({"day": self.day, "action": "save", "target": saved_player})

        if poison_candidate and poison_candidate in self.alive and poison_candidate != witch and self.witch_poison_available:
            poisoned_player = poison_candidate
            self.witch_poison_available = False
            actions.append({"actor": witch, "action": "witch_poison", "target": poisoned_player, "result": "poisoned", "meta": meta})
            self.witch_action_log.setdefault(witch, []).append({"day": self.day, "action": "poison", "target": poisoned_player})

        self._refresh_role_metadata()
        return {
            "actor": witch,
            "saved_player": saved_player,
            "poisoned_player": poisoned_player,
            "actions": actions,
            "meta": meta,
        }

    def _random_vote_choice(
        self,
        voter: str,
        alive_list: List[str],
        allow_self: bool = False,
        exclude: Optional[List[str]] = None,
    ) -> Optional[str]:
        exclude = exclude or []
        options = [p for p in alive_list if (allow_self or p != voter) and p not in exclude]
        if options:
            return random.choice(options)
        return None

    def _run_discussion(self, rounds: int = 2) -> List[Dict[str, Any]]:
        talks: List[Dict[str, Any]] = []
        for round_index in range(1, rounds + 1):
            for player in self.players:
                if player not in self.alive:
                    continue
                fallback_text = f"{player} 暂时没有明确的看法，继续观察。"
                fallback_payload = {"speech": fallback_text, "meta": {"heuristic": True}}
                context = self._build_player_context(
                    player,
                    "day_discussion",
                    {
                        "round": round_index,
                        "previous_speeches": list(talks),
                    },
                )
                raw, meta = self._call_ai_function("talk", player, context, fallback=lambda: fallback_payload, talk_history=talks)
                speech, speech_meta = self._normalize_speech(raw, fallback_text)
                if meta.get("heuristic"):
                    speech_meta["heuristic"] = True
                speech_meta.setdefault("provider", meta.get("provider"))
                talks.append(
                    {
                        "player": player,
                        "round": round_index,
                        "speech": speech,
                        "meta": speech_meta,
                        "model": meta.get("model"),
                        "provider": meta.get("provider"),
                        "latency": meta.get("latency"),
                    }
                )
        self.current_talks = talks
        return talks

    def _run_voting(self, speech_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        alive_list = sorted(self.alive)
        votes_meta: List[Dict[str, Any]] = []
        tally: Dict[str, int] = {}

        for voter in alive_list:
            fallback_choice = self._random_vote_choice(voter, alive_list)
            context = self._build_player_context(
                voter,
                "day_voting",
                {
                    "previous_speeches": list(speech_history),
                    "vote_options": alive_list + ["abstain"],
                    "default_choice": fallback_choice,
                },
            )
            raw, meta = self._call_ai_function("vote", voter, context, fallback=lambda: {"vote_target": fallback_choice or "abstain"})
            choice = self._normalize_vote_choice(raw)
            if not choice:
                choice = fallback_choice or "abstain"
            choice = choice.strip()
            if choice not in alive_list and choice.lower() != "abstain":
                choice = fallback_choice or "abstain"
            tally.setdefault(choice, 0)
            tally[choice] += 1
            vote_meta = {
                "voter": voter,
                "vote": choice,
                "model": meta.get("model"),
                "provider": meta.get("provider"),
                "latency": meta.get("latency"),
            }
            if meta.get("heuristic"):
                vote_meta["heuristic"] = True
            votes_meta.append(vote_meta)

        self.current_votes = tally
        self.current_votes_meta = votes_meta

        non_abstain_votes = {k: v for k, v in tally.items() if k.lower() != "abstain"}
        lynched: Optional[str] = None
        if non_abstain_votes:
            max_votes = max(non_abstain_votes.values())
            if max_votes > len(alive_list) / 2:
                top_targets = [name for name, count in non_abstain_votes.items() if count == max_votes]
                if len(top_targets) == 1:
                    lynched = top_targets[0]

        return {"lynched": lynched, "tally": tally, "votes_meta": votes_meta}

    def _finalize_vote(self, voting_result: Optional[Dict[str, Any]] = None) -> Optional[str]:
        lynched = None
        if voting_result is not None:
            lynched = voting_result.get("lynched")
        elif self.current_votes:
            non_abstain = {k: v for k, v in self.current_votes.items() if isinstance(k, str) and k.lower() != "abstain"}
            if non_abstain:
                max_votes = max(non_abstain.values())
                top = [name for name, count in non_abstain.items() if count == max_votes]
                if len(top) == 1:
                    lynched = top[0]
        if lynched and lynched in self.alive:
            if self.roles.get(lynched) == "idiot":
                if self.gs and hasattr(self.gs, "get_player"):
                    try:
                        player_obj = self.gs.get_player(lynched)  # type: ignore[attr-defined]
                        if player_obj:
                            player_obj.idiot_revealed = True
                    except Exception:
                        pass
                self.history.append({"phase": "day", "day": self.day, "idiot_revealed": lynched})
                return None
            self._mark_dead(lynched, "vote")
        return lynched

    def day_phase(self):
        """执行白天阶段：公告 -> 多轮发言 -> 投票 -> 结算。"""
        self.state = "day"
        self._reset_day_buffers()
        speeches = self._run_discussion(self.day_discussion_rounds)
        voting_result = self._run_voting(speeches)
        lynched = self._finalize_vote(voting_result)
        day_event = {
            "phase": "day",
            "day": self.day,
            "lynched": lynched,
            "votes": dict(self.current_votes),
            "votes_meta": list(self.current_votes_meta),
            "talks": list(self.current_talks),
            "speeches": list(self.current_talks),
            "announcement": self.morning_announcement,
        }
        self.history.append(day_event)
        self._check_and_finalize_winner()

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
_AUTO_THREADS: Dict[str, threading.Thread] = {}
_AUTO_STOP_FLAGS: Dict[str, threading.Event] = {}
AUTO_STEP_DELAY = float(os.getenv("WEREWOLF_AUTO_STEP_DELAY", "1.5"))


def _auto_runner_active(room_id: str) -> bool:
    thread = _AUTO_THREADS.get(room_id)
    return bool(thread and thread.is_alive())


def _stop_auto_runner(room_id: str):
    flag = _AUTO_STOP_FLAGS.get(room_id)
    if flag:
        flag.set()


def _auto_run_room(room_id: str, stop_flag: threading.Event):
    while not stop_flag.is_set():
        with rooms_lock:
            r = rooms.get(room_id)
            if not r:
                break
            game: Optional[Game] = r.get("game")
            state = r.get("state")
        if not game or state != "running":
            break
        try:
            game.step()
            with rooms_lock:
                r = rooms.get(room_id)
                if r:
                    r["last_step"] = time.time()
                    if getattr(game, "state", None) == "ended":
                        r["state"] = "ended"
                        stop_flag.set()
                        break
        except Exception as exc:
            print(f"[ERROR] auto_run_room room={room_id} exception: {exc}")
            stop_flag.set()
            break
        stop_flag.wait(AUTO_STEP_DELAY)


def _ensure_auto_runner(room_id: str):
    if _auto_runner_active(room_id):
        return
    stop_flag = threading.Event()
    _AUTO_STOP_FLAGS[room_id] = stop_flag
    thread = threading.Thread(target=_auto_run_room, args=(room_id, stop_flag), daemon=True)
    _AUTO_THREADS[room_id] = thread
    thread.start()

def create_room(owner: str, max_players: int = 6) -> str:
    """
    Create a new room, but enforce a single active room policy:
      - If any existing room is in 'waiting' or 'running' state, return its id instead of creating a new one.
      - Only allow creation when no active (non-ended) room exists.
    Invoke-WebRequest -Uri "http://127.0.0.1:8080/rooms/<roomId>/state" -Method GET -UseBasicParsing | Select-Object -ExpandProperty Content    Invoke-WebRequest -Uri "http://127.0.0.1:8080/rooms/<roomId>/state" -Method GET -UseBasicParsing | Select-Object -ExpandProperty Content      - Clean up old 'ended' rooms to prevent accumulation.
    This keeps frontend logic simple: there is at most one room to show at any time.
    """
    with rooms_lock:
        # Clean up old ended rooms first (keep only most recent ended room for history)
        ended_rooms = [(rid, r) for rid, r in rooms.items() if r.get("state") == "ended"]
        if len(ended_rooms) > 1:
            # sort by created_at descending, keep newest, remove rest
            ended_rooms.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
            for rid, _ in ended_rooms[1:]:
                print(f"[DEBUG] create_room cleanup: deleting old ended room {rid}")
                _stop_auto_runner(rid)
                _AUTO_THREADS.pop(rid, None)
                _AUTO_STOP_FLAGS.pop(rid, None)
                del rooms[rid]
        
        # If an active (non-ended) room exists, return it
        for rid, r in rooms.items():
            state = r.get("state")
            if state and state != "ended":
                # Ensure owner is in players list (防止空列表导致房间被删除)
                if owner not in r["players"]:
                    r["players"].append(owner)
                return rid
        
        # Otherwise create a fresh room (清理所有ended房间,只保留新房间)
        # Remove all ended rooms when creating new one
        for rid in list(rooms.keys()):
            if rooms[rid].get("state") == "ended":
                print(f"[DEBUG] create_room removing ended room during new create: {rid}")
                _stop_auto_runner(rid)
                _AUTO_THREADS.pop(rid, None)
                _AUTO_STOP_FLAGS.pop(rid, None)
                del rooms[rid]
        
        rid = str(uuid.uuid4())[:8]
        rooms[rid] = {
            "id": rid,
            "owner": owner,
            "players": [owner],
            "max_players": max_players,
            "game": None,
            "created_at": time.time(),
            "last_step": 0,
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
            # 改进: 不立即删除空房间,而是标记为可清理状态
            # 这样前端切换标签时不会突然看不到房间
            if not r["players"] and r["state"] == "waiting":
                # 只在waiting状态且无玩家时才删除,running/ended状态保留以便查看
                print(f"[DEBUG] leave_room: deleting empty waiting room {room_id} because last player left")
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
        
        # 读取玩家配置文件，使用配置的AI玩家列表
        cfg = _read_json_file(PLAYERS_CONFIG_PATH) or {}
        configured_players = cfg.get("players", []) if isinstance(cfg, dict) else []
        
        # 如果有配置玩家，使用配置；否则使用房间玩家列表或默认AI玩家
        if configured_players and len(configured_players) >= 6:
            players = configured_players[:12]  # 最多12人
        elif len(r["players"]) >= 6:
            players = list(r["players"])
        else:
            # 默认创建6个AI玩家
            players = [f"AI_{i}" for i in range(1, 7)]
        
        # 创建游戏实例
        g = Game(players)
        
        # 应用角色偏好配置
        if cfg and isinstance(cfg, dict):
            prefs = cfg.get("role_preferences", {})
            for player, pref in prefs.items():
                if player in players and pref in ROLES:
                    g.set_player_role(player, pref)
        
        _stop_auto_runner(room_id)
        _AUTO_THREADS.pop(room_id, None)
        _AUTO_STOP_FLAGS.pop(room_id, None)

        r["game"] = g
        r["players"] = players  # 更新房间玩家列表为游戏玩家
        r["state"] = "running"
        _ensure_auto_runner(room_id)
        return None

def _get_room_state_unsafe(room_id: str) -> Optional[Dict[str, Any]]:
    """Internal helper: get room state WITHOUT acquiring lock (caller must hold lock)"""
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

def get_room_state(room_id: str) -> Optional[Dict[str, Any]]:
    """Public API: get room state WITH lock"""
    with rooms_lock:
        return _get_room_state_unsafe(room_id)

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

# Determine project root relative to this backend module so file reads work
API_KEYS_PATH = os.path.join(PROJECT_ROOT, "api_keys.json")
PLAYERS_CONFIG_PATH = os.path.join(PROJECT_ROOT, "games", "werewolf", "config.json")

def resolve_player_credentials(player: str) -> Dict[str, Any]:
    """Return a structured credential bundle for the given player."""
    providers: Dict[str, Dict[str, Any]] = {}
    provider_name: Optional[str] = None
    provider_entry: Optional[Dict[str, Any]] = None
    api_key_value: Optional[str] = None

    try:
        api_cfg = _read_json_file(API_KEYS_PATH) or {}
        if isinstance(api_cfg, dict):
            raw_providers = api_cfg.get("providers")
            if isinstance(raw_providers, dict):
                providers = {k: v for k, v in raw_providers.items() if isinstance(v, dict)}
            if not providers:
                providers = {k: v for k, v in api_cfg.items() if isinstance(v, dict) and (
                    "api_key" in v or "key" in v or "secret" in v
                )}
        players_cfg = _read_json_file(PLAYERS_CONFIG_PATH) or {}
        player_map = players_cfg.get("player_map", {}) if isinstance(players_cfg, dict) else {}

        provider_name = player_map.get(player)
        if provider_name and providers.get(provider_name):
            provider_entry = providers.get(provider_name)
        elif providers:
            provider_name, provider_entry = next(iter(providers.items()))

        if provider_entry:
            api_key_value = provider_entry.get("api_key") or provider_entry.get("key") or provider_entry.get("secret")
    except Exception:
        providers = {}

    if not api_key_value:
        try:
            api_cfg = _read_json_file(API_KEYS_PATH) or {}
            if isinstance(api_cfg, dict):
                for k in ("OPENAI_API_KEY", "openai", "api_key", "apiKey"):
                    val = api_cfg.get(k)
                    if isinstance(val, str) and val:
                        api_key_value = val
                        break
        except Exception:
            pass

    if not api_key_value:
        api_key_value = API_KEY or None

    return {
        "api_key": api_key_value,
        "provider": provider_name,
        "provider_config": provider_entry,
        "providers": providers,
    }

# Resolve per-player API key using /config/api_keys providers and /config/players.player_map
def get_api_key_for_player(player: str) -> Optional[str]:
    """
    Resolve an API key for a given player:
      - read api keys file at API_KEYS_PATH; expected shape: { "providers": { name: { "api_key": "...", ... } }, ... }
      - read players config at PLAYERS_CONFIG_PATH; expected shape includes "player_map": { player: providerName }
      - if mapping exists and provider contains api_key, return it
      - otherwise return the first provider api_key if any, else fallback to global API_KEY
    """
    creds = resolve_player_credentials(player)
    return creds.get("api_key")

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


@app.route("/config/api_keys/test", methods=["GET"])
def api_keys_test():
    """
    Test connectivity for a provider entry in api_keys.json
    Query params:
      provider=<name>
    Returns simple reachability check to provider.model_url (if present) and whether api_key exists.
    """
    provider_name = request.args.get("provider")
    if not provider_name:
        return jsonify({"ok": False, "error": "provider parameter required"}), 400
    data = _read_json_file(API_KEYS_PATH) or {}
    providers = {}
    if isinstance(data, dict):
        providers = data.get("providers") or {k: v for k, v in data.items() if isinstance(v, dict)}
    prov = providers.get(provider_name)
    if not prov:
        return jsonify({"ok": False, "error": "provider_not_found"}), 404

    model_url = prov.get("model_url") or prov.get("url") or prov.get("endpoint")
    has_key = bool(prov.get("api_key") or prov.get("key") or prov.get("secret"))

    # Try a simple HTTP HEAD/GET to the model_url to check reachability
    reachable = None
    if model_url:
        try:
            import urllib.request
            req = urllib.request.Request(model_url, method="GET")
            # don't hang long
            with urllib.request.urlopen(req, timeout=5) as resp:
                reachable = True
        except Exception as e:
            reachable = False
    else:
        reachable = None

    return jsonify({"ok": True, "provider": provider_name, "has_key": has_key, "model_url": model_url, "reachable": reachable})

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
            # 使用不加锁的内部版本,因为我们已经持有锁
            room_list = [_get_room_state_unsafe(rid) for rid in rooms.keys()]
            print(f"[DEBUG] GET /rooms -> 返回 {len(room_list)} 个房间: {[r['id'] for r in room_list if r]}")
            return jsonify({"rooms": room_list})
    body = request.json or {}
    owner = body.get("owner", "AI_owner")
    max_players = int(body.get("max_players", 6))
    rid = create_room(owner, max_players)
    room_state = get_room_state(rid)
    print(f"[DEBUG] POST /rooms -> 创建/复用房间 {rid}, 状态: {room_state.get('state') if room_state else 'None'}")
    # return both created room id and initial room state for convenience (201 Created)
    return jsonify({"room_id": rid, "room": room_state}), 201

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
    now = time.time()
    with rooms_lock:
        r = rooms.get(room_id)
        if not r:
            return jsonify({"error": "room_not_found"}), 404
        # debounce quick repeated step calls
        last = r.get("last_step", 0)
        if now - last < 0.7:
            return jsonify({"status": "throttled", "message": "step called too quickly"}), 429
        r["last_step"] = now
        g: Optional[Game] = r.get("game")
    if not g:
        return jsonify({"error": "game_not_started"}), 400
    if _auto_runner_active(room_id):
        return jsonify({"status": "auto", "message": "game is auto-running"}), 409
    g.step()
    with rooms_lock:
        if g.state == "ended":
            r["state"] = "ended"
    return jsonify({"status": "ok", "room": get_room_state(room_id)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)