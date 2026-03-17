"""
Backtest Report Generator - 回测报告生成器

生成 HTML 可视化报告，包含：
- 资金曲线图
- 回撤时间线
- 月度收益 heatmap
- 年度收益柱状图
- 交易分布
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import json


def generate_html_report(backtest_result: Dict, output_path: str = "backtest_report.html"):
    """
    生成 HTML 回测报告
    
    Args:
        backtest_result: 回测结果字典
        output_path: 输出文件路径
    """
    # 提取数据
    metrics = backtest_result.get('metrics', {})
    equity_curve = backtest_result.get('equity_curve', {})
    trades = backtest_result.get('trades', [])
    monthly_returns = backtest_result.get('monthly_returns', {})
    
    # 生成图表数据
    chart_data = prepare_chart_data(equity_curve, monthly_returns, trades)
    
    # HTML 模板
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAgent 回测报告 - {backtest_result.get('strategy_name', 'Strategy')}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .metric-label {{ font-size: 0.9em; opacity: 0.9; }}
        .positive {{ color: #4CAF50; }}
        .negative {{ color: #f44336; }}
        .chart {{ margin: 30px 0; height: 400px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f5f5f5; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 FAgent 回测报告</h1>
        
        <div style="margin: 20px 0; color: #666;">
            <strong>策略:</strong> {backtest_result.get('strategy_name', 'N/A')} | 
            <strong>标的:</strong> {backtest_result.get('symbol', 'N/A')} | 
            <strong>区间:</strong> {backtest_result.get('start_date', 'N/A')} ~ {backtest_result.get('end_date', 'N/A')} |
            <strong>交易日:</strong> {backtest_result.get('trading_days', 0)}
        </div>
        
        <h2>📈 核心指标</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-label">总收益率</div>
                <div class="metric-value {'positive' if metrics.get('total_return', 0) >= 0 else 'negative'}">{metrics.get('total_return', 0):+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">年化收益率</div>
                <div class="metric-value {'positive' if metrics.get('annual_return', 0) >= 0 else 'negative'}">{metrics.get('annual_return', 0):+.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">夏普比率</div>
                <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value negative">{metrics.get('max_drawdown', 0):.2f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">胜率</div>
                <div class="metric-value {'positive' if metrics.get('win_rate', 0) >= 50 else ''}">{metrics.get('win_rate', 0):.1f}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">交易次数</div>
                <div class="metric-value">{metrics.get('total_trades', 0)}</div>
            </div>
        </div>
        
        <h2>💹 资金曲线</h2>
        <div id="equity-chart" class="chart"></div>
        
        <h2>📉 回撤时间线</h2>
        <div id="drawdown-chart" class="chart"></div>
        
        <h2>📅 月度收益</h2>
        <div id="monthly-chart" class="chart"></div>
        
        <h2>📊 交易记录</h2>
        <table>
            <thead>
                <tr>
                    <th>序号</th>
                    <th>股票代码</th>
                    <th>入场日期</th>
                    <th>出场日期</th>
                    <th>入场价</th>
                    <th>出场价</th>
                    <th>数量</th>
                    <th>盈亏</th>
                    <th>盈亏率</th>
                </tr>
            </thead>
            <tbody>
                {''.join(generate_trade_rows(trades[:20]))}
            </tbody>
        </table>
        
        <div class="footer">
            生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | FAgent Backtest System
        </div>
    </div>
    
    <script>
        // 资金曲线
        Plotly.newPlot('equity-chart', {chart_data['equity']});
        
        // 回撤图
        Plotly.newPlot('drawdown-chart', {chart_data['drawdown']});
        
        // 月度收益
        Plotly.newPlot('monthly-chart', {chart_data['monthly']});
    </script>
</body>
</html>
"""
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def prepare_chart_data(equity_curve: Dict, monthly_returns: Dict, trades: List) -> Dict:
    """
    准备图表数据
    
    Args:
        equity_curve: 权益曲线
        monthly_returns: 月度收益
        trades: 交易记录
        
    Returns:
        图表数据字典
    """
    # 资金曲线
    dates = list(equity_curve.keys())
    equity_values = list(equity_curve.values())
    
    equity_trace = {
        'x': dates,
        'y': equity_values,
        'type': 'scatter',
        'mode': 'lines',
        'name': '资金曲线',
        'line': {'color': '#4CAF50', 'width': 2}
    }
    
    # 回撤计算
    equity_array = np.array(equity_values)
    peak = np.maximum.accumulate(equity_array)
    drawdown = (equity_array - peak) / peak * 100
    
    drawdown_trace = {
        'x': dates,
        'y': drawdown,
        'type': 'scatter',
        'mode': 'lines',
        'name': '回撤',
        'line': {'color': '#f44336', 'width': 1},
        'fill': 'tozeroy'
    }
    
    # 月度收益
    months = list(monthly_returns.keys())
    returns = [monthly_returns[m] for m in months]
    colors = ['#4CAF50' if r >= 0 else '#f44336' for r in returns]
    
    monthly_trace = {
        'x': months,
        'y': returns,
        'type': 'bar',
        'marker': {'color': colors},
        'name': '月度收益'
    }
    
    return {
        'equity': [equity_trace],
        'drawdown': [drawdown_trace],
        'monthly': [monthly_trace]
    }


def generate_trade_rows(trades: List) -> List[str]:
    """生成交易记录行"""
    rows = []
    for i, trade in enumerate(trades, 1):
        pnl = trade.get('pnl', 0)
        pnl_pct = trade.get('pnl_percent', 0)
        pnl_class = 'positive' if pnl >= 0 else 'negative'
        
        row = f"""
            <tr>
                <td>{i}</td>
                <td>{trade.get('symbol', 'N/A')}</td>
                <td>{trade.get('entry_time', 'N/A')}</td>
                <td>{trade.get('exit_time', 'N/A')}</td>
                <td>{trade.get('entry_price', 0):.2f}</td>
                <td>{trade.get('exit_price', 0):.2f}</td>
                <td>{trade.get('quantity', 0)}</td>
                <td class="{pnl_class}">{pnl:+.2f}</td>
                <td class="{pnl_class}">{pnl_pct:+.2f}%</td>
            </tr>
        """
        rows.append(row)
    
    return rows


# 示例用法
if __name__ == "__main__":
    # 测试数据
    test_result = {
        'strategy_name': '双均线策略',
        'symbol': '600519',
        'start_date': '2025-01-01',
        'end_date': '2025-12-31',
        'trading_days': 243,
        'metrics': {
            'total_return': 15.23,
            'annual_return': 15.23,
            'sharpe_ratio': 1.25,
            'max_drawdown': -8.50,
            'win_rate': 55.0,
            'total_trades': 20
        },
        'equity_curve': {
            '2025-01-01': 100000,
            '2025-01-02': 100500,
            '2025-01-03': 101200,
        },
        'monthly_returns': {
            '2025-01': 2.5,
            '2025-02': -1.2,
            '2025-03': 3.8
        },
        'trades': [
            {
                'symbol': '600519',
                'entry_time': '2025-01-02',
                'exit_time': '2025-01-15',
                'entry_price': 1500.0,
                'exit_price': 1580.0,
                'quantity': 100,
                'pnl': 8000,
                'pnl_percent': 5.33
            }
        ]
    }
    
    # 生成报告
    output_path = generate_html_report(test_result, "test_report.html")
    print(f"✅ 报告已生成：{output_path}")
