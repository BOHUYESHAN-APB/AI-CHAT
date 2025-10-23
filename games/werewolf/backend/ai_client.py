BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, "..", "..", ".."))

def load_model_config() -> Dict[str, Any]:
    """
    加载后端可配置的模型映射配置。
    搜索顺序：
      1) games/werewolf/backend/ai_models.json
      2) games/werewolf/backend/ai_models.example.json
      3) ai_models.json (project root)
    返回示例结构：
    {
      "default_model": "gpt-4o-mini",
      "player_models": {
         "AI_1": "gpt-4o-mini",
         "AI_2": "gpt-4o"
      },
      "openai_api_url": "https://api.openai.com/v1/chat/completions"
    }
    """
    candidates = [
        os.path.join(BACKEND_DIR, "ai_models.json"),
        os.path.join(BACKEND_DIR, "ai_models.example.json"),
        os.path.join(PROJECT_ROOT, "ai_models.json"),
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    return cfg if isinstance(cfg, dict) else {}
        except Exception:
            continue
    return {}

# Preserve helper functions from previous implementation
import os
import random
import requests
import json
import time
from typing import Dict, Any, Optional, List, Tuple

# Load config once
_MODEL_CFG = load_model_config()

# cached API keys file (project root: api_keys.json)
_API_KEYS: Optional[Dict[str, Any]] = None
def load_api_keys() -> Dict[str, Any]:
    """
    从项目根目录读取 api_keys.json 并缓存结果。
    支持两种 caller 传入 api_key 的形式：
      - 传入 provider id（即 api_keys.json 的 key）
      - 传入实际的 secret string（value['api_key']）
    返回 dict 或空 dict。
    """
    global _API_KEYS
    if _API_KEYS is not None:
        return _API_KEYS
    p = os.path.join(PROJECT_ROOT, "api_keys.json")
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                _API_KEYS = json.load(f) or {}
                if "player_map" not in _API_KEYS:
                    _API_KEYS["player_map"] = {}
                return _API_KEYS
    except Exception:
        _API_KEYS = {}
    _API_KEYS = {"player_map": {}}
    return _API_KEYS

OPENAI_API_URL = _MODEL_CFG.get("openai_api_url", "https://api.openai.com/v1/chat/completions")
_DEFAULT_MODEL = _MODEL_CFG.get("default_model", "gpt-4o-mini")
_PLAYER_MODELS: Dict[str, str] = _MODEL_CFG.get("player_models", {})
# runtime storage for last parsed actions per player (for logging/inspection)
_LAST_ACTIONS: Dict[str, Any] = {}

def choose_from_candidates(text: str, candidates: List[str]) -> Optional[str]:
    text_low = (text or "").strip().lower()
    # exact match
    for c in candidates:
        if c.lower() == text_low:
            return c
    # substring match
    for c in candidates:
        if c.lower() in text_low:
            return c
    # startswith match on first token
    for c in candidates:
        first = c.lower().split()[0]
        if text_low.startswith(first):
            return c
    return None

def summarize_history(state: Dict[str, Any], max_entries: int = 10) -> str:
    hist = state.get("history", [])[-max_entries:]
    parts = []
    for h in hist:
        phase = h.get("phase")
        day = h.get("day")
        if phase == "night":
            killed = h.get("killed")
            parts.append(f"Night {day}: killed={killed}")
        elif phase == "day":
            lynched = h.get("lynched")
            votes = h.get("votes")
            parts.append(f"Day {day}: lynched={lynched}, votes={votes}")
        elif phase == "end":
            parts.append(f"End: winner={h.get('winner')}")
    return "\n".join(parts)

def get_model_for(player: str) -> str:
    """
    返回用于该玩家决策调用的模型名称
    """
    return _PLAYER_MODELS.get(player, _DEFAULT_MODEL)

def call_openai_chat(prompt: str, api_key: str, model: Optional[str] = None, system: str = "You are a game AI.") -> Optional[str]:
    """
    Backwards-compatible call: returns the extracted text if available, else None.
    """
    res_text, _, _ = call_openai_chat_with_meta(prompt, api_key, model=model, system=system)
    return res_text

def call_openai_chat_with_meta(
    prompt: str,
    api_key: str,
    model: Optional[str] = None,
    system: str = "You are a game AI.",
    response_format: Optional[Dict[str, Any]] = None,
    force_json: bool = False,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Calls the model and returns a tuple: (text, raw_response_json_or_text, model_used).
    容错逻辑：
      - 若 caller 未传 api_key，则从项目根的 api_keys.json 随机选择一个可用的 entry。
      - 若传入的 api_key 是 provider id（api_keys.json 的 key）或实际 secret，则会自动匹配对应 entry，并优先使用该 entry 中的 "model" 和 "model_url"（若提供）。
      - 最终选择顺序：函数参数 model -> api_keys.json 中 entry.model -> _PLAYER_MODELS (按 player 使用时传入) -> _DEFAULT_MODEL
    """
    # try to resolve api_key -> provider entry (api_keys.json)
    model_from_key = None
    api_url_from_key = None
    keys = load_api_keys()
    providers: Dict[str, Dict[str, Any]] = {}
    if isinstance(keys, dict):
        raw_providers = keys.get("providers")
        if isinstance(raw_providers, dict):
            providers = {k: v for k, v in raw_providers.items() if isinstance(v, dict)}
        if not providers:
            providers = {k: v for k, v in keys.items() if isinstance(v, dict) and (
                "api_key" in v or "key" in v or "secret" in v
            )}

    resolved_api_key = api_key

    if not api_key and providers:
        # pick first available provider when no api_key provided
        first = next(iter(providers.values()), None)
        if first:
            resolved_api_key = first.get("api_key") or first.get("key") or first.get("secret")
            model_from_key = first.get("model")
            api_url_from_key = first.get("model_url") or first.get("url") or first.get("endpoint")

    if api_key and providers:
        # support caller passing provider name or raw key
        if api_key in providers:
            entry = providers.get(api_key) or {}
            resolved_api_key = entry.get("api_key") or entry.get("key") or entry.get("secret") or api_key
            model_from_key = entry.get("model") or model_from_key
            api_url_from_key = entry.get("model_url") or entry.get("url") or entry.get("endpoint") or api_url_from_key
        else:
            for prov, entry in providers.items():
                if api_key == entry.get("api_key") or api_key == entry.get("key") or api_key == entry.get("secret"):
                    resolved_api_key = entry.get("api_key") or entry.get("key") or entry.get("secret")
                    model_from_key = entry.get("model") or model_from_key
                    api_url_from_key = entry.get("model_url") or entry.get("url") or entry.get("endpoint") or api_url_from_key
                    break

    if not resolved_api_key:
        return None, None, None

    model_to_use = model or model_from_key or _DEFAULT_MODEL
    api_url = api_url_from_key or OPENAI_API_URL

    headers = {"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    auto_force_json = force_json or (isinstance(api_url, str) and "deepseek.com" in api_url.lower())
    payload = {
        "model": model_to_use,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 400,
    }
    json_mode = response_format if response_format is not None else ({"type": "json_object"} if auto_force_json else None)
    if json_mode:
        payload["response_format"] = json_mode
    try:
        r = requests.post(api_url, json=payload, headers=headers, timeout=12)
        r.raise_for_status()
        data = r.json()
        # try structured chat response
        if isinstance(data.get("choices"), list) and data["choices"]:
            msg = data["choices"][0].get("message", {}).get("content")
            text = msg.strip() if msg else None
            return text, data, model_to_use
        # fallback to older text completion shape
        if data.get("choices") and isinstance(data["choices"][0], dict):
            text = str(data["choices"][0].get("text", "")).strip() or None
            return text, data, model_to_use
        return None, data, model_to_use
    except Exception as e:
        # return the exception string as raw for diagnostics
        return None, {"error": str(e)}, model_to_use

def build_night_prompt(player: str, role: str, state: Dict[str, Any], game_id: Optional[str] = None, message_id: Optional[str] = None) -> str:
    """
    Build a JSON-first input payload string following LOGIC_SPEC for night phase.
    The model is expected to reply with a JSON object (see LOGIC_SPEC).
    """
    ctx = state.get("model_state") if state.get("model_state") else state
    alive = ctx.get("alive", [])
    alive = [p for p in alive if p != player]
    roles_map = ctx.get("roles_known_to_server", {})
    history = summarize_history(ctx, max_entries=6)
    input_obj = {
        "game_id": game_id or "local_game",
        "message_id": message_id or str(random.randint(1000, 9999)),
        "phase": "night",
        "day": ctx.get("day", state.get("day", 0)),
        "current_player": player,
        "your_role": role,
        "your_team": "werewolves" if role == "werewolf" else "villagers",
        "game_context": {
            "alive_players": alive,
            "dead_players": [p for p in ctx.get("players", []) if p not in alive],
            "sheriff": None,
            "game_config": {"total_players": len(ctx.get("players", []))}
        },
        "role_specific_info": {
            "werewolf_teammates": [p for p, r in roles_map.items() if r == "werewolf" and p != player],
            "witch_potions": {"save_available": state.get("resources", {}).get("witch_save_available", True),
                              "poison_available": state.get("resources", {}).get("witch_poison_available", True)},
            "seer_reveals": [],
            "guard_protections": []
        },
        "complete_history": {"night_events": [], "day_events": [], "player_reputations": {}},
        "current_phase_details": {"available_targets": alive},
        "action_requirements": {"expected_action": "kill" if role == "werewolf" else ("reveal" if role == "seer" else "witch_action" if role == "witch" else "protect" if role == "guard" else "none"),
                                "format_requirements": {}, "deadline": None}
    }
    prompt = (
        "INPUT_JSON:\n"
        f"{json.dumps(input_obj, ensure_ascii=False, indent=2)}\n\n"
        "INSTRUCTION: Reply with a single JSON object matching the LOGIC_SPEC for night actions.\n"
        "Examples (night): {\"action\":\"kill\",\"target\":\"AI_3\"} or {\"action\":\"none\"}.\n"
        "Do not include any extra text outside the JSON object."
    )
    return prompt

def build_day_prompt(player: str, state: Dict[str, Any], game_id: Optional[str] = None, message_id: Optional[str] = None) -> str:
    """
    Build JSON-first input for day voting/discussion per LOGIC_SPEC.
    """
    ctx = state.get("model_state") if state.get("model_state") else state
    alive = ctx.get("alive", [])
    alive = [p for p in alive if p != player]
    history = summarize_history(ctx, max_entries=8)
    input_obj = {
        "game_id": game_id or "local_game",
        "message_id": message_id or str(random.randint(1000, 9999)),
        "phase": "day_discussion",
        "day": ctx.get("day", state.get("day", 0)),
        "current_player": player,
        "your_role": ctx.get("roles_known_to_server", {}).get(player),
        "game_context": {
            "alive_players": alive,
            "dead_players": [p for p in ctx.get("players", []) if p not in alive],
            "game_config": {"total_players": len(ctx.get("players", []))}
        },
        "complete_history": {"day_events": ctx.get("history", [])},
        "current_phase_details": {"previous_speeches_today": ctx.get("phase_context", {}).get("current_talks", [])},
        "action_requirements": {"expected_action": "vote", "format_requirements": {}, "deadline": None}
    }
    prompt = (
        "INPUT_JSON:\n"
        f"{json.dumps(input_obj, ensure_ascii=False, indent=2)}\n\n"
        "INSTRUCTION: Reply with a single JSON object like {\"action\":\"vote\",\"target\":\"AI_2\"}.\n"
        "Do not include any extra text outside the JSON object."
    )
    return prompt

def build_talk_prompt(player: str, state: Dict[str, Any], talk_history: List[Dict[str, str]], game_id: Optional[str] = None, message_id: Optional[str] = None) -> str:
    """
    Build a JSON-first prompt for day speech. Expect {"speech":"...","meta":{}}.
    """
    ctx = state.get("model_state") if state.get("model_state") else state
    alive = ctx.get("alive", [])
    alive = [p for p in alive if p != player]
    hist = summarize_history(ctx, max_entries=8)
    past_list = talk_history[-10:] if talk_history else []
    input_obj = {
        "game_id": game_id or "local_game",
        "message_id": message_id or str(random.randint(1000, 9999)),
        "phase": "day_discussion",
        "day": ctx.get("day", state.get("day", 0)),
        "current_player": player,
        "your_role": ctx.get("roles_known_to_server", {}).get(player),
        "game_context": {"alive_players": alive},
        "complete_history": {"day_events": ctx.get("history", [])},
        "current_phase_details": {"previous_speeches_today": past_list},
        "action_requirements": {"expected_action": "speak", "format_requirements": {}, "deadline": None}
    }
    prompt = (
        "INPUT_JSON:\n"
        f"{json.dumps(input_obj, ensure_ascii=False, indent=2)}\n\n"
        "INSTRUCTION: Reply with a single JSON object like {\"action\":\"speak\",\"speech\":\"I suspect AI_4\",\"meta\":{}}.\n"
        "Do not include any extra text outside the JSON object."
    )
    return prompt

def validate_json_response(text: str, schema_type: str, role: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Lightweight JSON validator with extended schema support and error codes.
    schema_type: "night","vote","talk","witch_action","protect","speak"
    Returns (parsed_obj or None, error_code or None)
    """
    if not text:
        return None, "empty_response"
    t = text.strip().strip('"').strip("'")
    try:
        obj = json.loads(t)
    except Exception:
        return None, "not_json"
    if not isinstance(obj, dict):
        return None, "not_object"

    action = obj.get("action")
    # night-like actions
    if schema_type in ("night", "witch_action", "protect"):
        if "action" not in obj:
            return None, "missing_action"
        if schema_type == "witch_action":
            # expect {"action":"witch_action","save_target":..., "poison_target":...} or similar
            if "save_target" not in obj and "poison_target" not in obj and obj.get("action") not in ("none", "save", "poison", "witch_action"):
                return None, "missing_witch_fields"
            return obj, None
        if schema_type == "protect":
            if obj.get("action") != "protect" or "target" not in obj:
                return None, "invalid_protect"
            if not isinstance(obj.get("target"), str):
                return None, "invalid_target_type"
            return obj, None
        # generic night validator
        if obj.get("action") not in ("kill", "reveal", "save", "poison", "none", "protect"):
            # allow other actions but mark as warning (return as-is)
            pass
        if obj.get("action") != "none" and "target" not in obj and obj.get("action") not in ("reveal",):
            return None, "missing_target"
        return obj, None

    if schema_type == "vote":
        tgt = obj.get("target") or obj.get("vote")
        if not tgt or not isinstance(tgt, str):
            return None, "missing_target"
        return obj, None

    if schema_type in ("talk", "speak"):
        if "speech" not in obj or not isinstance(obj.get("speech"), str):
            return None, "missing_speech"
        return obj, None

    # fallback: accept object
    return obj, None

def decide_night_action(player: str, context: Dict[str, Any], api_key: str) -> Optional[str]:
    """
    Use call_openai_chat_with_meta, record meta, parse JSON-first response and fall back to heuristics.
    Returns target player name or None.
    """
    role = context.get("role")
    state = context.get("state", {})
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]

    if not alive:
        return None

    try:
        _LAST_ACTIONS.pop(player, None)
    except Exception:
        pass

    model = get_model_for(player)
    # Try online model if api_key provided
    if api_key:
        provider_hint = context.get("provider")
        prompt = build_night_prompt(player, role, state)
        start = time.time()
        text, raw, model_used = call_openai_chat_with_meta(
            prompt,
            api_key,
            model=model,
            system="You are a rational werewolf-game bot. Reply in JSON like {\"action\":\"kill\",\"target\":\"AI_3\"} or {\"action\":\"none\"}.",
            force_json=True,
        )
        latency = time.time() - start
        meta = {"model": model_used, "latency": latency, "provider": provider_hint, "raw": raw, "json_mode": True}
        if raw and isinstance(raw, dict) and raw.get("error"):
            meta["error"] = raw.get("error")
            print(f"[WARN] decide_night_action model error player={player} role={role} provider={provider_hint}: {raw.get('error')}")
        if text:
            text_clean = text.strip().strip('"').strip("'")
            try:
                obj = json.loads(text_clean)
                parsed, err = validate_json_response(json.dumps(obj), "night", role=role)
                if parsed and err is None:
                    tgt_raw = parsed.get("target") or parsed.get("vote") or parsed.get("player")
                    action_raw = parsed.get("action")
                    picked = None
                    if isinstance(tgt_raw, str):
                        picked = choose_from_candidates(tgt_raw, alive)
                    if parsed.get("action") in ("save", "poison") and parsed.get("target"):
                        picked = choose_from_candidates(parsed.get("target"), alive)
                    _LAST_ACTIONS[player] = {"action": action_raw, "target": picked, "raw": obj, "meta": meta}
                    if picked and isinstance(picked, str) and picked.lower() == "none":
                        return None
                    if picked:
                        return picked
            except Exception:
                pass
            if text_clean.lower() == "none":
                _LAST_ACTIONS[player] = {"action": "none", "target": None, "raw_text": text_clean, "meta": meta}
                return None
            picked = choose_from_candidates(text_clean, alive)
            if picked:
                _LAST_ACTIONS[player] = {"action": None, "target": picked, "raw_text": text_clean, "meta": meta}
                return picked
        # if online call returned no usable result, allow one retry with higher temperature off (not implemented) -> fallthrough

    # Heuristic fallback
    if role == "werewolf":
        known = state.get("roles_known_to_server", {})
        candidates = [p for p in alive if known.get(p) != "werewolf"]
        if not candidates:
            candidates = alive
        pick = random.choice(candidates)
        _LAST_ACTIONS[player] = {"action": "kill", "target": pick, "raw_text": "heuristic"}
        return pick
    if role == "seer":
        pick = random.choice(alive)
        _LAST_ACTIONS[player] = {"action": "reveal", "target": pick, "raw_text": "heuristic"}
        return pick
    if role == "witch":
        last = None
        hist = state.get("history", [])
        for h in reversed(hist):
            if h.get("phase") == "night" and h.get("killed"):
                last = h["killed"]
                break
        # Prefer saving if someone died and save is still available
        if last and random.random() < 0.7:
            _LAST_ACTIONS[player] = {"action": "save", "target": last, "raw_text": "heuristic"}
            return last
        # Only occasionally use poison to avoid连续大量淘汰
        if random.random() < 0.2:
            known = state.get("roles_known_to_server", {})
            candidates = [p for p in alive if known.get(p) != "werewolf"] or alive
            pick = random.choice(candidates)
            _LAST_ACTIONS[player] = {"action": "poison", "target": pick, "raw_text": "heuristic"}
            return pick
        _LAST_ACTIONS[player] = {"action": "none", "target": None, "raw_text": "heuristic"}
        return None
    pick = random.choice(alive)
    _LAST_ACTIONS[player] = {"action": None, "target": pick, "raw_text": "heuristic"}
    return pick

def decide_vote(player: str, context: Dict[str, Any], api_key: str) -> str:
    """
    返回一个存活玩家的名字作为投票对象（字符串）。
    context: {"state": Game.to_dict()}
    现在优先解析模型返回的 JSON，例如: {"action":"vote","target":"AI_2"} 或 {"target":"AI_2"}。
    """
    state = context.get("state", {})
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]
    if not alive:
        return player

    # reset last action
    try:
        _LAST_ACTIONS.pop(player, None)
    except Exception:
        pass

    model = get_model_for(player)
    if api_key:
        provider_hint = context.get("provider")
        prompt = build_day_prompt(player, state)
        start = time.time()
        text, raw, model_used = call_openai_chat_with_meta(
            prompt,
            api_key,
            model=model,
            system="You are a rational werewolf-game bot. Reply in JSON like {\"action\":\"vote\",\"target\":\"AI_2\"} or just the name.",
            force_json=True,
        )
        latency = time.time() - start
        meta = {"model": model_used, "latency": latency, "provider": provider_hint, "raw": raw, "json_mode": True}
        if raw and isinstance(raw, dict) and raw.get("error"):
            meta["error"] = raw.get("error")
            print(f"[WARN] decide_vote model error player={player} provider={provider_hint}: {raw.get('error')}")
        if text:
            cleaned = text.strip().strip('"').strip("'")
            try:
                obj = json.loads(cleaned)
                if isinstance(obj, dict):
                    tgt_raw = obj.get("target") or obj.get("vote") or obj.get("player")
                    action_raw = obj.get("action") or obj.get("type")
                    if isinstance(tgt_raw, str):
                        picked = choose_from_candidates(tgt_raw, alive)
                        if picked:
                            _LAST_ACTIONS[player] = {"action": action_raw or "vote", "target": picked, "raw": obj, "meta": meta}
                            return picked
            except Exception:
                pass
            picked = choose_from_candidates(cleaned, alive)
            if picked:
                _LAST_ACTIONS[player] = {"action": "vote", "target": picked, "raw_text": cleaned, "meta": meta}
                return picked

    # 启发式：当前随机（后续可替换为基于历史/交互的策略）
    pick = random.choice(alive)
    _LAST_ACTIONS[player] = {"action": "vote", "target": pick, "raw_text": "heuristic"}
    return pick
