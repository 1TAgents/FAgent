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


def test_normalize_route_for_capability_qa():
    route = normalize_route_for_task(RouteType.MARKET, TaskType.CAPABILITY_QA)

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


def test_parse_route_response_accepts_capability_qa():
    router = MainRouter()
    content = json.dumps(
        {
            "route": "chat",
            "task_type": "capability_qa",
            "query": "你现在能查询最新数据行情吗？",
            "params": {},
            "reasoning": "用户询问具体行情能力",
        },
        ensure_ascii=False,
    )

    decision = router._parse_route_response(content, "你现在能查询最新数据行情吗？")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.CAPABILITY_QA


def test_parse_route_response_repairs_concrete_market_question_from_capability_qa():
    router = MainRouter()
    content = json.dumps(
        {
            "route": "chat",
            "task_type": "capability_qa",
            "query": "那你能查询得到贵州茅台最近的行情数据是什么时候的呢？",
            "params": {},
            "reasoning": "模型误把具体行情查询当成能力问答",
        },
        ensure_ascii=False,
    )

    decision = router._parse_route_response(content, "那你能查询得到贵州茅台最近的行情数据是什么时候的呢？")

    assert decision.route == RouteType.MARKET
    assert decision.task_context.task_type == TaskType.GET_KLINE
    assert decision.task_context.params["symbol"] == "600519"
    assert "capability_qa to market" in decision.reasoning


def test_parse_route_response_repairs_overbroad_describe_self():
    router = MainRouter()
    content = json.dumps(
        {
            "route": "chat",
            "task_type": "describe_self",
            "query": "你现在能查询最新数据行情吗？",
            "params": {},
            "reasoning": "模型误把具体能力问题当成完整自我介绍",
        },
        ensure_ascii=False,
    )

    decision = router._parse_route_response(content, "你现在能查询最新数据行情吗？")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.CAPABILITY_QA
    assert "capability_qa" in decision.reasoning


def test_fallback_routes_self_description_to_chat():
    router = MainRouter()

    decision = router._fallback_route("你好，你有哪些功能能力？")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.DESCRIBE_SELF
    assert "自我介绍" in decision.reasoning


def test_fallback_routes_specific_capability_to_capability_qa():
    router = MainRouter()

    decision = router._fallback_route("你现在能查询最新数据行情吗？")

    assert decision.route == RouteType.CHAT
    assert decision.task_context.task_type == TaskType.CAPABILITY_QA
    assert "具体能力" in decision.reasoning


def test_direct_route_concrete_stock_market_date_question_to_kline():
    router = MainRouter()

    decision = router._direct_route("那你能查询得到贵州茅台最近的行情数据是什么时候的呢？")

    assert decision is not None
    assert decision.route == RouteType.MARKET
    assert decision.task_context.task_type == TaskType.GET_KLINE
    assert decision.task_context.params["symbol"] == "600519"
    assert decision.task_context.params["period"] == "daily"


def test_strategy_feature_question_is_not_self_description():
    router = MainRouter()

    decision = router._fallback_route("RSI 指标有什么功能，适合什么策略？")

    assert decision.task_context.task_type != TaskType.DESCRIBE_SELF
