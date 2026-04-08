"""
FAgent CLI - FAgent 股票助手的命令行界面

使用示例:
    python fagent_cli.py --help
    python fagent_cli.py --version
"""

import click
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .commands.session import session
from .commands.message import message
from .commands import memory as memory_commands

# 创建全局 console 实例
console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="FAgent CLI")
def cli():
    """📊 FAgent CLI - FAgent 股票助手的命令行界面
    
    用于测试和管理 FAgent Memory 系统。
    
    \b
    示例:
        fagent session new          创建新会话
        fagent message send "你好"   发送消息
        fagent memory overview      查看会话概览
        fagent test all             运行所有测试
    """
    pass


# 注册命令组
cli.add_command(session)
cli.add_command(message)
cli.add_command(memory_commands.memory)


@cli.command()
def hello():
    """测试命令 - 显示欢迎信息"""
    console.print(Panel(
        "[bold blue]欢迎使用 FAgent CLI![/bold blue]\n\n"
        "这是一个用于测试 Memory 系统的命令行工具。\n\n"
        "使用 [cyan]fagent --help[/cyan] 查看所有可用命令。",
        title="📊 FAgent",
        subtitle=f"版本 {__version__}"
    ))


def main():
    """CLI 入口点"""
    cli()


if __name__ == '__main__':
    main()
