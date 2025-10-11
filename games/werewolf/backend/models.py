from __future__ import annotations
import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4
from datetime import datetime
from pathlib import Path
import json
from collections import Counter

class Role(str, enum.Enum):
    VILLAGER = "villager"
    WEREWOLF = "werewolf"
    SEER = "seer"
    DOCTOR = "doctor"
    HUNTER = "hunter"
    # 可扩展更多角色

class AIConfig(BaseModel):
    provider: str = Field("openai", description="AI provider name")
    model: Optional[str] = None
    api_key_name: Optional[str] = Field(None, description="在根目录 api_keys.json 中的 key 名称")
    extra: Optional[Dict[str, Any]] = None

class Player(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    is_ai: bool = False
    role: Optional[Role] = None
    alive: bool = True
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    ai_config: Optional[AIConfig] = None

    @validator("name")
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

class BaseAction(BaseModel):
    actor_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def summary(self) -> str:
        return f"Action by {self.actor_id} at {self.timestamp.isoformat()}"

class VoteAction(BaseAction):
    target_id: UUID
    weight: int = 1

class NightAction(BaseAction):
    action_type: str
    target_id: Optional[UUID] = None
    meta: Optional[Dict[str, Any]] = None

class GameState(str, enum.Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAY = "day"
    ENDED = "ended"

class Game(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: Optional[str] = None
    players: List[Player] = Field(default_factory=list)
    state: GameState = GameState.LOBBY
    day: int = 0
    night: int = 0
    actions: List[BaseAction] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_player(self, player: Player):
        if any(p.id == player.id for p in self.players):
            raise ValueError("player already in game")
        self.players.append(player)
        self.updated_at = datetime.utcnow()

    def remove_player(self, player_id: UUID):
        self.players = [p for p in self.players if p.id != player_id]
        self.updated_at = datetime.utcnow()

    def find_player(self, player_id: UUID) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def alive_players(self) -> List[Player]:
        return [p for p in self.players if p.alive]

    def vote(self, actor_id: UUID, target_id: UUID, weight: int = 1):
        """
        Cast (or change) a vote for the current day.
        If the actor already voted this day, their previous vote is replaced.
        """
        actor = self.find_player(actor_id)
        if actor is None:
            raise ValueError("actor not found")
        if not actor.alive:
            raise ValueError("actor is not alive")
        # remove previous vote(s) by this actor for this day
        self.actions = [a for a in self.actions if not (isinstance(a, VoteAction) and a.actor_id == actor_id)]
        v = VoteAction(actor_id=actor_id, target_id=target_id, weight=weight)
        self.actions.append(v)
        self.logs.append(f"Vote: {actor.name} -> {target_id} (weight={weight})")
        self.updated_at = datetime.utcnow()

    def perform_night_action(self, actor_id: UUID, action_type: str, target_id: Optional[UUID] = None, meta: Optional[Dict[str, Any]] = None):
        """
        Record a night action. action_type examples: 'kill', 'inspect', 'save'
        """
        actor = self.find_player(actor_id)
        if actor is None:
            raise ValueError("actor not found")
        if not actor.alive:
            raise ValueError("actor is not alive")
        na = NightAction(actor_id=actor_id, action_type=action_type, target_id=target_id, meta=meta)
        self.actions.append(na)
        # make logs more descriptive when possible
        actor_name = actor.name
        target_name = None
        if target_id:
            tp = self.find_player(target_id)
            target_name = tp.name if tp else str(target_id)
        if action_type == "kill":
            self.logs.append(f"{actor_name} attempts to kill {target_name}")
        elif action_type == "inspect":
            self.logs.append(f"{actor_name} inspects {target_name}")
        elif action_type == "save":
            self.logs.append(f"{actor_name} attempts to save {target_name}")
        else:
            self.logs.append(na.summary())
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    def reset_actions(self):
        self.actions = []
        self.updated_at = datetime.utcnow()

    def resolve_night(self) -> List[Dict[str, Any]]:
        """
        Apply night actions in the following simplified priority:
        - Doctor saves ('save') protect targets from kills
        - Werewolf kills ('kill') mark targets for death unless saved
        - Seer inspections logged but do not change state
        Returns list of killed player reports.
        """
        kills = [a for a in self.actions if getattr(a, "action_type", "") == "kill"]
        saves = {a.target_id for a in self.actions if getattr(a, "action_type", "") == "save" and a.target_id}
        killed_ids = set()
        for k in kills:
            if k.target_id and k.target_id not in saves:
                killed_ids.add(k.target_id)

        report = []
        for kid in killed_ids:
            p = self.find_player(kid)
            if p and p.alive:
                p.alive = False
                report.append({"killed": p.name, "id": str(p.id), "role": p.role})
                self.logs.append(f"{p.name} was killed during night {self.night}")
                # hunter special: mark for potential retaliation handled elsewhere
                if p.role == Role.HUNTER:
                    self.logs.append(f"{p.name} (hunter) died and can shoot")

        # keep inspection logs (already logged in perform_night_action)
        self.reset_actions()
        self.day += 1
        self.state = GameState.DAY
        self.logs.append(f"Day {self.day} begins")
        self.updated_at = datetime.utcnow()
        # check for win conditions after night
        self.check_win_conditions()
        return report

    def tally_votes(self) -> Optional[str]:
        """
        Tally votes from actions recorded during the day and apply elimination.
        Returns eliminated player id as string or None.
        """
        votes = [a for a in self.actions if hasattr(a, "target_id") and isinstance(a, VoteAction)]
        counts: Counter = Counter()
        for v in votes:
            tid = str(v.target_id)
            counts[tid] += getattr(v, "weight", 1)
        if not counts:
            # no votes cast
            self.reset_actions()
            return None
        eliminated_id = max(counts.items(), key=lambda x: x[1])[0]
        try:
            elim_uuid = uuid4()  # placeholder to satisfy typing if invalid
            elim_uuid = UUID(eliminated_id)
        except Exception:
            elim_uuid = None
        if elim_uuid:
            p = self.find_player(elim_uuid)
            if p and p.alive:
                p.alive = False
                self.logs.append(f"{p.name} was eliminated by vote in day {self.day}")
                if p.role == Role.HUNTER:
                    self.logs.append(f"{p.name} (hunter) died and can shoot")
        self.reset_actions()
        # check win/next state
        self.check_win_conditions()
        if self.state != GameState.ENDED:
            self.state = GameState.NIGHT
            self.night += 1
            self.logs.append(f"Night {self.night} begins")
        self.updated_at = datetime.utcnow()
        return eliminated_id

    def check_win_conditions(self):
        """
        Evaluate win conditions and set state to ENDED with a log entry when met.
        """
        wolves = [p for p in self.alive_players() if p.role == Role.WEREWOLF]
        non_wolves = [p for p in self.alive_players() if p.role != Role.WEREWOLF]
        if not wolves:
            self.state = GameState.ENDED
            self.logs.append("Villagers win")
        elif len(wolves) >= len(non_wolves):
            self.state = GameState.ENDED
            self.logs.append("Werewolves win")
        self.updated_at = datetime.utcnow()

# Utilities to load API keys from project root `api_keys.json` or `api_keys.example.json`
def load_api_keys(filename: Optional[str] = None) -> Dict[str, str]:
    root = Path(__file__).resolve().parents[2]  # games/werewolf/backend -> project root
    candidates = []
    if filename:
        candidates.append(root / filename)
    candidates.extend([root / "api_keys.json", root / "api_keys.example.json"])
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {}

__all__ = ["Role", "AIConfig", "Player", "BaseAction", "VoteAction", "NightAction", "GameState", "Game", "load_api_keys"]