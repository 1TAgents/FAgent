"""
Lightweight local security scanning for FAgent CLI diagnostics.

The scanner is intentionally conservative: it reports high-confidence rules
and never includes the matched secret value in command output.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import subprocess
from typing import Iterable


DEFAULT_MAX_FILE_SIZE = 1_000_000

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "fagent_memory",
    "node_modules",
    "venv",
}

EXCLUDED_SUFFIXES = {
    ".db",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".lock",
    ".pdf",
    ".png",
    ".pyc",
    ".sqlite",
    ".webp",
    ".zip",
}

PLACEHOLDER_MARKERS = (
    "<your",
    "<strong-random-string>",
    "changeme",
    "dummy",
    "example",
    "placeholder",
    "replace-me",
    "replace_me",
    "your-api-key",
    "your_api_key",
    "your-key",
    "your-secret",
)


@dataclass(frozen=True)
class ScanRule:
    rule_id: str
    label: str
    severity: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class SecurityFinding:
    path: str
    line: int
    rule_id: str
    label: str
    severity: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScanReport:
    root: str
    scanned_files: int
    findings: list[SecurityFinding]

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "scanned_files": self.scanned_files,
            "findings": [finding.to_dict() for finding in self.findings],
        }


RULES: tuple[ScanRule, ...] = (
    ScanRule(
        "local-home-path",
        "Local home directory path",
        "medium",
        re.compile(r"(?:(?:/Users|/home)/[A-Za-z0-9._-]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)"),
    ),
    ScanRule(
        "openrouter-api-key",
        "OpenRouter API key",
        "high",
        re.compile(r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b"),
    ),
    ScanRule(
        "openai-api-key",
        "OpenAI API key",
        "high",
        re.compile(
            r"\b(?:sk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,}|"
            r"sk-[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}|"
            r"sk-[A-Za-z0-9]{48,})\b"
        ),
    ),
    ScanRule(
        "github-token",
        "GitHub token",
        "high",
        re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{82}|gh[pousr]_[A-Za-z0-9]{36})\b"),
    ),
    ScanRule(
        "aws-access-key",
        "AWS access key",
        "high",
        re.compile(r"\b(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16}\b"),
    ),
    ScanRule(
        "google-api-key",
        "Google API key",
        "high",
        re.compile(r"\bAIza[\w-]{35}\b"),
    ),
    ScanRule(
        "private-key",
        "Private key block",
        "critical",
        re.compile(
            r"-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----"
            r"[\s\S-]{64,}?"
            r"-----END[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----",
            re.IGNORECASE,
        ),
    ),
)


def scan_text(path: str, text: str) -> list[SecurityFinding]:
    """Scan one text blob and return findings without matched values."""
    findings: list[SecurityFinding] = []
    seen: set[tuple[str, int]] = set()
    line_starts = _line_starts(text)
    lines = text.splitlines()

    for rule in RULES:
        for match in rule.pattern.finditer(text):
            line_no = _line_number(line_starts, match.start())
            if line_no <= len(lines) and _is_placeholder_line(lines[line_no - 1]):
                continue
            dedupe_key = (rule.rule_id, line_no)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            findings.append(
                SecurityFinding(
                    path=path,
                    line=line_no,
                    rule_id=rule.rule_id,
                    label=rule.label,
                    severity=rule.severity,
                )
            )

    return findings


def scan_repo(
    root: Path | str,
    *,
    include_untracked: bool = False,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> ScanReport:
    """Scan candidate repository files for high-confidence local leaks."""
    root_path = Path(root).resolve()
    files = list(_candidate_files(root_path, include_untracked=include_untracked))
    findings: list[SecurityFinding] = []
    scanned = 0

    for file_path in files:
        if not _is_scannable_file(root_path, file_path, max_file_size=max_file_size):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue

        scanned += 1
        rel_path = file_path.relative_to(root_path).as_posix()
        findings.extend(scan_text(rel_path, content))

    findings.sort(key=lambda item: (item.path, item.line, item.rule_id))
    return ScanReport(root=".", scanned_files=scanned, findings=findings)


def _candidate_files(root: Path, *, include_untracked: bool) -> Iterable[Path]:
    tracked = _git_files(root, ["ls-files", "-z"])
    if tracked is None:
        yield from _walk_files(root)
        return

    for item in tracked:
        yield root / item

    if include_untracked:
        untracked = _git_files(root, ["ls-files", "-z", "--others", "--exclude-standard"])
        if untracked:
            for item in untracked:
                yield root / item


def _git_files(root: Path, args: list[str]) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    raw = result.stdout.decode("utf-8", errors="ignore")
    return [item for item in raw.split("\0") if item]


def _walk_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def _is_scannable_file(root: Path, path: Path, *, max_file_size: int) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return False

    if any(part in EXCLUDED_DIRS for part in relative_parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    try:
        return path.is_file() and path.stat().st_size <= max_file_size
    except OSError:
        return False


def _is_placeholder_line(line: str) -> bool:
    normalized = line.lower()
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for match in re.finditer("\n", text):
        starts.append(match.end())
    return starts


def _line_number(line_starts: list[int], offset: int) -> int:
    low = 0
    high = len(line_starts)
    while low < high:
        mid = (low + high) // 2
        if line_starts[mid] <= offset:
            low = mid + 1
        else:
            high = mid
    return max(1, low)
