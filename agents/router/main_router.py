"""
MainRouter - 主路由器

整个对话系统的入口点，负责：
1. 维护完整对话历史
2. 意图识别 + 路由决策
3. 提炼任务上下文给 SubAgent
4. 流式透传 SubAgent 的输出（不做二次 LLM 处理）
"""
import os
import sys
import time
import json
import re
from typing import AsyncIterator, Dict, List, Optional, Any

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.storage import message_storage

from .models import TaskContext, TaskType, RouteType, RouteDecision
from .policy import normalize_route_for_task
from ..services.llm import llm_service
from ..core.logging import logger, log_router, log_subagent
from ..core.context import set_context
from ..core.context_builder import context_builder
from .react_router import react_router


# 路由决策 Prompt
ROUTER_SYSTEM_PROMPT = """你是一个任务路由器，负责分析用户意图并路由到合适的处理模块。

根据用户消息和对话历史，判断：
1. 这是什么类型的问题
2. 需要路由到哪个处理模块
3. 提取关键参数

【路由类型】
- market: 行情查询、股票分析、K线数据、趋势分析、指数/行业/财务等市场数据
- strategy: 策略推荐、策略说明、策略比较、常见策略列表
- backtest: 回测执行、参数优化、回测指标说明
- trade: 下单、撤单、持仓、订单查询、交易规则/风控问答
- chat: 闲聊、问候、通用问答、金融知识解释、FAgent 自我介绍/能力说明

【任务类型及参数】
- get_quote: 查询实时行情
  参数: symbol (股票代码，如 "600519")
  
- get_kline: 查询K线数据
  参数: symbol (股票代码), period (周期), count (数量)
  period 有效值: "daily"(日K), "weekly"(周K), "monthly"(月K), "1min", "5min", "15min", "30min", "60min"
  
- search_stock: 搜索股票
  参数: keyword (搜索关键词)
  
- analyze_trend: 趋势分析
  参数: symbol (股票代码)

- list_strategies: 列出常见策略
  参数: category (可选)

- strategy_qa: 策略说明、推荐、比较
  参数: strategy_name (可选), symbol (可选)

- run_backtest: 执行回测
  参数: strategy_name (可选), symbol (可选), period (可选)

- optimize_backtest: 参数优化、网格搜索
  参数: strategy_name (可选), symbol (可选)

- backtest_qa: 回测相关问答
  参数: strategy_name (可选), symbol (可选)

- trade_qa: 交易规则、流程、风控问答
  参数: symbol (可选)

- place_order: 下单
  参数: symbol (可选), side (可选), quantity (可选), price (可选)

- cancel_order: 撤单
  参数: order_id (可选), symbol (可选)

- check_positions: 查询持仓/订单
  参数: symbol (可选)
  
- greeting: 问候（无需参数）
- describe_self: FAgent 自我介绍、能力说明、功能边界说明（无需参数）
- capability_qa: FAgent 某个具体能力是否支持、后台流程、能力边界问答（无需参数）
- general_qa: 通用问答（无需参数）

【重要】
1. 解析指代词：如果用户说"那个股票"、"它"等，根据上下文推断具体指什么
2. 提取股票代码：茅台=600519, 平安银行=000001 等
3. 如果无法确定股票代码，可以先搜索
4. 查询最近一周行情时，建议用 get_kline + period="daily" + count=5
5. “memory/历史偏好/过往结论”是辅助能力，不单独作为 route
6. 策略设计/比较/推荐优先走 strategy；回测和参数优化优先走 backtest；真实交易动作优先走 trade
7. 对“现在能不能买”“怎么看某策略”这类偏分析问题，不要误判为 place_order
8. 用户问“你是谁 / FAgent 是什么 / 你有哪些功能能力 / 你能做什么”这类完整能力总览时，route=chat 且 task_type=describe_self
9. 用户问某个具体能力是否支持或后台流程，例如“你现在能查询最新数据行情吗”“支持回测吗”“均线策略筛选后台会做什么”，route=chat 且 task_type=capability_qa，不要误判为 describe_self

输出 JSON 格式：
{
    "route": "market" | "strategy" | "backtest" | "trade" | "chat",
    "task_type": "get_quote" | "get_kline" | "analyze_trend" | "search_stock" | "list_strategies" | "strategy_qa" | "run_backtest" | "optimize_backtest" | "backtest_qa" | "trade_qa" | "place_order" | "cancel_order" | "check_positions" | "greeting" | "describe_self" | "capability_qa" | "general_qa",
    "query": "解析后的明确问题",
    "params": {"symbol": "600519", "period": "daily", "count": 5},
    "context_summary": "相关上下文（如有）",
    "reasoning": "决策理由"
}
"""


