"""
LLM Service - 封装 OpenAI SDK 调用（异步 + 重试）

职责：纯 LLM 调用，不涉及存储

设计参考：
- OpenManus: AsyncOpenAI + tenacity retry with exponential backoff
- Vibe-Trading: max_retries, timeout, provider env mapping

变更：使用 AsyncOpenAI 替代 OpenAI，避免阻塞事件循环。
"""
import os
import logging
from typing import Optional, AsyncIterator, List, Dict
from openai import AsyncOpenAI
from openai import APIError, AuthenticationError, RateLimitError, OpenAIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from types import SimpleNamespace

from .provider import provider_registry, Provider

logger = logging.getLogger(__name__)

# 保持向后兼容
AVAILABLE_MODELS = provider_registry.to_frontend_list()
MODEL_MAPPING = {m["id"]: m["model_id"] for m in AVAILABLE_MODELS}

# 需要 reasoning 特殊处理的模型前缀
REASONING_MODEL_PREFIXES = ("o1", "o3")


class LLMService:
    """LLM 服务类，使用 AsyncOpenAI 调用。

    支持多提供商：
    - 根据模型 ID 自动匹配提供商和 base_url
    - 自动重试（指数退避，最多 3 次）
    - 区分 rate limit / auth 错误
    """

    def __init__(self):
        self._clients: Dict[str, AsyncOpenAI] = {}
        self.mock_mode = False
        self.default_model = os.getenv("LLM_MODEL", "")

        for provider in provider_registry.providers:
            api_key = os.getenv(provider.api_key_env)
            if not api_key or api_key == "mock_key":
                logger.debug(f"提供商 {provider.name} 未配置 API Key，跳过")
                continue
            self._clients[provider.name] = AsyncOpenAI(
                base_url=provider.base_url,
                api_key=api_key,
            )
            logger.info(f"LLM 提供商 {provider.name} 已连接 | base_url={provider.base_url}")

        if not self._clients:
            logger.warning("所有提供商均未配置 API Key，启用 Mock 模式")
            self.mock_mode = True

        if not self.default_model:
            best = provider_registry.list_available_models()
            if best:
                self.default_model = best[0].model_id
                logger.info(f"自动选择默认模型: {self.default_model}")

    def _get_client_for_model(self, model_id: str) -> tuple[Optional[AsyncOpenAI], str]:
        """获取模型对应的客户端和解析后的模型 ID。"""
        resolved = provider_registry.resolve_model(model_id, self.default_model)
        model_info = provider_registry.get_model(resolved)

        if model_info:
            provider = provider_registry.get_provider(model_info.provider)
            if provider and provider.name in self._clients:
                return self._clients[provider.name], resolved

        return None, resolved

    def _build_params(
        self,
        resolved_model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: Optional[int],
        stream: bool,
        **kwargs,
    ) -> dict:
        """构建 LLM 请求参数，对 reasoning 模型做特殊处理。"""
        is_reasoning = any(
            resolved_model.startswith(p) for p in REASONING_MODEL_PREFIXES
        )
        params = {
            "model": resolved_model,
            "messages": messages,
            "stream": stream,
        }
        if is_reasoning:
            if max_tokens:
                params["max_completion_tokens"] = max_tokens
        else:
            if max_tokens:
                params["max_tokens"] = max_tokens
            params["temperature"] = temperature

        if "reasoning" in kwargs:
            params["extra_body"] = {"reasoning": kwargs["reasoning"]}
        return params

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIError, OpenAIError)),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: List[Dict],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ):
        """异步非流式/流式聊天完成（带重试）。"""
        client, resolved_model = self._get_client_for_model(model)

        if self.mock_mode or client is None:
            logger.info(f"Mock LLM 调用 | model={resolved_model}")
            content = "这是一个来自 Mock LLM 的回复。后端服务正在运行，但未配置有效的 API Key。"
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                model=resolved_model,
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            )

        params = self._build_params(resolved_model, messages, temperature, max_tokens, False, **kwargs)
        if tools:
            params["tools"] = tools

        logger.debug(f"LLM 请求 | model={resolved_model} | messages={len(messages)} | temp={temperature}")

        try:
            response = await client.chat.completions.create(**params)
            if response.usage:
                logger.info(
                    f"LLM 响应 | model={resolved_model} | "
                    f"prompt={response.usage.prompt_tokens} | "
                    f"completion={response.usage.completion_tokens} | "
                    f"total={response.usage.total_tokens}"
                )
            return response
        except AuthenticationError:
            logger.error(f"LLM 认证失败 | model={resolved_model} | 请检查 API Key")
            raise
        except RateLimitError:
            logger.error(f"LLM 限流 | model={resolved_model}")
            raise
        except APIError as e:
            logger.error(f"LLM API 错误 | model={resolved_model} | error={e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((APIError, OpenAIError)),
        reraise=True,
    )
    async def chat_completion_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """异步流式聊天完成（带重试）。"""
        client, resolved_model = self._get_client_for_model(model)

        if self.mock_mode or client is None:
            logger.info(f"Mock LLM 流式调用 | model={resolved_model}")
            last_msg = messages[-1]["content"] if messages else "未知"
            response_text = (
                f"【Mock 回复】我收到了你的消息：\"{last_msg}\"\n\n"
                f"后端服务链路正常，但未配置有效的 API Key。"
            )
            for char in response_text:
                yield char
            return

        params = self._build_params(resolved_model, messages, temperature, max_tokens, True, **kwargs)

        logger.debug(f"LLM 流式请求 | model={resolved_model} | messages={len(messages)}")

        try:
            stream = await client.chat.completions.create(**params)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError:
            logger.error(f"LLM 认证失败 | model={resolved_model}")
            raise
        except RateLimitError:
            logger.error(f"LLM 限流 | model={resolved_model}")
            raise
        except APIError as e:
            logger.error(f"LLM API 错误 | model={resolved_model} | error={e}")
            raise

    async def chat_completion_with_fallback(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ):
        """带模型回退链的聊天完成。

        当主模型失败（限流、超时、服务不可）时，自动尝试其他模型。
        认证错误不回退（配置问题无法通过换模型解决）。
        """
        resolved_model = model or self.default_model
        fallback_models = provider_registry.get_fallback_models(resolved_model)
        all_models = [resolved_model] + fallback_models

        last_error = None
        for model_id in all_models:
            if model_id != resolved_model:
                logger.warning(f"主模型失败，回退到: {model_id}")
            try:
                return await self.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model_id,
                    tools=tools,
                    **kwargs,
                )
            except AuthenticationError:
                raise  # 配置错误不回退
            except (RateLimitError, APIError, OpenAIError) as e:
                last_error = e
                logger.warning(f"模型 {model_id} 调用失败: {e}")
                continue

        if last_error:
            logger.error(f"所有模型均失败，最后错误: {last_error}")
            raise last_error
        # 所有模型均未配置
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content="所有模型均未配置或不可用。"
            ))],
            model=resolved_model,
            usage=SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )


# 实例化并导出
llm_service = LLMService()