# Additional helpers: parse generic action responses and day-speech handler
def _parse_action_text_and_pick(text: str, schema_type: str, alive: List[str], role: Optional[str] = None):
    """
    Try to parse model text into a normalized action dict and pick a concrete target from alive list.
    Returns (normalized_obj_or_none, error_code_or_none, picked_target_or_none)
    """
    if not text:
        return None, "empty_response", None
    txt = text.strip().strip('"').strip("'")
    # try direct JSON parse
    try:
        obj = json.loads(txt)
    except Exception:
        # try to find a JSON substring
        start = txt.find("{")
        end = txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                obj = json.loads(txt[start:end+1])
            except Exception:
                obj = None
        else:
            obj = None
    if obj is None:
        # fallback: treat entire text as a target candidate (e.g., "AI_3")
        picked = choose_from_candidates(txt, alive)
        return None, "not_json", picked
    # validate with existing validator
    parsed, err = validate_json_response(json.dumps(obj), schema_type, role)
    if parsed is None:
        # attempt some common convenience fields
        tgt = obj.get("target") or obj.get("vote") or obj.get("player") or obj.get("name")
        if isinstance(tgt, str):
            picked = choose_from_candidates(tgt, alive)
            return obj, "validated_with_fallback", picked
        return obj, err or "invalid_schema", None
    # normalized target extraction
    tgt_raw = parsed.get("target") or parsed.get("vote") or parsed.get("player") or parsed.get("name")
    picked = None
    if isinstance(tgt_raw, str):
        picked = choose_from_candidates(tgt_raw, alive)
    # handle witch shapes where save/poison exist - prefer explicit poison target when schema_type=="night"
    if schema_type in ("night", "witch_action"):
        if parsed.get("poison_target"):
            picked = choose_from_candidates(parsed.get("poison_target"), alive)
        elif parsed.get("save_target"):
            picked = choose_from_candidates(parsed.get("save_target"), alive)
    return parsed, None, picked

