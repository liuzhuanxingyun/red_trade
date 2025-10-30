import talib
import logging

from .utils import get_ohlcv_data  # 相对导入

def ema_atr_filter(exchange, symbol, ema_period, atr_period, multiplier, atr_threshold_pct):
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
    
    返回:
    tuple: (信号类型, ATR值) 或 (None, ATR值)
    """
    try:
        # 获取K线数据
        df = get_ohlcv_data(exchange, symbol, timeframe='15m')
        
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