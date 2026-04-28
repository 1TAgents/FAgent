import asyncio

from agents.router.models import TaskContext, TaskType
from agents.subagents.trade_subagent import TradeSubAgent
from agents.trading import PaperTradingService


def _agent(tmp_path):
    return TradeSubAgent(PaperTradingService(str(tmp_path / "paper.db")))


def test_trade_subagent_places_order_from_query(tmp_path):
    agent = _agent(tmp_path)
    context = TaskContext(
        task_type=TaskType.PLACE_ORDER,
        query="模拟买入 600519 100股 价格 100",
    )

    content = asyncio.run(agent.process(context))

    assert "模拟订单已成交" in content
    assert "`600519`" in content
    assert "本地模拟成交" in content


def test_trade_subagent_checks_positions_after_order(tmp_path):
    agent = _agent(tmp_path)
    asyncio.run(agent.process(TaskContext(
        task_type=TaskType.PLACE_ORDER,
        query="模拟买入 600519 100股 价格 100",
    )))

    content = asyncio.run(agent.process(TaskContext(
        task_type=TaskType.CHECK_POSITIONS,
        query="查看持仓",
    )))

    assert "模拟账户快照" in content
    assert "`600519`" in content
    assert "100 股" in content


def test_trade_subagent_requires_complete_order_fields(tmp_path):
    agent = _agent(tmp_path)
    context = TaskContext(
        task_type=TaskType.PLACE_ORDER,
        query="模拟买入 600519 100股",
    )

    content = asyncio.run(agent.process(context))

    assert "信息不完整" in content
    assert "模拟成交价" in content
    assert "未创建订单" in content


def test_trade_subagent_rejects_sell_without_position(tmp_path):
    agent = _agent(tmp_path)
    context = TaskContext(
        task_type=TaskType.PLACE_ORDER,
        query="模拟卖出 600519 100股 价格 100",
    )

    content = asyncio.run(agent.process(context))

    assert "模拟下单未通过" in content
    assert "模拟持仓不足" in content
