"""
日志配置模块 - 使用 loguru

使用方式:
    from backend.core.logging import logger
    
    logger.info("信息日志")
    logger.debug("调试日志")
    logger.warning("警告日志")
    logger.error("错误日志")
"""
import sys
import os
from pathlib import Path
from loguru import logger

# 移除默认的 handler
logger.remove()

# 日志目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 简洁格式（用于控制台）
CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | "
    "<level>{message}</level>"
)

# 获取日志级别（从环境变量，默认 INFO）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 控制台输出
logger.add(
    sys.stderr,
    format=CONSOLE_FORMAT,
    level=LOG_LEVEL,
    colorize=True,
)

# 文件输出 - 所有日志
logger.add(
    LOG_DIR / "app_{time:YYYY-MM-DD}.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="7 days",  # 保留 7 天
    compression="zip",  # 压缩旧日志
    encoding="utf-8",
)

# 文件输出 - 错误日志
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 导出 logger
__all__ = ["logger"]

