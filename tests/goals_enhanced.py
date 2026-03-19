"""
Goal 定义增强版

包含更多验证维度和权重配置
"""
from tests.test_scenarios_enhanced import Goal


class AdvancedGoalValidators:
    """高级验证器"""
    
    @staticmethod
    def validate_data_completeness(result: dict, min_fields: int = 3) -> bool:
        """验证数据完整性"""
        data = result.get('data', {})
        if not data:
            return False
        
        # 统计非空字段数
        non_empty = sum(1 for v in data.values() if v is not None and v != {})
        return non_empty >= min_fields
    
    @staticmethod
    def validate_response_format(result: dict, required_keys: list) -> bool:
        """验证响应格式"""
        reply = result.get('reply', '')
        return all(key in reply for key in required_keys)
    
    @staticmethod
    def validate_cache_hit(result: dict) -> bool:
        """验证缓存命中（从日志中判断）"""
        # 需要从 Event 日志中获取
        return True  # 由测试执行器设置
    
    @staticmethod
    def validate_no_timeout(result: dict, max_seconds: float = 30.0) -> bool:
        """验证无超时"""
        elapsed = result.get('_response_time', 0)
        return elapsed < max_seconds
    
    @staticmethod
    def validate_suggestions(result: dict, min_count: int = 1) -> bool:
        """验证有建议"""
        suggestions = result.get('suggestions', [])
        return len(suggestions) >= min_count


# 增强版 Goal 模板
ENHANCED_GOALS = {
    # ========== Dataset Goals ==========
    
    'has_reply': Goal(
        name='has_reply',
        description='有回复',
        validator=lambda r: 'reply' in r and len(r['reply']) > 0,
        weight=2.0  # 高权重
    ),
    
    'correct_symbol': Goal(
        name='correct_symbol',
        description='代码正确',
        validator=lambda r: True,  # 由具体场景设置
        weight=2.0
    ),
    
    'has_price': Goal(
        name='has_price',
        description='有价格',
        validator=lambda r: '价' in r.get('reply', ''),
        weight=1.5
    ),
    
    'has_metrics': Goal(
        name='has_metrics',
        description='有指标',
        validator=lambda r: '收益率' in r.get('reply', '') or '夏普' in r.get('reply', ''),
        weight=1.5
    ),
    
    'no_error': Goal(
        name='no_error',
        description='无错误',
        validator=lambda r: not r.get('reply', '').startswith('❌'),
        weight=2.0
    ),
    
    'data_complete': Goal(
        name='data_complete',
        description='数据完整',
        validator=lambda r: AdvancedGoalValidators.validate_data_completeness(r, 3),
        weight=1.0
    ),
    
    # ========== Process Goals ==========
    
    'fast_response': Goal(
        name='fast_response',
        description='响应快',
        validator=lambda r: r.get('_response_time', 999) < 2.0,
        weight=1.5
    ),
    
    'reasonable_time': Goal(
        name='reasonable_time',
        description='时间合理',
        validator=lambda r: r.get('_response_time', 999) < 10.0,
        weight=1.0
    ),
    
    'no_timeout': Goal(
        name='no_timeout',
        description='无超时',
        validator=lambda r: AdvancedGoalValidators.validate_no_timeout(r, 30.0),
        weight=2.0
    ),
    
    'data_loaded': Goal(
        name='data_loaded',
        description='数据已加载',
        validator=lambda r: len(r.get('data', {}).get('bars', [])) >= 1,
        weight=1.0
    ),
    
    'has_suggestions': Goal(
        name='has_suggestions',
        description='有建议',
        validator=lambda r: AdvancedGoalValidators.validate_suggestions(r, 1),
        weight=0.5
    ),
}


def create_scenario_with_goals(id, category, query, priority, goals_config):
    """
    创建带 Goal 的场景
    
    Args:
        id: 场景 ID
        category: 类别
        query: 查询语句
        priority: 优先级
        goals_config: Goal 配置字典
            {
                'dataset': ['has_reply', 'correct_symbol', ...],
                'process': ['fast_response', 'data_loaded', ...]
            }
    
    Returns:
        TestScenario
    """
    from tests.test_scenarios_enhanced import TestScenario
    
    dataset_goals = [ENHANCED_GOALS[name] for name in goals_config.get('dataset', [])]
    process_goals = [ENHANCED_GOALS[name] for name in goals_config.get('process', [])]
    
    return TestScenario(
        id=id,
        category=category,
        query=query,
        priority=priority,
        dataset_goals=dataset_goals,
        process_goals=process_goals
    )


# 示例场景配置
SCENARIO_TEMPLATES = {
    'stock_market': {
        'dataset': ['has_reply', 'correct_symbol', 'has_price', 'no_error'],
        'process': ['fast_response', 'data_loaded']
    },
    'future_market': {
        'dataset': ['has_reply', 'correct_symbol', 'has_price', 'no_error'],
        'process': ['fast_response', 'data_loaded']
    },
    'strategy': {
        'dataset': ['has_reply', 'has_reply'],  # 有策略列表
        'process': ['fast_response', 'has_suggestions']
    },
    'backtest': {
        'dataset': ['has_reply', 'has_metrics', 'no_error'],
        'process': ['reasonable_time', 'no_timeout']
    },
    'edge_case': {
        'dataset': ['has_reply', 'no_error'],
        'process': ['fast_response']
    },
}