def decide_talk(player: str, state: Dict[str, Any], talk_history: List[Dict[str, Any]], api_key: str) -> Optional[Dict[str, Any]]:
    """
    Produce a speech dict for the player during day discussion.
    Returns {"speech": "...", "meta": {...}} or None if no speech.
    """
    # backward-compatible wrapper expected by app.py as decide_talk(player, state, talk_history, api_key)
    # Note: some callers pass (player, state, talk_history, api_key) or (player, state, talk_history)
    # We implement the full signature here.
    try:
        # resolve alive list
        ctx = state.get("model_state") if state.get("model_state") else state
        alive = ctx.get("alive", [])
        if player not in alive:
            return None
        model = get_model_for(player)
        provider_hint = state.get("provider")
        # build prompt
        prompt = build_talk_prompt(player, state, talk_history)
        start = time.time()
        # prefer openai-style call_with_meta to capture raw
        text, raw, model_used = call_openai_chat_with_meta(
            prompt,
            api_key,
            model=model,
            system="You are a game AI. Reply with a JSON object like {\"action\":\"speak\",\"speech\":\"...\",\"meta\":{}}.",
            force_json=True,
        )
        latency = time.time() - start
        meta = {"model": model_used, "latency": latency, "provider": provider_hint, "raw": raw, "json_mode": True}
        if raw and isinstance(raw, dict) and raw.get("error"):
            meta["error"] = raw.get("error")
            print(f"[WARN] decide_talk model error player={player} provider={provider_hint}: {raw.get('error')}")
        speech_text = None
        if text:
            parsed, err = validate_json_response(text, "speak")
            if parsed and "speech" in parsed:
                speech_text = parsed.get("speech")
                meta.update({"validate_error": err} if err else {})
            else:
                # attempt to parse tolerant JSON and extract speech
                try:
                    obj = json.loads(text.strip().strip('"').strip("'"))
                    if isinstance(obj, dict) and "speech" in obj:
                        speech_text = obj.get("speech")
                except Exception:
                    # fallback: use text as raw speech
                    speech_text = text
        if not speech_text:
            # no valid output from model -> heuristic short statement
            speech_text = f"{player} has nothing special to say."
            meta["heuristic"] = True
        out = {"speech": speech_text, "meta": meta}
        _LAST_ACTIONS[player] = {"action": "speak", "speech": speech_text, "raw": text if 'text' in locals() else None, "meta": meta}
        return out
    except TypeError:
        # older callers might not pass api_key; try without it
        try:
            return decide_talk(player, state, talk_history, None)  # type: ignore[arg-type]
        except Exception:
            return {"speech": f"{player} has nothing to add.", "meta": {"heuristic": True}}
    except Exception:
        return {"speech": f"{player} has nothing to add.", "meta": {"heuristic": True}}