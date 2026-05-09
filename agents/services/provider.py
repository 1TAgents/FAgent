"""
Provider Registry - 多模型提供商管理

管理多个 LLM 提供商及其模型能力信息。
设计参考：Vibe-Trading 的 multi-provider 系统。

核心概念：
- Provider: 一个 LLM 提供商（OpenRouter, DashScope, Ollama 等）
- ModelInfo: 一个模型的详细信息和能力
- ProviderRegistry: 注册和管理所有提供商
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    """模型的详细信息。

    属性：
    - model_id: 提供商的完整模型 ID（如 qwen/qwen3.5-plus）
    - display_name: 前端显示名（如 Qwen 3.5 Plus）
    - provider: 提供商名称
    - context_window: 上下文窗口大小（tokens）
    - max_output_tokens: 最大输出 tokens
    - supports_tool_use: 是否支持工具调用
    - supports_reasoning: 是否支持 reasoning
    - cost_per_1m_input: 每百万输入 token 价格（USD）
    - cost_per_1m_output: 每百万输出 token 价格（USD）
    - priority: 优先级（数值越小优先级越高）
    """
    model_id: str
    display_name: str
    provider: str
    context_window: int = 32000
    max_output_tokens: int = 8192
    supports_tool_use: bool = True
    supports_reasoning: bool = False
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    priority: int = 10
    description: str = ""

    @property
    def short_id(self) -> str:
        """返回简短 ID（去掉 provider 前缀）。"""
        parts = self.model_id.split("/")
        return parts[-1].split(":")[0] if len(parts) > 1 else self.model_id.split(":")[0]


@dataclass
class Provider:
    """LLM 提供商配置。"""
    name: str
    base_url: str
    api_key_env: str
    models: List[ModelInfo] = field(default_factory=list)

    @property
    def model_ids(self) -> List[str]:
        return [m.model_id for m in self.models]

    @property
    def model_short_ids(self) -> Dict[str, ModelInfo]:
        """short_id -> ModelInfo 的映射。"""
        return {m.short_id: m for m in self.models}

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """通过 model_id 或 short_id 查找模型。"""
        for m in self.models:
            if m.model_id == model_id or m.short_id == model_id:
                return m
        return None


class ProviderRegistry:
    """提供商注册中心。

    管理多个 LLM 提供商，提供统一的模型查询和解析接口。
    """

    def __init__(self):
        self._providers: Dict[str, Provider] = {}
        self._all_models: Dict[str, ModelInfo] = {}  # model_id/short_id -> ModelInfo

    def register(self, provider: Provider) -> None:
        """注册一个提供商。"""
        self._providers[provider.name] = provider
        for model in provider.models:
            self._all_models[model.model_id] = model
            self._all_models[model.short_id] = model
        logger.info(f"注册提供商: {provider.name} ({len(provider.models)} models)")

    def get_provider(self, name: str) -> Optional[Provider]:
        return self._providers.get(name)

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._all_models.get(model_id)

    @property
    def all_models(self) -> List[ModelInfo]:
        return list(self._all_models.values())

    @property
    def providers(self) -> List[Provider]:
        return list(self._providers.values())

    def list_available_models(
        self,
        *,
        supports_tool_use: Optional[bool] = None,
        supports_reasoning: Optional[bool] = None,
        max_cost_input: Optional[float] = None,
        min_context_window: Optional[int] = None,
    ) -> List[ModelInfo]:
        """按能力筛选模型。"""
        models = list(self._all_models.values())
        if supports_tool_use is not None:
            models = [m for m in models if m.supports_tool_use == supports_tool_use]
        if supports_reasoning is not None:
            models = [m for m in models if m.supports_reasoning == supports_reasoning]
        if max_cost_input is not None:
            models = [m for m in models if m.cost_per_1m_input <= max_cost_input]
        if min_context_window is not None:
            models = [m for m in models if m.context_window >= min_context_window]
        return sorted(models, key=lambda m: m.priority)

    def resolve_model(self, model: str, default: Optional[str] = None) -> str:
        """解析模型 ID。

        支持 short_id 和完整 model_id，返回完整的 model_id。
        """
        info = self.get_model(model)
        if info:
            return info.model_id
        return model if model else default or ""

    def get_fallback_models(self, primary: str) -> List[str]:
        """获取主模型失败后的回退模型列表。

        按优先级排序，返回同级或更低优先级的模型。
        """
        primary_info = self.get_model(primary)
        if not primary_info:
            return []

        # 返回相同 provider 的其他模型，按优先级排序
        provider = self.get_provider(primary_info.provider)
        if not provider:
            return []

        fallbacks = []
        for m in sorted(provider.models, key=lambda x: x.priority):
            if m.model_id != primary:
                fallbacks.append(m.model_id)
        return fallbacks

    def to_frontend_list(self) -> List[dict]:
        """生成前端展示用的模型列表。"""
        result = []
        seen = set()
        for model in sorted(self._all_models.values(), key=lambda m: (m.priority, m.display_name)):
            key = f"{model.provider}/{model.short_id}"
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "id": model.short_id,
                "name": model.display_name,
                "description": model.description or f"上下文 {model.context_window//1000}k | "
                    f"{'支持工具' if model.supports_tool_use else '无工具'}",
                "model_id": model.model_id,
            })
        return result


# ---------- 预定义提供商 ----------

def create_openrouter_provider() -> Provider:
    """创建 OpenRouter 提供商（默认主提供商）。"""
    return Provider(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models=[
            ModelInfo(
                model_id="qwen/qwen3.5-plus",
                display_name="Qwen 3.5 Plus",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=1,
                description="主模型：通用能力强，工具调用稳定",
            ),
            ModelInfo(
                model_id="qwen/qwen3-max",
                display_name="Qwen 3 Max",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                supports_reasoning=True,
                priority=2,
                description="更强推理能力",
            ),
            ModelInfo(
                model_id="deepseek/deepseek-v4-pro",
                display_name="DeepSeek V4 Pro",
                provider="openrouter",
                context_window=128000,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=3,
                description="备选主模型",
            ),
            ModelInfo(
                model_id="deepseek/deepseek-v4-flash",
                display_name="DeepSeek V4 Flash",
                provider="openrouter",
                context_window=128000,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=4,
                description="快速响应模型",
            ),
            ModelInfo(
                model_id="qwen/qwen3-coder-plus",
                display_name="Qwen 3 Coder Plus",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=5,
                description="代码场景优化",
            ),
            ModelInfo(
                model_id="zhipu/glm-5",
                display_name="GLM 5",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=6,
            ),
            ModelInfo(
                model_id="moonshot/kimi-k2.5",
                display_name="Kimi K2.5",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=7,
            ),
            ModelInfo(
                model_id="minimax/minimax-m2.5",
                display_name="MiniMax M2.5",
                provider="openrouter",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=8,
            ),
        ],
    )


def create_dashscope_provider() -> Provider:
    """创建 DashScope（阿里云百炼）提供商。"""
    import os
    return Provider(
        name="dashscope",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="DASHSCOPE_API_KEY",
        models=[
            ModelInfo(
                model_id="qwen-plus",
                display_name="Qwen Plus (DashScope)",
                provider="dashscope",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=1,
            ),
            ModelInfo(
                model_id="qwen-max",
                display_name="Qwen Max (DashScope)",
                provider="dashscope",
                context_window=32000,
                max_output_tokens=8192,
                supports_tool_use=True,
                supports_reasoning=True,
                priority=2,
            ),
            ModelInfo(
                model_id="qwen-turbo",
                display_name="Qwen Turbo (DashScope)",
                provider="dashscope",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                priority=3,
                cost_per_1m_input=0.3,
                cost_per_1m_output=0.6,
            ),
        ],
    )


def create_aliyun_token_plan_provider() -> Provider:
    """创建阿里云 Token Plan（MAAS）提供商。"""
    return Provider(
        name="aliyun-token-plan",
        base_url="https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        api_key_env="ALIYUN_TOKEN_PLAN_API_KEY",
        models=[
            ModelInfo(
                model_id="qwen3.6-plus",
                display_name="Qwen 3.6 Plus (Aliyun Token Plan)",
                provider="aliyun-token-plan",
                context_window=131072,
                max_output_tokens=8192,
                supports_tool_use=True,
                supports_reasoning=True,
                priority=1,
                description="千问 3.6 Plus：推理模型、视觉理解、文本生成",
            ),
        ],
    )


def create_ollama_provider() -> Provider:
    """创建 Ollama（本地模型）提供商。"""
    import os
    return Provider(
        name="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key_env="OLLAMA_API_KEY",  # 通常为 "ollama" 或空
        models=[
            ModelInfo(
                model_id="qwen2.5-coder:32b",
                display_name="Qwen 2.5 Coder 32B (Local)",
                provider="ollama",
                context_window=32768,
                max_output_tokens=8192,
                supports_tool_use=False,
                priority=1,
                cost_per_1m_input=0.0,
                cost_per_1m_output=0.0,
            ),
        ],
    )


# ---------- 全局实例 ----------

provider_registry = ProviderRegistry()
# 默认注册 OpenRouter
provider_registry.register(create_openrouter_provider())
# 阿里云 Token Plan
provider_registry.register(create_aliyun_token_plan_provider())
