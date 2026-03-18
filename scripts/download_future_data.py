#!/usr/bin/env python3
"""
期货主力合约数据下载脚本

批量下载期货品种的主力合约历史数据，保存到数据库

用法:
    python scripts/download_future_data.py
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.data.future_source import FutureDataSource
from agents.data.future_database import FutureDatabase
from agents.data.models import Exchange, Interval

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 期货品种列表（主力合约）
FUTURE_SYMBOLS = [
    # 金融期货
    "IF",  # 沪深 300 股指期货
    "IC",  # 中证 500 股指期货
    "IH",  # 上证 50 股指期货
    
    # 金属
    "CU",  # 沪铜
    "AL",  # 沪铝
    "ZN",  # 沪锌
    "AU",  # 沪金
    "AG",  # 沪银
    "RB",  # 螺纹钢
    "HC",  # 热卷
    
    # 能源
    "SC",  # 原油
    "FU",  # 燃油
    
    # 农产品
    "M",   # 豆粕
    "Y",   # 豆油
    "P",   # 棕榈油
    "C",   # 玉米
    
    # 化工
    "SR",  # 白糖
    "CF",  # 棉花
    "MA",  # 甲醇
    "FG",  # 玻璃
    "SA",  # 纯碱
]


def download_future_data(
    symbols: List[str] = None,
    start_date: str = "20200101",
    end_date: str = None,
    period: str = "daily"
):
    """
    下载期货主力合约数据
    
    Args:
        symbols: 品种列表（默认全部）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期
        period: 周期（daily/weekly/monthly）
    """
    if symbols is None:
        symbols = FUTURE_SYMBOLS
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
    
    logger.info(f"开始下载期货数据 | symbols={len(symbols)}, period={period}")
    logger.info(f"日期范围：{start_date} - {end_date}")
    
    # 初始化
    data_source = FutureDataSource()
    database = FutureDatabase()
    
    # 统计
    total_symbols = len(symbols)
    success_count = 0
    failed_symbols = []
    
    # 逐个下载
    for i, symbol in enumerate(symbols, 1):
        try:
            logger.info(f"[{i}/{total_symbols}] 下载 {symbol}...")
            
            # 获取交易所
            exchange = data_source.get_exchange(symbol)
            
            # 下载主力合约数据
            df = data_source.get_main_contract_klines(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                logger.warning(f"{symbol} 无数据")
                failed_symbols.append(symbol)
                continue
            
            # 保存到数据库
            database.save_bars_df(df, symbol, exchange, data_source.parse_period(period))
            
            # 更新覆盖信息
            database.update_coverage(
                symbol=symbol,
                exchange=exchange,
                interval=data_source.parse_period(period),
                bar_count=len(df)
            )
            
            # 保存合约信息
            contract_info = data_source.get_contract_info(symbol)
            database.save_contract_info(contract_info.to_dict())
            
            logger.info(f"✓ {symbol} 完成 | rows={len(df)}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"✗ {symbol} 失败 | error={e}")
            failed_symbols.append(symbol)
    
    # 汇总报告
    logger.info("=" * 60)
    logger.info(f"下载完成 | 成功={success_count}/{total_symbols}")
    
    if failed_symbols:
        logger.warning(f"失败的品种：{', '.join(failed_symbols)}")
    
    # 显示数据覆盖
    logger.info("\n数据覆盖统计:")
    for symbol in symbols:
        if symbol not in failed_symbols:
            exchange = data_source.get_exchange(symbol)
            coverage = database.get_data_coverage(
                symbol=symbol,
                exchange=exchange,
                interval=data_source.parse_period(period)
            )
            
            if coverage:
                logger.info(f"  {symbol}: {coverage['bar_count']} 条 "
                           f"({coverage['start_date'][:10]} ~ {coverage['end_date'][:10]})")


def download_all_periods(
    symbols: List[str] = None,
    start_date: str = "20200101"
):
    """
    下载所有周期的数据
    
    Args:
        symbols: 品种列表
        start_date: 开始日期
    """
    if symbols is None:
        symbols = FUTURE_SYMBOLS
    
    periods = [
        ("daily", "日线"),
        ("weekly", "周线"),
        ("1m", "1 分钟"),
        ("5m", "5 分钟"),
    ]
    
    for period, period_name in periods:
        logger.info(f"\n{'='*60}")
        logger.info(f"开始下载 {period_name} 数据")
        logger.info(f"{'='*60}\n")
        
        download_future_data(
            symbols=symbols,
            start_date=start_date,
            period=period
        )


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载期货主力合约数据')
    
    parser.add_argument(
        '--symbols', '-s',
        nargs='+',
        default=None,
        help='品种列表（默认下载全部）'
    )
    
    parser.add_argument(
        '--start',
        type=str,
        default="20200101",
        help='开始日期（YYYYMMDD）'
    )
    
    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='结束日期（默认今天）'
    )
    
    parser.add_argument(
        '--period', '-p',
        type=str,
        default="daily",
        choices=['daily', 'weekly', 'monthly', '1m', '5m', '15m', '30m', '60m'],
        help='周期（默认日线）'
    )
    
    parser.add_argument(
        '--all-periods',
        action='store_true',
        help='下载所有周期'
    )
    
    args = parser.parse_args()
    
    try:
        if args.all_periods:
            download_all_periods(
                symbols=args.symbols,
                start_date=args.start
            )
        else:
            download_future_data(
                symbols=args.symbols,
                start_date=args.start,
                end_date=args.end,
                period=args.period
            )
        
        logger.info("\n✓ 所有任务完成")
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断")
    except Exception as e:
        logger.error(f"\n✗ 程序异常：{e}")
        raise


if __name__ == "__main__":
    main()
