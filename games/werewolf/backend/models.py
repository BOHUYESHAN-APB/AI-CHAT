from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import random

"""
增强的数据模型：
- 明确记录女巫资源（救人/毒药是否可用）
- Player 增加角色相关状态（例如预言家查看记录）
- NightAction 增加元数据字段用于记录决策来源与结果
- GameState 包含便于推理的 helper 方法
"""

class Role(Enum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    VILLAGER = "villager"

@dataclass
class Player:
    name: str
    role: Role
    alive: bool = True
    meta: Dict[str, Any] = field(default_factory=dict)
    # 女巫资源：仅在该玩家为 WITCH 时有效
    witch_save_available: bool = True
    witch_poison_available: bool = True
    # 预言家查看记录（player_name -> role string），供服务端记录历史
    seer_views: Dict[str, str] = field(default_factory=dict)

@dataclass
class NightAction:
    actor: str
    action: str  # e.g., "vote_kill", "reveal", "witch_save", "witch_poison"
    target: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Vote:
    voter: str
    target: str

@dataclass
class GameState:
    players: List[Player]
    day: int = 0
    state: str = "lobby"  # lobby, night, day, ended
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "players": [p.name for p in self.players],
            "alive": [p.name for p in self.players if p.alive],
            "roles_known_to_server": {p.name: p.role.value for p in self.players},
            "day": self.day,
            "state": self.state,
            "history": self.history[-20:],
            # expose limited per-player state useful for debugging
            "player_states": {
                p.name: {
                    "role": p.role.value,
                    "alive": p.alive,
                    "witch_save_available": p.witch_save_available,
                    "witch_poison_available": p.witch_poison_available,
                    "seer_views": p.seer_views,
                }
                for p in self.players
            },
        }

    def alive_players(self) -> List[str]:
        return [p.name for p in self.players if p.alive]

    def get_player(self, name: str) -> Optional[Player]:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def assign_roles_default(self):
        n = len(self.players)
        roles = default_roles_for(n)
        random.shuffle(roles)
        for p, r in zip(self.players, roles):
            p.role = r
            # initialize role-based resources/state
            p.alive = True
            p.meta = {}
            p.witch_save_available = True
            p.witch_poison_available = True
            p.seer_views = {}

    def check_win(self) -> Optional[str]:
        wolves = [p for p in self.players if p.alive and p.role == Role.WEREWOLF]
        villagers = [p for p in self.players if p.alive and p.role != Role.WEREWOLF]
        if not wolves:
            return "villagers"
        if len(wolves) >= len(villagers):
            return "werewolves"
        return None

    def record_history(self, entry: Dict[str, Any]):
        # ensure history entries are serializable and limited in size
        self.history.append(entry)
        if len(self.history) > 200:
            self.history = self.history[-200:]

    def serialize_for_ai(self) -> Dict[str, Any]:
        """
        返回一个简化的状态字典，供 ai_client 构建提示使用。
        避免泄露不必要的内部状态（例如隐藏其他玩家的 seer_views）
        """
        return {
            "players": [p.name for p in self.players],
            "alive": [p.name for p in self.players if p.alive],
            "roles_known_to_server": {p.name: p.role.value for p in self.players},
            "day": self.day,
            "state": self.state,
            "history": self.history[-20:],
        }

def default_roles_for(n: int) -> List[Role]:
    if n < 4:
        return [Role.VILLAGER] * n
    roles = [Role.WEREWOLF, Role.WEREWOLF, Role.SEER, Role.WITCH]
    roles += [Role.VILLAGER] * (n - 4)
    return roles

def create_default_game(player_names: List[str]) -> GameState:
    players = [Player(name, Role.VILLAGER) for name in player_names]
    gs = GameState(players)
    gs.assign_roles_default()
    return gs