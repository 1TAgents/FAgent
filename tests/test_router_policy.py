import json

from agents.router.main_router import MainRouter
from agents.router.models import RouteType, TaskType
from agents.router.policy import normalize_route_for_task


def test_normalize_route_for_task_keeps_compatible_decision():
    route = normalize_route_for_task(RouteType.MARKET, TaskType.GET_QUOTE)

    assert route == RouteType.MARKET


def test_normalize_route_for_task_repairs_mismatched_decision():
    route = normalize_route_for_task(RouteType.MARKET, TaskType.PLACE_ORDER)

    assert route == RouteType.TRADE


def test_normalize_route_for_self_description():
    route = normalize_route_for_task(RouteType.MARKET, TaskType.DESCRIBE_SELF)

    assert route == RouteType.CHAT


def test_parse_route_response_repairs_route_task_mismatch():
    router = MainRouter()
    content = json.dumps(
        {
            "route": "market",
            "task_type": "place_order",
            "query": "模拟买入 600519 100股",
            "params": {"symbol": "600519", "quantity": 100},
            "reasoning": "模型误把交易动作放到了 market",
        },
        ensure_ascii=False,
    )

    decision = router._parse_route_response(content, "模拟买入 600519 100股")

    assert decision.route == RouteType.TRADE
    assert decision.task_context.task_type == TaskType.PLACE_ORDER
    assert "normalized from market to trade" in decision.reasoning


def test_parse_route_response_accepts_describe_self():
    router = MainRouter()
    content = json.dumps(
        {
            "route": "chat",
            "task_type": "describe_self",
            "query": "你有哪些功能能力",
            "params": {},
            "reasoning": "用户询问 FAgent 能力",
        },
        ensure_ascii=False,
    )

    decision = router._parse_route_response(content, "你有哪些功能能力")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.DESCRIBE_SELF


def test_fallback_routes_self_description_to_chat():
    router = MainRouter()

    decision = router._fallback_route("你好，你有哪些功能能力？")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.DESCRIBE_SELF
    assert "自我介绍" in decision.reasoning


def test_strategy_feature_question_is_not_self_description():
    router = MainRouter()

    decision = router._fallback_route("RSI 指标有什么功能，适合什么策略？")

    assert decision.task_context.task_type != TaskType.DESCRIBE_SELF
