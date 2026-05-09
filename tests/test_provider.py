"""
Provider Registry 测试 - Aliyun Token Plan
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.services.provider import (
    provider_registry,
    create_aliyun_token_plan_provider,
)


class TestAliyunTokenPlan:
    def test_provider_registered(self):
        provider = provider_registry.get_provider("aliyun-token-plan")
        assert provider is not None
        assert provider.name == "aliyun-token-plan"
        assert "token-plan" in provider.base_url

    def test_qwen36_model_exists(self):
        model = provider_registry.get_model("qwen3.6-plus")
        assert model is not None
        assert model.display_name == "Qwen 3.6 Plus (Aliyun Token Plan)"
        assert model.supports_tool_use is True
        assert model.supports_reasoning is True
        assert model.context_window == 131072

    def test_frontend_list_includes_qwen36(self):
        models = provider_registry.to_frontend_list()
        model_ids = [m["model_id"] for m in models]
        assert "qwen3.6-plus" in model_ids

    def test_no_duplicate_in_frontend_list(self):
        models = provider_registry.to_frontend_list()
        seen_ids = [m["id"] for m in models]
        assert len(seen_ids) == len(set(seen_ids))

    def test_resolve_qwen36(self):
        resolved = provider_registry.resolve_model("qwen3.6-plus")
        assert resolved == "qwen3.6-plus"

    def test_tool_use_capability(self):
        models = provider_registry.list_available_models(supports_tool_use=True)
        qwen36 = [m for m in models if m.short_id == "qwen3.6-plus"]
        assert len(qwen36) == 1
