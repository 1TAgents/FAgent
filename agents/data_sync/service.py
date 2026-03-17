"""
Data Sync Service - 数据同步服务

独立服务，负责缓慢但稳定地缓存历史数据到本地

启动命令:
    PYTHONPATH=. python3 -m uvicorn agents.data_sync.service:app --reload --port 8003

API:
    GET  /status          - 同步状态
    POST /sync/stocks     - 同步股票列表
    POST /sync/klines     - 同步单只股票 K 线
    POST /sync/historical - 后台同步历史数据
    GET  /stats           - 数据统计
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uvicorn

from agents.data_service import get_data_service
from agents.common.market.dataset_manager import DatasetManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 全局状态 ====================

class SyncState:
    """同步状态管理"""
    
    def __init__(self):
        self.is_syncing = False
        self.current_task: Optional[str] = None
        self.total_stocks = 0
        self.synced_stocks = 0
        self.last_sync_time: Optional[datetime] = None
        self.errors: List[str] = []
        self.start_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_syncing": self.is_syncing,
            "current_task": self.current_task,
            "progress": f"{self.synced_stocks}/{self.total_stocks}" if self.total_stocks > 0 else "0/0",
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "errors_count": len(self.errors),
            "recent_errors": self.errors[-5:],
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600 if self.start_time else 0
        }


sync_state = SyncState()
data_service = None
dataset_manager = None


# ==================== 应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global data_service, dataset_manager
    
    logger.info("=" * 50)
    logger.info("FAgent Data Sync Service 启动中...")
    
    # 初始化数据服务
    data_service = get_data_service(
        db_path="data/stock_data.db",
        redis_url="redis://localhost:6379",
        cache_enabled=True,
        auto_sync=False  # 手动控制同步
    )
    logger.info("数据服务初始化完成")
    
    # 初始化数据集管理
    dataset_manager = DatasetManager()
    logger.info("数据集管理初始化完成")
    
    sync_state.start_time = datetime.now()
    
    logger.info("服务已就绪")
    logger.info("=" * 50)
    
    yield
    
    # 关闭时
    logger.info("Data Sync Service 关闭中...")


app = FastAPI(
    title="FAgent Data Sync Service",
    description="数据同步服务 - 缓慢但稳定地缓存历史数据",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== 数据模型 ====================

class SyncRequest(BaseModel):
    symbol: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 100


class SyncResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ==================== API 端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "sync_state": sync_state.to_dict()
    }


@app.get("/status")
async def get_status():
    """获取同步状态"""
    return sync_state.to_dict()


@app.post("/sync/stocks", response_model=SyncResponse)
async def sync_stocks():
    """
    同步股票列表
    
    从 AKShare 获取最新的 A 股列表并保存到数据库
    """
    try:
        logger.info("开始同步股票列表...")
        sync_state.is_syncing = True
        sync_state.current_task = "sync_stocks"
        
        # 调用数据服务同步股票列表
        result = await data_service.sync_stock_list()
        
        sync_state.last_sync_time = datetime.now()
        sync_state.is_syncing = False
        sync_state.current_task = None
        
        logger.info(f"股票列表同步完成 | count={result.get('count', 0)}")
        
        return SyncResponse(
            success=True,
            message="股票列表同步完成",
            data=result
        )
        
    except Exception as e:
        logger.error(f"同步股票列表失败 | error={e}")
        sync_state.is_syncing = False
        sync_state.errors.append(f"{datetime.now().isoformat()}: {str(e)}")
        
        return SyncResponse(
            success=False,
            message=str(e)
        )


@app.post("/sync/klines", response_model=SyncResponse)
async def sync_klines(request: SyncRequest):
    """
    同步单只股票 K 线数据
    
    Args:
        symbol: 股票代码（可选，不传则同步沪深 300 成分股）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        limit: 同步条数限制
    """
    try:
        if not request.symbol:
            # 同步沪深 300 成分股
            return await sync_hs300_klines(request.limit)
        
        logger.info(f"开始同步 K 线 | symbol={request.symbol}")
        sync_state.is_syncing = True
        sync_state.current_task = f"sync_kline_{request.symbol}"
        
        # 同步 K 线
        result = await data_service.sync_klines(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit
        )
        
        sync_state.synced_stocks += 1
        sync_state.last_sync_time = datetime.now()
        sync_state.is_syncing = False
        sync_state.current_task = None
        
        logger.info(f"K 线同步完成 | symbol={request.symbol} | count={result.get('count', 0)}")
        
        return SyncResponse(
            success=True,
            message=f"{request.symbol} K 线同步完成",
            data=result
        )
        
    except Exception as e:
        logger.error(f"同步 K 线失败 | symbol={request.symbol} | error={e}")
        sync_state.is_syncing = False
        sync_state.errors.append(f"{datetime.now().isoformat()}: {str(e)}")
        
        return SyncResponse(
            success=False,
            message=str(e)
        )


@app.post("/sync/historical", response_model=SyncResponse)
async def sync_historical_background(background_tasks: BackgroundTasks):
    """
    后台同步历史数据
    
    在后台缓慢同步全量股票的历史数据
    速度：1 只股票/秒，避免触发限流
    """
    try:
        if sync_state.is_syncing:
            raise HTTPException(status_code=400, detail="已有同步任务进行中")
        
        logger.info("启动后台历史数据同步...")
        
        # 在后台执行
        background_tasks.add_task(run_historical_sync)
        
        return SyncResponse(
            success=True,
            message="后台同步任务已启动"
        )
        
    except Exception as e:
        logger.error(f"启动后台同步失败 | error={e}")
        return SyncResponse(
            success=False,
            message=str(e)
        )


@app.get("/stats")
async def get_stats():
    """获取数据统计"""
    try:
        stats = data_service.get_stats()
        
        # 添加数据库大小
        import os
        db_path = "data/stock_data.db"
        db_size_mb = 0
        if os.path.exists(db_path):
            db_size_mb = os.path.getsize(db_path) / 1024 / 1024
        
        stats["database_size_mb"] = round(db_size_mb, 2)
        stats["sync_state"] = sync_state.to_dict()
        
        return stats
        
    except Exception as e:
        logger.error(f"获取统计信息失败 | error={e}")
        return {"error": str(e)}


# ==================== 后台任务 ====================

async def sync_hs300_klines(limit: int = 100):
    """同步沪深 300 成分股 K 线"""
    try:
        # 获取沪深 300 成分股
        hs300_stocks = await dataset_manager.get_hs300_stocks()
        
        if not hs300_stocks:
            # 从 AKShare 获取
            import akshare as ak
            df = ak.index_stock_cons(symbol="000300")
            hs300_stocks = df["品种代码"].tolist() if not df.empty else []
        
        total = len(hs300_stocks)
        synced = 0
        
        for symbol in hs300_stocks[:limit]:
            try:
                await data_service.sync_klines(symbol=symbol, limit=1000)
                synced += 1
                sync_state.synced_stocks = synced
                sync_state.total_stocks = total
                
                # 限速：1 只/秒
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"同步 {symbol} 失败 | error={e}")
                sync_state.errors.append(f"{symbol}: {str(e)}")
        
        return SyncResponse(
            success=True,
            message=f"沪深 300 同步完成 | {synced}/{total}",
            data={"synced": synced, "total": total}
        )
        
    except Exception as e:
        logger.error(f"同步沪深 300 失败 | error={e}")
        return SyncResponse(
            success=False,
            message=str(e)
        )


async def run_historical_sync():
    """
    运行历史数据同步
    
    策略：
    1. 优先同步沪深 300 成分股
    2. 然后同步中证 500
    3. 最后同步其他股票
    4. 速度：1 只/秒
    """
    sync_state.is_syncing = True
    sync_state.current_task = "historical_sync"
    sync_state.start_time = datetime.now()
    
    try:
        import akshare as ak
        
        # 1. 获取所有 A 股列表
        logger.info("获取 A 股列表...")
        stocks_df = ak.stock_info_a_code_name()
        all_stocks = stocks_df["code"].tolist() if not stocks_df.empty else []
        
        # 2. 获取沪深 300 成分股（优先）
        logger.info("获取沪深 300 成分股...")
        try:
            hs300_df = ak.index_stock_cons(symbol="000300")
            hs300_stocks = hs300_df["品种代码"].tolist() if not hs300_df.empty else []
        except Exception:
            hs300_stocks = []
        
        # 3. 优先同步沪深 300
        priority_stocks = list(set(hs300_stocks) & set(all_stocks))
        other_stocks = list(set(all_stocks) - set(priority_stocks))
        
        logger.info(f"优先同步：{len(priority_stocks)} 只，其他：{len(other_stocks)} 只")
        
        # 4. 开始同步
        all_stocks_ordered = priority_stocks + other_stocks
        total = len(all_stocks_ordered)
        synced = 0
        failed = 0
        
        for i, symbol in enumerate(all_stocks_ordered):
            sync_state.synced_stocks = synced
            sync_state.total_stocks = total
            sync_state.current_task = f"syncing_{symbol} ({i+1}/{total})"
            
            try:
                # 同步最近 1 年数据（快速缓存）
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                await data_service.sync_klines(
                    symbol=symbol,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                    limit=500
                )
                
                synced += 1
                
                # 每 100 只记录一次
                if synced % 100 == 0:
                    logger.info(f"已同步 {synced}/{total} 只股票")
                
            except Exception as e:
                failed += 1
                logger.warning(f"同步 {symbol} 失败 | error={e}")
                
                if failed % 10 == 0:
                    sync_state.errors.append(f"批量失败：{failed} 只")
            
            # 限速：1 只/秒（避免触发 API 限流）
            await asyncio.sleep(1)
            
            # 每同步 100 只，休息 10 秒
            if synced % 100 == 0:
                logger.info("休息 10 秒...")
                await asyncio.sleep(10)
        
        sync_state.last_sync_time = datetime.now()
        logger.info(f"历史数据同步完成 | 成功：{synced}, 失败：{failed}")
        
    except Exception as e:
        logger.error(f"历史数据同步失败 | error={e}")
        sync_state.errors.append(f"历史同步失败：{str(e)}")
    
    finally:
        sync_state.is_syncing = False
        sync_state.current_task = None


# ==================== 主程序 ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
