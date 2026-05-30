"""
Router task policy.

LLM routing output is treated as a proposal. This module enforces the stable
route/task compatibility table before MainRouter dispatches to a SubAgent.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

from .models import RouteType, TaskType


ROUTE_TASKS: Dict[RouteType, Set[TaskType]] = {
    RouteType.CHAT: {
        TaskType.GREETING,
        TaskType.GENERAL_QA,
        TaskType.DESCRIBE_SELF,
        TaskType.CAPABILITY_QA,
        TaskType.UNKNOWN,
    },
    RouteType.MARKET: {
        TaskType.GET_QUOTE,
        TaskType.GET_KLINE,
        TaskType.SEARCH_STOCK,
        TaskType.ANALYZE_TREND,
    },
    RouteType.STRATEGY: {
        TaskType.LIST_STRATEGIES,
        TaskType.STRATEGY_QA,
    },
    RouteType.BACKTEST: {
        TaskType.RUN_BACKTEST,
        TaskType.OPTIMIZE_BACKTEST,
        TaskType.BACKTEST_QA,
    },
    RouteType.TRADE: {
        TaskType.TRADE_QA,
        TaskType.PLACE_ORDER,
        TaskType.CANCEL_ORDER,
        TaskType.CHECK_POSITIONS,
    },
}

TASK_DEFAULT_ROUTE: Dict[TaskType, RouteType] = {
    task_type: route
    for route, task_types in ROUTE_TASKS.items()
    for task_type in task_types
}


def get_default_route_for_task(task_type: TaskType) -> Optional[RouteType]:
    """Return the canonical route for a task type, if one is known."""
    return TASK_DEFAULT_ROUTE.get(task_type)


def normalize_route_for_task(route: RouteType, task_type: TaskType) -> RouteType:
    """Return a compatible route for the task type."""
    if task_type in ROUTE_TASKS.get(route, set()):
        return route

    return TASK_DEFAULT_ROUTE.get(task_type, route)
