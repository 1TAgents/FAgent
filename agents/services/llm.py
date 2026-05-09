"""
LLM Service - 封装 OpenAI SDK 调用

职责：纯 LLM 调用，不涉及存储

注意：环境变量需要在启动服务前设置好（通过 .env 加载或 export）

集成 provider registry 以支持多提供商模型管理和能力追踪。
"""
import os
import sys
import logging
import asyncio
from typing import Optional, Iterator, List, Dict, Any
from openai import OpenAI
from types import SimpleNamespace

from .provider import provider_registry, Provider

# 设置 logger
logger = logging.getLogger(__name__)

# 保持向后兼容：导出 AVAILABLE_MODELS 和 MODEL_MAPPING 供旧代码使用
AVAILABLE_MODELS = provider_registry.to_frontend_list()
MODEL_MAPPING = {m["id"]: m["model_id"] for m in AVAILABLE_MODELS}


class LLMService:
    """LLM 服务类，封装 OpenAI SDK 调用。

    支持多提供商：
    - 根据模型 ID 自动匹配提供商和 base_url
    - 支持 provider fallback（主模型失败时自动切换）
    - 追踪模型能力和 token 使用
    """

    def __init__(self):
        self._clients: Dict[str, OpenAI] = {}  # provider_name -> client
        self.mock_mode = False
        self.default_model = os.getenv("LLM_MODEL", "")

        # 初始化各提供商的客户端
        for provider in provider_registry.providers:
            api_key = os.getenv(provider.api_key_env)
            if not api_key or api_key == "mock_key":
                logger.debug(f"提供商 {provider.name} 未配置 API Key，跳过")
                continue
            self._clients[provider.name] = OpenAI(
                base_url=provider.base_url,
                api_key=api_key,
            )
            logger.info(f"LLM 提供商 {provider.name} 已连接 | base_url={provider.base_url}")

        if not self._clients:
            logger.warning("所有提供商均未配置 API Key，启用 Mock 模式")
            self.mock_mode = True

        if not self.default_model:
            # 使用 provider registry 中优先级最高的模型
            best = provider_registry.list_available_models()
            if best:
                self.default_model = best[0].model_id
                logger.info(f"自动选择默认模型: {self.default_model}")

    def _get_client_for_model(self, model_id: str) -> tuple[Optional[OpenAI], str]:
        """获取模型对应的客户端和解析后的模型 ID。

        Returns:
            (client, resolved_model_id) - client 为 None 表示 mock 模式
        """
        resolved = provider_registry.resolve_model(model_id, self.default_model)
        model_info = provider_registry.get_model(resolved)

        if model_info:
            provider = provider_registry.get_provider(model_info.provider)
            if provider and provider.name in self._clients:
                return self._clients[provider.name], resolved

        return None, resolved

    def _resolve_model(self, model: Optional[str] = None) -> str:
        """解析模型名称（向后兼容）。"""
        _, resolved = self._get_client_for_model(model or self.default_model)
        return resolved

    def get_model_info(self, model: Optional[str] = None):
        """获取模型信息。"""
        resolved = self._resolve_model(model)
        return provider_registry.get_model(resolved)

    def chat_completion(
        self,
        messages: List[Dict],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        """非流式聊天完成。"""
        client, resolved_model = self._get_client_for_model(model)

        if self.mock_mode or client is None:
            logger.info(f"Mock LLM 调用 (非流式) | model={resolved_model}")
            content = "这是一个来自 Mock LLM 的回复。后端服务正在运行，但未配置有效的 API Key。"
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=content)
                    )
                ],
                model=resolved_model,
                usage=SimpleNamespace(
                    prompt_tokens=10,
                    completion_tokens=20,
                    total_tokens=30
                )
            )

        params = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if max_tokens:
            params["max_tokens"] = max_tokens

        if "reasoning" in kwargs:
            params["extra_body"] = {"reasoning": kwargs["reasoning"]}

        logger.debug(f"LLM 非流式请求 | model={resolved_model} | messages_count={len(messages)} | temp={temperature}")

        try:
            response = client.chat.completions.create(**params)
            if response.usage:
                logger.info(
                    f"LLM 响应完成 | model={resolved_model} | "
                    f"prompt_tokens={response.usage.prompt_tokens} | "
                    f"completion_tokens={response.usage.completion_tokens} | "
                    f"total_tokens={response.usage.total_tokens}"
                )
            return response
        except Exception as e:
            logger.error(f"LLM 调用失败 | model={resolved_model} | error={str(e)}")
            raise

    def chat_completion_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Iterator[str]:
        """流式聊天完成。"""
        client, resolved_model = self._get_client_for_model(model)

        if self.mock_mode or client is None:
            logger.info(f"Mock LLM 调用 (流式) | model={resolved_model}")
            last_msg = messages[-1]['content'] if messages else "未知"
            response_text = f"【Mock 回复】\n我收到了你的消息：\"{last_msg}\"\n\n后端服务链路正常（Frontend -> Backend -> Agents），但由于未配置有效的 OPENROUTER_API_KEY，Agents 服务当前运行在 Mock 模式。请在 .env 文件中配置 API Key 以接入真实的大模型。"
            import time
            for char in response_text:
                time.sleep(0.02)
                yield char
            return

        params = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            params["max_tokens"] = max_tokens

        if "reasoning" in kwargs:
            params["extra_body"] = {"reasoning": kwargs["reasoning"]}

        logger.debug(f"LLM 流式请求 | model={resolved_model} | messages_count={len(messages)} | temp={temperature}")

        try:
            stream = client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LLM 流式调用失败 | model={resolved_model} | error={str(e)}")
            raise


# 实例化并导出
llm_service = LLMService()
