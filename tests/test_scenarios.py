"""
统一查询接口 - 完整测试场景集

包含 100+ 个真实使用场景的测试用例
"""
from typing import List, Dict, Any


class TestScenarios:
    """测试场景集合"""
    
    @staticmethod
    def get_all_scenarios() -> List[Dict[str, Any]]:
        """获取所有测试场景"""
        return (
            TestScenarios.market_queries() +
            TestScenarios.strategy_queries() +
            TestScenarios.backtest_queries() +
            TestScenarios.edge_cases() +
            TestScenarios.multi_turn_conversations()
        )
    
    @classmethod
    def market_queries(cls) -> List[Dict[str, Any]]:
        """行情查询场景（40 个）"""
        return [
            # 股票行情 - 标准查询
            {
                'id': 'MQ001',
                'category': 'stock_market',
                'query': '贵州茅台行情',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600519',
                'priority': 'high'
            },
            {
                'id': 'MQ002',
                'category': 'stock_market',
                'query': '600519 股价',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600519',
                'priority': 'high'
            },
            {
                'id': 'MQ003',
                'category': 'stock_market',
                'query': '平安银行走势',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '000001',
                'priority': 'high'
            },
            {
                'id': 'MQ004',
                'category': 'stock_market',
                'query': '宁德时代 K 线数据',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '300750',
                'priority': 'high'
            },
            {
                'id': 'MQ005',
                'category': 'stock_market',
                'query': '五粮液价格',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '000858',
                'priority': 'medium'
            },
            
            # 股票行情 - 带时间范围
            {
                'id': 'MQ006',
                'category': 'stock_market',
                'query': '茅台最近 30 天行情',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600519',
                'priority': 'medium'
            },
            {
                'id': 'MQ007',
                'category': 'stock_market',
                'query': '600519 本月走势',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600519',
                'priority': 'medium'
            },
            {
                'id': 'MQ008',
                'category': 'stock_market',
                'query': '贵州茅台 2026 年数据',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600519',
                'priority': 'low'
            },
            
            # 期货行情 - 标准查询
            {
                'id': 'MQ009',
                'category': 'future_market',
                'query': '螺纹钢行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'RB',
                'priority': 'high'
            },
            {
                'id': 'MQ010',
                'category': 'future_market',
                'query': '沪金价格',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'AU',
                'priority': 'high'
            },
            {
                'id': 'MQ011',
                'category': 'future_market',
                'query': '沪银走势',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'AG',
                'priority': 'high'
            },
            {
                'id': 'MQ012',
                'category': 'future_market',
                'query': '原油行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'SC',
                'priority': 'high'
            },
            {
                'id': 'MQ013',
                'category': 'future_market',
                'query': '沪深 300 股指期货',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'IF',
                'priority': 'high'
            },
            
            # 期货行情 - 带周期
            {
                'id': 'MQ014',
                'category': 'future_market',
                'query': '螺纹钢 5 分钟数据',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'RB',
                'expected_frequency': '5m',
                'priority': 'high'
            },
            {
                'id': 'MQ015',
                'category': 'future_market',
                'query': '沪金 5 分钟 K 线',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'AU',
                'expected_frequency': '5m',
                'priority': 'high'
            },
            {
                'id': 'MQ016',
                'category': 'future_market',
                'query': '原油日线数据',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'SC',
                'expected_frequency': '1d',
                'priority': 'medium'
            },
            {
                'id': 'MQ017',
                'category': 'future_market',
                'query': '中证 500 股指期货走势',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'IC',
                'priority': 'medium'
            },
            
            # 其他品种
            {
                'id': 'MQ018',
                'category': 'future_market',
                'query': '沪铜行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'CU',
                'priority': 'medium'
            },
            {
                'id': 'MQ019',
                'category': 'future_market',
                'query': '豆粕价格',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'M',
                'priority': 'medium'
            },
            {
                'id': 'MQ020',
                'category': 'future_market',
                'query': '豆油走势',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'Y',
                'priority': 'medium'
            },
            {
                'id': 'MQ021',
                'category': 'future_market',
                'query': '棕榈油行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'P',
                'priority': 'medium'
            },
            {
                'id': 'MQ022',
                'category': 'future_market',
                'query': '白糖价格',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'SR',
                'priority': 'medium'
            },
            {
                'id': 'MQ023',
                'category': 'future_market',
                'query': '甲醇行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'MA',
                'priority': 'low'
            },
            
            # 股票行情 - 更多股票
            {
                'id': 'MQ024',
                'category': 'stock_market',
                'query': '招商银行行情',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600036',
                'priority': 'medium'
            },
            {
                'id': 'MQ025',
                'category': 'stock_market',
                'query': '中国平安股价',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '601318',
                'priority': 'medium'
            },
            {
                'id': 'MQ026',
                'category': 'stock_market',
                'query': '东方财富走势',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '300059',
                'priority': 'medium'
            },
            {
                'id': 'MQ027',
                'category': 'stock_market',
                'query': '比亚迪价格',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '002594',
                'priority': 'medium'
            },
            {
                'id': 'MQ028',
                'category': 'stock_market',
                'query': '恒瑞医药 K 线',
                'expected_type': 'market_quote',
                'expected_market': 'stock',
                'expected_symbol': '600276',
                'priority': 'low'
            },
            
            # 期货行情 - 更多品种
            {
                'id': 'MQ029',
                'category': 'future_market',
                'query': '沪铝行情',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'AL',
                'priority': 'low'
            },
            {
                'id': 'MQ030',
                'category': 'future_market',
                'query': '热卷价格',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'HC',
                'priority': 'low'
            },
            {
                'id': 'MQ031',
                'category': 'future_market',
                'query': '上证 50 股指期货',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'IH',
                'priority': 'medium'
            },
            {
                'id': 'MQ032',
                'category': 'future_market',
                'query': '中证 1000 股指',
                'expected_type': 'market_quote',
                'expected_market': 'future',
                'expected_symbol': 'IM',
                'priority': 'low'
            },
        ]
    
    @classmethod
    def strategy_queries(cls) -> List[Dict[str, Any]]:
        """策略查询场景（20 个）"""
        return [
            # 股票策略查询
            {
                'id': 'SQ001',
                'category': 'strategy',
                'query': '有什么策略',
                'expected_type': 'strategy_list',
                'expected_market': 'stock',
                'priority': 'high'
            },
            {
                'id': 'SQ002',
                'category': 'strategy',
                'query': '股票策略',
                'expected_type': 'strategy_list',
                'expected_market': 'stock',
                'priority': 'high'
            },
            {
                'id': 'SQ003',
                'category': 'strategy',
                'query': '有哪些交易方法',
                'expected_type': 'strategy_list',
                'expected_market': 'stock',
                'priority': 'medium'
            },
            {
                'id': 'SQ004',
                'category': 'strategy',
                'query': '双均线策略详情',
                'expected_type': 'strategy_detail',
                'expected_strategy': 'dual_ma',
                'priority': 'high'
            },
            {
                'id': 'SQ005',
                'category': 'strategy',
                'query': 'RSI 策略怎么用',
                'expected_type': 'strategy_detail',
                'expected_strategy': 'rsi',
                'priority': 'high'
            },
            {
                'id': 'SQ006',
                'category': 'strategy',
                'query': '趋势策略有哪些',
                'expected_type': 'strategy_list',
                'expected_market': 'stock',
                'priority': 'medium'
            },
            {
                'id': 'SQ007',
                'category': 'strategy',
                'query': '震荡策略',
                'expected_type': 'strategy_list',
                'expected_market': 'stock',
                'priority': 'medium'
            },
            
            # 期货策略查询
            {
                'id': 'SQ008',
                'category': 'strategy',
                'query': '期货有什么策略',
                'expected_type': 'strategy_list',
                'expected_market': 'future',
                'priority': 'high'
            },
            {
                'id': 'SQ009',
                'category': 'strategy',
                'query': '期货策略列表',
                'expected_type': 'strategy_list',
                'expected_market': 'future',
                'priority': 'high'
            },
            {
                'id': 'SQ010',
                'category': 'strategy',
                'query': '期货双均线策略',
                'expected_type': 'strategy_detail',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'priority': 'high'
            },
            {
                'id': 'SQ011',
                'category': 'strategy',
                'query': '期货 RSI 策略详情',
                'expected_type': 'strategy_detail',
                'expected_market': 'future',
                'expected_strategy': 'future_rsi',
                'priority': 'high'
            },
            {
                'id': 'SQ012',
                'category': 'strategy',
                'query': '期货趋势策略',
                'expected_type': 'strategy_list',
                'expected_market': 'future',
                'priority': 'medium'
            },
            {
                'id': 'SQ013',
                'category': 'strategy',
                'query': '期货套利策略',
                'expected_type': 'strategy_list',
                'expected_market': 'future',
                'priority': 'medium'
            },
            
            # 策略参数查询
            {
                'id': 'SQ014',
                'category': 'strategy',
                'query': '双均线策略参数',
                'expected_type': 'strategy_params',
                'expected_strategy': 'dual_ma',
                'priority': 'medium'
            },
            {
                'id': 'SQ015',
                'category': 'strategy',
                'query': 'RSI 策略参数设置',
                'expected_type': 'strategy_params',
                'expected_strategy': 'rsi',
                'priority': 'medium'
            },
            {
                'id': 'SQ016',
                'category': 'strategy',
                'query': '期货策略参数',
                'expected_type': 'strategy_params',
                'expected_market': 'future',
                'priority': 'low'
            },
            
            # 策略对比
            {
                'id': 'SQ017',
                'category': 'strategy',
                'query': '双均线和 RSI 哪个好',
                'expected_type': 'strategy_compare',
                'priority': 'low'
            },
            {
                'id': 'SQ018',
                'category': 'strategy',
                'query': '趋势策略和震荡策略区别',
                'expected_type': 'strategy_compare',
                'priority': 'low'
            },
            {
                'id': 'SQ019',
                'category': 'strategy',
                'query': '股票和期货策略有什么不同',
                'expected_type': 'strategy_compare',
                'priority': 'low'
            },
            {
                'id': 'SQ020',
                'category': 'strategy',
                'query': '新手适合什么策略',
                'expected_type': 'strategy_recommend',
                'priority': 'medium'
            },
        ]
    
    @classmethod
    def backtest_queries(cls) -> List[Dict[str, Any]]:
        """回测查询场景（25 个）"""
        return [
            # 股票回测 - 标准查询
            {
                'id': 'BQ001',
                'category': 'backtest',
                'query': '回测双均线策略 600519',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '600519',
                'priority': 'high'
            },
            {
                'id': 'BQ002',
                'category': 'backtest',
                'query': '测试 RSI 策略 贵州茅台',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'rsi',
                'expected_symbol': '600519',
                'priority': 'high'
            },
            {
                'id': 'BQ003',
                'category': 'backtest',
                'query': '双均线策略回测 000001',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '000001',
                'priority': 'high'
            },
            {
                'id': 'BQ004',
                'category': 'backtest',
                'query': '回测宁德时代双均线',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '300750',
                'priority': 'high'
            },
            {
                'id': 'BQ005',
                'category': 'backtest',
                'query': '测试五粮液 RSI 策略',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'rsi',
                'expected_symbol': '000858',
                'priority': 'medium'
            },
            
            # 期货回测 - 标准查询
            {
                'id': 'BQ006',
                'category': 'backtest',
                'query': '回测期货双均线策略 IF',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'IF',
                'priority': 'high'
            },
            {
                'id': 'BQ007',
                'category': 'backtest',
                'query': '测试期货 RSI 策略 螺纹钢',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_rsi',
                'expected_symbol': 'RB',
                'priority': 'high'
            },
            {
                'id': 'BQ008',
                'category': 'backtest',
                'query': '回测沪金趋势策略',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'AU',
                'priority': 'high'
            },
            {
                'id': 'BQ009',
                'category': 'backtest',
                'query': '原油 RSI 策略回测',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_rsi',
                'expected_symbol': 'SC',
                'priority': 'high'
            },
            {
                'id': 'BQ010',
                'category': 'backtest',
                'query': '回测中证 500 股指期货策略',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'IC',
                'priority': 'medium'
            },
            
            # 带时间范围的回测
            {
                'id': 'BQ011',
                'category': 'backtest',
                'query': '回测双均线 600519 最近 1 年',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '600519',
                'expected_period': '1y',
                'priority': 'medium'
            },
            {
                'id': 'BQ012',
                'category': 'backtest',
                'query': '回测 RSI 策略 茅台 2025 年',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'rsi',
                'expected_symbol': '600519',
                'expected_period': '2025',
                'priority': 'medium'
            },
            {
                'id': 'BQ013',
                'category': 'backtest',
                'query': '回测期货 IF 最近 3 年',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'IF',
                'expected_period': '3y',
                'priority': 'medium'
            },
            {
                'id': 'BQ014',
                'category': 'backtest',
                'query': '螺纹钢回测 2024 年',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'RB',
                'expected_period': '2024',
                'priority': 'low'
            },
            
            # 带参数的回测
            {
                'id': 'BQ015',
                'category': 'backtest',
                'query': '回测双均线 600519 参数 short_period=10 long_period=30',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '600519',
                'expected_params': {'short_period': 10, 'long_period': 30},
                'priority': 'medium'
            },
            {
                'id': 'BQ016',
                'category': 'backtest',
                'query': '回测 RSI 策略 参数 rsi_period=21',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'rsi',
                'expected_params': {'rsi_period': 21},
                'priority': 'low'
            },
            
            # 对比回测
            {
                'id': 'BQ017',
                'category': 'backtest',
                'query': '对比双均线和 RSI 策略',
                'expected_type': 'backtest_compare',
                'expected_market': 'stock',
                'priority': 'low'
            },
            {
                'id': 'BQ018',
                'category': 'backtest',
                'query': '股票和期货策略回测对比',
                'expected_type': 'backtest_compare',
                'priority': 'low'
            },
            
            # 更多股票回测
            {
                'id': 'BQ019',
                'category': 'backtest',
                'query': '回测招商银行双均线',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '600036',
                'priority': 'medium'
            },
            {
                'id': 'BQ020',
                'category': 'backtest',
                'query': '中国平安 RSI 策略回测',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'rsi',
                'expected_symbol': '601318',
                'priority': 'medium'
            },
            {
                'id': 'BQ021',
                'category': 'backtest',
                'query': '回测东方财富趋势策略',
                'expected_type': 'backtest_result',
                'expected_market': 'stock',
                'expected_strategy': 'dual_ma',
                'expected_symbol': '300059',
                'priority': 'low'
            },
            
            # 更多期货回测
            {
                'id': 'BQ022',
                'category': 'backtest',
                'query': '回测沪铜趋势策略',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'CU',
                'priority': 'medium'
            },
            {
                'id': 'BQ023',
                'category': 'backtest',
                'query': '豆粕 RSI 回测',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_rsi',
                'expected_symbol': 'M',
                'priority': 'low'
            },
            {
                'id': 'BQ024',
                'category': 'backtest',
                'query': '回测豆油双均线',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'Y',
                'priority': 'low'
            },
            {
                'id': 'BQ025',
                'category': 'backtest',
                'query': '棕榈油策略回测',
                'expected_type': 'backtest_result',
                'expected_market': 'future',
                'expected_strategy': 'future_dual_ma',
                'expected_symbol': 'P',
                'priority': 'low'
            },
        ]
    
    @classmethod
    def edge_cases(cls) -> List[Dict[str, Any]]:
        """边界和异常场景（15 个）"""
        return [
            # 无效输入
            {
                'id': 'EC001',
                'category': 'edge_case',
                'query': '',
                'expected_type': 'error',
                'expected_error': 'empty_query',
                'priority': 'high'
            },
            {
                'id': 'EC002',
                'category': 'edge_case',
                'query': '???',
                'expected_type': 'error',
                'expected_error': 'invalid_query',
                'priority': 'high'
            },
            {
                'id': 'EC003',
                'category': 'edge_case',
                'query': '回测不存在的策略',
                'expected_type': 'error',
                'expected_error': 'strategy_not_found',
                'priority': 'high'
            },
            {
                'id': 'EC004',
                'category': 'edge_case',
                'query': '回测 999999 股票',
                'expected_type': 'error',
                'expected_error': 'symbol_not_found',
                'priority': 'high'
            },
            
            # 模糊查询
            {
                'id': 'EC005',
                'category': 'edge_case',
                'query': '行情',
                'expected_type': 'clarification',
                'priority': 'medium'
            },
            {
                'id': 'EC006',
                'category': 'edge_case',
                'query': '策略',
                'expected_type': 'clarification',
                'priority': 'medium'
            },
            {
                'id': 'EC007',
                'category': 'edge_case',
                'query': '回测',
                'expected_type': 'clarification',
                'priority': 'medium'
            },
            
            # 混合查询
            {
                'id': 'EC008',
                'category': 'edge_case',
                'query': '茅台行情和策略',
                'expected_type': 'mixed',
                'priority': 'low'
            },
            {
                'id': 'EC009',
                'category': 'edge_case',
                'query': '先查行情再回测',
                'expected_type': 'multi_step',
                'priority': 'low'
            },
            
            # 特殊字符
            {
                'id': 'EC010',
                'category': 'edge_case',
                'query': '回测 600519!!!',
                'expected_type': 'backtest_result',
                'expected_symbol': '600519',
                'priority': 'medium'
            },
            {
                'id': 'EC011',
                'category': 'edge_case',
                'query': '贵州茅台@#$行情',
                'expected_type': 'market_quote',
                'expected_symbol': '600519',
                'priority': 'medium'
            },
            
            # 超长查询
            {
                'id': 'EC012',
                'category': 'edge_case',
                'query': '我想查询贵州茅台股票在 2026 年 3 月份的最新行情数据，包括开盘价、收盘价、最高价、最低价、成交量等详细信息',
                'expected_type': 'market_quote',
                'expected_symbol': '600519',
                'priority': 'low'
            },
            
            # 大小写测试
            {
                'id': 'EC013',
                'category': 'edge_case',
                'query': '回测 DUAL_MA 策略 600519',
                'expected_type': 'backtest_result',
                'expected_strategy': 'dual_ma',
                'priority': 'medium'
            },
            {
                'id': 'EC014',
                'category': 'edge_case',
                'query': '贵州茅台 HANGQING',
                'expected_type': 'market_quote',
                'expected_symbol': '600519',
                'priority': 'low'
            },
            
            # 性能测试
            {
                'id': 'EC015',
                'category': 'edge_case',
                'query': '回测所有股票',
                'expected_type': 'error',
                'expected_error': 'too_many_symbols',
                'priority': 'medium'
            },
        ]
    
    @classmethod
    def multi_turn_conversations(cls) -> List[Dict[str, Any]]:
        """多轮对话场景（10 个）"""
        return [
            {
                'id': 'MC001',
                'category': 'multi_turn',
                'conversation': [
                    '贵州茅台行情',
                    '回测这个股票的双均线策略',
                    '看看 RSI 策略怎么样',
                    '对比两个策略'
                ],
                'expected_context_aware': True,
                'priority': 'high'
            },
            {
                'id': 'MC002',
                'category': 'multi_turn',
                'conversation': [
                    '有什么策略',
                    '双均线策略详情',
                    '回测这个策略 600519',
                    '参数改成 short_period=10'
                ],
                'expected_context_aware': True,
                'priority': 'high'
            },
            {
                'id': 'MC003',
                'category': 'multi_turn',
                'conversation': [
                    '螺纹钢行情',
                    '5 分钟数据',
                    '回测 5 分钟策略',
                    '看看日线回测'
                ],
                'expected_context_aware': True,
                'priority': 'medium'
            },
            {
                'id': 'MC004',
                'category': 'multi_turn',
                'conversation': [
                    '期货有什么策略',
                    '回测 IF',
                    '再回测 RB',
                    '对比结果'
                ],
                'expected_context_aware': True,
                'priority': 'medium'
            },
            {
                'id': 'MC005',
                'category': 'multi_turn',
                'conversation': [
                    '600519 行情',
                    '000001 呢',
                    '300750 呢',
                    '对比这三只股票'
                ],
                'expected_context_aware': True,
                'priority': 'medium'
            },
            {
                'id': 'MC006',
                'category': 'multi_turn',
                'conversation': [
                    '回测双均线',
                    '换个股票 000858',
                    '再换个策略 RSI',
                    '用默认股票'
                ],
                'expected_context_aware': True,
                'priority': 'low'
            },
            {
                'id': 'MC007',
                'category': 'multi_turn',
                'conversation': [
                    '沪金行情',
                    '沪银呢',
                    '原油呢',
                    '这三个哪个更好'
                ],
                'expected_context_aware': True,
                'priority': 'low'
            },
            {
                'id': 'MC008',
                'category': 'multi_turn',
                'conversation': [
                    '有什么期货策略',
                    '双均线参数多少',
                    '回测看看',
                    '参数改成 20 和 60'
                ],
                'expected_context_aware': True,
                'priority': 'medium'
            },
            {
                'id': 'MC009',
                'category': 'multi_turn',
                'conversation': [
                    '股票行情',
                    '期货行情',
                    '股票策略',
                    '期货策略'
                ],
                'expected_context_aware': True,
                'priority': 'low'
            },
            {
                'id': 'MC010',
                'category': 'multi_turn',
                'conversation': [
                    '回测 600519',
                    '回测结果怎么样',
                    '最大回撤多少',
                    '夏普比率呢'
                ],
                'expected_context_aware': True,
                'priority': 'medium'
            },
        ]


# 测试场景统计
def get_scenario_statistics():
    """获取测试场景统计"""
    scenarios = TestScenarios.get_all_scenarios()
    
    stats = {
        'total': len(scenarios),
        'by_category': {},
        'by_priority': {'high': 0, 'medium': 0, 'low': 0}
    }
    
    for scenario in scenarios:
        # 按类别统计
        category = scenario['category']
        stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
        
        # 按优先级统计
        priority = scenario.get('priority', 'medium')
        stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
    
    return stats


if __name__ == '__main__':
    # 打印统计信息
    stats = get_scenario_statistics()
    
    print("=" * 80)
    print("测试场景统计")
    print("=" * 80)
    print(f"总场景数：{stats['total']}")
    print(f"\n按类别:")
    for category, count in stats['by_category'].items():
        print(f"  {category}: {count}")
    print(f"\n按优先级:")
    for priority, count in stats['by_priority'].items():
        print(f"  {priority}: {count}")
    print("=" * 80)
