#!/usr/bin/env python3
"""
准备 GDPS 路演 Demo 数据

1. 确保贵州茅台 (600519) 数据存在
2. 预运行回测生成结果
3. 准备策略库数据
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.stock.strategies.dual_ma import StockDualMAStrategy
from agents.backtest.models import StrategyConfig, Portfolio, Position
from agents.backtest.engine import BacktestEngine
import pandas as pd


def generate_mock_data(symbol: str = '600519', days: int = 365):
    """生成模拟数据用于 Demo"""
    print(f"📊 生成 {symbol} 的模拟数据 ({days}天)...")
    
    # 生成日期
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')  # 工作日
    
    # 生成模拟价格（随机游走 + 趋势）
    np.random.seed(42)  # 固定种子，保证每次 Demo 数据一致
    
    # 初始价格
    initial_price = 1700
    
    # 生成收益率（带趋势的随机游走）
    trend = 0.0003  # 轻微上涨趋势
    volatility = 0.02  # 波动率
    
    returns = np.random.normal(trend, volatility, len(dates))
    
    # 计算收盘价
    close_prices = initial_price * np.cumprod(1 + returns)
    
    # 生成 OHLC 数据
    data = []
    for i, date in enumerate(dates):
        close = close_prices[i]
        daily_range = close * np.random.uniform(0.01, 0.03)
        high = close + daily_range * np.random.uniform(0.3, 0.7)
        low = close - daily_range * np.random.uniform(0.3, 0.7)
        open_price = low + (high - low) * np.random.uniform(0.3, 0.7)
        volume = int(np.random.uniform(1e6, 5e6))
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'symbol': symbol,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    print(f"✅ 生成 {len(df)} 条数据")
    print(f"   价格范围：¥{df['close'].min():.2f} - ¥{df['close'].max():.2f}")
    
    return df


def run_demo_backtest(data: pd.DataFrame):
    """运行 Demo 回测"""
    print("\n📈 运行回测（双均线策略，参数 5/20）...")
    
    # 创建策略配置
    config = StrategyConfig(
        name='dual_ma',
        params={'short_period': 5, 'long_period': 20},
        initial_capital=100000,
        commission_rate=0.0003
    )
    
    # 创建回测引擎
    engine = BacktestEngine(config)
    
    # 运行回测
    result = engine.run(StockDualMAStrategy, data)
    
    # 打印结果
    print("\n✅ 回测完成！")
    m = result.metrics
    
    print("\n📊 绩效指标:")
    print(f"   初始资金：¥{m.initial_capital:,.2f}")
    print(f"   最终资金：¥{m.final_capital:,.2f}")
    print(f"   总收益：{m.total_return*100:.2f}%")
    print(f"   年化收益：{m.annual_return*100:.2f}%")
    print(f"   夏普比率：{m.sharpe_ratio:.2f}")
    print(f"   最大回撤：{m.max_drawdown*100:.2f}%")
    print(f"   交易次数：{m.total_trades}")
    print(f"   胜率：{m.win_rate*100:.1f}%")
    
    # 保存结果到 JSON（用于前端展示）
    output = {
        'initial_capital': m.initial_capital,
        'final_capital': m.final_capital,
        'total_return': m.total_return,
        'annual_return': m.annual_return,
        'sharpe_ratio': m.sharpe_ratio,
        'max_drawdown': m.max_drawdown,
        'total_trades': m.total_trades,
        'win_rate': m.win_rate,
        'trades': [
            {
                'symbol': t.symbol,
                'entry_date': t.entry_date.strftime('%Y-%m-%d') if hasattr(t.entry_date, 'strftime') else str(t.entry_date),
                'exit_date': t.exit_date.strftime('%Y-%m-%d') if hasattr(t.exit_date, 'strftime') else str(t.exit_date),
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'pnl': t.pnl,
                'return_pct': t.return_pct
            }
            for t in result.trades[:10]  # 只显示前 10 笔
        ]
    }
    
    import json
    output_path = Path(__file__).parent.parent / 'data' / 'demo_backtest_result.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存到：{output_path}")
    
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("🎬 FAgent GDPS 路演 Demo 数据准备")
    print("=" * 60)
    
    # 1. 生成模拟数据
    data = generate_mock_data('600519', 365)
    
    # 2. 运行回测
    result = run_demo_backtest(data)
    
    # 3. 保存数据到数据库
    db_path = Path(__file__).parent.parent / 'data' / 'stock_data.db'
    print(f"\n💾 保存数据到数据库：{db_path}")
    
    conn = sqlite3.connect(db_path)
    data.to_sql('stock_kline', conn, if_exists='append', index=False)
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Demo 数据准备完成！")
    print("=" * 60)
    print("\n下一步:")
    print("1. 启动后端：cd <repo-root> && python3 -m uvicorn backend.api.main:app --reload --port 8000")
    print("2. 启动前端：cd <repo-root>/frontend && npm run dev")
    print("3. 访问 http://localhost:5173 进行演示")
    print("\nDemo 脚本:")
    print("  1. 对话查询：'帮我看看贵州茅台现在怎么样'")
    print("  2. 策略回测：'用双均线策略回测一下茅台，参数 5 日和 20 日，过去一年'")
    print("  3. 策略库：'你们有哪些策略可以用？'")


if __name__ == '__main__':
    main()
