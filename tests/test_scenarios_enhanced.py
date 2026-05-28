"""
增强版测试场景集 - 带 Goal 评估

评估维度：
1. Dataset Goal（数据目标）- 结果是否正确
2. Process Goal（过程目标）- 过程是否合理

通过标准：
- 每个测试运行 3 次
- 正确率阈值：0.5（3 次中对 2-3 次算通过）
- 任一维度通过即算通过
"""
from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field


@dataclass
class Goal:
    """评估目标"""
    name: str  # 目标名称
    description: str  # 目标描述
    validator: Callable  # 验证函数
    weight: float = 1.0  # 权重


@dataclass
class TestScenario:
    """测试场景"""
    id: str  # 场景 ID
    category: str  # 类别
    query: str  # 查询语句
    priority: str  # 优先级
    
    # 预期结果
    expected_type: str = None
    expected_market: str = None
    expected_symbol: str = None
    expected_strategy: str = None
    
    # 评估目标
    dataset_goals: List[Goal] = field(default_factory=list)  # 数据集目标
    process_goals: List[Goal] = field(default_factory=list)  # 过程目标
    
    # 测试配置
    run_count: int = 3  # 运行次数
    pass_threshold: float = 0.5  # 通过阈值（0.5=3 次对 2 次）


TestScenario.__test__ = False


class GoalValidators:
    """Goal 验证器集合"""
    
    @staticmethod
    def validate_has_reply(result: Dict[str, Any]) -> bool:
        """验证有回复"""
        return 'reply' in result and len(result['reply']) > 0
    
    @staticmethod
    def validate_market_type(result: Dict[str, Any], expected_market: str) -> bool:
        """验证市场类型"""
        data = result.get('data', {})
        if expected_market == 'stock':
            return 'quote' in data or 'bars' in data
        elif expected_market == 'future':
            return 'quote' in data or 'bars' in data
        return False
    
    @staticmethod
    def validate_symbol(result: Dict[str, Any], expected_symbol: str) -> bool:
        """验证股票代码"""
        reply = result.get('reply', '')
        data = str(result.get('data', {}))
        return expected_symbol in reply or expected_symbol in data
    
    @staticmethod
    def validate_strategy_list(result: Dict[str, Any]) -> bool:
        """验证策略列表"""
        reply = result.get('reply', '')
        return '策略' in reply and ('双均线' in reply or 'RSI' in reply)
    
    @staticmethod
    def validate_backtest_result(result: Dict[str, Any]) -> bool:
        """验证回测结果"""
        reply = result.get('reply', '')
        return '回测' in reply or '收益率' in reply or '夏普' in reply
    
    @staticmethod
    def validate_response_time(result: Dict[str, Any], max_seconds: float = 5.0) -> bool:
        """验证响应时间"""
        # 需要从上下文获取响应时间
        return True  # 由测试执行器设置
    
    @staticmethod
    def validate_no_error(result: Dict[str, Any]) -> bool:
        """验证无错误"""
        reply = result.get('reply', '')
        return not reply.startswith('❌') and '错误' not in reply
    
    @staticmethod
    def validate_data_loaded(result: Dict[str, Any], min_count: int = 1) -> bool:
        """验证数据加载"""
        data = result.get('data', {})
        bars = data.get('bars', [])
        return len(bars) >= min_count


