#!/usr/bin/env python3
"""Replay and evaluate FAgent badcases from docs/badcases.json."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO = SCRIPT_DIR.parents[3]
DEFAULT_BADCASES = "docs/badcases.json"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def url_port(url: str, default: int) -> int:
    parsed = urllib.parse.urlparse(url)
    return parsed.port or default


def http_json(url: str, timeout: float = 5.0) -> Any:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(url: str, name: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            http_json(url, timeout=3.0)
            print(f"[ok] {name} healthy: {url}")
            return True
        except Exception:
            time.sleep(1)
    print(f"[warn] {name} did not become healthy before timeout: {url}", file=sys.stderr)
    return False


def is_fagent_agents(url: str) -> bool:
    try:
        data = http_json(f"{url.rstrip('/')}/", timeout=3.0)
    except Exception:
        return False
    return data.get("service") == "FAgent Agents"


def resolve_agents_base_url(cli_value: str | None) -> str:
    if cli_value:
        return cli_value
    env_value = os.getenv("AGENTS_BASE_URL")
    if env_value:
        return env_value

    primary = f"http://localhost:{os.getenv('AGENTS_PORT', '8001')}"
    candidates = [primary, "http://localhost:8011"]
    for candidate in dict.fromkeys(candidates):
        if is_fagent_agents(candidate):
            return candidate
    return primary


def tmux_has_session(name: str) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def tmux_kill_session(name: str) -> None:
    subprocess.run(
        ["tmux", "kill-session", "-t", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def tmux_start_session(name: str, command: str) -> None:
    if tmux_has_session(name):
        print(f"[skip] tmux session exists: {name}")
        return
    subprocess.run(["tmux", "new-session", "-d", "-s", name, command], check=True)
    print(f"[start] tmux session: {name}")


def start_services(
    repo: Path,
    agents_base_url: str,
    backend_base_url: str,
    frontend_url: str,
    include_frontend: bool,
    restart_owned: bool,
) -> None:
    if shutil.which("tmux") is None:
        raise RuntimeError("tmux is required for --start-services")

    agents_port = url_port(agents_base_url, 8001)
    backend_port = url_port(backend_base_url, 8000)
    frontend_port = url_port(frontend_url, 5173)

    sessions = {
        "fagent-badcase-agents": (
            f"cd {shell_quote(repo)} && "
            "set -a; [ -f .env ] && . ./.env; set +a; "
            f"export PYTHONPATH=. AGENTS_PORT={agents_port}; "
            f"python -m uvicorn agents.api.main:app --host 0.0.0.0 --port {agents_port}"
        ),
        "fagent-badcase-backend": (
            f"cd {shell_quote(repo)} && "
            "set -a; [ -f .env ] && . ./.env; set +a; "
            f"export PYTHONPATH=. AGENTS_BASE_URL={shell_quote(agents_base_url)} BACKEND_PORT={backend_port}; "
            f"python -m uvicorn backend.api.main:app --host 0.0.0.0 --port {backend_port}"
        ),
    }
    if include_frontend:
        sessions["fagent-badcase-frontend"] = (
            f"cd {shell_quote(repo / 'frontend')} && "
            f"npm run dev -- --host 0.0.0.0 --port {frontend_port} --strictPort"
        )

    if restart_owned:
        for name in sessions:
            tmux_kill_session(name)

    try:
        if not is_fagent_agents(agents_base_url):
            raise RuntimeError("healthy endpoint is not FAgent Agents")
        print(f"[skip] agents already healthy: {agents_base_url}")
    except Exception:
        tmux_start_session("fagent-badcase-agents", sessions["fagent-badcase-agents"])

    try:
        http_json(f"{backend_base_url.rstrip('/')}/health", timeout=3.0)
        print(f"[skip] backend already healthy: {backend_base_url}")
    except Exception:
        tmux_start_session("fagent-badcase-backend", sessions["fagent-badcase-backend"])

    if include_frontend:
        tmux_start_session("fagent-badcase-frontend", sessions["fagent-badcase-frontend"])

    wait_for_health(f"{agents_base_url.rstrip('/')}/health", "agents")
    wait_for_health(f"{backend_base_url.rstrip('/')}/health", "backend")
    if not is_fagent_agents(agents_base_url):
        raise RuntimeError(
            f"{agents_base_url} is not FAgent Agents. Pass --agents-base-url for the running FAgent Agents service."
        )


def shell_quote(path_or_value: Any) -> str:
    return "'" + str(path_or_value).replace("'", "'\"'\"'") + "'"


def load_badcases(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("badcases", [])


def print_case_list(cases: list[dict[str, Any]]) -> None:
    for case in cases:
        replay = case.get("replay") or {}
        marker = "replay" if replay else "no-replay"
        print(
            f"{case['id']} [{case.get('status', 'unknown')}] [{marker}] "
            f"cid={replay.get('cid', '-')} mid={replay.get('message_id', '-')} "
            f"query={case.get('query', '')}"
        )


def parse_sse_content(body: bytes) -> tuple[str, list[str]]:
    content_parts: list[str] = []
    errors: list[str] = []
    for raw_line in body.decode("utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if payload == "[DONE]":
            break
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            errors.append(f"malformed SSE JSON: {payload[:200]}")
            continue
        if "error" in data:
            errors.append(str(data["error"]))
        if "content" in data:
            content_parts.append(str(data["content"]))
    return "".join(content_parts), errors


def replay_case(case: dict[str, Any], agents_base_url: str, timeout: float) -> dict[str, Any]:
    replay = case.get("replay")
    if not replay:
        return {
            "case_id": case.get("id"),
            "ok": False,
            "error": "missing replay metadata",
            "actual_answer": "",
        }

    payload = {
        "cid": replay["cid"],
        "message_id": replay["message_id"],
        "user_message": case["query"],
        "history_limit": replay.get("history_limit") or 10,
        "model": replay.get("model"),
    }
    endpoint = f"{agents_base_url.rstrip('/')}/agent/chat/router/stream"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
        actual, stream_errors = parse_sse_content(body)
        return {
            "case_id": case["id"],
            "ok": not stream_errors,
            "endpoint": endpoint,
            "payload": redact_payload(payload),
            "actual_answer": actual,
            "stream_errors": stream_errors,
            "duration_sec": round(time.time() - started_at, 3),
        }
    except urllib.error.HTTPError as exc:
        return {
            "case_id": case["id"],
            "ok": False,
            "endpoint": endpoint,
            "payload": redact_payload(payload),
            "actual_answer": "",
            "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}",
            "duration_sec": round(time.time() - started_at, 3),
        }
    except Exception as exc:
        return {
            "case_id": case["id"],
            "ok": False,
            "endpoint": endpoint,
            "payload": redact_payload(payload),
            "actual_answer": "",
            "error": str(exc),
            "duration_sec": round(time.time() - started_at, 3),
        }


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k != "api_key"}


def evaluate_case(
    case: dict[str, Any],
    actual_answer: str,
    judge_mode: str,
    timeout: float,
) -> dict[str, Any]:
    if judge_mode == "none":
        return {
            "passed": None,
            "failure_type": "not_evaluated",
            "score": None,
            "rationale": "judge disabled",
        }
    if not actual_answer.strip():
        return {
            "passed": False,
            "failure_type": "fagent",
            "score": 0,
            "rationale": "empty actual answer",
        }
    if judge_mode == "heuristic":
        return heuristic_evaluate(case["expected_answer"], actual_answer)
    return llm_evaluate(case, actual_answer, timeout)


def heuristic_evaluate(expected_answer: str, actual_answer: str) -> dict[str, Any]:
    expected_tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]{2,}", expected_answer)
        if token.lower() not in {"should", "answer", "expected", "fagent"}
    }
    actual_lower = actual_answer.lower()
    hits = sorted(token for token in expected_tokens if token in actual_lower)
    score = len(hits) / max(len(expected_tokens), 1)
    return {
        "passed": score >= 0.35,
        "failure_type": "none" if score >= 0.35 else "fagent",
        "score": round(score, 3),
        "rationale": "heuristic token overlap; use --judge-mode llm for authoritative evaluation",
        "matched_terms": hits[:20],
    }


def llm_evaluate(case: dict[str, Any], actual_answer: str, timeout: float) -> dict[str, Any]:
    api_key = (
        os.getenv("BADCASE_EVAL_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        return {
            "passed": False,
            "failure_type": "evaluator",
            "score": 0,
            "rationale": "missing BADCASE_EVAL_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY",
        }

    base_url = (
        os.getenv("BADCASE_EVAL_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.deepseek.com"
    ).rstrip("/")
    model = os.getenv("BADCASE_EVAL_MODEL") or os.getenv("DEEPSEEK_EVAL_MODEL") or "deepseek-v4-pro"
    endpoint = f"{base_url}/chat/completions"

    system = (
        "You are a strict but fair regression evaluator for FAgent badcases. "
        "Return only valid JSON. Judge whether ACTUAL_ANSWER satisfies EXPECTED_ANSWER. "
        "Do not require exact wording. If expected_answer is vague, stale, contradictory, "
        "or not observable, use failure_type='expected_answer'. If the judge cannot evaluate "
        "because of missing/malformed inputs or API issues, use failure_type='evaluator'. "
        "If FAgent's actual answer fails a reasonable expectation, use failure_type='fagent'."
    )
    user = {
        "case_id": case.get("id"),
        "query": case.get("query"),
        "expected_answer": case.get("expected_answer"),
        "actual_answer": actual_answer,
        "allowed_failure_types": ["none", "evaluator", "expected_answer", "fagent"],
        "required_json_schema": {
            "passed": "boolean",
            "score": "number 0..1",
            "failure_type": "none|evaluator|expected_answer|fagent",
            "rationale": "short string",
            "missing_or_wrong": "array of strings",
        },
    }
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return normalize_judge_json(content)
    except urllib.error.HTTPError as exc:
        return {
            "passed": False,
            "failure_type": "evaluator",
            "score": 0,
            "rationale": f"judge HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}",
        }
    except Exception as exc:
        return {
            "passed": False,
            "failure_type": "evaluator",
            "score": 0,
            "rationale": f"judge error: {exc}",
        }


def normalize_judge_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return {
            "passed": False,
            "failure_type": "evaluator",
            "score": 0,
            "rationale": f"judge returned non-json: {content[:300]}",
        }

    passed = bool(result.get("passed"))
    failure_type = result.get("failure_type") or ("none" if passed else "fagent")
    if failure_type not in {"none", "evaluator", "expected_answer", "fagent"}:
        failure_type = "evaluator"
    if passed:
        failure_type = "none"
    return {
        "passed": passed,
        "failure_type": failure_type,
        "score": result.get("score"),
        "rationale": result.get("rationale", ""),
        "missing_or_wrong": result.get("missing_or_wrong", []),
    }


def select_cases(cases: list[dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return cases
    wanted = set(ids)
    selected = [case for case in cases if case.get("id") in wanted]
    missing = sorted(wanted - {case.get("id") for case in selected})
    if missing:
        raise SystemExit(f"Unknown badcase id(s): {', '.join(missing)}")
    return selected


def default_output_path(repo: Path) -> Path:
    now = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return repo / "reports" / "badcase-eval" / f"{now}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(DEFAULT_REPO), help="FAgent repo root")
    parser.add_argument("--badcases", default=DEFAULT_BADCASES, help="badcases JSON path")
    parser.add_argument("--case-id", action="append", default=[], help="badcase id to run; repeatable")
    parser.add_argument("--list", action="store_true", help="list badcases and exit")
    parser.add_argument("--start-services", action="store_true", help="start missing local services in tmux")
    parser.add_argument("--restart-owned", action="store_true", help="restart only tmux sessions created by this script")
    parser.add_argument("--with-frontend", action="store_true", help="start frontend too")
    parser.add_argument("--agents-base-url", default=None)
    parser.add_argument("--backend-base-url", default=None)
    parser.add_argument("--frontend-url", default=None)
    parser.add_argument("--judge-mode", choices=["llm", "none", "heuristic"], default="llm")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout seconds")
    parser.add_argument("--output", default=None, help="JSON report path; default writes under reports/badcase-eval")
    parser.add_argument("--no-output", action="store_true", help="do not write a JSON report")
    parser.add_argument("--no-fail-exit", action="store_true", help="always exit 0 after running")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    load_dotenv(repo / ".env")

    badcases_path = (repo / args.badcases).resolve()
    cases = load_badcases(badcases_path)
    if args.list:
        print_case_list(cases)
        return 0

    agents_base_url = resolve_agents_base_url(args.agents_base_url)
    backend_base_url = args.backend_base_url or f"http://localhost:{os.getenv('BACKEND_PORT', '8000')}"
    frontend_url = args.frontend_url or f"http://localhost:{os.getenv('FRONTEND_PORT', '5173')}"

    if args.start_services:
        start_services(
            repo=repo,
            agents_base_url=agents_base_url,
            backend_base_url=backend_base_url,
            frontend_url=frontend_url,
            include_frontend=args.with_frontend,
            restart_owned=args.restart_owned,
        )

    selected = select_cases(cases, args.case_id)
    results: list[dict[str, Any]] = []
    for case in selected:
        print(f"[run] {case['id']} cid={(case.get('replay') or {}).get('cid')} mid={(case.get('replay') or {}).get('message_id')}")
        replay_result = replay_case(case, agents_base_url, args.timeout)
        eval_result = evaluate_case(case, replay_result.get("actual_answer", ""), args.judge_mode, args.timeout)
        result = {
            "case_id": case["id"],
            "query": case.get("query"),
            "replay": case.get("replay"),
            "replay_result": replay_result,
            "evaluation": eval_result,
        }
        results.append(result)
        status = "PASS" if eval_result.get("passed") else "FAIL"
        if eval_result.get("passed") is None:
            status = "NOT_EVALUATED"
        print(
            f"[{status}] {case['id']} "
            f"failure_type={eval_result.get('failure_type')} "
            f"score={eval_result.get('score')} "
            f"duration={replay_result.get('duration_sec')}s"
        )
        rationale = eval_result.get("rationale")
        if rationale:
            print(f"  rationale: {rationale}")

    report = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "repo": str(repo),
        "badcases": str(badcases_path),
        "agents_base_url": agents_base_url,
        "judge_mode": args.judge_mode,
        "results": results,
    }

    if not args.no_output:
        output_path = Path(args.output).resolve() if args.output else default_output_path(repo)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[report] {output_path}")

    any_fail = any(item["evaluation"].get("passed") is False for item in results)
    return 0 if args.no_fail_exit or not any_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
