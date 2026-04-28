"""
Backtest Run Store

持久化回测执行记录和产物，便于后续比较、审计和复盘。
"""
from __future__ import annotations

import csv
import hashlib
import inspect
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .models import BacktestReport, BacktestRequest
from .strategies import STRATEGY_REGISTRY
from .vectorized_strategies import STRATEGY_MAP


ROOT_DIR = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT_DIR / "data" / "backtests"
INDEX_FILE = RUNS_DIR / "index.jsonl"


class BacktestRunStore:
    """文件型回测运行记录仓库。"""

    def __init__(self, base_dir: Path = RUNS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run_id(self) -> str:
        return f"bt_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def persist_run(
        self,
        request: BacktestRequest,
        report: BacktestReport,
        *,
        engine: str,
    ) -> tuple[str, str]:
        report_id = self.create_run_id()
        run_dir = self.base_dir / report_id
        run_dir.mkdir(parents=True, exist_ok=True)

        strategy_meta = self._resolve_strategy_metadata(request.strategy_name)

        self._write_json(
            run_dir / "request.json",
            request.model_dump(),
        )
        self._write_json(
            run_dir / "report.json",
            report.model_dump(),
        )
        self._write_json(
            run_dir / "strategy_metadata.json",
            strategy_meta,
        )
        self._write_text(
            run_dir / "summary.md",
            report.summary() + "\n",
        )
        self._write_equity_curve(run_dir / "equity_curve.csv", report)
        self._write_trades(run_dir / "trades.csv", report)

        source_code = strategy_meta.get("source_code")
        if source_code:
            self._write_text(run_dir / "strategy_source.py", source_code)

        manifest = {
            "report_id": report_id,
            "created_at": datetime.now().isoformat(),
            "engine": engine,
            "strategy_name": request.strategy_name,
            "symbol": request.symbol,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_capital": request.initial_capital,
            "params": request.params,
            "metadata": request.metadata,
            "summary": report.summary(),
            "artifacts": {
                "request": "request.json",
                "report": "report.json",
                "strategy_metadata": "strategy_metadata.json",
                "strategy_source": "strategy_source.py" if source_code else None,
                "equity_curve": "equity_curve.csv",
                "trades": "trades.csv" if report.trades else None,
                "summary": "summary.md",
            },
        }
        self._write_json(run_dir / "manifest.json", manifest)
        self._append_index(manifest)

        relative_dir = str(run_dir.relative_to(ROOT_DIR))
        return report_id, relative_dir

    def load_run(self, report_id: str) -> Optional[Dict[str, Any]]:
        run_dir = self.base_dir / report_id
        manifest_path = run_dir / "manifest.json"
        report_path = run_dir / "report.json"
        request_path = run_dir / "request.json"

        if not manifest_path.exists():
            return None

        payload: Dict[str, Any] = {
            "report_id": report_id,
            "artifacts_dir": str(run_dir.relative_to(ROOT_DIR)),
            "manifest": self._read_json(manifest_path),
        }
        if request_path.exists():
            payload["request"] = self._read_json(request_path)
        if report_path.exists():
            payload["report"] = self._read_json(report_path)
        return payload

    def _resolve_strategy_metadata(self, strategy_name: str) -> Dict[str, Any]:
        strategy_cls = None
        engine = "unknown"

        if strategy_name in STRATEGY_MAP:
            strategy_cls = STRATEGY_MAP[strategy_name]
            engine = "vectorized"
        elif strategy_name in STRATEGY_REGISTRY:
            strategy_cls = STRATEGY_REGISTRY[strategy_name]
            engine = "classic"

        if strategy_cls is None:
            return {
                "strategy_name": strategy_name,
                "engine": engine,
                "class_name": None,
                "source_file": None,
                "source_hash": None,
            }

        source_file = inspect.getsourcefile(strategy_cls)
        source_code = inspect.getsource(strategy_cls)
        relative_file = None
        if source_file:
            path = Path(source_file)
            try:
                relative_file = str(path.relative_to(ROOT_DIR))
            except ValueError:
                relative_file = str(path)

        return {
            "strategy_name": strategy_name,
            "engine": engine,
            "class_name": strategy_cls.__name__,
            "source_file": relative_file,
            "source_hash": hashlib.sha256(source_code.encode("utf-8")).hexdigest(),
            "source_code": source_code,
        }

    def _append_index(self, manifest: Dict[str, Any]) -> None:
        with INDEX_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(manifest, ensure_ascii=False, default=str) + "\n")

    def _write_equity_curve(self, path: Path, report: BacktestReport) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "equity"])
            for date, equity in report.equity_curve.items():
                writer.writerow([date, equity])

    def _write_trades(self, path: Path, report: BacktestReport) -> None:
        if not report.trades:
            return

        with path.open("w", encoding="utf-8", newline="") as f:
            fieldnames = list(report.trades[0].model_dump().keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for trade in report.trades:
                writer.writerow(trade.model_dump())

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    def _read_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_text(self, path: Path, content: str) -> None:
        with path.open("w", encoding="utf-8") as f:
            f.write(content)


_run_store: Optional[BacktestRunStore] = None


def get_run_store() -> BacktestRunStore:
    global _run_store
    if _run_store is None:
        _run_store = BacktestRunStore()
    return _run_store
