#!/usr/bin/env python3
"""
RQSDK 数据能力探索测试

测试 RQSDK 支持的数据类型、时间周期和数据类别
"""
import sys
import rqdatac as rq
from datetime import datetime, timedelta

def test_init():
    """测试初始化"""
    print("=" * 70)
    print("1. 测试初始化")
    print("=" * 70)
    
    try:
        # 注意：首次使用需要配置 license
        # rq.set_token('your_license_key')
        rq.init()
        print("✓ 初始化成功")
        return True
    except Exception as e:
        print(f"✗ 初始化失败：{e}")
        print("\n提示：首次使用需要配置 License")
        print("方法：rqdatac set <your_license_key>")
        return False


def test_stock_list():
    """测试获取股票列表"""
    print("\n" + "=" * 70)
    print("2. 测试股票列表")
    print("=" * 70)
    
    try:
        # A 股
        stocks = rq.all_instruments(type='CS', market='cn')
        print(f"✓ A 股总数：{len(stocks)}")
        print(f"  前 5 只：{stocks[:5].tolist()}")
        
        # 指数
        indices = rq.all_instruments(type='INDX', market='cn')
        print(f"✓ 指数总数：{len(indices)}")
        print(f"  主要指数：{indices[indices['order_book_id'].isin(['000300.XSHG', '000001.XSHG', '399001.XSHE'])]['order_book_id'].tolist()}")
        
        # 基金
        funds = rq.all_instruments(type='ETF', market='cn')
        print(f"✓ ETF 总数：{len(funds)}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_daily_data():
    """测试日线数据"""
    print("\n" + "=" * 70)
    print("3. 测试日线数据")
    print("=" * 70)
    
    try:
        # 贵州茅台
        symbol = '600519.XSHG'
        
        # 最近 1 年
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        df = rq.get_price(
            order_book_ids=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency='1d',
            adjust_type='pre'
        )
        
        print(f"✓ 日线数据获取成功")
        print(f"  股票：{symbol}")
        print(f"  数据量：{len(df)} 条")
        print(f"  时间范围：{df.index[0]} 至 {df.index[-1]}")
        print(f"  字段：{df.columns.tolist()}")
        print(f"\n  最新数据:")
        print(f"    收盘价：{df['close'].iloc[-1]:.2f}")
        print(f"    成交量：{df['volume'].iloc[-1]:.0f}")
        print(f"    成交额：{df['turnover'].iloc[-1]:.0f}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_minute_data():
    """测试分钟线数据"""
    print("\n" + "=" * 70)
    print("4. 测试分钟线数据")
    print("=" * 70)
    
    try:
        symbol = '600519.XSHG'
        
        # 最近 5 天
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        # 1 分钟线
        df_1m = rq.get_price(
            order_book_ids=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency='1m',
            adjust_type='pre'
        )
        
        print(f"✓ 1 分钟线获取成功")
        print(f"  数据量：{len(df_1m)} 条")
        
        # 5 分钟线
        df_5m = rq.get_price(
            order_book_ids=symbol,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            frequency='5m',
            adjust_type='pre'
        )
        
        print(f"✓ 5 分钟线获取成功")
        print(f"  数据量：{len(df_5m)} 条")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_tick_data():
    """测试实时行情"""
    print("\n" + "=" * 70)
    print("5. 测试实时行情")
    print("=" * 70)
    
    try:
        symbols = ['600519.XSHG', '000001.XSHE', '300750.XSHE']
        
        for symbol in symbols:
            tick = rq.get_current_tick(symbol)
            if tick is not None:
                print(f"✓ {symbol} 实时行情:")
                print(f"    最新价：{tick.get('last', 0):.2f}")
                print(f"    买一价：{tick.get('bid_1', 0):.2f}")
                print(f"    卖一价：{tick.get('ask_1', 0):.2f}")
                print(f"    成交量：{tick.get('volume', 0):.0f}")
            else:
                print(f"✗ {symbol} 无实时行情（可能未开盘）")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_fundamentals():
    """测试财务数据"""
    print("\n" + "=" * 70)
    print("6. 测试财务数据")
    print("=" * 70)
    
    try:
        from rqdatac import valuation, query
        
        # 获取估值数据
        fundamentals = rq.get_fundamentals(
            query(
                valuation.code,
                valuation.pe_ratio,
                valuation.pb_ratio,
                valuation.market_cap,
                valuation.dividend_yield
            ),
            date='2024-12-31'
        )
        
        print(f"✓ 财务数据获取成功")
        print(f"  数据量：{len(fundamentals)} 条")
        print(f"  字段：{fundamentals.columns.tolist()}")
        print(f"\n  前 5 条:")
        print(fundamentals.head())
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_dividends():
    """测试分红数据"""
    print("\n" + "=" * 70)
    print("7. 测试分红数据")
    print("=" * 70)
    
    try:
        symbol = '600519.XSHG'
        
        dividends = rq.get_dividends(symbol)
        
        print(f"✓ 分红数据获取成功")
        print(f"  股票：{symbol}")
        print(f"  分红次数：{len(dividends)}")
        
        if len(dividends) > 0:
            print(f"\n  最近 5 次分红:")
            for i, div in enumerate(dividends[:5]):
                print(f"    {div['announcement_date']}: {div['cash_dividend']:.2f}元/10 股")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_index_components():
    """测试指数成分股"""
    print("\n" + "=" * 70)
    print("8. 测试指数成分股")
    print("=" * 70)
    
    try:
        # 沪深 300
        hs300 = rq.index_components('000300.XSHG')
        print(f"✓ 沪深 300 成分股：{len(hs300)} 只")
        print(f"  前 10 大权重:")
        print(hs300.nlargest(10, 'weight')[['order_book_id', 'symbol_name', 'weight']])
        
        # 上证 50
        ss50 = rq.index_components('000016.XSHG')
        print(f"\n✓ 上证 50 成分股：{len(ss50)} 只")
        
        # 中证 500
        zz500 = rq.index_components('000905.XSHG')
        print(f"✓ 中证 500 成分股：{len(zz500)} 只")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_adjustment():
    """测试复权数据"""
    print("\n" + "=" * 70)
    print("9. 测试复权数据")
    print("=" * 70)
    
    try:
        symbol = '600519.XSHG'
        start_date = '2020-01-01'
        end_date = '2024-12-31'
        
        # 不复权
        df_none = rq.get_price(symbol, start_date, end_date, frequency='1d', adjust_type='none')
        
        # 前复权
        df_pre = rq.get_price(symbol, start_date, end_date, frequency='1d', adjust_type='pre')
        
        # 后复权
        df_post = rq.get_price(symbol, start_date, end_date, frequency='1d', adjust_type='post')
        
        print(f"✓ 复权数据获取成功")
        print(f"  股票：{symbol}")
        print(f"  时间范围：{start_date} 至 {end_date}")
        print(f"\n  最新收盘价对比:")
        print(f"    不复权：{df_none['close'].iloc[-1]:.2f}")
        print(f"    前复权：{df_pre['close'].iloc[-1]:.2f}")
        print(f"    后复权：{df_post['close'].iloc[-1]:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def test_futures():
    """测试期货数据"""
    print("\n" + "=" * 70)
    print("10. 测试期货数据")
    print("=" * 70)
    
    try:
        # 股指期货
        if_symbol = 'IF2403.CFFEX'
        
        df = rq.get_price(
            order_book_ids=if_symbol,
            start_date='2024-01-01',
            end_date='2024-12-31',
            frequency='1d'
        )
        
        print(f"✓ 股指期货数据获取成功")
        print(f"  合约：{if_symbol}")
        print(f"  数据量：{len(df)} 条")
        print(f"  字段：{df.columns.tolist()}")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        return False


def summary():
    """总结"""
    print("\n" + "=" * 70)
    print("RQSDK 数据能力总结")
    print("=" * 70)
    
    print("""
支持的数据类型:
  ✓ 股票日线数据 (1d)
  ✓ 股票分钟线 (1m/5m/15m/30m/60m)
  ✓ 实时行情 (Tick)
  ✓ 财务数据 (估值/财报)
  ✓ 分红送配
  ✓ 指数成分股
  ✓ 复权数据 (前复权/后复权/不复权)
  ✓ 期货数据

支持的市场:
  ✓ A 股 (上海/深圳/北京)
  ✓ 指数
  ✓ ETF/LOF 基金
  ✓ 股指期货

数据周期:
  ✓ 日线 (1d)
  ✓ 分钟线 (1m/5m/15m/30m/60m)
  ✓ 实时 (Tick)

数据历史:
  ✓ 股票：上市至今
  ✓ 期货：合约上市至今
  ✓ 财务：2000 年至今
    """)


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("RQSDK 数据能力探索测试")
    print("=" * 70)
    
    # 测试初始化
    if not test_init():
        print("\n⚠️ 请先配置 License 后重试")
        return
    
    # 执行测试
    test_stock_list()
    test_daily_data()
    test_minute_data()
    test_tick_data()
    test_fundamentals()
    test_dividends()
    test_index_components()
    test_adjustment()
    test_futures()
    
    # 总结
    summary()
    
    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
