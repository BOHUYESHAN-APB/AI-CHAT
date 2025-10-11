from __future__ import annotations
import os
import json
import random
from typing import Optional, List, Dict, Any
import httpx
from pathlib import Path
from .models import Game, Player, AIConfig, load_api_keys

ROOT_KEYS = load_api_keys()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

def _get_key(provider: str, api_key_name: Optional[str] = None) -> Optional[str]:
    keys = ROOT_KEYS or {}
    # If explicit api_key_name passed, try to resolve nested or string value
    if api_key_name:
        v = keys.get(api_key_name)
        if isinstance(v, dict):
            return v.get("api_key") or v.get("key")
        if isinstance(v, str):
            return v
    # Fallback to provider top-level entry
    prov = keys.get(provider)
    if isinstance(prov, dict):
        return prov.get("api_key") or prov.get("key")
    # Fallback to environment variable
    return os.getenv(api_key_name or f"{provider.upper()}_API_KEY")

async def choose_target(game: Game, player: Player) -> Optional[str]:
    """
    Generic target chooser for attack/vote decisions.
    Returns the UUID string of chosen target or None.
    """
    alive = [p for p in game.alive_players() if p.id != player.id]
    if not alive:
        return None
    cfg = player.ai_config or AIConfig()
    provider = (cfg.provider or "openai").lower()
    if provider == "openai":
        return await _choose_openai(game, player, cfg)
    # Other providers can be added here
    return str(random.choice(alive).id)

async def _choose_openai(game: Game, player: Player, cfg: AIConfig) -> Optional[str]:
    key = _get_key(cfg.provider or "openai", cfg.api_key_name)
    alive = [p for p in game.alive_players() if p.id != player.id]
    if not alive:
        return None
    if not key:
        return str(random.choice(alive).id)
    model = cfg.model or DEFAULT_OPENAI_MODEL
    names = [p.name for p in alive]
    prompt = (
        f"You are a werewolf player named {player.name} (role: {player.role}).\n"
        f"Choose one target from the list exactly by name. Options: {names}\n"
        "Return only the name of the chosen target, nothing else."
    )
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 16}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers)
            resp.raise_for_status()
            js = resp.json()
            text = js["choices"][0]["message"]["content"].strip()
            for p in alive:
                if p.name == text:
                    return str(p.id)
    except Exception:
        pass
    return str(random.choice(alive).id)

async def choose_inspect_target(game: Game, player: Player) -> Optional[str]:
    """
    Helper for roles such as seer to pick inspection targets.
    """
    return await _choose_openai(game, player, player.ai_config or AIConfig())