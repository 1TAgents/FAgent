"""
Trade SubAgent - 交易子智能体

当前只接入本地模拟交易，不连接真实券商或交易网关。
"""
import re
import time
from typing import Any, AsyncIterator, Dict, Optional

from .base import BaseSubAgent
from ..core.logging import log_subagent
from ..router.models import TaskContext, TaskType
from ..trading import PaperTradingService, get_paper_trading_service


class TradeSubAgent(BaseSubAgent):
    """交易相关任务子智能体。"""

    name = "trade"

    def __init__(self, paper_service: Optional[PaperTradingService] = None):
        super().__init__()
        self.paper_service = paper_service or get_paper_trading_service()

    async def process_stream(self, context: TaskContext) -> AsyncIterator[str]:
        start_time = time.time()
        log_subagent.start("TradeSubAgent", context.task_type.value, context)

        try:
            if context.task_type == TaskType.PLACE_ORDER:
                content = self._place_order(context)
            elif context.task_type == TaskType.CANCEL_ORDER:
                content = self._cancel_order(context)
            elif context.task_type == TaskType.CHECK_POSITIONS:
                content = self._check_positions(context)
            else:
                content = self._build_general_response(context)

            yield content
            log_subagent.done("TradeSubAgent", time.time() - start_time)
        except Exception as e:
            log_subagent.done("TradeSubAgent", time.time() - start_time, success=False)
            yield f"抱歉，模拟交易任务处理失败：{e}"

    async def process(self, context: TaskContext) -> str:
        result = []
        async for chunk in self.process_stream(context):
            result.append(chunk)
        return "".join(result)

    def _place_order(self, context: TaskContext) -> str:
        spec = self._normalize_order_spec(context)
        missing = [key for key in ["symbol", "side", "quantity", "price"] if not spec.get(key)]
        if missing:
            return self._format_missing_order_fields(missing, spec)

        result = self.paper_service.place_order(
            symbol=spec["symbol"],
            side=spec["side"],
            quantity=int(spec["quantity"]),
            price=float(spec["price"]),
            account_id=spec["account_id"],
            reason=context.original_message or context.query,
        )

        if not result.get("success"):
            order = result.get("order") or {}
            return "\n".join([
                "模拟下单未通过。",
                "",
                f"- 原因：{result.get('error', '未知错误')}",
                f"- 模拟订单 ID：`{order.get('order_id', 'N/A')}`",
                f"- 标的：`{spec['symbol'] or 'N/A'}`",
                f"- 方向：`{spec['side'] or 'N/A'}`",
                f"- 数量：`{spec.get('quantity') or 'N/A'}`",
                f"- 价格：`{spec.get('price') or 'N/A'}`",
                "",
                "注意：当前 TradeSubAgent 只执行本地模拟交易，不会触发真实下单。",
            ])

        order = result["order"]
        snapshot = result["snapshot"]
        return "\n".join([
            "模拟订单已成交。",
            "",
            f"- 模拟订单 ID：`{order['order_id']}`",
            f"- 标的：`{order['symbol']}`",
            f"- 方向：`{self._display_side(order['side'])}`",
            f"- 数量：`{order['quantity']}` 股",
            f"- 成交价：`{order['price']:.3f}`",
            f"- 交易费用：`{order['cost']:.2f}`",
            f"- 账户现金：`{snapshot['cash']:.2f}`",
            f"- 持仓市值：`{snapshot['position_value']:.2f}`",
            f"- 总资产：`{snapshot['total_value']:.2f}`",
            "",
            "注意：这是本地模拟成交，不是实盘委托。",
        ])

    def _cancel_order(self, context: TaskContext) -> str:
        order_id = (context.params or {}).get("order_id") or self._extract_order_id(context.query)
        if not order_id:
            return "请提供要撤销的模拟订单 ID，例如 `撤销 po_xxx`。当前不会触发真实撤单。"

        result = self.paper_service.cancel_order(order_id)
        if not result.get("success"):
            return f"模拟撤单失败：{result.get('error', '未知错误')}。当前不会触发真实撤单。"

        order = result["order"]
        return f"模拟订单 `{order['order_id']}` 已撤销。当前不会触发真实撤单。"

    def _check_positions(self, context: TaskContext) -> str:
        account_id = (context.params or {}).get("account_id") or "default"
        snapshot = self.paper_service.get_snapshot(account_id)
        lines = [
            "模拟账户快照：",
            "",
            f"- 账户 ID：`{snapshot['account_id']}`",
            f"- 现金：`{snapshot['cash']:.2f}`",
            f"- 持仓市值：`{snapshot['position_value']:.2f}`",
            f"- 总资产：`{snapshot['total_value']:.2f}`",
            f"- 总盈亏：`{snapshot['total_pnl']:+.2f}`",
            f"- 仓位比例：`{snapshot['position_ratio']:.2%}`",
        ]

        if snapshot["positions"]:
            lines.extend(["", "**持仓**"])
            for item in snapshot["positions"]:
                lines.append(
                    f"- `{item['symbol']}`：{item['quantity']} 股，"
                    f"成本 `{item['avg_cost']:.3f}`，现价 `{item['last_price']:.3f}`，"
                    f"市值 `{item['market_value']:.2f}`，浮盈亏 `{item['unrealized_pnl']:+.2f}`"
                )
        else:
            lines.extend(["", "当前没有模拟持仓。"])

        lines.extend(["", "注意：这是本地模拟账户，不代表真实券商账户。"])
        return "\n".join(lines)

    def _normalize_order_spec(self, context: TaskContext) -> Dict[str, Any]:
        params = context.params or {}
        query = context.query or context.original_message or ""
        price = params.get("price") or self._extract_price(query)
        quantity = params.get("quantity") or self._extract_quantity(query)
        amount = params.get("amount") or self._extract_amount(query)

        if not quantity and amount and price:
            quantity = int(float(amount) // float(price) // 100 * 100)

        return {
            "account_id": params.get("account_id") or "default",
            "symbol": params.get("symbol") or self._extract_symbol(query),
            "side": self._normalize_side(params.get("side"), query),
            "quantity": int(quantity) if quantity else None,
            "price": float(price) if price else None,
        }

    def _format_missing_order_fields(self, missing: list[str], spec: Dict[str, Any]) -> str:
        field_names = {
            "symbol": "标的代码",
            "side": "买卖方向",
            "quantity": "数量",
            "price": "模拟成交价",
        }
        missing_text = "、".join(field_names.get(key, key) for key in missing)
        return "\n".join([
            "模拟下单信息不完整，未创建订单。",
            "",
            f"- 缺少：{missing_text}",
            f"- 当前解析：symbol=`{spec.get('symbol')}` side=`{spec.get('side')}` "
            f"quantity=`{spec.get('quantity')}` price=`{spec.get('price')}`",
            "",
            "请用类似格式：`模拟买入 600519 1000股 价格 1688`。",
            "注意：当前 TradeSubAgent 只做本地模拟交易，不会触发真实下单。",
        ])

    def _normalize_side(self, side: Optional[str], query: str) -> Optional[str]:
        if side:
            normalized = str(side).lower()
            if normalized in {"buy", "b", "long", "买", "买入"}:
                return "buy"
            if normalized in {"sell", "s", "short", "卖", "卖出"}:
                return "sell"

        if any(token in query for token in ["买入", "买", "开仓"]):
            return "buy"
        if any(token in query for token in ["卖出", "卖", "平仓"]):
            return "sell"
        return None

    def _extract_symbol(self, query: str) -> Optional[str]:
        match = re.search(r"(?<!\d)([0368]\d{5})(?!\d)", query)
        if match:
            return match.group(1)
        aliases = {
            "贵州茅台": "600519",
            "茅台": "600519",
            "平安银行": "000001",
            "宁德时代": "300750",
        }
        for alias, symbol in aliases.items():
            if alias in query:
                return symbol
        return None

    def _extract_quantity(self, query: str) -> Optional[int]:
        lot_match = re.search(r"(\d+)\s*手", query)
        if lot_match:
            return int(lot_match.group(1)) * 100

        share_match = re.search(r"(\d+)\s*(?:股|shares?)", query, re.IGNORECASE)
        if share_match:
            return int(share_match.group(1))
        return None

    def _extract_price(self, query: str) -> Optional[float]:
        match = re.search(r"(?:价格|价|price|@)\s*(\d+(?:\.\d+)?)", query, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _extract_amount(self, query: str) -> Optional[float]:
        match = re.search(r"(\d+(?:\.\d+)?)\s*万", query)
        if match:
            return float(match.group(1)) * 10000

        match = re.search(r"(\d+(?:\.\d+)?)\s*元", query)
        if match:
            return float(match.group(1))
        return None

    def _extract_order_id(self, query: str) -> Optional[str]:
        match = re.search(r"(po_[A-Za-z0-9]+)", query)
        return match.group(1) if match else None

    def _display_side(self, side: str) -> str:
        return "买入" if side == "buy" else "卖出"

    def _build_general_response(self, context: TaskContext) -> str:
        return (
            "TradeSubAgent 当前只支持本地模拟交易，可处理模拟下单、模拟撤单和模拟持仓查询。"
            "真实交易接口尚未接入，也不会触发真实委托。"
        )


trade_subagent = TradeSubAgent()
