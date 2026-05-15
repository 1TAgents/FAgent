"""
Doctor commands for local FAgent diagnostics.
"""

from __future__ import annotations

from pathlib import Path
import json

import click
from rich.console import Console
from rich.table import Table

from src.cli.security_scan import scan_repo, scan_staged


console = Console()


@click.group()
def doctor():
    """诊断命令 - 检查本地配置、仓库安全与运行准备度"""
    pass


@doctor.command("security-scan")
@click.option(
    "--include-untracked",
    is_flag=True,
    help="同时扫描未跟踪但未被 .gitignore 忽略的文件",
)
@click.option("--json", "json_output", is_flag=True, help="输出 JSON，便于 CI 或脚本使用")
@click.option("--staged", is_flag=True, help="只扫描 git 暂存区中的内容")
@click.option(
    "--root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    hidden=True,
)
def doctor_security_scan(
    include_untracked: bool,
    json_output: bool,
    staged: bool,
    root: Path | None,
):
    """扫描本地路径、API key、token 和私钥等明显风险"""
    if staged and include_untracked:
        raise click.UsageError("--staged 不能和 --include-untracked 同时使用")

    scan_root = root or Path.cwd()
    report = (
        scan_staged(scan_root)
        if staged
        else scan_repo(scan_root, include_untracked=include_untracked)
    )

    if json_output:
        click.echo(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    elif report.ok:
        console.print(
            f"[green]安全扫描通过[/green]，已扫描 {report.scanned_files} 个文件。"
        )
    else:
        table = Table(title="FAgent 安全扫描发现", show_header=True)
        table.add_column("级别", style="red")
        table.add_column("规则", style="cyan")
        table.add_column("位置", style="white")

        for finding in report.findings:
            table.add_row(
                finding.severity,
                finding.rule_id,
                f"{finding.path}:{finding.line}",
            )

        console.print(table)
        console.print(
            f"\n[red]发现 {len(report.findings)} 个风险。[/red]"
            "输出不会显示命中的敏感值，请打开对应文件清理后重试。"
        )

    if not report.ok:
        raise click.exceptions.Exit(1)
