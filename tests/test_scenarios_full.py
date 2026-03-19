"""
完整版测试场景集 - 110 个场景带 Goal 评估

包含所有行情、策略、回测、边界、多轮对话场景
每个场景都定义了 Dataset Goal 和 Process Goal
"""
from tests.test_scenarios_enhanced import (
    TestScenario, Goal, GoalValidators, create_scenarios_with_goals
)


def create_full_scenarios_with_goals() -> list:
    """创建完整的 110 个测试场景（带 Goal）"""
    
    # 先获取基础的 10 个高优先级场景
    scenarios = create_scenarios_with_goals()
    
    # ========== 扩展行情查询场景（共 40 个） ==========
    
    # 股票行情场景
    stock_market_scenarios = [
        TestScenario(
            id=f'MQ{i:03d}',
            category='stock_market',
            query=query,
            priority=priority,
            expected_type='market_quote',
            expected_market='stock',
            expected_symbol=symbol,
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
                Goal('correct_symbol', '股票代码正确', 
                     lambda r, s=symbol: GoalValidators.validate_symbol(r, s)),
                Goal('has_price', '有价格信息', 
                     lambda r: '价' in r.get('reply', '')),
            ],
            process_goals=[
                Goal('fast_response', '响应快速', 
                     lambda r: GoalValidators.validate_response_time(r, 2.0)),
            ]
        )
        for i, (query, symbol, priority) in enumerate([
            ('平安银行走势', '000001', 'high'),
            ('宁德时代 K 线数据', '300750', 'high'),
            ('五粮液价格', '000858', 'medium'),
            ('茅台最近 30 天行情', '600519', 'medium'),
            ('招商银行行情', '600036', 'medium'),
            ('中国平安股价', '601318', 'medium'),
            ('东方财富走势', '300059', 'medium'),
            ('比亚迪价格', '002594', 'low'),
            ('恒瑞医药 K 线', '600276', 'low'),
        ], start=6)
    ]
    scenarios.extend(stock_market_scenarios)
    
    # 期货行情场景
    future_market_scenarios = [
        TestScenario(
            id=f'MQ{i:03d}',
            category='future_market',
            query=query,
            priority=priority,
            expected_type='market_quote',
            expected_market='future',
            expected_symbol=symbol,
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
                Goal('correct_symbol', '品种代码正确', 
                     lambda r, s=symbol: GoalValidators.validate_symbol(r, s)),
                Goal('has_price', '有价格信息', 
                     lambda r: '价' in r.get('reply', '')),
            ],
            process_goals=[
                Goal('fast_response', '响应快速', 
                     lambda r: GoalValidators.validate_response_time(r, 2.0)),
            ]
        )
        for i, (query, symbol, priority) in enumerate([
            ('沪金价格', 'AU', 'high'),
            ('沪银走势', 'AG', 'high'),
            ('原油行情', 'SC', 'high'),
            ('沪深 300 股指期货', 'IF', 'high'),
            ('中证 500 股指期货', 'IC', 'medium'),
            ('上证 50 股指期货', 'IH', 'medium'),
            ('沪铜行情', 'CU', 'medium'),
            ('豆粕价格', 'M', 'medium'),
            ('豆油走势', 'Y', 'medium'),
            ('棕榈油行情', 'P', 'medium'),
            ('白糖价格', 'SR', 'low'),
            ('甲醇行情', 'MA', 'low'),
            ('沪铝行情', 'AL', 'low'),
            ('热卷价格', 'HC', 'low'),
            ('中证 1000 股指', 'IM', 'low'),
        ], start=15)
    ]
    scenarios.extend(future_market_scenarios)
    
    # ========== 扩展策略查询场景（共 20 个） ==========
    
    strategy_scenarios = [
        TestScenario(
            id=f'SQ{i:03d}',
            category='strategy',
            query=query,
            priority=priority,
            expected_type='strategy_list',
            expected_market=market,
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
                Goal('has_strategy_list', '有策略列表', 
                     GoalValidators.validate_strategy_list),
            ],
            process_goals=[
                Goal('fast_response', '响应快速', 
                     lambda r: GoalValidators.validate_response_time(r, 2.0)),
            ]
        )
        for i, (query, market, priority) in enumerate([
            ('股票策略', 'stock', 'high'),
            ('有哪些交易方法', 'stock', 'medium'),
            ('双均线策略详情', 'stock', 'high'),
            ('RSI 策略怎么用', 'stock', 'high'),
            ('趋势策略有哪些', 'stock', 'medium'),
            ('震荡策略', 'stock', 'medium'),
            ('期货策略列表', 'future', 'high'),
            ('期货双均线策略', 'future', 'high'),
            ('期货 RSI 策略详情', 'future', 'high'),
            ('期货趋势策略', 'future', 'medium'),
            ('期货套利策略', 'future', 'medium'),
            ('双均线策略参数', 'stock', 'medium'),
            ('RSI 策略参数设置', 'stock', 'medium'),
            ('期货策略参数', 'future', 'low'),
            ('双均线和 RSI 哪个好', 'stock', 'low'),
            ('趋势策略和震荡策略区别', 'stock', 'low'),
            ('新手适合什么策略', 'stock', 'medium'),
        ], start=4)
    ]
    scenarios.extend(strategy_scenarios)
    
    # ========== 扩展回测查询场景（共 25 个） ==========
    
    backtest_scenarios = [
        TestScenario(
            id=f'BQ{i:03d}',
            category='backtest',
            query=query,
            priority=priority,
            expected_type='backtest_result',
            expected_market=market,
            expected_strategy=strategy,
            expected_symbol=symbol,
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
                Goal('has_backtest_result', '有回测结果', 
                     GoalValidators.validate_backtest_result),
                Goal('has_metrics', '有绩效指标', 
                     lambda r: '收益率' in r.get('reply', '') or '夏普' in r.get('reply', '')),
            ],
            process_goals=[
                Goal('reasonable_time', '时间合理', 
                     lambda r: GoalValidators.validate_response_time(r, 10.0)),
            ]
        )
        for i, (query, market, strategy, symbol, priority) in enumerate([
            ('测试 RSI 策略 贵州茅台', 'stock', 'rsi', '600519', 'high'),
            ('回测双均线策略 000001', 'stock', 'dual_ma', '000001', 'high'),
            ('回测宁德时代双均线', 'stock', 'dual_ma', '300750', 'high'),
            ('测试五粮液 RSI 策略', 'stock', 'rsi', '000858', 'medium'),
            ('测试期货 RSI 策略 螺纹钢', 'future', 'future_rsi', 'RB', 'high'),
            ('回测沪金趋势策略', 'future', 'future_dual_ma', 'AU', 'high'),
            ('原油 RSI 策略回测', 'future', 'future_rsi', 'SC', 'high'),
            ('回测中证 500 股指期货策略', 'future', 'future_dual_ma', 'IC', 'medium'),
            ('回测双均线 600519 最近 1 年', 'stock', 'dual_ma', '600519', 'medium'),
            ('回测 RSI 策略 茅台 2025 年', 'stock', 'rsi', '600519', 'medium'),
            ('回测期货 IF 最近 3 年', 'future', 'future_dual_ma', 'IF', 'medium'),
            ('螺纹钢回测 2024 年', 'future', 'future_dual_ma', 'RB', 'low'),
            ('回测招商银行双均线', 'stock', 'dual_ma', '600036', 'medium'),
            ('中国平安 RSI 策略回测', 'stock', 'rsi', '601318', 'medium'),
            ('回测东方财富趋势策略', 'stock', 'dual_ma', '300059', 'low'),
            ('回测沪铜趋势策略', 'future', 'future_dual_ma', 'CU', 'medium'),
            ('豆粕 RSI 回测', 'future', 'future_rsi', 'M', 'low'),
            ('回测豆油双均线', 'future', 'future_dual_ma', 'Y', 'low'),
            ('棕榈油策略回测', 'future', 'future_dual_ma', 'P', 'low'),
        ], start=7)
    ]
    scenarios.extend(backtest_scenarios)
    
    # ========== 扩展边界情况场景（共 15 个） ==========
    
    edge_scenarios = [
        TestScenario(
            id=f'EC{i:03d}',
            category='edge_case',
            query=query,
            priority=priority,
            expected_type='error',
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
                Goal('has_error_hint', '有错误提示', 
                     lambda r: '抱歉' in r.get('reply', '') or '错误' in r.get('reply', '')),
            ],
            process_goals=[
                Goal('fast_response', '响应快速', 
                     lambda r: GoalValidators.validate_response_time(r, 1.0)),
            ]
        )
        for i, (query, priority) in enumerate([
            ('???', 'high'),
            ('回测不存在的策略', 'high'),
            ('回测 999999 股票', 'high'),
            ('行情', 'medium'),
            ('策略', 'medium'),
            ('回测', 'medium'),
            ('茅台行情和策略', 'low'),
            ('先查行情再回测', 'low'),
            ('回测 600519!!!', 'medium'),
            ('贵州茅台@#$行情', 'medium'),
            ('我想查询贵州茅台股票在 2026 年 3 月份的最新行情数据，包括开盘价、收盘价、最高价、最低价、成交量等详细信息', 'low'),
            ('回测 DUAL_MA 策略 600519', 'medium'),
            ('贵州茅台 HANGQING', 'low'),
            ('回测所有股票', 'medium'),
        ], start=4)
    ]
    scenarios.extend(edge_scenarios)
    
    # ========== 多轮对话场景（10 个，特殊处理） ==========
    # 多轮对话需要在测试执行器中特殊处理，这里先定义基础场景
    multi_turn_scenarios = [
        TestScenario(
            id=f'MC{i:03d}',
            category='multi_turn',
            query=conversation[0],  # 第一轮
            priority=priority,
            expected_type='market_quote',
            dataset_goals=[
                Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            ],
            process_goals=[
                Goal('fast_response', '响应快速', 
                     lambda r: GoalValidators.validate_response_time(r, 2.0)),
            ]
        )
        for i, (conversation, priority) in enumerate([
            (['贵州茅台行情', '回测这个股票的双均线策略'], 'high'),
            (['有什么策略', '双均线策略详情'], 'high'),
            (['螺纹钢行情', '5 分钟数据'], 'medium'),
            (['期货有什么策略', '回测 IF'], 'medium'),
            (['600519 行情', '000001 呢'], 'medium'),
            (['回测双均线', '换个股票 000858'], 'low'),
            (['沪金行情', '沪银呢'], 'low'),
            (['有什么期货策略', '双均线参数多少'], 'medium'),
            (['股票行情', '期货行情'], 'low'),
            (['回测 600519', '回测结果怎么样'], 'medium'),
        ])
    ]
    scenarios.extend(multi_turn_scenarios)
    
    return scenarios


