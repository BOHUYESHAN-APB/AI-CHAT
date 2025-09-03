#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
狼人杀游戏引擎
处理游戏规则、状态管理和游戏流程
"""

import logging
import random
from enum import Enum, auto
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

class GamePhase(Enum):
    """游戏阶段枚举"""
    NOT_STARTED = auto()   # 游戏未开始
    NIGHT = auto()         # 夜晚阶段
    DAY = auto()           # 白天阶段
    VOTING = auto()        # 投票阶段
    GAME_OVER = auto()     # 游戏结束

class PlayerStatus(Enum):
    """玩家状态枚举"""
    ALIVE = auto()         # 存活
    DEAD = auto()          # 死亡
    EXILED = auto()        # 被放逐

class Team(Enum):
    """阵营枚举"""
    VILLAGER = "villager"  # 村民阵营
    WEREWOLF = "werewolf"  # 狼人阵营

@dataclass
class Player:
    """玩家类"""
    id: int
    name: str
    role: str
    team: Team
    status: PlayerStatus = PlayerStatus.ALIVE
    is_ai: bool = True
    ai_provider: Optional[str] = None
    
    def __str__(self):
        return f"{self.name} ({self.role})"

@dataclass
class GameEvent:
    """游戏事件"""
    type: str
    round: int
    phase: GamePhase
    source_player: Optional[Player] = None
    target_player: Optional[Player] = None
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class GameState:
    """游戏状态"""
    phase: GamePhase = GamePhase.NOT_STARTED
    round: int = 0
    players: List[Player] = field(default_factory=list)
    alive_players: List[Player] = field(default_factory=list)
    dead_players: List[Player] = field(default_factory=list)
    events: List[GameEvent] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.alive_players = [p for p in self.players if p.status == PlayerStatus.ALIVE]
        self.dead_players = [p for p in self.players if p.status != PlayerStatus.ALIVE]

class GameEngine:
    """狼人杀游戏引擎"""
    
    def __init__(self):
        self.state = GameState()
        self.role_definitions = self._load_role_definitions()
        
    def _load_role_definitions(self) -> Dict[str, Dict]:
        """加载角色定义"""
        return {
            "werewolf": {
                "name": "狼人",
                "team": Team.WEREWOLF,
                "description": "夜晚可以杀死一名玩家",
                "night_action": True,
                "priority": 10
            },
            "villager": {
                "name": "村民",
                "team": Team.VILLAGER,
                "description": "没有特殊能力，依靠投票找出狼人",
                "night_action": False,
                "priority": 100
            },
            "prophet": {
                "name": "预言家",
                "team": Team.VILLAGER,
                "description": "每晚可以查验一名玩家的真实身份",
                "night_action": True,
                "priority": 20
            },
            "witch": {
                "name": "女巫",
                "team": Team.VILLAGER,
                "description": "拥有一瓶解药和一瓶毒药，每晚只能使用一瓶",
                "night_action": True,
                "priority": 30
            }
        }
    
    def initialize_game(self, player_count: int = 8, role_distribution: Optional[Dict[str, int]] = None):
        """
        初始化游戏
        
        Args:
            player_count: 玩家数量
            role_distribution: 角色分布配置
        """
        try:
            # 设置默认角色分布
            if role_distribution is None:
                role_distribution = {
                    "werewolf": 2,
                    "villager": 4,
                    "prophet": 1,
                    "witch": 1
                }
            
            # 验证角色分布
            total_roles = sum(role_distribution.values())
            if total_roles != player_count:
                raise ValueError(f"角色总数({total_roles})与玩家数量({player_count})不匹配")
            
            # 创建玩家列表
            players = []
            role_list = []
            
            # 生成角色列表
            for role, count in role_distribution.items():
                role_list.extend([role] * count)
            
            # 随机分配角色
            random.shuffle(role_list)
            
            # 创建玩家对象
            for i, role in enumerate(role_list):
                role_def = self.role_definitions[role]
                player = Player(
                    id=i + 1,
                    name=f"玩家{i + 1}",
                    role=role,
                    team=role_def["team"],
                    is_ai=True
                )
                players.append(player)
            
            # 更新游戏状态
            self.state = GameState(
                phase=GamePhase.NOT_STARTED,
                round=0,
                players=players,
                alive_players=players.copy(),
                dead_players=[],
                events=[],
                settings={
                    "player_count": player_count,
                    "role_distribution": role_distribution
                }
            )
            
            # 记录游戏开始事件
            self._add_event("game_start", "游戏开始")
            
            logger.info(f"✅ 游戏初始化完成，{player_count}名玩家")
            return True
            
        except Exception as e:
            logger.error(f"❌ 游戏初始化失败: {e}")
            return False
    
    def start_game(self):
        """开始游戏"""
        if self.state.phase != GamePhase.NOT_STARTED:
            logger.warning("⚠️ 游戏已经开始或已结束")
            return False
        
        self.state.phase = GamePhase.NIGHT
        self.state.round = 1
        
        self._add_event("phase_change", "进入第一夜")
        logger.info("🌙 游戏开始 - 第一夜")
        return True
    
    def next_phase(self):
        """进入下一阶段"""
        try:
            if self.state.phase == GamePhase.NOT_STARTED:
                return self.start_game()
            
            elif self.state.phase == GamePhase.NIGHT:
                # 夜晚结束，进入白天
                self.state.phase = GamePhase.DAY
                self._add_event("phase_change", "进入白天")
                logger.info("☀️ 进入白天阶段")
                return True
                
            elif self.state.phase == GamePhase.DAY:
                # 白天结束，进入投票
                self.state.phase = GamePhase.VOTING
                self._add_event("phase_change", "进入投票阶段")
                logger.info("🗳️ 进入投票阶段")
                return True
                
            elif self.state.phase == GamePhase.VOTING:
                # 投票结束，进入下一夜或游戏结束
                if self._check_game_over():
                    self.state.phase = GamePhase.GAME_OVER
                    self._add_event("game_over", "游戏结束")
                    logger.info("🎮 游戏结束")
                else:
                    self.state.phase = GamePhase.NIGHT
                    self.state.round += 1
                    self._add_event("phase_change", f"进入第{self.state.round}夜")
                    logger.info(f"🌙 进入第{self.state.round}夜")
                return True
                
            else:
                logger.warning("⚠️ 游戏已结束，无法进入下一阶段")
                return False
                
        except Exception as e:
            logger.error(f"❌ 阶段切换失败: {e}")
            return False
    
    def perform_night_action(self, player: Player, target: Optional[Player] = None) -> bool:
        """
        执行夜晚行动
        
        Args:
            player: 执行行动的玩家
            target: 目标玩家（可选）
            
        Returns:
            bool: 行动是否成功
        """
        try:
            if self.state.phase != GamePhase.NIGHT:
                logger.warning("⚠️ 当前不是夜晚阶段，无法执行夜晚行动")
                return False
            
            if player.status != PlayerStatus.ALIVE:
                logger.warning("⚠️ 死亡玩家无法执行行动")
                return False
            
            role_def = self.role_definitions.get(player.role)
            if not role_def or not role_def.get("night_action", False):
                logger.warning(f"⚠️ 角色 {player.role} 没有夜晚行动能力")
                return False
            
            # 根据不同角色执行不同的夜晚行动
            action_result = self._execute_role_action(player, target)
            
            if action_result:
                action_desc = f"{player.name}({player.role}) 执行了夜晚行动"
                if target:
                    action_desc += f"，目标: {target.name}"
                self._add_event("night_action", action_desc, player, target)
                logger.info(action_desc)
            
            return action_result
            
        except Exception as e:
            logger.error(f"❌ 夜晚行动执行失败: {e}")
            return False
    
    def _execute_role_action(self, player: Player, target: Optional[Player]) -> bool:
        """执行具体角色行动"""
        if player.role == "werewolf":
            return self._werewolf_action(player, target)
        elif player.role == "prophet":
            return self._prophet_action(player, target)
        elif player.role == "witch":
            return self._witch_action(player, target)
        return False
    
    def _werewolf_action(self, player: Player, target: Player) -> bool:
        """狼人行动 - 杀人"""
        if not target or target.status != PlayerStatus.ALIVE:
            return False
        
        # 标记目标为死亡
        target.status = PlayerStatus.DEAD
        self._update_player_lists()
        
        self._add_event("player_killed", f"{target.name} 被狼人杀害", player, target)
        return True
    
    def _prophet_action(self, player: Player, target: Player) -> bool:
        """预言家行动 - 查验身份"""
        if not target or target.status != PlayerStatus.ALIVE:
            return False
        
        # 返回查验结果（在实际实现中，这会返回给玩家）
        is_werewolf = target.role == "werewolf"
        result = "狼人" if is_werewolf else "好人"
        
        self._add_event("prophet_check", 
                       f"{player.name} 查验了 {target.name}，身份: {result}", 
                       player, target)
        return True
    
    def _witch_action(self, player: Player, target: Player) -> bool:
        """女巫行动 - 使用药水"""
        # 简化实现：女巫总是救人
        if target and target.status == PlayerStatus.DEAD:
            target.status = PlayerStatus.ALIVE
            self._update_player_lists()
            
            self._add_event("witch_save", 
                           f"{player.name} 使用解药救了 {target.name}", 
                           player, target)
            return True
        return False
    
    def vote_player(self, voter: Player, candidate: Player) -> bool:
        """
        玩家投票
        
        Args:
            voter: 投票的玩家
            candidate: 被投票的玩家
            
        Returns:
            bool: 投票是否成功
        """
        if self.state.phase != GamePhase.VOTING:
            logger.warning("⚠️ 当前不是投票阶段")
            return False
        
        if voter.status != PlayerStatus.ALIVE:
            logger.warning("⚠️ 死亡玩家不能投票")
            return False
        
        if candidate.status != PlayerStatus.ALIVE:
            logger.warning("⚠️ 不能投票给死亡玩家")
            return False
        
        # 记录投票（简化实现）
        self._add_event("vote", 
                       f"{voter.name} 投票给 {candidate.name}", 
                       voter, candidate)
        return True
    
    def _check_game_over(self) -> bool:
        """检查游戏是否结束"""
        # 统计各阵营存活玩家
        werewolf_count = 0
        villager_count = 0
        
        for player in self.state.alive_players:
            if player.team == Team.WEREWOLF:
                werewolf_count += 1
            else:
                villager_count += 1
        
        # 检查胜利条件
        if werewolf_count == 0:
            self._add_event("victory", "村民阵营胜利！")
            logger.info("🎉 村民阵营胜利！")
            return True
        
        if werewolf_count >= villager_count:
            self._add_event("victory", "狼人阵营胜利！")
            logger.info("🎉 狼人阵营胜利！")
            return True
        
        return False
    
    def _update_player_lists(self):
        """更新存活和死亡玩家列表"""
        self.state.alive_players = [p for p in self.state.players if p.status == PlayerStatus.ALIVE]
        self.state.dead_players = [p for p in self.state.players if p.status != PlayerStatus.ALIVE]
    
    def _add_event(self, event_type: str, description: str, 
                  source: Optional[Player] = None, target: Optional[Player] = None):
        """添加游戏事件"""
        event = GameEvent(
            type=event_type,
            round=self.state.round,
            phase=self.state.phase,
            source_player=source,
            target_player=target,
            description=description
        )
        self.state.events.append(event)
    
    def get_game_info(self) -> Dict[str, Any]:
        """获取游戏信息"""
        return {
            "phase": self.state.phase.name,
            "round": self.state.round,
            "total_players": len(self.state.players),
            "alive_players": len(self.state.alive_players),
            "dead_players": len(self.state.dead_players),
            "events_count": len(self.state.events)
        }

# 测试函数
if __name__ == "__main__":
    # 简单测试游戏引擎
    engine = GameEngine()
    
    # 初始化游戏
    success = engine.initialize_game(player_count=8)
    if success:
        print("✅ 游戏初始化成功")
        
        # 开始游戏
        engine.start_game()
        print(f"游戏阶段: {engine.state.phase.name}")
        
        # 获取游戏信息
        info = engine.get_game_info()
        print(f"存活玩家: {info['alive_players']}/{info['total_players']}")
        
        # 显示玩家信息
        print("\n玩家列表:")
        for player in engine.state.players:
            print(f"  {player.id}. {player.name} - {player.role} ({player.team.value})")
    else:
        print("❌ 游戏初始化失败")