# coding: gbk
import talib

def init(ContextInfo):
    C = ContextInfo
    # 从主界面获取当前交易品种
    C.stock = C.stockcode + '.' + C.market
    # EMA 周期
    C.ema_short = 9
    C.ema_long  = 20
    # 当前持仓手数
    C.position = 0
    # 使用策略配置中选择的资金账号
    C.account  = C.accountid  # 资金账号配置项 

def after_init(ContextInfo):
    C = ContextInfo
    # 取该品种全部日线收盘价
    data = C.get_market_data_ex(['close'], [C.stock],
                                period='1d', subscribe=False)
    df = data[C.stock]
    # 记录起止日期
    C.start_date = df.index[0]
    C.end_date   = df.index[-1]
    # 1) 打印基础范围
    C.log.info(f"{C.stock} 日线从 {C.start_date.date()} 到 {C.end_date.date()}")  

    # 2) 获取区间内所有应有的交易日
    start_str = C.start_date.strftime('%Y%m%d')
    end_str   = C.end_date.strftime('%Y%m%d')
    # count 参数此时无效，period 用 '1d' 表示日线
    trade_days = C.get_trading_dates(C.stock, start_str, end_str, 0, '1d')
    total_days = len(trade_days)
    actual_days = len(df)
    missing_days = total_days - actual_days

    # 3) 打印交易日统计
    if missing_days > 0:
        # 找出到底缺了哪些日期
        df_dates = set(d.strftime('%Y%m%d') for d in df.index)
        missed = sorted(set(trade_days) - df_dates)
        C.log.info(f"应有交易日共 {total_days} 天，实际获取 {actual_days} 条，缺失 {missing_days} 条；缺失日期：{missed}")
    else:
        C.log.info(f"交易日完整，共 {total_days} 天，无缺失")  :contentReference[oaicite:1]{index=1}


def handlebar(ContextInfo):
    C = ContextInfo
    # 仅在最新日线收尾时执行
    if not C.is_last_bar():
        return

    # 获取最近 ema_long+1 根日线收盘价
    data = C.get_market_data_ex(['close'], [C.stock],
                                period='1d', subscribe=False,
                                count=C.ema_long+1)
    close = data[C.stock]['close'].values

    # 计算 EMA
    ema_short = talib.EMA(close, timeperiod=C.ema_short)
    ema_long  = talib.EMA(close, timeperiod=C.ema_long)

    # 昨日 EMA 对比，判断金叉/死叉
    prev_short, prev_long = ema_short[-2], ema_long[-2]
    curr_short, curr_long = ema_short[-1], ema_long[-1]
    last_price = round(close[-1], 2)

    # 金叉：短期线上穿长期线 → 全仓买入
    if prev_short < prev_long and curr_short > curr_long:
        # 计算可用资金与买入股数
        avail = C.get_account_available(C.account)
        vol   = int(avail / last_price)
        if vol > 0:
            # opType=48(买入)，orderType=0(按股数)，prType=1(限价)，quickTrade=1(快速)
            C.passorder(48, 0, C.account, C.stock,
                        1, last_price, vol,
                        'EMA金叉买入', 1, '', C)
            C.position = vol

    # 死叉：短期线下穿长期线 → 全卖
    elif prev_short > prev_long and curr_short < curr_long:
        if C.position > 0:
            C.passorder(49, 0, C.account, C.stock,
                        1, last_price, C.position,
                        'EMA死叉卖出', 1, '', C)
            C.position = 0
