"""
Observability API - 可观测性接口

提供追踪、指标、工具列表、模型列表等查询端点。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..core.tracing import trace_store
from ..core.logging import logger
from ..core.session_state import session_state
from ..tools.registry import tool_registry
from ..tools.builtin import register_builtin_tools
from ..services.provider import provider_registry
from ..services.memory_bridge import memory_bridge

router = APIRouter(prefix="/api", tags=["observability"])

# 确保内置工具已注册
register_builtin_tools(tool_registry)


@router.get("/tools")
async def list_tools():
    """获取所有可用工具及其 schema。"""
    tools = []
    for name in tool_registry.tool_names:
        tool = tool_registry.get(name)
        if tool:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "category": tool.category,
                "schema": tool.schema,
            })
    return {"tools": tools, "total": len(tools)}


@router.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """获取指定工具的详细信息。"""
    tool = tool_registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return {
        "name": tool.name,
        "description": tool.description,
        "category": tool.category,
        "schema": tool.schema,
    }


@router.get("/models")
async def list_models():
    """获取所有可用模型及其能力信息。"""
    models = provider_registry.to_frontend_list()
    return {"models": models, "total": len(models)}


@router.get("/providers")
async def list_providers():
    """获取所有提供商信息。"""
    providers = []
    for p in provider_registry.providers:
        providers.append({
            "name": p.name,
            "base_url": p.base_url,
            "model_count": len(p.models),
            "model_ids": p.model_short_ids,
        })
    return {"providers": providers}


@router.get("/traces/recent")
async def get_recent_traces(limit: int = 20):
    """获取最近的追踪记录。"""
    traces = trace_store.get_recent_traces(limit)
    for t in traces:
        t.pop("trace_json", None)  # 不返回完整 JSON
        t.pop("final_response", None)
    return {"traces": traces, "total": len(traces)}


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str):
    """获取指定追踪记录的详细信息。"""
    trace = trace_store.get_by_trace_id(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
    return {"trace": trace}


@router.get("/sessions/{cid}/traces")
async def get_session_traces(cid: int, limit: int = 20):
    """获取指定会话的追踪记录。"""
    traces = trace_store.get_by_session(cid, limit)
    for t in traces:
        t.pop("trace_json", None)
        t.pop("final_response", None)
    return {"traces": traces, "total": len(traces)}


@router.get("/sessions/{cid}/metrics")
async def get_session_metrics(cid: int):
    """获取指定会话的聚合指标。"""
    metrics = trace_store.get_session_metrics(cid)
    return {"metrics": metrics.to_dict()}


@router.get("/memory/stats")
async def get_memory_stats():
    """获取记忆系统统计信息。"""
    return {"memory": memory_bridge.stats()}


@router.get("/sessions/{cid}/state")
async def get_session_state(cid: int):
    """获取会话状态。"""
    info = session_state.get_info(cid)
    if not info:
        return {"cid": cid, "state": "idle"}
    return info


@router.get("/sessions/active")
async def list_active_sessions():
    """列出所有活跃会话。"""
    active = session_state.list_active()
    return {"active": active, "total": len(active)}


@router.post("/sessions/{cid}/cancel")
async def cancel_session(cid: int):
    """取消指定会话。"""
    cancelled = session_state.cancel(cid)
    if cancelled:
        return {"cid": cid, "cancelled": True}
    raise HTTPException(status_code=400, detail=f"Session cid={cid} 未在处理中或不存在")


@router.get("/observability/summary")
async def observability_summary():
    """可观测性总览：工具数、模型数、最近追踪数、记忆数。"""
    tools = tool_registry.tool_names
    if not tools:
        register_builtin_tools(tool_registry)
        tools = tool_registry.tool_names

    recent_traces = trace_store.get_recent_traces(1)
    memory_stats = memory_bridge.stats()

    return {
        "tools": {
            "count": len(tools),
            "categories": tool_registry.categories,
        },
        "models": {
            "count": len(provider_registry.all_models),
            "providers": len(provider_registry.providers),
        },
        "traces": {
            "recent_count": len(recent_traces),
        },
        "memory": memory_stats,
    }


# ==================== 增强端点 ====================


@router.get("/traces/filter")
async def filter_traces(
    route: Optional[str] = None,
    cid: Optional[int] = None,
    start_ts: Optional[float] = None,
    end_ts: Optional[float] = None,
    limit: int = Query(default=50, le=200),
):
    """按条件过滤追踪记录（路由/会话/时间范围）。"""
    traces = trace_store.get_traces_filtered(
        route=route, cid=cid, start_ts=start_ts, end_ts=end_ts, limit=limit,
    )
    for t in traces:
        t.pop("trace_json", None)
        t.pop("final_response", None)
    return {"traces": traces, "total": len(traces)}


@router.get("/metrics/global")
async def global_metrics():
    """全局聚合指标：总请求数、token 消耗、路由分布、24h 活跃度。"""
    return {"metrics": trace_store.get_global_metrics()}


@router.get("/metrics/by-route")
async def metrics_by_route():
    """按路由类型分组的指标。"""
    global_data = trace_store.get_global_metrics()
    routes = global_data.get("route_distribution", {})
    # 补充各路由的平均延迟
    result = {}
    for route_name, info in routes.items():
        cid_traces = trace_store.get_traces_filtered(route=route_name, limit=500)
        total_latency = sum(t.get("total_latency_ms", 0) for t in cid_traces)
        count = len(cid_traces)
        result[route_name] = {
            **info,
            "avg_latency_ms": round(total_latency / max(count, 1), 1),
            "sample_count": count,
        }
    return {"routes": result}
