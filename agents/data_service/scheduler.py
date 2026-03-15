"""
Data Service Scheduler - 数据定时同步任务

运行方式：
    python -m agents.data_service.scheduler

定时任务：
- 交易日 15:30 - 同步当日 K 线
- 周六 02:00 - 同步股票列表
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/data_service/scheduler.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    from . import get_data_service
    
    logger.info("=" * 50)
    logger.info("数据服务定时同步任务启动")
    logger.info("=" * 50)
    
    # 初始化数据服务
    data_service = get_data_service(
        db_path="data/stock_data.db",
        redis_url="redis://localhost:6379",
        cache_enabled=True,
        auto_sync=False  # 定时任务中手动控制
    )
    
    logger.info("数据服务已初始化")
    
    # 首次全量同步
    logger.info("执行首次全量同步...")
    try:
        await data_service.sync_all(force=True)
        logger.info("首次同步完成")
    except Exception as e:
        logger.error(f"首次同步失败 | error={e}")
    
    # 启动定时任务
    logger.info("启动定时任务循环...")
    
    while True:
        try:
            now = datetime.now()
            
            # 交易日 15:30 - 同步当日 K 线
            if now.hour == 15 and now.minute == 30 and now.weekday() < 5:
                logger.info("定时任务：同步当日 K 线")
                try:
                    await data_service.sync_all(force=False)
                    logger.info("K 线同步完成")
                except Exception as e:
                    logger.error(f"K 线同步失败 | error={e}")
            
            # 周六 02:00 - 同步股票列表
            if now.hour == 2 and now.minute == 0 and now.weekday() == 5:
                logger.info("定时任务：同步股票列表")
                try:
                    await data_service.sync_manager.sync_stock_list()
                    logger.info("股票列表同步完成")
                except Exception as e:
                    logger.error(f"股票列表同步失败 | error={e}")
            
            # 每分钟检查一次
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("定时任务已停止")
            break
        except Exception as e:
            logger.error(f"定时任务执行失败 | error={e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    # 确保日志目录存在
    Path("logs/data_service").mkdir(parents=True, exist_ok=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序已中断")
