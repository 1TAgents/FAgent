"""
Backtest API - 回测服务 FastAPI 接口

提供回测执行、报告查询等接口
"""
import logging
from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .models import (
    BacktestRequest, BacktestResponse, BacktestReport, StrategyConfig
)
from .engine import BacktestEngine
from .strategies import get_strategy_class

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


# 模拟数据生成（用于测试）
def generate_mock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """生成模拟 K 线数据"""
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    
    np.random.seed(42)
    base_price = 100.0
    
    # 生成随机游走价格
    returns = np.random.normal(0.0005, 0.02, len(dates))  # 日均收益 0.05%，波动 2%
    prices = base_price * np.cumprod(1 + returns)
    
    # 生成 OHLCV
    data = {
        'symbol': symbol,
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, len(dates))),
        'high': prices * (1 + np.random.uniform(0, 0.02, len(dates))),
        'low': prices * (1 - np.random.uniform(0, 0.02, len(dates))),
        'close': prices,
        'volume': np.random.uniform(1e6, 1e7, len(dates)).astype(int),
    }
    
    df = pd.DataFrame(data, index=dates)
    return df


async def load_real_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    加载真实历史数据
    
    TODO: 集成 MCP client 或 data_service 获取真实数据
    当前使用模拟数据
    """
    # 暂时使用模拟数据
    logger.info(f"加载数据 | symbol={symbol}, start={start_date}, end={end_date}")
    return generate_mock_data(symbol, start_date, end_date)


@router.post("/run")
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """
    执行回测
    
    Args:
        request: 回测请求
        
    Returns:
        回测报告
    """
    try:
        logger.info(f"收到回测请求 | strategy={request.strategy_name}, symbol={request.symbol}")
        
        # 1. 加载数据
        data = await load_real_data(
            request.symbol,
            request.start_date,
            request.end_date
        )
        
        if data.empty:
            return BacktestResponse(
                success=False,
                error=f"无数据：{request.symbol}"
            )
        
        # 2. 创建策略配置
        config = StrategyConfig(
            name=request.strategy_name,
            initial_capital=request.initial_capital,
            params=request.params
        )
        
        # 3. 获取策略类
        try:
            strategy_class = get_strategy_class(request.strategy_name)
        except ValueError as e:
            return BacktestResponse(
                success=False,
                error=str(e)
            )
        
        # 4. 执行回测
        engine = BacktestEngine(config)
        report = engine.run(strategy_class, data)
        
        logger.info(f"回测完成 | 总收益={report.metrics.total_return:.2f}%")
        
        return BacktestResponse(
            success=True,
            report=report
        )
        
    except Exception as e:
        logger.error(f"回测失败 | error={e}")
        return BacktestResponse(
            success=False,
            error=str(e)
        )


@router.get("/strategies")
async def list_strategies() -> Dict[str, Any]:
    """列出所有可用策略"""
    from .strategies import STRATEGY_REGISTRY
    
    strategies = {}
    for name, cls in STRATEGY_REGISTRY.items():
        strategies[name] = {
            "name": cls.__name__,
            "description": cls.__doc__.split('\n')[0] if cls.__doc__ else "",
        }
    
    return {"strategies": strategies}


@router.get("/report/{report_id}")
async def get_report(report_id: str) -> Dict[str, Any]:
    """
    获取回测报告
    
    TODO: 实现报告存储和查询
    """
    return {"error": "Not implemented"}
