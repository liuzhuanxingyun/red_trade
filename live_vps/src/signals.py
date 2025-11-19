import talib
import logging
from datetime import datetime, timezone
import pandas as pd
import time
from .utils import get_ohlcv_data, is_trading_allowed  # 添加导入

def ema_atr_filter(exchange, symbol, ema_period, atr_period, multiplier, atr_threshold_pct, forbidden_hours=None, timeframe='15m'):
    """
    生成EMA-ATR过滤信号。
    
    计算EMA通道和ATR，检查波动率和突破条件。
    
    参数:
    exchange: ccxt交易所对象
    symbol: 交易对
    ema_period: EMA周期
    atr_period: ATR周期
    multiplier: 通道倍数
    atr_threshold_pct: ATR阈值百分比
    forbidden_hours: 禁止交易时段列表，如 [[23,2], [12,17]]，默认None（允许所有时段）
    timeframe: K线时间框架，如 '15m', '30m', '1h'，默认 '15m'
    
    返回:
    tuple: (信号类型, ATR值) 或 (None, ATR值)
    """
    if forbidden_hours is None:
        forbidden_hours = []  # 默认允许所有时段
    
    try:
        # 检查时段过滤器
        current_hour = datetime.now(timezone.utc).hour
        if not is_trading_allowed(current_hour, forbidden_hours):
            logging.info("当前时段禁止交易。")
            return None, None

        max_retries = 100
        for attempt in range(max_retries):
            df = get_ohlcv_data(exchange, symbol, timeframe=timeframe)
            duration_seconds = exchange.parse_timeframe(timeframe)
            now_ts = time.time()
            expected_last_ts = (int(now_ts // duration_seconds) - 1) * duration_seconds
            expected_prev_ts = (int(now_ts // duration_seconds) - 2) * duration_seconds
            last_ts = int(df.index[-2].timestamp())
            prev_ts = int(df.index[-3].timestamp())
            if last_ts == expected_last_ts and prev_ts == expected_prev_ts:
                break
            else:
                logging.warning(
                    f"K线数据时间不匹配，需重新获取。期望: {pd.to_datetime(expected_prev_ts, unit='s')} 和 {pd.to_datetime(expected_last_ts, unit='s')}，实际: {df.index[-3]} 和 {df.index[-2]}"
                )
                time.sleep(2)
        else:
            logging.error("重试次数过多，仍未获取到匹配时间的数据。")
            return None, None

        # 添加调试日志：检查数据是否更新（一一对应输出上上根和上一根K线的时间和成交量）
        for i, (ts, vol) in enumerate(zip(df.index[-3:-1], df['volume'].iloc[-3:-1]), 1):
            logging.info(f"K线{i}: 时间 {ts}, 成交量 {vol}")
        
        # 计算技术指标
        df['ema'] = talib.EMA(df['close'], timeperiod=ema_period)
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=atr_period)
        df['upper_band'] = df['ema'] + (multiplier * df['atr'])
        df['lower_band'] = df['ema'] - (multiplier * df['atr'])
        
        atr_value = df['atr'].iloc[-2]  # 获取ATR值

        # 获取价格数据（使用前两根已确定的k线及其对应的通道值）
        last_close = df['close'].iloc[-2]  # 上一根k线的收盘价
        prev_close = df['close'].iloc[-3]  # 上上根k线的收盘价
        last_upper_band = df['upper_band'].iloc[-2]  # 上一根k线的上轨
        last_lower_band = df['lower_band'].iloc[-2]  # 上一根k线的下轨
        prev_upper_band = df['upper_band'].iloc[-3]  # 上上根k线的上轨
        prev_lower_band = df['lower_band'].iloc[-3]  # 上上根k线的下轨

        # 检查是否已有持仓
        positions = exchange.fetch_positions()
        has_position = any(pos['symbol'] == symbol and pos['contracts'] != 0 for pos in positions)
        if has_position:
            logging.info("已有持仓，跳过开仓信号。")
            return None, atr_value
        
        # 波动率过滤器
        atr_pct = atr_value / last_close
        if atr_pct < atr_threshold_pct:
            logging.info(f"波动率过低 ({atr_pct:.4f} < {atr_threshold_pct})，跳过交易。")
            return None, atr_value
        
        # 新增：成交量过滤器
        # 检查上一根和上上根K线颜色一致（都是上涨或都是下跌）
        last_color = df['close'].iloc[-2] > df['open'].iloc[-2]  # True: 绿（上涨），False: 红（下跌）
        prev_color = df['close'].iloc[-3] > df['open'].iloc[-3]
        if last_color != prev_color:
            logging.info("上一根和上上根K线颜色不一致，跳过交易。")
            return None, atr_value
        
        # 检查上一根K线成交量大于上上根K线成交量
        last_volume = df['volume'].iloc[-2]
        prev_volume = df['volume'].iloc[-3]
        if last_volume <= prev_volume:
            logging.info(f"上一根K线成交量 ({last_volume}) 不大于上上根K线成交量 ({prev_volume})，跳过交易。")
            return None, atr_value
        
        # 上轨突破条件（上上根在通道内，上一根突破上轨）
        upper_breakout = (prev_close <= prev_upper_band) and (last_close > last_upper_band)
        
        # 下轨突破条件（上上根在通道内，上一根突破下轨）
        lower_breakout = (prev_close >= prev_lower_band) and (last_close < last_lower_band)
        
        if upper_breakout:
            return 'upper_breakout', atr_value
        
        elif lower_breakout:
            return 'lower_breakout', atr_value
        
        return None, atr_value  # 无信号时也返回 atr_value
        
    except Exception as e:
        logging.error(f"策略信号生成失败: {e}")
        return None, None