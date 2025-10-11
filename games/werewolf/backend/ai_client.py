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
        os.path.join(os.getcwd(), "games", "werewolf", "backend", "ai_models.json"),
        os.path.join(os.getcwd(), "games", "werewolf", "backend", "ai_models.example.json"),
        os.path.join(os.getcwd(), "ai_models.json"),
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
from typing import Dict, Any, Optional, List

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
    p = os.path.join(os.getcwd(), "api_keys.json")
    try:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                _API_KEYS = json.load(f) or {}
                # normalize: ensure player_map exists
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

def call_openai_chat_with_meta(prompt: str, api_key: str, model: Optional[str] = None, system: str = "You are a game AI.") -> (Optional[str], Optional[Dict[str, Any]], Optional[str]):
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
    resolved_api_key = api_key

    if not api_key and keys:
        # pick first available provider when no api_key provided
        first = next(iter(keys.values()), None)
        if first:
            resolved_api_key = first.get("api_key")
            model_from_key = first.get("model")
            api_url_from_key = first.get("model_url")

    if api_key and keys:
        for prov, entry in keys.items():
            # support caller passing provider id (prov) or the actual secret
            if api_key == prov or api_key == entry.get("api_key"):
                resolved_api_key = entry.get("api_key") or api_key
                model_from_key = entry.get("model") or model_from_key
                api_url_from_key = entry.get("model_url") or api_url_from_key
                break

    if not resolved_api_key:
        return None, None, None

    model_to_use = model or model_from_key or _DEFAULT_MODEL
    api_url = api_url_from_key or OPENAI_API_URL

    headers = {"Authorization": f"Bearer {resolved_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model_to_use,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200,
    }
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

def build_night_prompt(player: str, role: str, state: Dict[str, Any]) -> str:
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]
    roles_map = state.get("roles_known_to_server", {})
    history = summarize_history(state, max_entries=6)
    prompt = (
        f"You are {player}, playing as {role} in a werewolf game.\n"
        f"Alive players: {', '.join(alive)}.\n"
        f"Known role assignments to the server (for simulation): {roles_map}.\n"
        f"Short history:\n{history}\n"
    )
    if role == "werewolf":
        prompt += (
            "As a werewolf, coordinate with your teammates to choose a kill target. "
            "Provide one player name from the Alive list and nothing else."
        )
    elif role == "seer":
        prompt += "As the seer, choose one player to reveal (to yourself). Reply with only the exact player name."
    elif role == "witch":
        prompt += (
            "As the witch, you can save the night victim (if you choose) or poison another player. "
            "If you want to save, reply with the exact name of the victim. If you want to poison, "
            "reply with the exact name of the poison target. If neither, reply with 'none'. "
            "Reply with only one token: a player name or 'none'."
        )
    else:
        prompt += "Choose a player at night (if any) or 'none'. Reply with only the exact name or 'none'."
    return prompt

def build_day_prompt(player: str, state: Dict[str, Any]) -> str:
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]
    history = summarize_history(state, max_entries=8)
    prompt = (
        f"You are {player} during the day discussion. Alive players: {', '.join(alive)}.\n"
        f"Short history:\n{history}\n"
        "Based on available information, choose one player to vote to lynch. Reply with only the exact player name."
    )
    return prompt

def build_talk_prompt(player: str, state: Dict[str, Any], talk_history: List[Dict[str, str]]) -> str:
    """
    为玩家生成发言（白天按顺序发言）提示，要求模型返回 JSON:
    {"speech":"..."} 或 {"speech":"...", "meta": {...}}
    """
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]
    hist = summarize_history(state, max_entries=8)
    past = "\n".join([f'{h["player"]}: {h["speech"]}' for h in talk_history[-10:]]) if talk_history else "None"
    prompt = (
        f"You are {player} during the day discussion. Alive players: {', '.join(alive)}.\n"
        f"Short history:\n{hist}\n"
        f"Previous speeches:\n{past}\n"
        "Now make a short in-character speech (one or two sentences) and reply in JSON: {\"speech\":\"...\"}."
    )
    return prompt

