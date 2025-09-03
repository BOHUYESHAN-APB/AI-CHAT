#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI控制器
处理与各种AI API的通信和交互
"""

import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """AI响应数据类"""
    success: bool
    content: str
    provider: str
    model: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None

class BaseAIProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "Unknown")
        self.provider = config.get("provider", "unknown")
        self.model = config.get("model", "")
        self.api_key = config.get("api_key", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1000)
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    async def send_message(self, message: str, **kwargs) -> AIResponse:
        """发送消息给AI并获取响应"""
        pass
    
    @abstractmethod
    async def get_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            logger.error(f"❌ {self.name}: API密钥为空")
            return False
        if not self.model:
            logger.error(f"❌ {self.name}: 模型名为空")
            return False
        return True

class OpenAIClient(BaseAIProvider):
    """OpenAI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.openai.com/v1"
    
    async def send_message(self, message: str, **kwargs) -> AIResponse:
        """发送消息到OpenAI API"""
        if not self.validate_config():
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error="配置验证失败"
            )
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": message}],
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        
                        return AIResponse(
                            success=True,
                            content=content,
                            provider=self.provider,
                            model=self.model,
                            usage=usage
                        )
                    else:
                        error_text = await response.text()
                        return AIResponse(
                            success=False,
                            content="",
                            provider=self.provider,
                            model=self.model,
                            error=f"API错误: {response.status} - {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"❌ OpenAI请求失败: {e}")
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error=str(e)
            )
    
    async def get_models(self) -> List[str]:
        """获取OpenAI支持的模型列表"""
        # 简化实现，返回常见模型
        return [
            "gpt-4", "gpt-4-turbo", "gpt-4-32k",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]

class AnthropicClient(BaseAIProvider):
    """Anthropic (Claude) 客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://api.anthropic.com/v1"
        self.version = "2023-06-01"
    
    async def send_message(self, message: str, **kwargs) -> AIResponse:
        """发送消息到Anthropic API"""
        if not self.validate_config():
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error="配置验证失败"
            )
        
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": self.version,
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": message}],
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data["content"][0]["text"]
                        
                        return AIResponse(
                            success=True,
                            content=content,
                            provider=self.provider,
                            model=self.model
                        )
                    else:
                        error_text = await response.text()
                        return AIResponse(
                            success=False,
                            content="",
                            provider=self.provider,
                            model=self.model,
                            error=f"API错误: {response.status} - {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"❌ Anthropic请求失败: {e}")
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error=str(e)
            )
    
    async def get_models(self) -> List[str]:
        """获取Anthropic支持的模型列表"""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0"
        ]

class GoogleAIClient(BaseAIProvider):
    """Google AI客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def send_message(self, message: str, **kwargs) -> AIResponse:
        """发送消息到Google AI API"""
        if not self.validate_config():
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error="配置验证失败"
            )
        
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [{"text": message}]
                }],
                "generationConfig": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "maxOutputTokens": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data["candidates"][0]["content"]["parts"][0]["text"]
                        
                        return AIResponse(
                            success=True,
                            content=content,
                            provider=self.provider,
                            model=self.model
                        )
                    else:
                        error_text = await response.text()
                        return AIResponse(
                            success=False,
                            content="",
                            provider=self.provider,
                            model=self.model,
                            error=f"API错误: {response.status} - {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"❌ Google AI请求失败: {e}")
            return AIResponse(
                success=False,
                content="",
                provider=self.provider,
                model=self.model,
                error=str(e)
            )
    
    async def get_models(self) -> List[str]:
        """获取Google AI支持的模型列表"""
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-ultra"
        ]

