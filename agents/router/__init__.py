"""
Router 模块 - 主路由器
"""

from .models import TaskContext, RouteDecision

__all__ = [
    "TaskContext",
    "RouteDecision",
    "MainRouter",
    "main_router",
]


def __getattr__(name):
    if name in {"MainRouter", "main_router"}:
        from .main_router import MainRouter, main_router

        exports = {
            "MainRouter": MainRouter,
            "main_router": main_router,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
