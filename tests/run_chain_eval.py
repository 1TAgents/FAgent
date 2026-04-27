"""
Chain 评估运行器

目标：
1. 运行带 expected_chain 的测试用例
2. 从 backend / agents / mcp 的 chain JSONL 中还原实际调用链
3. 独立输出 result_pass 和 chain_pass
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx


ROOT_DIR = Path(__file__).resolve().parents[1]
TEST_CASES_FILE = Path(__file__).with_name("test_cases.json")
REPORTS_ROOT = ROOT_DIR / "reports" / "chain_eval"
CHAIN_LOG_DIRS = [
    ROOT_DIR / "logs" / "backend",
    ROOT_DIR / "logs" / "agents",
    ROOT_DIR / "logs" / "mcp",
]
PREDICATE_KEYS = {"eq", "exists", "one_of", "contains", "regex"}
MISSING = object()


@dataclass
class EvalResult:
    suite: str
    case_id: str
    step: Optional[int]
    rid: str
    result_pass: bool
    chain_pass: bool
    response_ok: bool
    chain_ok: bool
    issues: List[str]
    missing_events: List[Dict[str, Any]]
    unexpected_events: List[Dict[str, Any]]
    param_mismatches: List[Dict[str, Any]]
    trace_file: str


def load_cases() -> Dict[str, Any]:
    with TEST_CASES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_report_dir() -> Path:
    report_dir = REPORTS_ROOT / datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def get_cases(test_data: Dict[str, Any], suite_filter: Optional[str], case_filter: Optional[str]) -> List[Tuple[str, Dict[str, Any], Dict[str, Any]]]:
    selected: List[Tuple[str, Dict[str, Any], Dict[str, Any]]] = []
    for suite_name, suite in test_data.get("test_suites", {}).items():
        if suite_filter and suite_name != suite_filter:
            continue
        for case in suite.get("cases", []):
            if case_filter and case.get("id") != case_filter:
                continue
            has_case_chain = bool(case.get("expected_chain"))
            has_step_chain = any(step.get("expected_chain") for step in case.get("steps", []))
            if has_case_chain or has_step_chain:
                selected.append((suite_name, suite, case))
    return selected


def stream_chat(base_url: str, cid: int, message: str, rid: str, model: Optional[str] = None) -> Dict[str, Any]:
    url = f"{base_url}/api/chat/send/stream"
    payload = {
        "cid": cid,
        "user_message": message,
    }
    if model:
        payload["model"] = model

    content_parts: List[str] = []
    done_payload: Dict[str, Any] = {}

    with httpx.Client(timeout=180.0) as client:
        with client.stream("POST", url, json=payload, headers={"X-Request-ID": rid}) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8", errors="ignore")
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                data = json.loads(data_str)
                if "error" in data:
                    raise RuntimeError(data["error"])
                if "content" in data:
                    content_parts.append(data["content"])
                if data.get("done"):
                    done_payload = data

    return {
        "cid": done_payload.get("cid", cid),
        "content": "".join(content_parts),
        "user_message_id": done_payload.get("user_message_id"),
        "assistant_message_id": done_payload.get("assistant_message_id"),
    }


def create_session(base_url: str) -> Dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{base_url}/api/chat/session/create", json={})
        resp.raise_for_status()
        return resp.json()


def call_market_api(base_url: str, case: Dict[str, Any], rid: str) -> Dict[str, Any]:
    endpoint = case["endpoint"]
    input_data = case.get("input", {})

    for key, value in input_data.items():
        if key != "query_params":
            endpoint = endpoint.replace(f"{{{key}}}", str(value))

    url = f"{base_url}{endpoint}"
    params = input_data.get("query_params", {})
    method = case.get("method", "GET").upper()

    with httpx.Client(timeout=60.0) as client:
        if method == "GET":
            resp = client.get(url, params=params, headers={"X-Request-ID": rid})
        elif method == "POST":
            resp = client.post(url, json=input_data.get("body", {}), headers={"X-Request-ID": rid})
        else:
            raise ValueError(f"不支持的 HTTP 方法: {method}")

    return {
        "status_code": resp.status_code,
        "json": resp.json() if resp.content else {},
    }


def load_chain_events(rid: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for log_dir in CHAIN_LOG_DIRS:
        if not log_dir.exists():
            continue
        for path in sorted(log_dir.glob("chain_*.jsonl")):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("rid") == rid:
                        events.append(event)
    events.sort(key=lambda item: item.get("timestamp", ""))
    return events


def extract_route(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for event in events:
        if event.get("layer") == "router" and event.get("event") == "route_decision":
            return {
                "route": event.get("route"),
                "task": event.get("task"),
                "params": event.get("params", {}),
            }
    return None


def is_predicate(spec: Any) -> bool:
    return isinstance(spec, dict) and spec and set(spec.keys()).issubset(PREDICATE_KEYS)


def match_predicate(spec: Dict[str, Any], actual: Any, path: str, mismatches: List[Dict[str, Any]]) -> bool:
    if "exists" in spec:
        exists = actual is not MISSING
        if bool(spec["exists"]) != exists:
            mismatches.append({"path": path, "expected": spec, "actual": None if actual is MISSING else actual})
            return False
        if not spec["exists"]:
            return True

    if actual is MISSING:
        mismatches.append({"path": path, "expected": spec, "actual": None})
        return False

    if "eq" in spec and actual != spec["eq"]:
        mismatches.append({"path": path, "expected": spec["eq"], "actual": actual})
        return False

    if "one_of" in spec and actual not in spec["one_of"]:
        mismatches.append({"path": path, "expected": spec["one_of"], "actual": actual})
        return False

    if "contains" in spec:
        needle = spec["contains"]
        ok = False
        if isinstance(actual, str):
            ok = str(needle) in actual
        elif isinstance(actual, list):
            ok = needle in actual
        elif isinstance(actual, dict) and isinstance(needle, str):
            ok = needle in actual
        if not ok:
            mismatches.append({"path": path, "expected": spec, "actual": actual})
            return False

    if "regex" in spec:
        if re.search(spec["regex"], str(actual)) is None:
            mismatches.append({"path": path, "expected": spec["regex"], "actual": actual})
            return False

    return True


def match_value(expected: Any, actual: Any, path: str, mismatches: List[Dict[str, Any]]) -> bool:
    if is_predicate(expected):
        return match_predicate(expected, actual, path, mismatches)

    if isinstance(expected, dict):
        if actual is MISSING or not isinstance(actual, dict):
            mismatches.append({"path": path, "expected": expected, "actual": None if actual is MISSING else actual})
            return False
        ok = True
        for key, value in expected.items():
            actual_value = actual.get(key, MISSING)
            if not match_value(value, actual_value, f"{path}.{key}" if path else key, mismatches):
                ok = False
        return ok

    if actual is MISSING:
        mismatches.append({"path": path, "expected": expected, "actual": None})
        return False

    if isinstance(expected, list):
        if actual != expected:
            mismatches.append({"path": path, "expected": expected, "actual": actual})
            return False
        return True

    if actual != expected:
        mismatches.append({"path": path, "expected": expected, "actual": actual})
        return False
    return True


def match_event(spec: Dict[str, Any], event: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    mismatches: List[Dict[str, Any]] = []
    ok = True
    for key, expected in spec.items():
        actual = event.get(key, MISSING)
        if not match_value(expected, actual, key, mismatches):
            ok = False
    return ok, mismatches


def find_matching_event(spec: Dict[str, Any], events: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    candidates = [
        event for event in events
        if event.get("layer") == spec.get("layer") and event.get("event") == spec.get("event")
    ]
    if "name" in spec:
        candidates = [event for event in candidates if event.get("name") == spec.get("name")]

    first_mismatch: List[Dict[str, Any]] = []
    for event in candidates:
        ok, mismatches = match_event(spec, event)
        if ok:
            return event, []
        if not first_mismatch:
            first_mismatch = mismatches
    return None, first_mismatch


def event_tokens(event: Dict[str, Any]) -> List[str]:
    base = f"{event.get('layer')}.{event.get('event')}"
    tokens = [base]
    name = event.get("name")
    result = event.get("result")
    success = event.get("success")

    if name is not None:
        tokens.append(f"{base}:{name}")
    if result is not None:
        tokens.append(f"{base}:{result}")
        if name is not None:
            tokens.append(f"{base}:{name}:{result}")
    if success is not None:
        status = "success" if success else "failure"
        tokens.append(f"{base}:{status}")
        if name is not None:
            tokens.append(f"{base}:{name}:{status}")
    return tokens


def order_matches(order: List[str], events: List[Dict[str, Any]]) -> bool:
    if not order:
        return True

    index = 0
    for event in events:
        if order[index] in event_tokens(event):
            index += 1
            if index >= len(order):
                return True
    return False


def evaluate_chain(expected_chain: Dict[str, Any], events: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    missing_events: List[Dict[str, Any]] = []
    unexpected_events: List[Dict[str, Any]] = []
    param_mismatches: List[Dict[str, Any]] = []

    route_spec = expected_chain.get("route")
    if route_spec:
        actual_route = extract_route(events)
        route_mismatches: List[Dict[str, Any]] = []
        if not actual_route or not match_value(route_spec, actual_route, "route", route_mismatches):
            missing_events.append({"type": "route", "expected": route_spec})
            if route_mismatches:
                param_mismatches.append({"type": "route", "details": route_mismatches})

    for spec in expected_chain.get("must", []):
        matched_event, mismatches = find_matching_event(spec, events)
        if matched_event is None:
            missing_events.append(spec)
            if mismatches:
                param_mismatches.append({"expected": spec, "mismatches": mismatches})

    for spec in expected_chain.get("forbid", []):
        matched_event, _ = find_matching_event(spec, events)
        if matched_event is not None:
            unexpected_events.append(matched_event)

    order = expected_chain.get("order", [])
    if order and not order_matches(order, events):
        param_mismatches.append({"type": "order", "expected": order})

    chain_pass = not missing_events and not unexpected_events and not any(item.get("type") == "order" for item in param_mismatches)
    return chain_pass, missing_events, unexpected_events, param_mismatches


def evaluate_chat_response(step: Dict[str, Any], response: Dict[str, Any], events: List[Dict[str, Any]], previous_ids: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
    expected = step.get("expected", {})
    issues: List[str] = []

    if expected.get("success") and not response.get("content"):
        issues.append("响应内容为空")
    if expected.get("has_response") and not response.get("content"):
        issues.append("缺少回复内容")
    if expected.get("has_message_ids") and not (response.get("user_message_id") and response.get("assistant_message_id")):
        issues.append("缺少 message_id")
    if expected.get("has_cid") and not response.get("cid"):
        issues.append("缺少 cid")
    for text in expected.get("response_contains", []):
        if text not in response.get("content", ""):
            issues.append(f"回复未包含: {text}")

    if expected.get("tool_called") or expected.get("should_use_tool"):
        if not any(event.get("event") == "tool_call" for event in events):
            issues.append("未检测到工具调用")

    if expected.get("has_real_data"):
        if not any(event.get("event") == "tool_result" and event.get("success") is True for event in events):
            issues.append("未检测到成功的工具结果")

    if expected.get("message_id_incremented") and previous_ids:
        current_assistant = response.get("assistant_message_id")
        last_assistant = previous_ids.get("assistant_message_id")
        if current_assistant is None or last_assistant is None or current_assistant <= last_assistant:
            issues.append("assistant_message_id 未递增")

    return not issues, issues


def evaluate_api_response(case: Dict[str, Any], response: Dict[str, Any], events: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    expected = case.get("expected", {})
    issues: List[str] = []
    status_code = response.get("status_code")
    payload = response.get("json", {})

    if status_code != expected.get("status_code", 200):
        issues.append(f"状态码不匹配: {status_code} != {expected.get('status_code', 200)}")

    for field in expected.get("json_fields", []):
        if field not in payload:
            issues.append(f"缺少字段: {field}")

    if expected.get("success") and not payload.get("success", False):
        issues.append("接口 success=false")

    if case.get("expected_chain", {}).get("must"):
        if not any(event.get("event") == "tool_call" for event in events):
            issues.append("未检测到工具调用")

    return not issues, issues


def write_trace_file(report_dir: Path, payload: Dict[str, Any]) -> Path:
    trace_path = report_dir / f"{payload['rid']}.trace.json"
    with trace_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return trace_path


def run_conversation_case(
    suite_name: str,
    suite: Dict[str, Any],
    case: Dict[str, Any],
    backend_base_url: str,
    report_dir: Path,
) -> List[EvalResult]:
    results: List[EvalResult] = []
    session = create_session(backend_base_url)
    cid = session["cid"]
    previous_ids: Dict[str, Any] = {}

    last_chain_step = max((step["step"] for step in case.get("steps", []) if step.get("expected_chain")), default=0)
    for step in case.get("steps", []):
        if step["step"] > last_chain_step:
            break
        if step.get("action") != "send_message":
            continue

        rid = f"{case['id']}-s{step['step']}-{int(time.time() * 1000)}"
        response = stream_chat(
            base_url=backend_base_url,
            cid=cid,
            message=step["input"]["message"],
            rid=rid,
        )
        time.sleep(0.5)
        events = load_chain_events(rid)

        result_ok, issues = evaluate_chat_response(step, response, events, previous_ids)
        chain_spec = step.get("expected_chain", {})
        chain_ok, missing_events, unexpected_events, param_mismatches = evaluate_chain(chain_spec, events) if chain_spec else (True, [], [], [])

        trace_payload = {
            "suite": suite_name,
            "case_id": case["id"],
            "step": step["step"],
            "rid": rid,
            "cid": cid,
            "user_mid": response.get("user_message_id"),
            "assistant_mid": response.get("assistant_message_id"),
            "response": response,
            "route": extract_route(events),
            "events": events,
        }
        trace_file = write_trace_file(report_dir, trace_payload)

        results.append(
            EvalResult(
                suite=suite_name,
                case_id=case["id"],
                step=step["step"],
                rid=rid,
                result_pass=result_ok,
                chain_pass=chain_ok,
                response_ok=result_ok,
                chain_ok=chain_ok,
                issues=issues,
                missing_events=missing_events,
                unexpected_events=unexpected_events,
                param_mismatches=param_mismatches,
                trace_file=str(trace_file.relative_to(ROOT_DIR)),
            )
        )
        previous_ids = response

    return results


def run_market_api_case(
    suite_name: str,
    suite: Dict[str, Any],
    case: Dict[str, Any],
    agents_base_url: str,
    report_dir: Path,
) -> List[EvalResult]:
    rid = f"{case['id']}-api-{int(time.time() * 1000)}"
    response = call_market_api(agents_base_url, case, rid)
    time.sleep(0.5)
    events = load_chain_events(rid)

    result_ok, issues = evaluate_api_response(case, response, events)
    chain_ok, missing_events, unexpected_events, param_mismatches = evaluate_chain(case.get("expected_chain", {}), events)

    trace_payload = {
        "suite": suite_name,
        "case_id": case["id"],
        "step": None,
        "rid": rid,
        "response": response,
        "route": extract_route(events),
        "events": events,
    }
    trace_file = write_trace_file(report_dir, trace_payload)

    return [
        EvalResult(
            suite=suite_name,
            case_id=case["id"],
            step=None,
            rid=rid,
            result_pass=result_ok,
            chain_pass=chain_ok,
            response_ok=result_ok,
            chain_ok=chain_ok,
            issues=issues,
            missing_events=missing_events,
            unexpected_events=unexpected_events,
            param_mismatches=param_mismatches,
            trace_file=str(trace_file.relative_to(ROOT_DIR)),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="FAgent Chain 评估运行器")
    parser.add_argument("--suite", help="仅运行指定 suite")
    parser.add_argument("--case", help="仅运行指定 case id")
    parser.add_argument("--backend-base-url", default="http://127.0.0.1:8000", help="Backend 服务地址")
    parser.add_argument("--agents-base-url", default="http://127.0.0.1:8001", help="Agents 服务地址")
    args = parser.parse_args()

    test_data = load_cases()
    report_dir = make_report_dir()
    selected_cases = get_cases(test_data, args.suite, args.case)

    if not selected_cases:
        print("未找到带 expected_chain 的用例")
        return 1

    all_results: List[EvalResult] = []
    for suite_name, suite, case in selected_cases:
        print(f"运行 {suite_name} / {case['id']} - {case['name']}")
        try:
            if suite_name == "multi_turn_chat":
                all_results.extend(
                    run_conversation_case(
                        suite_name=suite_name,
                        suite=suite,
                        case=case,
                        backend_base_url=args.backend_base_url,
                        report_dir=report_dir,
                    )
                )
            elif suite_name == "market_api":
                all_results.extend(
                    run_market_api_case(
                        suite_name=suite_name,
                        suite=suite,
                        case=case,
                        agents_base_url=args.agents_base_url,
                        report_dir=report_dir,
                    )
                )
            else:
                print(f"  跳过: 当前仅支持 multi_turn_chat / market_api，收到 {suite_name}")
        except Exception as e:
            rid = f"{case['id']}-error-{int(time.time() * 1000)}"
            trace_path = report_dir / f"{rid}.trace.json"
            trace_path.write_text(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2), encoding="utf-8")
            all_results.append(
                EvalResult(
                    suite=suite_name,
                    case_id=case["id"],
                    step=None,
                    rid=rid,
                    result_pass=False,
                    chain_pass=False,
                    response_ok=False,
                    chain_ok=False,
                    issues=[str(e)],
                    missing_events=[],
                    unexpected_events=[],
                    param_mismatches=[],
                    trace_file=str(trace_path.relative_to(ROOT_DIR)),
                )
            )

    summary = []
    for item in all_results:
        step_label = f" step={item.step}" if item.step is not None else ""
        print(
            f"  [{'PASS' if item.result_pass and item.chain_pass else 'FAIL'}] "
            f"{item.case_id}{step_label} | result={item.result_pass} | chain={item.chain_pass} | rid={item.rid}"
        )
        if item.issues:
            for issue in item.issues:
                print(f"    issue: {issue}")
        if item.missing_events:
            print(f"    missing_events: {len(item.missing_events)}")
        if item.unexpected_events:
            print(f"    unexpected_events: {len(item.unexpected_events)}")
        if item.param_mismatches:
            print(f"    param_mismatches: {len(item.param_mismatches)}")

        summary.append(
            {
                "suite": item.suite,
                "case_id": item.case_id,
                "step": item.step,
                "rid": item.rid,
                "result_pass": item.result_pass,
                "chain_pass": item.chain_pass,
                "issues": item.issues,
                "missing_events": item.missing_events,
                "unexpected_events": item.unexpected_events,
                "param_mismatches": item.param_mismatches,
                "trace_file": item.trace_file,
            }
        )

    summary_path = report_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告目录: {report_dir.relative_to(ROOT_DIR)}")

    return 0 if all(item.result_pass and item.chain_pass for item in all_results) else 2


if __name__ == "__main__":
    sys.exit(main())
