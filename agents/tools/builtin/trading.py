"""
Trading Tools - 模拟交易工具

将 PaperTradingService 封装为 ReAct Loop 可调用的 Tool。

工具列表：
- place_order: 模拟下单
- cancel_order: 模拟撤单
- check_positions: 查询持仓和账户快照
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from ..base import BaseTool, DangerLevel
from ..result import ToolResult
from ...trading import get_paper_trading_service

logger = logging.getLogger(__name__)

SYMBOL_NAMES = {
    "600519": "贵州茅台",
    "000001": "平安银行",
    "300750": "宁德时代",
}


# ==================== PlaceOrderTool ====================

class PlaceOrderTool(BaseTool):
    """模拟下单。"""

    name = "place_order"
    description = "模拟买入或卖出股票（仅本地模拟，不会真实下单），A 股买入需 100 股整数倍"
    category = "trading"
    danger_level = DangerLevel.TRADE

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 600519",
                },
                "side": {
                    "type": "string",
                    "description": "买卖方向：buy（买入）或 sell（卖出）",
                    "enum": ["buy", "sell"],
                },
                "quantity": {
                    "type": "integer",
                    "description": "交易数量（A 股买入需为 100 的倍数）",
                },
                "price": {
                    "type": "number",
                    "description": "委托价格",
                },
            },
            "required": ["symbol", "side", "quantity", "price"],
        }

    async def execute(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        **kw,
    ) -> ToolResult:
        paper = get_paper_trading_service()
        result = paper.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            reason=kw.get("reason", "ReAct 工具调用"),
        )

        if result.get("success"):
            order = result.get("order", {})
            snapshot = result.get("snapshot", {})
            symbol_name = SYMBOL_NAMES.get(symbol, symbol)
            side_label = "买入" if side == "buy" else "卖出"
            text = (
                f"模拟{side_label}成功\n"
                f"- 标的: {symbol_name} ({symbol})\n"
                f"- 数量: {quantity}\n"
                f"- 价格: {price}\n"
                f"- 订单 ID: `{order.get('order_id', 'N/A')}`\n"
                f"- 账户现金: {snapshot.get('cash', 'N/A'):,.2f}\n"
                f"- 账户总资产: {snapshot.get('total_value', 'N/A'):,.2f}"
            )
            return ToolResult.ok(self.name, data=result, text=text)
        else:
            error = result.get("error", "未知错误")
            return ToolResult.fail(self.name, error=f"模拟下单被拒绝: {error}")


# ==================== CancelOrderTool ====================

class CancelOrderTool(BaseTool):
    """模拟撤单。"""

    name = "cancel_order"
    description = "撤销模拟订单"
    category = "trading"
    danger_level = DangerLevel.TRADE

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "要撤销的模拟订单 ID，如 po_a1b2c3d4e5f6",
                },
            },
            "required": ["order_id"],
        }

    async def execute(self, order_id: str, **kw) -> ToolResult:
        paper = get_paper_trading_service()
        result = paper.cancel_order(order_id)

        if result.get("success"):
            return ToolResult.ok(self.name, data=result, text=f"模拟订单 `{order_id}` 已成功撤销。")
        else:
            return ToolResult.fail(self.name, error=result.get("error", "撤单失败"))


# ==================== CheckPositionsTool ====================

class CheckPositionsTool(BaseTool):
    """查询持仓和账户快照。"""

    name = "check_positions"
    description = "查询模拟账户的持仓、现金和总资产"
    category = "trading"
    danger_level = DangerLevel.READ_ONLY

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "可选：只查询指定标的持仓",
                },
            },
            "required": [],
        }

    async def execute(self, symbol: Optional[str] = None, **kw) -> ToolResult:
        paper = get_paper_trading_service()
        snapshot = paper.get_snapshot()

        positions = snapshot.get("positions", [])
        if symbol:
            positions = [p for p in positions if p.get("symbol") == symbol]

        lines = [
            f"## 账户快照",
            f"- 现金: {snapshot['cash']:,.2f}",
            f"- 持仓市值: {snapshot['position_value']:,.2f}",
            f"- 总资产: {snapshot['total_value']:,.2f}",
            f"- 总盈亏: {snapshot['total_pnl']:,.2f}",
            f"- 仓位比例: {snapshot['position_ratio']:.1%}",
        ]

        if positions:
            lines.append("")
            lines.append("## 持仓明细")
            for p in positions:
                name = SYMBOL_NAMES.get(p["symbol"], p["symbol"])
                pnl = p.get("unrealized_pnl", 0)
                pnl_pct = p.get("unrealized_pnl_percent", 0)
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"- **{name}** ({p['symbol']}): "
                    f"{p['quantity']} 股 @ {p['avg_cost']:.2f}, "
                    f"现价 {p['last_price']:.2f}, "
                    f"市值 {p['market_value']:,.2f}, "
                    f"浮盈亏 {sign}{pnl:,.2f} ({sign}{pnl_pct:.2f}%)"
                )
        else:
            sym_filter = f" ({symbol})" if symbol else ""
            lines.append(f"\n当前无持仓{sym_filter}。")

        return ToolResult.ok(self.name, data=snapshot, text="\n".join(lines))


# ==================== Factory ====================

def get_trading_tools() -> list[BaseTool]:
    """获取所有交易工具实例。"""
    return [
        PlaceOrderTool(),
        CancelOrderTool(),
        CheckPositionsTool(),
    ]
