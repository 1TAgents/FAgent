"""
通用测试运行器

从 test_cases.json 读取测试用例并执行
支持按 suite、tag、id 过滤测试
"""

import json
import sys
import os
import time
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试用例文件路径
TEST_CASES_FILE = Path(__file__).parent / "test_cases.json"


class TestStatus(Enum):
    PASSED = "✅"
    FAILED = "❌"
    SKIPPED = "⏭️"
    ERROR = "💥"


@dataclass
class TestResult:
    case_id: str
    name: str
    status: TestStatus
    duration_ms: float = 0
    message: str = ""
    details: Any = None


class TestRunner:
    """测试运行器"""
    
    def __init__(self, cases_file: Path = TEST_CASES_FILE):
        self.cases_file = cases_file
        self.test_data = self._load_cases()
        self.results: List[TestResult] = []

    def _load_cases(self) -> dict:
        """加载测试用例"""
        with open(self.cases_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_suites(self) -> List[str]:
        """获取所有测试套件名称"""
        return list(self.test_data.get("test_suites", {}).keys())
    
    def get_cases_by_suite(self, suite_name: str) -> List[dict]:
        """获取指定套件的所有用例"""
        suite = self.test_data.get("test_suites", {}).get(suite_name, {})
        return suite.get("cases", [])
    
    def get_cases_by_tag(self, tag: str) -> List[tuple]:
        """获取指定 tag 的所有用例，返回 (suite_name, case) 列表"""
        results = []
        for suite_name, suite in self.test_data.get("test_suites", {}).items():
            for case in suite.get("cases", []):
                if tag in case.get("tags", []):
                    results.append((suite_name, case))
        return results
    
    def run_market_service_case(self, case: dict) -> TestResult:
        """运行 Market Service 测试用例"""
        case_id = case["id"]
        name = case["name"]
        start_time = time.time()
        
        try:
            from agents.common.market import market_service, KLinePeriod
            
            func_name = case["function"]
            input_data = case["input"]
            expected = case["expected"]
            
            # 执行不同的函数
            if "get_quote" in func_name:
                result = market_service.get_quote(input_data["symbol"])
                success = result is not None
                if success and expected.get("fields"):
                    for field in expected["fields"]:
                        if not hasattr(result, field):
                            return TestResult(
                                case_id=case_id, name=name,
                                status=TestStatus.FAILED,
                                message=f"缺少字段: {field}",
                                duration_ms=(time.time() - start_time) * 1000
                            )
                            
            elif "get_kline" in func_name:
                period = getattr(KLinePeriod, input_data["period"])
                result = market_service.get_kline(
                    input_data["symbol"], period, input_data["count"]
                )
                success = result is not None
                if success and expected.get("data_count"):
                    if len(result.data) < expected["data_count"]:
                        return TestResult(
                            case_id=case_id, name=name,
                            status=TestStatus.FAILED,
                            message=f"数据条数不足: {len(result.data)} < {expected['data_count']}",
                            duration_ms=(time.time() - start_time) * 1000
                        )
                        
            elif "search" in func_name:
                result = market_service.search(
                    input_data["keyword"], input_data.get("limit", 10)
                )
                # search 可能返回 None 或列表
                if result is None:
                    result = []
                success = len(result) >= expected.get("min_results", 1)
                if success and expected.get("contains_symbol"):
                    symbols = [r.symbol for r in result]
                    if expected["contains_symbol"] not in symbols:
                        return TestResult(
                            case_id=case_id, name=name,
                            status=TestStatus.FAILED,
                            message=f"结果未包含: {expected['contains_symbol']}，实际: {symbols}",
                            duration_ms=(time.time() - start_time) * 1000
                        )
                if not success:
                    return TestResult(
                        case_id=case_id, name=name,
                        status=TestStatus.FAILED,
                        message=f"结果数量不足: {len(result)} < {expected.get('min_results', 1)}",
                        duration_ms=(time.time() - start_time) * 1000
                    )
            else:
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.SKIPPED,
                    message=f"未实现的函数: {func_name}"
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if success == expected.get("success", True):
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.PASSED,
                    duration_ms=duration_ms
                )
            else:
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.FAILED,
                    message="结果与预期不符",
                    duration_ms=duration_ms
                )
                
        except Exception as e:
            return TestResult(
                case_id=case_id, name=name,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def run_market_subagent_case(self, case: dict) -> TestResult:
        """运行 Market SubAgent 测试用例"""
        case_id = case["id"]
        name = case["name"]
        start_time = time.time()
        
        try:
            from agents.subagents import market_subagent
            from agents.subagents.market_agent import MarketQuery, MarketIntent
            
            func_name = case["function"]
            input_data = case["input"]
            expected = case["expected"]
            
            if "process" in func_name:
                intent = getattr(MarketIntent, input_data["intent"])
                query = MarketQuery(
                    intent=intent,
                    symbol=input_data.get("symbol"),
                    count=input_data.get("count", 30)
                )
                result = market_subagent.process(query)
                success = result.success == expected.get("success", True)
                if expected.get("has_summary") and not result.summary:
                    success = False
                    
            elif "quick_quote" in func_name:
                result = market_subagent.quick_quote(input_data["symbol"])
                success = result is not None
                if expected.get("contains"):
                    for text in expected["contains"]:
                        if text not in result:
                            return TestResult(
                                case_id=case_id, name=name,
                                status=TestStatus.FAILED,
                                message=f"结果未包含: {text}",
                                duration_ms=(time.time() - start_time) * 1000
                            )
            else:
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.SKIPPED,
                    message=f"未实现的函数: {func_name}"
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            if success:
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.PASSED,
                    duration_ms=duration_ms
                )
            else:
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.FAILED,
                    message="结果与预期不符",
                    duration_ms=duration_ms
                )
                
        except Exception as e:
            return TestResult(
                case_id=case_id, name=name,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def run_api_case(self, case: dict, base_url: str) -> TestResult:
        """运行 API 测试用例"""
        case_id = case["id"]
        name = case["name"]
        start_time = time.time()
        
        try:
            import httpx
            
            # 构建 URL
            endpoint = case["endpoint"]
            input_data = case["input"]
            
            # 替换路径参数
            for key, value in input_data.items():
                if key != "query_params":
                    endpoint = endpoint.replace(f"{{{key}}}", str(value))
            
            url = f"{base_url}{endpoint}"
            params = input_data.get("query_params", {})
            
            # 发送请求
            with httpx.Client(timeout=10) as client:
                if case["method"] == "GET":
                    resp = client.get(url, params=params)
                elif case["method"] == "POST":
                    resp = client.post(url, json=input_data.get("body", {}))
                else:
                    return TestResult(
                        case_id=case_id, name=name,
                        status=TestStatus.SKIPPED,
                        message=f"未支持的方法: {case['method']}"
                    )
            
            duration_ms = (time.time() - start_time) * 1000
            expected = case["expected"]
            
            # 验证状态码
            if resp.status_code != expected.get("status_code", 200):
                return TestResult(
                    case_id=case_id, name=name,
                    status=TestStatus.FAILED,
                    message=f"状态码: {resp.status_code} != {expected['status_code']}",
                    duration_ms=duration_ms
                )
            
            # 验证 JSON 字段
            if expected.get("json_fields"):
                data = resp.json()
                for field in expected["json_fields"]:
                    if field not in data:
                        return TestResult(
                            case_id=case_id, name=name,
                            status=TestStatus.FAILED,
                            message=f"缺少字段: {field}",
                            duration_ms=duration_ms
                        )
            
            return TestResult(
                case_id=case_id, name=name,
                status=TestStatus.PASSED,
                duration_ms=duration_ms
            )
            
        except httpx.ConnectError:
            return TestResult(
                case_id=case_id, name=name,
                status=TestStatus.SKIPPED,
                message="服务未运行",
                duration_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return TestResult(
                case_id=case_id, name=name,
                status=TestStatus.ERROR,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def run_suite(self, suite_name: str) -> List[TestResult]:
        """运行指定测试套件"""
        suite = self.test_data.get("test_suites", {}).get(suite_name)
        if not suite:
            print(f"⚠️ 未找到套件: {suite_name}")
            return []
        
        print(f"\n{'=' * 60}")
        print(f"  {suite_name}: {suite.get('description', '')}")
        print("=" * 60)
        
        results = []
        cases = suite.get("cases", [])
        
        for case in cases:
            if suite_name == "market_service":
                result = self.run_market_service_case(case)
            elif suite_name == "market_subagent":
                result = self.run_market_subagent_case(case)
            elif suite_name == "market_api":
                base_url = suite.get("base_url", "http://localhost:8001")
                result = self.run_api_case(case, base_url)
            else:
                result = TestResult(
                    case_id=case["id"],
                    name=case["name"],
                    status=TestStatus.SKIPPED,
                    message=f"未实现的套件: {suite_name}"
                )
            
            results.append(result)
            self._print_result(result)
        
        return results
    
    def run_by_tag(self, tag: str) -> List[TestResult]:
        """按 tag 运行测试"""
        cases = self.get_cases_by_tag(tag)
        if not cases:
            print(f"⚠️ 未找到 tag: {tag}")
            return []
        
        print(f"\n{'=' * 60}")
        print(f"  Tag: {tag} ({len(cases)} 个用例)")
        print("=" * 60)
        
        results = []
        for suite_name, case in cases:
            suite = self.test_data["test_suites"][suite_name]
            
            if suite_name == "market_service":
                result = self.run_market_service_case(case)
            elif suite_name == "market_subagent":
                result = self.run_market_subagent_case(case)
            elif suite_name == "market_api":
                base_url = suite.get("base_url", "http://localhost:8001")
                result = self.run_api_case(case, base_url)
            else:
                result = TestResult(
                    case_id=case["id"],
                    name=case["name"],
                    status=TestStatus.SKIPPED,
                    message=f"未实现的套件: {suite_name}"
                )
            
            results.append(result)
            self._print_result(result)
        
        return results
    
    def run_all(self) -> List[TestResult]:
        """运行所有测试"""
        results = []
        for suite_name in self.get_suites():
            results.extend(self.run_suite(suite_name))
        return results
    
    def _print_result(self, result: TestResult):
        """打印单个测试结果"""
        status_icon = result.status.value
        duration = f"({result.duration_ms:.0f}ms)" if result.duration_ms > 0 else ""
        message = f" - {result.message}" if result.message else ""
        print(f"  {status_icon} [{result.case_id}] {result.name} {duration}{message}")
    
    def print_summary(self, results: List[TestResult]):
        """打印测试摘要"""
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        error = sum(1 for r in results if r.status == TestStatus.ERROR)
        total = len(results)
        
        total_time = sum(r.duration_ms for r in results)
        
        print(f"\n{'=' * 60}")
        print("  测试摘要")
        print("=" * 60)
        print(f"  总计: {total} 用例 | 耗时: {total_time/1000:.2f}s")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⏭️ 跳过: {skipped}")
        print(f"  💥 错误: {error}")
        
        if failed > 0:
            print(f"\n  失败用例:")
            for r in results:
                if r.status == TestStatus.FAILED:
                    print(f"    - [{r.case_id}] {r.name}: {r.message}")


TestStatus.__test__ = False
TestResult.__test__ = False
TestRunner.__test__ = False


def main():
    parser = argparse.ArgumentParser(description="FAgent 测试运行器")
    parser.add_argument("--suite", "-s", help="运行指定套件")
    parser.add_argument("--tag", "-t", help="运行指定 tag 的用例")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有套件和用例")
    parser.add_argument("--all", "-a", action="store_true", help="运行所有测试")
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.list:
        print("\n可用测试套件:")
        for suite_name in runner.get_suites():
            suite = runner.test_data["test_suites"][suite_name]
            cases = suite.get("cases", [])
            print(f"\n  📁 {suite_name}: {suite.get('description', '')}")
            for case in cases:
                tags = ", ".join(case.get("tags", []))
                print(f"     [{case['id']}] {case['name']} ({tags})")
        
        print("\n可用 Tags:")
        for tag, desc in runner.test_data.get("tags_description", {}).items():
            print(f"  - {tag}: {desc}")
        return
    
    print("=" * 60)
    print("  FAgent 测试运行器")
    print("=" * 60)
    print(f"  用例文件: {runner.cases_file}")
    print(f"  版本: {runner.test_data.get('version', 'unknown')}")
    
    if args.suite:
        results = runner.run_suite(args.suite)
    elif args.tag:
        results = runner.run_by_tag(args.tag)
    elif args.all:
        results = runner.run_all()
    else:
        # 默认运行非 API 的套件
        results = []
        for suite_name in ["market_service", "market_subagent"]:
            results.extend(runner.run_suite(suite_name))
    
    runner.print_summary(results)


if __name__ == "__main__":
    main()
