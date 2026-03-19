#!/usr/bin/env python3
"""
统一查询接口 - 自动化测试执行器

执行 100+ 个测试场景并生成报告
"""
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_scenarios import TestScenarios, get_scenario_statistics
from modules.services.unified_query_interface import UnifiedQueryInterface


class AutomatedTestRunner:
    """自动化测试执行器"""
    
    def __init__(self):
        """初始化测试执行器"""
        self.interface = UnifiedQueryInterface()
        self.results = []
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self, priority_filter: str = None) -> Dict[str, Any]:
        """
        运行所有测试
        
        Args:
            priority_filter: 优先级过滤（high/medium/low）
        
        Returns:
            测试结果汇总
        """
        self.start_time = datetime.now()
        self.results = []
        
        # 获取测试场景
        scenarios = TestScenarios.get_all_scenarios()
        
        # 按优先级过滤
        if priority_filter:
            scenarios = [s for s in scenarios if s.get('priority') == priority_filter]
        
        total = len(scenarios)
        print("=" * 80)
        print(f"自动化测试执行")
        print("=" * 80)
        print(f"开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试场景：{total} 个")
        if priority_filter:
            print(f"优先级过滤：{priority_filter}")
        print("=" * 80)
        print()
        
        # 执行测试
        passed = 0
        failed = 0
        errors = 0
        
        for i, scenario in enumerate(scenarios, 1):
            # 显示进度
            print(f"[{i:3d}/{total}] {scenario['id']}: {scenario['query'][:50]:50s} ", end='')
            
            try:
                # 执行查询
                start = time.time()
                result = self.interface.query(scenario['query'])
                elapsed = time.time() - start
                
                # 验证结果
                test_passed = self._validate_result(scenario, result)
                
                if test_passed:
                    print(f"✓ 通过 ({elapsed:.2f}s)")
                    passed += 1
                else:
                    print(f"✗ 失败 ({elapsed:.2f}s)")
                    failed += 1
                
                # 记录结果
                self.results.append({
                    'scenario': scenario,
                    'result': result,
                    'passed': test_passed,
                    'elapsed': elapsed
                })
                
            except Exception as e:
                print(f"⚠ 错误 ({str(e)[:30]})")
                errors += 1
                
                self.results.append({
                    'scenario': scenario,
                    'error': str(e),
                    'passed': False,
                    'elapsed': 0
                })
        
        self.end_time = datetime.now()
        
        # 生成报告
        report = self._generate_report(passed, failed, errors, total)
        
        return report
    
    def _validate_result(self, scenario: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """
        验证测试结果
        
        Args:
            scenario: 测试场景
            result: 查询结果
        
        Returns:
            是否通过
        """
        expected_type = scenario.get('expected_type')
        
        # 错误类型测试
        if expected_type == 'error':
            return 'error' in result or result.get('reply', '').startswith('抱歉')
        
        # 行情查询验证
        if expected_type == 'market_quote':
            expected_market = scenario.get('expected_market')
            expected_symbol = scenario.get('expected_symbol')
            
            # 检查回复中是否包含关键信息
            reply = result.get('reply', '')
            
            if expected_symbol:
                # 检查股票代码或品种代码是否在回复中
                if expected_symbol not in reply and expected_symbol not in str(result.get('data', {})):
                    return False
            
            return 'reply' in result
        
        # 策略查询验证
        elif expected_type == 'strategy_list':
            return 'reply' in result and '策略' in result.get('reply', '')
        
        # 回测查询验证
        elif expected_type == 'backtest_result':
            return 'reply' in result and ('回测' in result.get('reply', '') or '收益率' in result.get('reply', ''))
        
        # 默认：只要有回复就算通过
        return 'reply' in result
    
    def _generate_report(self, passed: int, failed: int, errors: int, total: int) -> Dict[str, Any]:
        """生成测试报告"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        report = {
            'total': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': passed / total * 100 if total > 0 else 0,
            'duration': duration,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'results': self.results
        }
        
        # 打印报告
        print()
        print("=" * 80)
        print("测试报告")
        print("=" * 80)
        print(f"总测试数：{total}")
        print(f"通过：{passed} ({report['pass_rate']:.1f}%)")
        print(f"失败：{failed}")
        print(f"错误：{errors}")
        print(f"耗时：{duration:.2f}秒")
        print(f"平均速度：{duration/total:.2f}秒/测试")
        print("=" * 80)
        
        # 失败详情
        if failed > 0 or errors > 0:
            print()
            print("失败/错误详情:")
            print("-" * 80)
            for result in self.results:
                if not result['passed']:
                    scenario = result['scenario']
                    print(f"{scenario['id']}: {scenario['query']}")
                    if 'error' in result:
                        print(f"  错误：{result['error']}")
                    print()
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: Dict[str, Any]):
        """保存测试报告"""
        report_path = Path(__file__).parent / 'test_reports'
        report_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_path / f'test_report_{timestamp}.json'
        
        import json
        
        # 转换结果为 JSON 可序列化格式
        report_json = {
            'total': report['total'],
            'passed': report['passed'],
            'failed': report['failed'],
            'errors': report['errors'],
            'pass_rate': report['pass_rate'],
            'duration': report['duration'],
            'start_time': report['start_time'],
            'end_time': report['end_time'],
            'summary': {
                'by_category': {},
                'by_priority': {}
            }
        }
        
        # 按类别统计
        for result in self.results:
            category = result['scenario']['category']
            report_json['summary']['by_category'][category] = \
                report_json['summary']['by_category'].get(category, 0) + 1
            
            priority = result['scenario'].get('priority', 'medium')
            if result['passed']:
                report_json['summary']['by_priority'][f'{priority}_passed'] = \
                    report_json['summary']['by_priority'].get(f'{priority}_passed', 0) + 1
            else:
                report_json['summary']['by_priority'][f'{priority}_failed'] = \
                    report_json['summary']['by_priority'].get(f'{priority}_failed', 0) + 1
        
        # 保存失败详情
        report_json['failed_tests'] = [
            {
                'id': r['scenario']['id'],
                'query': r['scenario']['query'],
                'category': r['scenario']['category'],
                'error': r.get('error', '验证失败')
            }
            for r in self.results if not r['passed']
        ]
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_json, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 测试报告已保存：{report_file}")
        
        # 保存详细结果（可选）
        # detailed_file = report_path / f'test_report_{timestamp}_detailed.json'
        # with open(detailed_file, 'w', encoding='utf-8') as f:
        #     json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='统一查询接口自动化测试')
    parser.add_argument('--priority', type=str, choices=['high', 'medium', 'low'],
                       help='只测试指定优先级的场景')
    parser.add_argument('--count', type=int,
                       help='只测试前 N 个场景')
    
    args = parser.parse_args()
    
    try:
        # 创建测试执行器
        runner = AutomatedTestRunner()
        
        # 运行测试
        report = runner.run_all_tests(priority_filter=args.priority)
        
        # 返回退出码
        if report['passed'] == report['total']:
            print("\n✅ 所有测试通过！")
            sys.exit(0)
        else:
            print(f"\n⚠️ {report['failed']} 个测试失败，{report['errors']} 个错误")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试执行失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