class MainRouter:
    """
    主路由器
    
    职责：
    1. 维护对话历史（通过 cid 关联）
    2. 意图识别和路由决策
    3. 上下文提炼
    4. 流式透传 SubAgent 输出
    """
    
    def __init__(self):
        self.llm = llm_service
        logger.info("MainRouter 初始化完成 (ReAct 模式)")
    
    async def process_stream(
        self,
        cid: int,
        message_id: int,
        user_message: str,
        history_limit: int = 10,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        处理用户消息（流式）- 系统主入口

        Args:
            cid: 会话 ID
            message_id: 当前消息 ID（用于获取历史）
            user_message: 用户消息
            history_limit: 历史消息条数限制
            model: 动态模型选择（可选）

        Yields:
            流式文本片段
        """
        start_time = time.time()

        # 设置 mid 到上下文
        set_context(mid=str(message_id))

        # 记录请求
        log_router.request(cid=cid, message_id=message_id, user_message=user_message)

        # 1. 获取对话历史
        history = self._get_history(cid, message_id, history_limit)
        log_router.history(cid=cid, message_count=len(history), messages=history if len(history) < 10 else None)

        # 2. 路由决策
        decision = await self._route(user_message, history)
        log_router.intent(
            route=decision.route.value,
            task=decision.task_context.task_type.value,
            params=decision.task_context.params,
            raw_response=decision.reasoning,
        )

        # 3. 设置上下文的原始信息
        decision.task_context.original_message = user_message
        decision.task_context.cid = cid
        decision.task_context.mid = message_id
        decision.task_context.model = model

        log_router.context(decision.task_context)

        # 4. 执行：ReAct 循环（带工具调用）
        try:
            log_router.dispatch(
                f"ReAct({decision.route.value})",
                decision.task_context.task_type.value,
            )
            async for chunk in react_router.process_stream(
                route=decision.route,
                context=decision.task_context,
                history=history,
            ):
                yield chunk

            duration = time.time() - start_time
            log_router.done(cid=cid, duration=duration, route=decision.route.value)

        except Exception as e:
            logger.error(f"[ROUTER] ReAct 处理失败 | 输入=cid={cid}, route={decision.route.value} | 原因={str(e)}")
            log_router.fallback(f"ReAct 处理失败: {str(e)}")
            yield f"抱歉，处理请求时出现错误：{str(e)}"
    
    async def process(
        self,
        cid: int,
        message_id: int,
        user_message: str,
        history_limit: int = 10,
    ) -> str:
        """
        处理用户消息（非流式）
        """
        result = ""
        async for chunk in self.process_stream(cid, message_id, user_message, history_limit):
            result += chunk
        return result
    
    def _get_history(
        self,
        cid: int,
        before_message_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """获取对话历史"""
        messages = message_storage.get_history_before_message(cid, before_message_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
    
    async def _route(
        self,
        user_message: str,
        history: List[Dict]
    ) -> RouteDecision:
        """
        路由决策

        使用 LLM 分析意图并决定路由
        """
        direct_decision = self._direct_route(user_message)
        if direct_decision:
            return direct_decision

        messages = context_builder.build_router_messages(
            system_prompt=ROUTER_SYSTEM_PROMPT,
            history=history,
            user_message=user_message,
        )

        # 调用 LLM
        try:
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # 低温度，更确定性
            )
            
            content = response.choices[0].message.content
            
            # 解析 JSON
            decision = self._parse_route_response(content, user_message)
            return decision
            
        except Exception as e:
            logger.error(f"[ROUTER] 路由决策失败 | 输入=user_message | 原因={str(e)}")
            # 降级：默认路由到 chat
            return RouteDecision(
                route=RouteType.CHAT,
                task_context=TaskContext(
                    task_type=TaskType.GENERAL_QA,
                    query=user_message,
                ),
                reasoning=f"路由失败，降级到 chat: {str(e)}"
            )
    
    def _parse_route_response(self, content: str, original_message: str) -> RouteDecision:
        """解析 LLM 的路由决策响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("未找到 JSON")
            
            # 解析路由类型
            route_str = data.get("route", "chat")
            try:
                route = RouteType(route_str)
            except ValueError:
                route = RouteType.CHAT
            
            # 解析任务类型
            task_str = data.get("task_type", "general_qa")
            try:
                task_type = TaskType(task_str)
            except ValueError:
                task_type = TaskType.GENERAL_QA

            reasoning = data.get("reasoning", "")
            if (
                task_type == TaskType.DESCRIBE_SELF
                and not self._is_broad_self_description_message(original_message)
                and self._is_specific_capability_question(original_message)
            ):
                task_type = TaskType.CAPABILITY_QA
                route = RouteType.CHAT
                suffix = "task normalized from describe_self to capability_qa for specific capability question"
                reasoning = f"{reasoning} | {suffix}" if reasoning else suffix

            normalized_route = normalize_route_for_task(route, task_type)
            if normalized_route != route:
                suffix = (
                    f"route normalized from {route.value} to "
                    f"{normalized_route.value} for task {task_type.value}"
                )
                reasoning = f"{reasoning} | {suffix}" if reasoning else suffix
                route = normalized_route
            
            # 构建 TaskContext
            task_context = TaskContext(
                task_type=task_type,
                query=data.get("query", original_message),
                params=data.get("params", {}),
                context_summary=data.get("context_summary", ""),
            )
            
            return RouteDecision(
                route=route,
                task_context=task_context,
                confidence=1.0,
                reasoning=reasoning,
            )
            
        except Exception as e:
            logger.warning(f"解析路由响应失败 | error={e} | content={content[:200]}")
            # 使用简单规则降级
            return self._fallback_route(original_message)
    
    def _fallback_route(self, message: str) -> RouteDecision:
        """
        降级路由（当 LLM 解析失败时）
        
        使用简单规则判断
        """
        message_lower = message.lower()

        symbol = self._extract_symbol(message)

        direct_decision = self._direct_route(message)
        if direct_decision:
            return direct_decision

        strategy_keywords = ["策略", "双均线", "macd", "rsi", "布林", "均线策略", "选股策略"]
        backtest_keywords = ["回测", "最大回撤", "夏普", "收益曲线", "收益率", "参数优化", "网格搜索"]
        trade_keywords = [
            "下单", "撤单", "持仓", "仓位", "委托", "成交", "开仓", "平仓",
            "买一手", "卖一手", "模拟买入", "模拟卖出",
        ]
        market_keywords = ["行情", "股票", "股价", "涨", "跌", "k线", "均线", "趋势", "指数", "行业", "财务", "资金流", "查询", "搜索"]

        if any(keyword in message_lower for keyword in strategy_keywords):
            task_type = TaskType.STRATEGY_QA
            if "列出" in message or "列表" in message or "有哪些" in message or "常见" in message:
                task_type = TaskType.LIST_STRATEGIES

            return RouteDecision(
                route=RouteType.STRATEGY,
                task_context=TaskContext(
                    task_type=task_type,
                    query=message,
                    params={"symbol": symbol} if symbol else {},
                ),
                reasoning="规则匹配 strategy 关键词",
            )

        if any(keyword in message_lower for keyword in backtest_keywords):
            task_type = TaskType.BACKTEST_QA
            if "优化" in message or "网格搜索" in message:
                task_type = TaskType.OPTIMIZE_BACKTEST
            elif "回测" in message and not any(token in message for token in ["是什么", "怎么", "解释", "说明", "介绍"]):
                task_type = TaskType.RUN_BACKTEST

            params = {"symbol": symbol} if symbol else {}
            return RouteDecision(
                route=RouteType.BACKTEST,
                task_context=TaskContext(
                    task_type=task_type,
                    query=message,
                    params=params,
                ),
                reasoning="规则匹配 backtest 关键词",
            )

        explicit_order = self._is_explicit_order_message(message)
        if any(keyword in message_lower for keyword in trade_keywords) or explicit_order:
            task_type = TaskType.TRADE_QA
            if "撤单" in message:
                task_type = TaskType.CANCEL_ORDER
            elif "持仓" in message or "仓位" in message or "委托" in message or "成交" in message:
                task_type = TaskType.CHECK_POSITIONS
            elif explicit_order or "下单" in message or "开仓" in message or "平仓" in message or "买一手" in message or "卖一手" in message:
                task_type = TaskType.PLACE_ORDER

            params = {"symbol": symbol} if symbol else {}
            return RouteDecision(
                route=RouteType.TRADE,
                task_context=TaskContext(
                    task_type=task_type,
                    query=message,
                    params=params,
                ),
                reasoning="规则匹配 trade 关键词",
            )

        if any(keyword in message_lower for keyword in market_keywords) or symbol:
            params: Dict[str, Any] = {}
            task_type = TaskType.GET_QUOTE

            if symbol:
                params["symbol"] = symbol

            if "搜索" in message or "代码" in message or ("找" in message and not symbol):
                task_type = TaskType.SEARCH_STOCK
                params = {"keyword": self._extract_search_keyword(message)}
            elif any(token in message_lower for token in ["k线", "日k", "周k", "月k", "最近一周", "近一周", "走势"]):
                task_type = TaskType.GET_KLINE
                params["period"] = "daily"
                params["count"] = self._infer_kline_count(message)
            elif "趋势" in message or "形态" in message or ("分析" in message and symbol):
                task_type = TaskType.ANALYZE_TREND

            return RouteDecision(
                route=RouteType.MARKET,
                task_context=TaskContext(
                    task_type=task_type,
                    query=message,
                    params=params,
                ),
                reasoning="规则匹配 market 关键词",
            )
        
        # 默认：通用对话
        return RouteDecision(
            route=RouteType.CHAT,
            task_context=TaskContext(
                task_type=TaskType.GENERAL_QA,
                query=message,
            ),
            reasoning="无匹配关键词，默认 chat",
        )

    def _direct_route(self, message: str) -> Optional[RouteDecision]:
        """Handle deterministic intents that should not spend a router LLM call."""
        if self._is_broad_self_description_message(message):
            return RouteDecision(
                route=RouteType.CHAT,
                task_context=TaskContext(
                    task_type=TaskType.DESCRIBE_SELF,
                    query=message,
                ),
                reasoning="规则匹配 FAgent 自我介绍/能力说明意图",
            )

        if self._is_specific_capability_question(message):
            return RouteDecision(
                route=RouteType.CHAT,
                task_context=TaskContext(
                    task_type=TaskType.CAPABILITY_QA,
                    query=message,
                ),
                reasoning="规则匹配 FAgent 具体能力问答意图",
            )

        return None

    def _is_broad_self_description_message(self, message: str) -> bool:
        """Recognize broad questions about FAgent's overall capabilities."""
        normalized = re.sub(r"\s+", "", message.lower())
        exact_markers = [
            "你是谁",
            "你是做什么",
            "你能做什么",
            "你会什么",
            "你有哪些功能",
            "你有哪些能力",
            "功能能力",
            "能力介绍",
            "介绍一下你",
            "介绍一下fagent",
            "fagent是什么",
            "fagent有哪些",
            "fagent有什么",
            "这个agent有什么",
            "这个agent能做",
            "当前fagent能力",
            "当前fagent功能",
        ]
        if any(marker in normalized for marker in exact_markers):
            return True

        return (
            any(marker in normalized for marker in ["fagent", "agent", "你", "你们", "系统"])
            and any(marker in normalized for marker in ["功能", "能力"])
            and any(marker in normalized for marker in ["介绍", "总览", "全部", "整体", "有哪些", "有什么"])
        )

    def _is_specific_capability_question(self, message: str) -> bool:
        """Recognize focused questions about whether/how FAgent supports one capability."""
        normalized = re.sub(r"\s+", "", message.lower())

        if any(token in normalized for token in ["能不能买", "可以买吗", "能买吗", "要不要买", "值得买"]):
            return False

        subject_markers = ["fagent", "agent", "你", "你们", "系统", "后台"]
        support_markers = [
            "能查询",
            "能查",
            "可以查询",
            "可以查",
            "会查询",
            "会查",
            "是否支持",
            "支不支持",
            "能不能",
            "可不可以",
            "会不会",
            "支持",
            "后台会做",
            "后台做",
        ]
        domain_markers = [
            "行情",
            "最新数据",
            "实时数据",
            "数据",
            "股价",
            "k线",
            "趋势",
            "股票",
            "策略",
            "回测",
            "参数优化",
            "模拟交易",
            "下单",
            "持仓",
            "撤单",
            "记忆",
            "流式",
            "均线",
        ]

        return (
            any(marker in normalized for marker in subject_markers)
            and any(marker in normalized for marker in support_markers)
            and any(marker in normalized for marker in domain_markers)
        )

    def _extract_symbol(self, message: str) -> Optional[str]:
        """从消息中提取股票代码或常见别名。"""
        code_match = re.search(r"(?<!\d)([0368]\d{5})(?!\d)", message)
        if code_match:
            return code_match.group(1)

        alias_map = {
            "贵州茅台": "600519",
            "茅台": "600519",
            "平安银行": "000001",
        }
        for alias, symbol in alias_map.items():
            if alias in message:
                return symbol
        return None

    def _extract_search_keyword(self, message: str) -> str:
        """提取搜索关键词，尽量返回短而稳定的关键词。"""
        for alias in ["贵州茅台", "茅台", "平安银行"]:
            if alias in message:
                return alias

        parts = re.findall(r"[\u4e00-\u9fffA-Za-z]+", message)
        if parts:
            return max(parts, key=len)[:12]
        return message[:12]

    def _infer_kline_count(self, message: str) -> int:
        """根据自然语言估算 K 线数量。"""
        if "最近一周" in message or "近一周" in message:
            return 5

        match = re.search(r"(最近|近)(\d+)(个)?(交易)?日", message)
        if match:
            return max(1, min(int(match.group(2)), 120))

        return 30

    def _is_explicit_order_message(self, message: str) -> bool:
        """识别明确交易指令，避免把“能不能买”这类分析问题误判为下单。"""
        if not any(token in message for token in ["买入", "卖出", "买", "卖"]):
            return False
        if any(token in message for token in ["能不能买", "可以买吗", "能买吗", "要不要买", "值得买"]):
            return False

        has_quantity = bool(re.search(r"\d+\s*(?:手|股)", message))
        has_order_prefix = any(token in message for token in ["模拟", "下单", "开仓", "平仓"])
        has_symbol = self._extract_symbol(message) is not None
        return has_quantity and (has_order_prefix or has_symbol)


# 全局实例
main_router = MainRouter()
