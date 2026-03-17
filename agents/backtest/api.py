"""
Backtest API - 回测服务 FastAPI 接口

提供回测执行、报告查询等接口

优化：
1. 集成真实数据源（SQLite + AKShare）
2. 向量化策略（性能提升 10-100x）
3. 参数网格搜索
"""
import logging
from fastapi import APIRouter, HTTPException
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time

from .models import (
    BacktestRequest, BacktestResponse, BacktestReport, StrategyConfig
)
from .engine import BacktestEngine
from .strategies import get_strategy_class
from .data_loader import get_data_loader
from .vectorized_strategies import get_vectorized_strategy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run")
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """
    执行回测（使用真实数据库数据）
    
    Args:
        request: 回测请求
        
    Returns:
        回测报告
    """
    start_time = time.time()
    
    try:
        logger.info(f"收到回测请求 | strategy={request.strategy_name}, symbol={request.symbol}")
        
        # 1. 从 SQLite 数据库加载真实数据
        data_loader = get_data_loader()
        data = data_loader.load_klines(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            period="daily",
            adjust="qfq"  # 前复权
        )
        
        if data.empty:
            logger.warning(f"无数据 | symbol={request.symbol}, range={request.start_date}~{request.end_date}")
            return BacktestResponse(
                success=False,
                error=f"无数据：{request.symbol}，请先同步数据或检查日期范围"
            )
        
        logger.info(f"数据加载完成 | symbol={request.symbol}, rows={len(data)}")
        
        # 2. 尝试向量化回测（更快）
        try:
            strategy = get_vectorized_strategy(
                request.strategy_name,
                **request.params
            )
            
            # 生成信号
            data_with_signals = strategy.generate_signals(data)
            
            # 快速回测
            result = strategy.backtest(data_with_signals, request.initial_capital)
            
            elapsed = time.time() - start_time
            logger.info(f"向量化回测完成 | time={elapsed:.3f}s, 总收益={result['total_returns']:.2%}")
            
            # 转换为标准响应格式
            return BacktestResponse(
                success=True,
                report=_create_report_from_dict(
                    request.strategy_name, request.symbol,
                    request.start_date, request.end_date,
                    result, request.params
                )
            )
            
        except KeyError:
            # 向量化策略不支持，使用原始引擎
            logger.info("使用原始回测引擎")
            pass
        
        # 3. 原始回测引擎（兼容旧策略）
        config = StrategyConfig(
            name=request.strategy_name,
            initial_capital=request.initial_capital,
            params=request.params
        )
        
        strategy_class = get_strategy_class(request.strategy_name)
        engine = BacktestEngine(config)
        report = engine.run(strategy_class, data)
        
        elapsed = time.time() - start_time
        logger.info(f"回测完成 | time={elapsed:.2f}s, 总收益={report.metrics.total_return:.2f}%")
        
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


@router.post("/grid_search")
async def grid_search(
    strategy_name: str,
    symbol: str,
    start_date: str,
    end_date: str,
    param_grid: Dict[str, List[Any]],
    initial_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    参数网格搜索
    
    Args:
        strategy_name: 策略名称
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        param_grid: 参数网格（如 {"short_period": [5, 10, 20], "long_period": [20, 50, 100]}）
        initial_capital: 初始资金
        
    Returns:
        最优参数和绩效
    """
    start_time = time.time()
    
    try:
        logger.info(f"开始网格搜索 | strategy={strategy_name}, combinations={np.prod([len(v) for v in param_grid.values()])}")
        
        # 1. 加载数据
        data_loader = get_data_loader()
        data = data_loader.load_klines(symbol, start_date, end_date)
        
        if data.empty:
            return {"success": False, "error": f"无数据：{symbol}"}
        
        # 2. 网格搜索
        best_result = None
        best_params = None
        best_sharpe = -999
        
        all_results = []
        
        # 生成参数组合
        from itertools import product
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        for values in product(*param_values):
            params = dict(zip(param_names, values))
            
            try:
                strategy = get_vectorized_strategy(strategy_name, **params)
                data_with_signals = strategy.generate_signals(data)
                result = strategy.backtest(data_with_signals, initial_capital)
                
                # 记录结果
                if result['sharpe_ratio'] > best_sharpe:
                    best_sharpe = result['sharpe_ratio']
                    best_params = params
                    best_result = result
                
                all_results.append({
                    'params': params,
                    'sharpe': result['sharpe_ratio'],
                    'returns': result['total_returns'],
                    'max_drawdown': result['max_drawdown']
                })
                
            except Exception as e:
                logger.warning(f"参数组合失败 | params={params}, error={e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"网格搜索完成 | time={elapsed:.2f}s, best_sharpe={best_sharpe:.2f}")
        
        return {
            'success': True,
            'best_params': best_params,
            'best_result': best_result,
            'total_combinations': len(all_results),
            'elapsed_seconds': elapsed,
            'all_results': sorted(all_results, key=lambda x: x['sharpe'], reverse=True)[:20]  # 返回前 20
        }
        
    except Exception as e:
        logger.error(f"网格搜索失败 | error={e}")
        return {'success': False, 'error': str(e)}


def _create_report_from_dict(
    strategy_name: str, symbol: str,
    start_date: str, end_date: str,
    result: Dict, params: Dict
) -> BacktestReport:
    """从字典创建回测报告（简化版）"""
    from .models import PerformanceMetrics
    
    metrics = PerformanceMetrics(
        total_return=result['total_returns'] * 100,
        annual_return=result['total_returns'] * 100,  # 简化
        sharpe_ratio=result['sharpe_ratio'],
        max_drawdown=result['max_drawdown'] * 100,
        final_capital=result['equity_curve'][-1] if result['equity_curve'] else 0,
        initial_capital=100000.0
    )
    
    return BacktestReport(
        strategy_name=strategy_name,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        trading_days=len(result.get('dates', [])),
        config=StrategyConfig(name=strategy_name, params=params),
        metrics=metrics,
        trades=[],  # 向量化版本暂不返回详细交易
        equity_curve={str(d): v for d, v in zip(result.get('dates', []), result.get('equity_curve', []))}
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
