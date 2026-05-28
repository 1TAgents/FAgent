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
import uuid

from .models import (
    BacktestRequest, BacktestResponse, BacktestReport, StrategyConfig
)
from .engine import BacktestEngine
from .strategies import get_strategy_class
from .data_loader import get_data_loader
from .run_store import get_run_store
from .vectorized_strategies import get_vectorized_strategy, split_vectorized_params

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
            strategy_params, execution_params = split_vectorized_params(request.params)
            strategy = get_vectorized_strategy(
                request.strategy_name,
                **strategy_params,
            )
            
            # 生成信号
            data_with_signals = strategy.generate_signals(data)
            
            # 快速回测
            result = strategy.backtest(
                data_with_signals,
                request.initial_capital,
                **execution_params,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"向量化回测完成 | time={elapsed:.3f}s, 总收益={result['total_returns']:.2%}")

            report = _create_report_from_dict(
                request.strategy_name,
                request.symbol,
                request.start_date,
                request.end_date,
                result,
                request.params,
                request.initial_capital,
            )
            report_id, artifacts_dir = get_run_store().persist_run(
                request,
                report,
                engine="vectorized",
            )
            
            # 转换为标准响应格式
            return BacktestResponse(
                success=True,
                report=report,
                report_id=report_id,
                artifacts_dir=artifacts_dir,
                engine="vectorized",
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
        report_id, artifacts_dir = get_run_store().persist_run(
            request,
            report,
            engine="classic",
        )
        
        elapsed = time.time() - start_time
        logger.info(f"回测完成 | time={elapsed:.2f}s, 总收益={report.metrics.total_return:.2f}%")
        
        return BacktestResponse(
            success=True,
            report=report,
            report_id=report_id,
            artifacts_dir=artifacts_dir,
            engine="classic",
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
                strategy_params, execution_params = split_vectorized_params(params)
                strategy = get_vectorized_strategy(strategy_name, **strategy_params)
                data_with_signals = strategy.generate_signals(data)
                result = strategy.backtest(
                    data_with_signals,
                    initial_capital,
                    **execution_params,
                )
                
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
    result: Dict, params: Dict,
    initial_capital: float,
) -> BacktestReport:
    """从字典创建回测报告（简化版）"""
    from .models import PerformanceMetrics, Trade

    equity_values = []
    for value in result.get("equity_curve", []):
        if pd.isna(value):
            equity_values.append(initial_capital)
        else:
            equity_values.append(float(value))

    max_drawdown_pct = result.get("max_drawdown", 0) * 100
    annual_return_pct = result.get("annual_return", result.get("total_returns", 0)) * 100
    benchmark_return_pct = result.get("benchmark_return")
    if benchmark_return_pct is not None:
        benchmark_return_pct *= 100
    alpha_pct = result.get("alpha")
    if alpha_pct is not None:
        alpha_pct *= 100
    winning_trades = int(result.get("winning_trades", 0))
    losing_trades = int(result.get("losing_trades", 0))
    
    metrics = PerformanceMetrics(
        total_return=result['total_returns'] * 100,
        annual_return=annual_return_pct,
        benchmark_return=benchmark_return_pct,
        alpha=alpha_pct,
        volatility=result.get("volatility", 0) * 100,
        sharpe_ratio=result['sharpe_ratio'],
        max_drawdown=max_drawdown_pct,
        calmar_ratio=(annual_return_pct / abs(max_drawdown_pct)) if max_drawdown_pct else 0,
        final_capital=result.get("final_capital", equity_values[-1] if equity_values else initial_capital),
        initial_capital=initial_capital,
        total_trades=int(result.get("trades", 0)),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=result.get("win_rate", 0) * 100,
        profit_factor=result.get("profit_factor", 0),
        avg_win=result.get("avg_win", 0),
        avg_loss=result.get("avg_loss", 0),
        total_pnl=result.get("total_pnl", (equity_values[-1] - initial_capital) if equity_values else 0),
    )

    trades = []
    for raw_trade in result.get("trade_records", []):
        trades.append(Trade(
            trade_id=str(uuid.uuid4()),
            symbol=raw_trade.get("symbol") or symbol,
            entry_price=float(raw_trade["entry_price"]),
            exit_price=raw_trade.get("exit_price"),
            entry_time=str(raw_trade["entry_time"]),
            exit_time=raw_trade.get("exit_time"),
            quantity=int(raw_trade["quantity"]),
            side=raw_trade.get("side", "long"),
            pnl=raw_trade.get("pnl"),
            pnl_percent=raw_trade.get("pnl_percent"),
            commission_total=raw_trade.get("commission_total"),
            is_open=bool(raw_trade.get("is_open", False)),
            exit_reason=raw_trade.get("exit_reason"),
        ))
    
    return BacktestReport(
        strategy_name=strategy_name,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        trading_days=len(result.get('dates', [])),
        config=StrategyConfig(name=strategy_name, initial_capital=initial_capital, params=params),
        metrics=metrics,
        trades=trades,
        equity_curve={str(d): v for d, v in zip(result.get('dates', []), equity_values)}
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
    """
    payload = get_run_store().load_run(report_id)
    if payload is None:
        return {"success": False, "error": f"report_id 不存在：{report_id}"}
    return {"success": True, **payload}


@router.post("/validate")
async def validate_strategy(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行策略验证（支持多种验证方式）
    
    Args:
        request: 验证请求，包含：
            - strategy_name: 策略名称
            - symbol: 股票代码
            - start_date: 开始日期
            - end_date: 结束日期
            - validation_mode: 验证方式 (holdout | walk_forward | expanding_window | auto)
            - validation_config: 验证器配置（可选）
            - param_grid: 参数网格（可选，用于优化）
            - initial_capital: 初始资金（默认 100000）
    
    Returns:
        验证报告
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"收到验证请求 | strategy={request.get('strategy_name')} | "
            f"validation_mode={request.get('validation_mode', 'auto')}"
        )
        
        # 1. 加载数据
        data_loader = get_data_loader()
        data = data_loader.load_klines(
            symbol=request["symbol"],
            start_date=request["start_date"],
            end_date=request["end_date"],
            period="daily",
            adjust="qfq"
        )
        
        if data.empty:
            return {
                "success": False,
                "error": f"无数据：{request['symbol']}，请先同步数据或检查日期范围"
            }
        
        logger.info(f"数据加载完成 | rows={len(data)}")
        
        # 2. 创建验证器引擎
        from .validator_engine import create_validator_engine
        
        validator_type = request.get("validation_mode", "auto")
        validation_config = request.get("validation_config", {})
        initial_capital = request.get("initial_capital", 100000.0)
        
        engine = create_validator_engine(
            validator_type=validator_type,
            validator_config=validation_config,
            initial_capital=initial_capital
        )
        
        # 3. 执行验证
        param_grid = request.get("param_grid")
        default_params = request.get("default_params", {})
        
        report = engine.run(
            strategy_name=request["strategy_name"],
            data=data,
            param_grid=param_grid,
            default_params=default_params
        )
        
        elapsed = time.time() - start_time
        logger.info(f"验证完成 | time={elapsed:.2f}s, rounds={report.num_rounds}")
        
        # 4. 返回报告
        return {
            "success": True,
            "report": report.to_dict(),
            "elapsed_seconds": elapsed
        }
        
    except Exception as e:
        logger.error(f"验证失败 | error={e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.get("/validators")
async def list_validators() -> Dict[str, Any]:
    """列出所有可用的验证器类型"""
    return {
        "validators": [
            {
                "type": "holdout",
                "name": "固定分割验证",
                "description": "将数据按固定比例分为训练集和测试集",
                "suitable_for": "长期策略（参数稳定）",
                "default_config": {
                    "train_ratio": 0.6
                }
            },
            {
                "type": "walk_forward",
                "name": "滚动窗口验证",
                "description": "使用滚动窗口进行多轮验证",
                "suitable_for": "中短期策略（参数随市场变化）",
                "default_config": {
                    "window_size": 120,
                    "step_size": 20,
                    "test_size": 20
                }
            },
            {
                "type": "expanding_window",
                "name": "扩展窗口验证",
                "description": "训练集逐步扩展，测试集滚动",
                "suitable_for": "参数稳定的策略，希望用更多历史数据",
                "default_config": {
                    "initial_window": 120,
                    "step_size": 20,
                    "test_size": 20
                }
            },
            {
                "type": "auto",
                "name": "自动选择",
                "description": "根据策略类型自动选择验证方式（默认使用 walk_forward）",
                "suitable_for": "通用",
                "default_config": {}
            }
        ]
    }
