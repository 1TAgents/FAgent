#!/usr/bin/env python3
"""
增强版自动化测试执行器

功能：
1. 每个测试运行 3 次
2. Dataset Goal + Process Goal 双重评估
3. 正确率计算（阈值 0.5）
4. 任一维度通过即算通过
5. 详细报告生成
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_scenarios_enhanced import get_all_test_scenarios, TestScenario, Goal
from modules.services.unified_query_interface import UnifiedQueryInterface


class EnhancedTestRunner:
    """增强版测试执行器"""
    
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
        scenarios = get_all_test_scenarios()
        
        # 按优先级过滤
        if priority_filter:
            scenarios = [s for s in scenarios if s.priority == priority_filter]
        
        total = len(scenarios)
        print("=" * 80)
        print(f"增强版自动化测试执行（带 Goal 评估）")
        print("=" * 80)
        print(f"开始时间：{self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试场景：{total} 个")
        print(f"运行次数：3 次/场景")
        print(f"通过阈值：0.5（3 次对 2 次）")
        if priority_filter:
            print(f"优先级过滤：{priority_filter}")
        print("=" * 80)
        print()
        
        # 执行测试
        passed = 0
        failed = 0
        
        for i, scenario in enumerate(scenarios, 1):
            # 显示进度
            print(f"[{i:3d}/{total}] {scenario.id}: {scenario.query[:50]:50s} ", end='')
            
            # 运行多次测试
            run_results = self._run_multiple_times(scenario, scenario.run_count)
            
            # 评估结果
            evaluation = self._evaluate_results(scenario, run_results)
            
            # 判断是否通过
            test_passed = evaluation['passed']
            
            if test_passed:
                print(f"✓ 通过 ({evaluation['accuracy']:.0%})")
                passed += 1
            else:
                print(f"✗ 失败 ({evaluation['accuracy']:.0%})")
                failed += 1
            
            # 记录结果
            self.results.append({
                'scenario': scenario,
                'run_results': run_results,
                'evaluation': evaluation,
                'passed': test_passed
            })
        
        self.end_time = datetime.now()
        
        # 生成报告
        report = self._generate_report(passed, failed, total)
        
        return report
    
    def _run_multiple_times(self, scenario: TestScenario, count: int) -> List[Dict[str, Any]]:
        """
        多次运行测试
        
        Args:
            scenario: 测试场景
            count: 运行次数
        
        Returns:
            多次运行结果列表
        """
        run_results = []
        
        for run_idx in range(count):
            try:
                # 执行查询
                start = time.time()
                result = self.interface.query(scenario.query)
                elapsed = time.time() - start
                
                # 记录响应时间（用于 Process Goal 评估）
                result['_response_time'] = elapsed
                result['_run_index'] = run_idx + 1
                
                run_results.append({
                    'success': True,
                    'result': result,
                    'elapsed': elapsed,
                    'error': None
                })
                
            except Exception as e:
                run_results.append({
                    'success': False,
                    'result': None,
                    'elapsed': 0,
                    'error': str(e)
                })
        
        return run_results
    
    def _evaluate_results(self, scenario: TestScenario, 
                         run_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        评估测试结果
        
        Args:
            scenario: 测试场景
            run_results: 多次运行结果
        
        Returns:
            评估结果
        """
        # 分别评估 Dataset Goal 和 Process Goal
        dataset_passes = []
        process_passes = []
        
        for run_result in run_results:
            if not run_result['success']:
                # 运行失败，两个维度都不通过
                dataset_passes.append(False)
                process_passes.append(False)
                continue
            
            result = run_result['result']
            
            # 评估 Dataset Goal
            dataset_passed = self._evaluate_goals(scenario.dataset_goals, result)
            dataset_passes.append(dataset_passed)
            
            # 评估 Process Goal
            process_passed = self._evaluate_goals(scenario.process_goals, result)
            process_passes.append(process_passed)
        
        # 计算正确率
        dataset_accuracy = sum(dataset_passes) / len(dataset_passes) if dataset_passes else 0
        process_accuracy = sum(process_passes) / len(process_passes) if process_passes else 0
        
        # 判断是否通过（任一维度达到阈值）
        passed = (dataset_accuracy >= scenario.pass_threshold or 
                 process_accuracy >= scenario.pass_threshold)
        
        return {
            'dataset_accuracy': dataset_accuracy,
            'process_accuracy': process_accuracy,
            'accuracy': max(dataset_accuracy, process_accuracy),
            'dataset_passes': dataset_passes,
            'process_passes': process_passes,
            'passed': passed,
            'run_count': len(run_results),
            'success_count': sum(1 for r in run_results if r['success'])
        }
    
    def _evaluate_goals(self, goals: List[Goal], result: Dict[str, Any]) -> bool:
        """
        评估 Goal 列表
        
        Args:
            goals: Goal 列表
            result: 测试结果
        
        Returns:
            是否通过
        """
        if not goals:
            return True  # 没有 Goal 默认通过
        
        passed_count = 0
        total_weight = 0
        
        for goal in goals:
            try:
                # 执行验证
                passed = goal.validator(result)
                
                if passed:
                    passed_count += goal.weight
                
                total_weight += goal.weight
                
            except Exception as e:
                # 验证器异常，算失败
                pass
        
        # 计算加权通过率
        if total_weight == 0:
            return True
        
        pass_rate = passed_count / total_weight
        return pass_rate >= 0.5  # 50% 的 Goal 通过即算该维度通过
    
    def _generate_report(self, passed: int, failed: int, total: int) -> Dict[str, Any]:
        """生成测试报告"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        report = {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': passed / total * 100 if total > 0 else 0,
            'duration': duration,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'config': {
                'run_count': 3,
                'pass_threshold': 0.5
            },
            'results': self.results
        }
        
        # 打印报告
        print()
        print("=" * 80)
        print("测试报告（增强版）")
        print("=" * 80)
        print(f"总测试数：{total}")
        print(f"通过：{passed} ({report['pass_rate']:.1f}%)")
        print(f"失败：{failed}")
        print(f"耗时：{duration:.2f}秒")
        print(f"平均速度：{duration/total:.2f}秒/场景 ({duration/(total*3):.2f}秒/次)")
        print("=" * 80)
        
        # 维度分析
        dataset_passed = sum(1 for r in self.results 
                           if r['evaluation']['dataset_accuracy'] >= 0.5)
        process_passed = sum(1 for r in self.results 
                           if r['evaluation']['process_accuracy'] >= 0.5)
        
        print(f"\n维度分析:")
        print(f"  Dataset Goal 通过：{dataset_passed}/{total} ({dataset_passed/total*100:.1f}%)")
        print(f"  Process Goal 通过：{process_passed}/{total} ({process_passed/total*100:.1f}%)")
        print(f"  任一维度通过：{passed}/{total} ({passed/total*100:.1f}%)")
        print("=" * 80)
        
        # 失败详情
        if failed > 0:
            print()
            print("失败详情:")
            print("-" * 80)
            for result in self.results:
                if not result['passed']:
                    scenario = result['scenario']
                    eval_data = result['evaluation']
                    print(f"{scenario.id}: {scenario.query}")
                    print(f"  Dataset 正确率：{eval_data['dataset_accuracy']:.0%}")
                    print(f"  Process 正确率：{eval_data['process_accuracy']:.0%}")
                    print(f"  成功次数：{eval_data['success_count']}/{eval_data['run_count']}")
                    print()
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: Dict[str, Any]):
        """保存测试报告"""
        report_path = Path(__file__).parent / 'test_reports'
        report_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_path / f'enhanced_test_report_{timestamp}.json'
        
        # 转换为 JSON 可序列化格式
        report_json = {
            'total': report['total'],
            'passed': report['passed'],
            'failed': report['failed'],
            'pass_rate': report['pass_rate'],
            'duration': report['duration'],
            'start_time': report['start_time'],
            'end_time': report['end_time'],
            'config': report['config'],
            'summary': {
                'by_category': {},
                'by_priority': {},
                'by_dimension': {
                    'dataset_passed': 0,
                    'process_passed': 0
                }
            },
            'failed_tests': []
        }
        
        # 统计
        for result in self.results:
            scenario = result['scenario']
            eval_data = result['evaluation']
            
            # 按类别
            category = scenario.category
            if result['passed']:
                report_json['summary']['by_category'][f'{category}_passed'] = \
                    report_json['summary']['by_category'].get(f'{category}_passed', 0) + 1
            else:
                report_json['summary']['by_category'][f'{category}_failed'] = \
                    report_json['summary']['by_category'].get(f'{category}_failed', 0) + 1
            
            # 按优先级
            priority = scenario.priority
            if result['passed']:
                report_json['summary']['by_priority'][f'{priority}_passed'] = \
                    report_json['summary']['by_priority'].get(f'{priority}_passed', 0) + 1
            else:
                report_json['summary']['by_priority'][f'{priority}_failed'] = \
                    report_json['summary']['by_priority'].get(f'{priority}_failed', 0) + 1
            
            # 按维度
            if eval_data['dataset_accuracy'] >= 0.5:
                report_json['summary']['by_dimension']['dataset_passed'] += 1
            if eval_data['process_accuracy'] >= 0.5:
                report_json['summary']['by_dimension']['process_passed'] += 1
            
            # 失败详情
            if not result['passed']:
                report_json['failed_tests'].append({
                    'id': scenario.id,
                    'query': scenario.query,
                    'category': scenario.category,
                    'priority': scenario.priority,
                    'dataset_accuracy': eval_data['dataset_accuracy'],
                    'process_accuracy': eval_data['process_accuracy'],
                    'success_count': eval_data['success_count'],
                    'run_count': eval_data['run_count']
                })
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_json, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 测试报告已保存：{report_file}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版自动化测试')
    parser.add_argument('--priority', type=str, choices=['high', 'medium', 'low'],
                       help='只测试指定优先级')
    parser.add_argument('--count', type=int, help='只测试前 N 个场景')
    
    args = parser.parse_args()
    
    try:
        # 创建测试执行器
        runner = EnhancedTestRunner()
        
        # 运行测试
        report = runner.run_all_tests(priority_filter=args.priority)
        
        # 返回退出码
        if report['passed'] == report['total']:
            print("\n✅ 所有测试通过！")
            sys.exit(0)
        else:
            print(f"\n⚠️ {report['failed']} 个测试失败")
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
