from __future__ import annotations
import asyncio
from typing import Dict, Any, List, Optional, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import random
import uuid
from pathlib import Path
import os

from .models import Game, Player, Role, AIConfig, load_api_keys

app = FastAPI(title="Werewolf AI Arena")
GAMES: Dict[str, Game] = {}
API_KEYS = load_api_keys()

# WebSocket connection manager for real-time game updates
class ConnectionManager:
    def __init__(self):
        # map game_id -> set of WebSocket connections
        self.active: Dict[str, Set[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket):
        await websocket.accept()
        conns = self.active.setdefault(game_id, set())
        conns.add(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket):
        conns = self.active.get(game_id)
        if conns and websocket in conns:
            conns.remove(websocket)
            if not conns:
                del self.active[game_id]

    async def send_personal(self, websocket: WebSocket, message: Any):
        await websocket.send_json(message)

    async def broadcast_game(self, game_id: str, message: Any):
        conns = list(self.active.get(game_id, []))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                # ignore broken connections here; disconnect handled on receive
                pass

manager = ConnectionManager()

class CreateGameRequest(BaseModel):
    name: Optional[str] = "werewolf-match"

class JoinRequest(BaseModel):
    name: str
    is_ai: bool = False
    role: Optional[Role] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    api_key_name: Optional[str] = None

@app.post("/games")
async def create_game(req: CreateGameRequest):
    g = Game(name=req.name)
    GAMES[str(g.id)] = g
    # notify any clients listening on this game channel (clients may subscribe after creation)
    try:
        await manager.broadcast_game(str(g.id), {"type": "game_created", "game": g.to_dict()})
    except Exception:
        pass
    return JSONResponse({"game_id": str(g.id), "game": g.to_dict()})

@app.post("/games/{game_id}/join")
async def join_game(game_id: str, req: JoinRequest):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    player = Player(name=req.name, is_ai=req.is_ai)
    if req.role:
        player.role = req.role
    if req.is_ai:
        player.ai_config = AIConfig(provider=req.ai_provider or "openai", model=req.ai_model, api_key_name=req.api_key_name)
    g.add_player(player)
    return {"player_id": str(player.id), "game": g.to_dict()}

@app.post("/games/{game_id}/start")
async def start_game(game_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    players = g.players
    n = len(players)
    if n < 4:
        raise HTTPException(400, "need at least 4 players")
    roles = []
    roles.append(Role.WEREWOLF)
    roles.append(Role.SEER)
    while len(roles) < n:
        roles.append(Role.VILLAGER)
    random.shuffle(roles)
    for p, r in zip(players, roles):
        p.role = r
    g.state = g.state.NIGHT
    g.night = 1
    g.logs.append(f"Game started. Night {g.night}")
    return {"game": g.to_dict()}

@app.get("/games/{game_id}")
async def get_game(game_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    return g.to_dict()

@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """
    WebSocket endpoint for real-time game updates.
    Clients should connect to /ws/{game_id} and may send text messages like "get_state" or "ping".
    Server will push JSON messages with {"type": "...", ...} including "game_state" updates.
    """
    await manager.connect(game_id, websocket)
    try:
        # Immediately send current state if available
        g = GAMES.get(game_id)
        if g:
            await manager.send_personal(websocket, {"type": "game_state", "game": g.to_dict()})
        while True:
            data = await websocket.receive_text()
            # simple protocol: if client requests state, send it
            if data and data.strip().lower() in ("get_state", "state", "refresh"):
                g = GAMES.get(game_id)
                if g:
                    await manager.send_personal(websocket, {"type": "game_state", "game": g.to_dict()})
            else:
                # ignore other messages or use them for future commands
                await manager.send_personal(websocket, {"type": "ack", "message": "received"})
    except WebSocketDisconnect:
        manager.disconnect(game_id, websocket)

async def ai_choose_target(game: Game, player: Player) -> Optional[str]:
    alive = [p for p in game.alive_players() if p.id != player.id]
    if not alive:
        return None
    cfg = player.ai_config
    if cfg and cfg.provider == "openai":
        key_name = cfg.api_key_name or "OPENAI_API_KEY"
        key = API_KEYS.get(key_name) or os.getenv(key_name)
        if key:
            try:
                import httpx
                prompt = f"You are a werewolf player. Choose one target from: {[p.name for p in alive]}. Respond with the exact name only."
                headers = {"Authorization": f"Bearer {key}"}
                data = {"model": cfg.model or "gpt-4o-mini", "messages":[{"role":"user","content":prompt}], "max_tokens":16}
                resp = httpx.post("https://api.openai.com/v1/chat/completions", json=data, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip()
                    for p in alive:
                        if p.name == text:
                            return str(p.id)
            except Exception:
                pass
    return str(random.choice(alive).id)

@app.post("/games/{game_id}/ai_turn")
async def ai_turn(game_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    if g.state != g.state.NIGHT:
        raise HTTPException(400, "ai_turn allowed only during night")
    actions = []
    for p in list(g.alive_players()):
        if p.is_ai:
            if p.role == Role.WEREWOLF:
                tgt = await ai_choose_target(g, p)
                if tgt:
                    g.perform_night_action(actor_id=p.id, action_type="kill", target_id=uuid.UUID(tgt))
                    actions.append({"actor": p.name, "action": "kill", "target_id": tgt})
            elif p.role == Role.SEER:
                tgt = await ai_choose_target(g, p)
                if tgt:
                    g.perform_night_action(actor_id=p.id, action_type="inspect", target_id=uuid.UUID(tgt))
                    actions.append({"actor": p.name, "action": "inspect", "target_id": tgt})
            else:
                pass
    return {"performed": actions, "game": g.to_dict()}

@app.post("/games/{game_id}/resolve_night")
async def resolve_night(game_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    if g.state != g.state.NIGHT:
        raise HTTPException(400, "not night")
    # Delegate to Game.resolve_night which applies saves/kills/inspections and updates state
    report = g.resolve_night()
    # broadcast updated game state to websocket clients
    try:
        await manager.broadcast_game(game_id, {"type": "game_state", "game": g.to_dict(), "event": "night_resolved", "report": report})
    except Exception:
        pass
    return {"killed": report, "game": g.to_dict()}

@app.post("/games/{game_id}/vote")
async def vote(game_id: str, actor_id: str, target_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    try:
        g.vote(actor_id=uuid.UUID(actor_id), target_id=uuid.UUID(target_id))
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"game": g.to_dict()}

@app.post("/games/{game_id}/tally_votes")
async def tally_votes(game_id: str):
    g = GAMES.get(game_id)
    if not g:
        raise HTTPException(404, "game not found")
    eliminated_id = g.tally_votes()
    # broadcast updated game state
    try:
        await manager.broadcast_game(game_id, {"type": "game_state", "game": g.to_dict(), "event": "vote_tallied", "eliminated": eliminated_id})
    except Exception:
        pass
    return {"eliminated": eliminated_id, "game": g.to_dict()}

# --- AI simulation and matchmaking helpers ---
@app.post("/simulate_ai_game")
async def simulate_ai_game(num_players: int = 6):
    """
    Create a game fully populated by AI players and run it to completion.
    Useful for automated model-vs-model evaluation.
    """
    if num_players < 4:
        raise HTTPException(400, "need at least 4 players")
    # create game
    g = Game(name=f"ai-sim-{num_players}")
    GAMES[str(g.id)] = g
    # add AI players
    for i in range(1, num_players + 1):
        p = Player(name=f"AI_{i}", is_ai=True, ai_config=AIConfig(provider="openai"))
        g.add_player(p)
    # assign roles and start
    players = g.players
    roles = []
    roles.append(Role.WEREWOLF)
    roles.append(Role.SEER)
    while len(roles) < len(players):
        roles.append(Role.VILLAGER)
    random.shuffle(roles)
    for p, r in zip(players, roles):
        p.role = r
    g.state = g.state.NIGHT
    g.night = 1
    g.logs.append(f"AI simulation started. Night {g.night}")

    # run loop until end
    from .ai_client import choose_target, choose_inspect_target
    while g.state != g.state.ENDED:
        # NIGHT actions
        if g.state == g.state.NIGHT:
            for p in list(g.alive_players()):
                if p.is_ai:
                    if p.role == Role.WEREWOLF:
                        tgt = await choose_target(g, p)
                        if tgt:
                            g.perform_night_action(actor_id=p.id, action_type="kill", target_id=uuid.UUID(tgt))
                    elif p.role == Role.SEER:
                        tgt = await choose_inspect_target(g, p)
                        if tgt:
                            # record inspection as a log (not altering alive state)
                            tplayer = g.find_player(uuid.UUID(tgt))
                            if tplayer:
                                g.logs.append(f"{p.name} (seer) inspects {tplayer.name}: role={tplayer.role}")
                                g.perform_night_action(actor_id=p.id, action_type="inspect", target_id=uuid.UUID(tgt))
                    else:
                        # villagers may skip or leave traces
                        pass
            # resolve night
            kills = [a for a in g.actions if getattr(a, "action_type", "") == "kill"]
            killed_ids = set()
            for k in kills:
                if k.target_id:
                    killed_ids.add(k.target_id)
            report = []
            for kid in killed_ids:
                p = g.find_player(kid)
                if p and p.alive:
                    p.alive = False
                    report.append({"killed": p.name, "id": str(p.id)})
                    g.logs.append(f"{p.name} was killed during night {g.night}")
            g.reset_actions()
            g.day += 1
            g.state = g.state.DAY
            g.logs.append(f"Day {g.day} begins")
            await asyncio.sleep(0)  # yield to event loop

        # DAY actions: AI vote
        if g.state == g.state.DAY and g.state != g.state.ENDED:
            for p in list(g.alive_players()):
                if p.is_ai:
                    # simple vote chooser using same target logic
                    from .ai_client import choose_target as vote_choose
                    tgt = await vote_choose(g, p)
                    if tgt:
                        try:
                            g.vote(actor_id=p.id, target_id=uuid.UUID(tgt))
                        except Exception:
                            pass
            # tally votes
            votes = [a for a in g.actions if hasattr(a, "target_id")]
            counts: Dict[str, int] = {}
            for v in votes:
                tid = str(v.target_id)
                counts[tid] = counts.get(tid, 0) + getattr(v, "weight", 1)
            if counts:
                eliminated_id = max(counts.items(), key=lambda x: x[1])[0]
                p = g.find_player(uuid.UUID(eliminated_id))
                if p:
                    p.alive = False
                    g.logs.append(f"{p.name} was eliminated by vote in day {g.day}")
            g.reset_actions()
            wolves = [p for p in g.alive_players() if p.role == Role.WEREWOLF]
            non_wolves = [p for p in g.alive_players() if p.role != Role.WEREWOLF]
            if not wolves:
                g.state = g.state.ENDED
                g.logs.append("Villagers win")
            elif len(wolves) >= len(non_wolves):
                g.state = g.state.ENDED
                g.logs.append("Werewolves win")
            else:
                g.state = g.state.NIGHT
                g.night += 1
                g.logs.append(f"Night {g.night} begins")
            await asyncio.sleep(0)

    return {"game": g.to_dict(), "logs": g.logs}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("games.werewolf.backend.app:app", host="127.0.0.1", port=8000, reload=True)