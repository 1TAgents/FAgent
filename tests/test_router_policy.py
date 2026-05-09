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
