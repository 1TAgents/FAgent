from agents.router.main_router import MainRouter
from agents.router.models import RouteType, TaskType


def test_fallback_routes_explicit_paper_order_to_trade():
    router = MainRouter()

    decision = router._fallback_route("模拟买入 600519 100股 价格 100")

    assert decision.route == RouteType.TRADE
    assert decision.task_context.task_type == TaskType.PLACE_ORDER
    assert decision.task_context.params["symbol"] == "600519"


def test_fallback_does_not_treat_buy_analysis_as_order():
    router = MainRouter()

    decision = router._fallback_route("600519 现在能不能买")

    assert decision.task_context.task_type != TaskType.PLACE_ORDER