def validate_json_response(text: str, schema_type: str, role: Optional[str] = None) -> (Optional[Dict[str, Any]], Optional[str]):
    """
    基本的轻量级 JSON 校验器，根据 schema_type 检查必要字段并返回解析后的对象或错误字符串。
    schema_type: "night", "vote", "talk"
    role: optional role hint for night (werewolf/seer/witch)
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
    if schema_type == "night":
        # expected examples:
        # werewolf: {"action":"kill","target":"AI_3"}
        # seer: {"action":"reveal","target":"AI_2"}
        # witch: {"action":"save"/"poison"/"none","target": "AI_x" or null}
        if "action" not in obj:
            return None, "missing_action"
        if obj.get("action") not in ("kill", "reveal", "save", "poison", "none"):
            # allow other actions but warn
            pass
        # target may be optional for "none"
        if obj.get("action") != "none" and "target" not in obj:
            return None, "missing_target"
        return obj, None
    if schema_type == "vote":
        # expect {"target":"AI_X"} or {"action":"vote","target":"AI_X"}
        tgt = obj.get("target") or obj.get("vote")
        if not tgt or not isinstance(tgt, str):
            return None, "missing_target"
        return obj, None
    if schema_type == "talk":
        if "speech" not in obj or not isinstance(obj.get("speech"), str):
            return None, "missing_speech"
        return obj, None
    return obj, None

def decide_night_action(player: str, context: Dict[str, Any], api_key: str) -> Optional[str]:
    """
    返回一个目标玩家名称（字符串）或 None。
    context: {"role": "werewolf"/"seer"/"witch"/..., "state": Game.to_dict()}
    现在优先解析模型返回的 JSON，例如: {"action":"kill","target":"AI_3"}。
    - 若解析成功则记录在 _LAST_ACTIONS[player] 并返回 target。
    - 若解析失败，则回退到原有的文本解析或启发式选择。
    """
    role = context.get("role")
    state = context.get("state", {})
    alive = state.get("alive", [])
    alive = [p for p in alive if p != player]

    if not alive:
        return None

    # reset last action for player
    try:
        _LAST_ACTIONS.pop(player, None)
    except Exception:
        pass

    # 尝试在线模型决策（若提供 api_key）
    model = get_model_for(player)
    if api_key:
        prompt = build_night_prompt(player, role, state)
        resp = call_openai_chat(prompt, api_key, model=model, system="You are a rational werewolf-game bot. Reply in JSON like {\"action\":\"kill\",\"target\":\"AI_3\"} or 'none'.")
        if resp:
            text = resp.strip().strip('"').strip("'")
            # try parse JSON first
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    tgt_raw = obj.get("target") or obj.get("vote") or obj.get("player")
                    action_raw = obj.get("action")
                    if isinstance(tgt_raw, str):
                        picked = choose_from_candidates(tgt_raw, alive)
                        if picked:
                            _LAST_ACTIONS[player] = {"action": action_raw, "target": picked, "raw": obj}
                            if picked.lower() == "none":
                                return None
                            return picked
            except Exception:
                # not JSON, fall through to text parsing
                pass
            # fallback: text parsing as before
            if text.lower() == "none":
                return None
            picked = choose_from_candidates(text, alive)
            if picked:
                _LAST_ACTIONS[player] = {"action": None, "target": picked, "raw_text": text}
                return picked

    # 启发式后备策略 (并记录选择)
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
        if last and random.random() < 0.6:
            _LAST_ACTIONS[player] = {"action": "save", "target": last, "raw_text": "heuristic"}
            return last
        pick = random.choice(alive)
        _LAST_ACTIONS[player] = {"action": "poison", "target": pick, "raw_text": "heuristic"}
        return pick
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
        prompt = build_day_prompt(player, state)
        resp = call_openai_chat(prompt, api_key, model=model, system="You are a rational werewolf-game bot. Reply in JSON like {\"target\":\"AI_2\"} or just the name.")
        if resp:
            text = resp.strip().strip('"').strip("'")
            # try parse JSON first
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    tgt_raw = obj.get("target") or obj.get("vote") or obj.get("player")
                    action_raw = obj.get("action") or obj.get("type")
                    if isinstance(tgt_raw, str):
                        picked = choose_from_candidates(tgt_raw, alive)
                        if picked:
                            _LAST_ACTIONS[player] = {"action": action_raw or "vote", "target": picked, "raw": obj}
                            return picked
            except Exception:
                pass
            # fallback to text parsing
            picked = choose_from_candidates(text, alive)
            if picked:
                _LAST_ACTIONS[player] = {"action": "vote", "target": picked, "raw_text": text}
                return picked

    # 启发式：当前随机（后续可替换为基于历史/交互的策略）
    pick = random.choice(alive)
    _LAST_ACTIONS[player] = {"action": "vote", "target": pick, "raw_text": "heuristic"}
    return pick