def get_full_test_scenarios() -> list:
    """获取完整测试场景（110 个）"""
    return create_full_scenarios_with_goals()


def get_scenario_statistics():
    """获取完整统计"""
    scenarios = get_full_test_scenarios()
    
    from collections import Counter
    stats = {
        'total': len(scenarios),
        'by_category': dict(Counter(s.category for s in scenarios)),
        'by_priority': dict(Counter(s.priority for s in scenarios)),
        'total_goals': sum(len(s.dataset_goals) + len(s.process_goals) for s in scenarios),
        'avg_goals_per_scenario': sum(len(s.dataset_goals) + len(s.process_goals) for s in scenarios) / len(scenarios)
    }
    
    return stats


if __name__ == '__main__':
    stats = get_scenario_statistics()
    
    print("=" * 80)
    print("完整版测试场景统计（110 个场景带 Goal）")
    print("=" * 80)
    print(f"总场景数：{stats['total']}")
    print(f"总 Goal 数：{stats['total_goals']}")
    print(f"平均每个场景：{stats['avg_goals_per_scenario']:.1f} 个 Goal")
    print(f"\n按类别:")
    for category, count in sorted(stats['by_category'].items()):
        print(f"  {category}: {count}")
    print(f"\n按优先级:")
    for priority, count in sorted(stats['by_priority'].items()):
        print(f"  {priority}: {count}")
    print("=" * 80)
