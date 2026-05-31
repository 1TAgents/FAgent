from agents.common.market.models import KLineData, KLinePeriod
from agents.tools.builtin.market import _format_kline_tool_text


def test_kline_tool_text_includes_query_scope_and_fields():
    kline = KLineData(
        symbol="600519",
        period=KLinePeriod.DAILY,
        source="local:stock_data.db",
        as_of_date="2026-04-24",
        note="本地离线日线数据，不是实时行情。",
        data=[
            {
                "date": "2026-04-20",
                "open": 1403.0,
                "high": 1413.94,
                "low": 1400.0,
                "close": 1410.89,
                "volume": 3645139,
                "amount": 5127145984.0,
                "change_percent": 0.2594,
            },
            {
                "date": "2026-04-24",
                "open": 1413.10,
                "high": 1458.88,
                "low": 1413.10,
                "close": 1458.49,
                "volume": 5545531,
                "amount": 8003410944.0,
                "change_percent": 2.7829,
            },
        ],
    )

    text = _format_kline_tool_text(kline, symbol="600519", period="daily", requested_count=5)

    assert "后台查询：工具=get_kline，symbol=600519，period=daily，count=5" in text
    assert "实际数据范围：2026-04-20 至 2026-04-24" in text
    assert "数据源：local:stock_data.db" in text
    assert "volume(原始成交量，单位以数据源为准，不要改写成手/万手)" in text
    assert "amount(成交额，元；这是金额，不是成交量)" in text
    assert "2026-04-24" in text
    assert "原始成交量5545531" in text
    assert "成交额80.03亿元" in text