class AIController:
    """AI控制器，管理所有AI提供商"""
    
    def __init__(self):
        self.providers: Dict[str, BaseAIProvider] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    def initialize_providers(self, provider_configs: List[Dict[str, Any]]) -> bool:
        """
        初始化AI提供商
        
        Args:
            provider_configs: 提供商配置列表
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            self.providers.clear()
            
            for config in provider_configs:
                provider_type = config.get("provider", "").lower()
                enabled = config.get("enabled", True)
                
                if not enabled:
                    logger.info(f"⏭️ 跳过禁用的提供商: {config.get('name')}")
                    continue
                
                provider = self._create_provider(provider_type, config)
                if provider and provider.validate_config():
                    self.providers[config["name"]] = provider
                    logger.info(f"✅ 初始化AI提供商: {config['name']} ({provider_type})")
                else:
                    logger.warning(f"⚠️ 跳过无效的AI提供商: {config['name']}")
            
            logger.info(f"✅ 共初始化 {len(self.providers)} 个AI提供商")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI提供商初始化失败: {e}")
            return False
    
    def _create_provider(self, provider_type: str, config: Dict[str, Any]) -> Optional[BaseAIProvider]:
        """创建具体的AI提供商实例"""
        try:
            if provider_type == "openai":
                return OpenAIClient(config)
            elif provider_type == "anthropic":
                return AnthropicClient(config)
            elif provider_type == "google":
                return GoogleAIClient(config)
            else:
                logger.warning(f"⚠️ 不支持的AI提供商类型: {provider_type}")
                return None
        except Exception as e:
            logger.error(f"❌ 创建AI提供商失败: {e}")
            return None
    
    async def send_message(self, provider_name: str, message: str, **kwargs) -> AIResponse:
        """
        通过指定提供商发送消息
        
        Args:
            provider_name: 提供商名称
            message: 要发送的消息
            **kwargs: 额外参数
            
        Returns:
            AIResponse: AI响应
        """
        provider = self.providers.get(provider_name)
        if not provider:
            return AIResponse(
                success=False,
                content="",
                provider="unknown",
                model="",
                error=f"未找到提供商: {provider_name}"
            )
        
        return await provider.send_message(message, **kwargs)
    
    async def broadcast_message(self, message: str, **kwargs) -> Dict[str, AIResponse]:
        """
        向所有启用的提供商广播消息
        
        Args:
            message: 要发送的消息
            **kwargs: 额外参数
            
        Returns:
            Dict[str, AIResponse]: 各提供商的响应
        """
        results = {}
        
        for provider_name, provider in self.providers.items():
            if provider.enabled:
                response = await provider.send_message(message, **kwargs)
                results[provider_name] = response
        
        return results
    
    def get_provider_names(self) -> List[str]:
        """获取所有提供商名称"""
        return list(self.providers.keys())
    
    def get_enabled_providers(self) -> List[str]:
        """获取所有启用的提供商名称"""
        return [name for name, provider in self.providers.items() if provider.enabled]
    
    async def test_connection(self, provider_name: str) -> bool:
        """测试提供商连接"""
        provider = self.providers.get(provider_name)
        if not provider:
            return False
        
        # 发送简单的测试消息
        test_message = "Hello! Please respond with 'OK' if you can hear me."
        response = await provider.send_message(test_message, max_tokens=10)
        
        return response.success and "OK" in response.content.upper()
    
    async def close(self):
        """关闭所有连接"""
        if self.session:
            await self.session.close()

# 测试函数
async def test_ai_controller():
    """测试AI控制器"""
    controller = AIController()
    
    # 测试配置
    test_configs = [
        {
            "name": "Test OpenAI",
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-3.5-turbo",
            "enabled": True
        }
    ]
    
    # 初始化提供商
    success = controller.initialize_providers(test_configs)
    print(f"初始化结果: {success}")
    print(f"提供商列表: {controller.get_provider_names()}")
    
    # 测试消息发送（会失败，因为API密钥无效）
    if success:
        response = await controller.send_message(
            "Test OpenAI", 
            "Hello, this is a test message."
        )
        print(f"响应成功: {response.success}")
        if not response.success:
            print(f"错误信息: {response.error}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_ai_controller())