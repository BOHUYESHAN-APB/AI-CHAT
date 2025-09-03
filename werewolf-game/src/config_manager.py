#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件管理类
处理YAML配置文件的加载、验证和保存
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)

@dataclass
class AIProviderConfig:
    """AI服务提供商配置"""
    name: str
    provider: str  # openai, anthropic, google
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    enabled: bool = True

@dataclass
class GameSettings:
    """游戏设置"""
    display_theme: str = "dark"  # light/dark/system
    language: str = "zh-CN"
    font_size: int = 12
    chat_style: str = "bubble"  # bubble/list
    layout: str = "circular"  # circular/grid/linear

@dataclass
class WerewolfGameSettings:
    """狼人杀游戏特定设置"""
    player_count: int = 8
    roles: Dict[str, int] = None  # 角色数量配置
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = {
                "werewolf": 2,
                "villager": 4,
                "prophet": 1,
                "witch": 1
            }

class ConfigManager:
    """配置文件管理器"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        self.default_config = self._get_default_config()
        self.current_config: Dict[str, Any] = {}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "1.0.0",
            "ai_providers": [
                {
                    "name": "GPT-4",
                    "provider": "openai",
                    "api_key": "",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": True
                },
                {
                    "name": "Claude-3",
                    "provider": "anthropic", 
                    "api_key": "",
                    "model": "claude-3-sonnet-20240229",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "enabled": True
                }
            ],
            "game_settings": {
                "display": {
                    "theme": "dark",
                    "language": "zh-CN",
                    "font_size": 12,
                    "chat_style": "bubble",
                    "layout": "circular"
                },
                "chat": {
                    "show_timestamps": True,
                    "show_avatars": True,
                    "avatar_size": 40,
                    "bubble_max_width": 300,
                    "animation_enabled": True
                }
            },
            "werewolf_game": {
                "default_settings": {
                    "player_count": 8,
                    "roles": {
                        "werewolf": 2,
                        "villager": 4,
                        "prophet": 1,
                        "witch": 1
                    }
                },
                "game_flow": {
                    "day_time_limit": 120,
                    "night_time_limit": 60,
                    "voting_time_limit": 30,
                    "auto_proceed": False
                }
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "file_path": "logs/game.log",
                "max_file_size": 10485760,
                "backup_count": 5
            }
        }
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 是否成功加载配置
        """
        try:
            # 确保配置目录存在
            self.config_path.parent.mkdir(exist_ok=True)
            
            # 如果配置文件不存在，创建默认配置
            if not self.config_path.exists():
                logger.warning("⚠️ 配置文件不存在，创建默认配置")
                self._create_default_config()
                return True
            
            # 读取配置文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
            
            # 验证配置
            if self._validate_config(loaded_config):
                self.current_config = self._merge_configs(loaded_config)
                logger.info("✅ 配置文件加载成功")
                return True
            else:
                logger.warning("⚠️ 配置验证失败，使用默认配置")
                self.current_config = self.default_config.copy()
                return False
                
        except Exception as e:
            logger.error(f"❌ 配置文件加载失败: {e}")
            self.current_config = self.default_config.copy()
            return False
    
    def _create_default_config(self):
        """创建默认配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.default_config, f, allow_unicode=True, sort_keys=False)
            logger.info("✅ 默认配置文件创建成功")
        except Exception as e:
            logger.error(f"❌ 创建默认配置文件失败: {e}")
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置文件格式"""
        try:
            # 检查必需字段
            if "version" not in config:
                logger.warning("⚠️ 配置缺少版本号")
                return False
            
            # 检查AI提供商配置
            if "ai_providers" not in config or not isinstance(config["ai_providers"], list):
                logger.warning("⚠️ AI提供商配置格式错误")
                return False
            
            # 验证每个AI提供商配置
            for provider in config["ai_providers"]:
                if not self._validate_ai_provider(provider):
                    return False
            
            # 检查游戏设置
            if "game_settings" not in config:
                logger.warning("⚠️ 游戏设置配置缺失")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置验证过程中发生错误: {e}")
            return False
    
    def _validate_ai_provider(self, provider: Dict[str, Any]) -> bool:
        """验证单个AI提供商配置"""
        required_fields = ["name", "provider", "api_key", "model"]
        
        for field in required_fields:
            if field not in provider or not provider[field]:
                logger.warning(f"⚠️ AI提供商配置缺少必需字段: {field}")
                return False
        
        # 检查提供商类型
        valid_providers = ["openai", "anthropic", "google"]
        if provider["provider"] not in valid_providers:
            logger.warning(f"⚠️ 不支持的AI提供商: {provider['provider']}")
            return False
        
        return True
    
    def _merge_configs(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并加载的配置和默认配置"""
        merged = self.default_config.copy()
        
        # 递归合并配置
        def _merge_dicts(default: Dict, new: Dict) -> Dict:
            for key, value in new.items():
                if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                    default[key] = _merge_dicts(default[key], value)
                else:
                    default[key] = value
            return default
        
        return _merge_dicts(merged, loaded_config)
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存配置文件
        
        Args:
            config: 要保存的配置，如果为None则保存当前配置
            
        Returns:
            bool: 是否成功保存
        """
        try:
            config_to_save = config or self.current_config
            
            # 确保配置目录存在
            self.config_path.parent.mkdir(exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_to_save, f, allow_unicode=True, sort_keys=False)
            
            logger.info("✅ 配置文件保存成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置文件保存失败: {e}")
            return False
    
    def get_ai_providers(self) -> List[AIProviderConfig]:
        """获取AI提供商配置列表"""
        providers = []
        for provider_config in self.current_config.get("ai_providers", []):
            try:
                provider = AIProviderConfig(**provider_config)
                providers.append(provider)
            except Exception as e:
                logger.warning(f"⚠️ 无效的AI提供商配置: {e}")
        return providers
    
    def get_game_settings(self) -> GameSettings:
        """获取游戏设置"""
        game_settings = self.current_config.get("game_settings", {})
        display_settings = game_settings.get("display", {})
        
        return GameSettings(
            display_theme=display_settings.get("theme", "dark"),
            language=display_settings.get("language", "zh-CN"),
            font_size=display_settings.get("font_size", 12),
            chat_style=display_settings.get("chat_style", "bubble"),
            layout=display_settings.get("layout", "circular")
        )
    
    def get_werewolf_settings(self) -> WerewolfGameSettings:
        """获取狼人杀游戏设置"""
        werewolf_settings = self.current_config.get("werewolf_game", {})
        default_settings = werewolf_settings.get("default_settings", {})
        
        return WerewolfGameSettings(
            player_count=default_settings.get("player_count", 8),
            roles=default_settings.get("roles", {
                "werewolf": 2,
                "villager": 4,
                "prophet": 1,
                "witch": 1
            })
        )
    
    def update_ai_provider(self, provider_name: str, updates: Dict[str, Any]) -> bool:
        """更新AI提供商配置"""
        for i, provider in enumerate(self.current_config.get("ai_providers", [])):
            if provider["name"] == provider_name:
                self.current_config["ai_providers"][i].update(updates)
                return self.save_config()
        return False
    
    def add_ai_provider(self, provider_config: Dict[str, Any]) -> bool:
        """添加新的AI提供商"""
        if self._validate_ai_provider(provider_config):
            self.current_config["ai_providers"].append(provider_config)
            return self.save_config()
        return False
    
    def remove_ai_provider(self, provider_name: str) -> bool:
        """移除AI提供商"""
        providers = self.current_config.get("ai_providers", [])
        self.current_config["ai_providers"] = [
            p for p in providers if p["name"] != provider_name
        ]
        return self.save_config()

# 测试函数
if __name__ == "__main__":
    # 简单测试配置管理器
    config_manager = ConfigManager()
    success = config_manager.load_config()
    
    if success:
        print("✅ 配置加载成功")
        providers = config_manager.get_ai_providers()
        print(f"找到 {len(providers)} 个AI提供商")
        
        for provider in providers:
            print(f"  - {provider.name} ({provider.provider})")
    else:
        print("❌ 配置加载失败")