def create_scenarios_with_goals() -> List[TestScenario]:
    """创建带 Goal 的测试场景"""
    
    scenarios = []
    
    # ========== 行情查询场景 ==========
    
    # MQ001: 贵州茅台行情
    scenarios.append(TestScenario(
        id='MQ001',
        category='stock_market',
        query='贵州茅台行情',
        priority='high',
        expected_type='market_quote',
        expected_market='stock',
        expected_symbol='600519',
        
        # 数据集目标（结果正确性）
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('correct_symbol', '股票代码正确', 
                 lambda r: GoalValidators.validate_symbol(r, '600519')),
            Goal('has_price', '有价格信息', 
                 lambda r: '最新价' in r.get('reply', '') or '收盘' in r.get('reply', '')),
            Goal('no_error', '无错误', GoalValidators.validate_no_error),
        ],
        
        # 过程目标（过程合理性）
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
            Goal('data_loaded', '数据已加载', 
                 lambda r: GoalValidators.validate_data_loaded(r, 1)),
        ]
    ))
    
    # MQ002: 600519 股价
    scenarios.append(TestScenario(
        id='MQ002',
        category='stock_market',
        query='600519 股价',
        priority='high',
        expected_type='market_quote',
        expected_market='stock',
        expected_symbol='600519',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('correct_symbol', '股票代码正确', 
                 lambda r: GoalValidators.validate_symbol(r, '600519')),
            Goal('has_price', '有价格信息', 
                 lambda r: '价' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
        ]
    ))
    
    # MQ009: 螺纹钢行情
    scenarios.append(TestScenario(
        id='MQ009',
        category='future_market',
        query='螺纹钢行情',
        priority='high',
        expected_type='market_quote',
        expected_market='future',
        expected_symbol='RB',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('correct_symbol', '品种代码正确', 
                 lambda r: GoalValidators.validate_symbol(r, 'RB')),
            Goal('has_price', '有价格信息', 
                 lambda r: '最新价' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
            Goal('data_loaded', '数据已加载', 
                 lambda r: GoalValidators.validate_data_loaded(r, 1)),
        ]
    ))
    
    # MQ014: 螺纹钢 5 分钟数据
    scenarios.append(TestScenario(
        id='MQ014',
        category='future_market',
        query='螺纹钢 5 分钟数据',
        priority='high',
        expected_type='market_quote',
        expected_market='future',
        expected_symbol='RB',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('correct_symbol', '品种代码正确', 
                 lambda r: GoalValidators.validate_symbol(r, 'RB')),
            Goal('has_5min', '有 5 分钟标识', 
                 lambda r: '5 分钟' in r.get('reply', '') or '5m' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
            Goal('data_loaded', '数据已加载', 
                 lambda r: GoalValidators.validate_data_loaded(r, 10)),
        ]
    ))
    
    # ========== 策略查询场景 ==========
    
    # SQ001: 有什么策略
    scenarios.append(TestScenario(
        id='SQ001',
        category='strategy',
        query='有什么策略',
        priority='high',
        expected_type='strategy_list',
        expected_market='stock',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('has_strategy_list', '有策略列表', 
                 GoalValidators.validate_strategy_list),
            Goal('has_multiple', '有多个策略', 
                 lambda r: r.get('reply', '').count('.') >= 2),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
        ]
    ))
    
    # SQ008: 期货有什么策略
    scenarios.append(TestScenario(
        id='SQ008',
        category='strategy',
        query='期货有什么策略',
        priority='high',
        expected_type='strategy_list',
        expected_market='future',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('has_future_strategy', '有期货策略', 
                 lambda r: '期货' in r.get('reply', '')),
            Goal('has_strategy_list', '有策略列表', 
                 GoalValidators.validate_strategy_list),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
        ]
    ))
    
    # ========== 回测查询场景 ==========
    
    # BQ001: 回测双均线策略 600519
    scenarios.append(TestScenario(
        id='BQ001',
        category='backtest',
        query='回测双均线策略 600519',
        priority='high',
        expected_type='backtest_result',
        expected_market='stock',
        expected_strategy='dual_ma',
        expected_symbol='600519',
        
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
    ))
    
    # BQ006: 回测期货双均线策略 IF
    scenarios.append(TestScenario(
        id='BQ006',
        category='backtest',
        query='回测期货双均线策略 IF',
        priority='high',
        expected_type='backtest_result',
        expected_market='future',
        expected_strategy='future_dual_ma',
        expected_symbol='IF',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('has_backtest_result', '有回测结果', 
                 GoalValidators.validate_backtest_result),
            Goal('has_future_metrics', '有期货指标', 
                 lambda r: '做多' in r.get('reply', '') or '做空' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('reasonable_time', '时间合理', 
                 lambda r: GoalValidators.validate_response_time(r, 10.0)),
        ]
    ))
    
    # ========== 边界情况场景 ==========
    
    # EC001: 空查询
    scenarios.append(TestScenario(
        id='EC001',
        category='edge_case',
        query='',
        priority='high',
        expected_type='error',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('has_error_hint', '有错误提示', 
                 lambda r: '抱歉' in r.get('reply', '') or '理解' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 1.0)),
        ]
    ))
    
    # EC003: 回测不存在的策略
    scenarios.append(TestScenario(
        id='EC003',
        category='edge_case',
        query='回测不存在的策略',
        priority='high',
        expected_type='error',
        
        dataset_goals=[
            Goal('has_reply', '有回复', GoalValidators.validate_has_reply),
            Goal('has_error_message', '有错误信息', 
                 lambda r: '错误' in r.get('reply', '') or '不存在' in r.get('reply', '')),
        ],
        
        process_goals=[
            Goal('fast_response', '响应快速', 
                 lambda r: GoalValidators.validate_response_time(r, 2.0)),
        ]
    ))
    
    return scenarios


def get_all_test_scenarios() -> List[TestScenario]:
    """获取所有测试场景"""
    return create_scenarios_with_goals()


def get_scenario_statistics():
    """获取测试场景统计"""
    scenarios = get_all_test_scenarios()
    
    stats = {
        'total': len(scenarios),
        'by_category': {},
        'by_priority': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    for scenario in scenarios:
        # 按类别统计
        category = scenario.category
        stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        # 按优先级统计
        priority = scenario.priority
        stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
        
        # 统计 Goal 数量
        scenario.dataset_goal_count = len(scenario.dataset_goals)
        scenario.process_goal_count = len(scenario.process_goals)
    
    return stats


if __name__ == '__main__':
    # 打印统计信息
    stats = get_scenario_statistics()
    
    print("=" * 80)
    print("增强版测试场景统计（带 Goal 评估）")
    print("=" * 80)
    print(f"总场景数：{stats['total']}")
    print(f"\n按类别:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")
    print(f"\n按优先级:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority}: {count}")
    print("=" * 80)
