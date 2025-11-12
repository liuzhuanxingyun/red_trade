import logging

def set_stop_loss_and_take_profit(exchange, SYMBOL, signal, entry_price, sl_price, tp_price, actual_size, TP_MODE, is_simulation=False):
    """
    设置止损和止盈订单。
    
    根据信号类型和TP_MODE创建相应的止损和止盈订单。
    
    参数:
    exchange: ccxt交易所对象
    SYMBOL: 交易对
    signal: 信号类型 ('long_entry' 或 'short_entry')
    entry_price: 入场价格
    sl_price: 止损价格
    tp_price: 止盈价格
    actual_size: 实际张数
    TP_MODE: 止盈模式 ('limit' 或 'trailing')
    is_simulation: 是否模拟交易
    
    返回:
    tuple: (止损订单ID, 止盈订单ID, 追踪止盈订单ID)
    """
    sl_order_id = None
    tp_order_id = None
    trailing_order_id = None

    try:
        if signal == 'long_entry':
            # 设置止损订单（卖出）
            sl_params = {'reduceOnly': True, 'posSide': 'long'} if not is_simulation else {'reduceOnly': True}
            sl_order = exchange.create_stop_loss_order(
                SYMBOL, 
                'market', 
                'sell', 
                actual_size, 
                stopLossPrice=sl_price, 
                params=sl_params
            )
            sl_order_id = sl_order['id']
            logging.info(f"\033[92m止损订单（卖出）已设置，订单ID: {sl_order_id}\033[0m")

            # 设置止盈订单
            if TP_MODE == 'limit':
                tp_params = {'reduceOnly': True, 'posSide': 'long'} if not is_simulation else {'reduceOnly': True}
                tp_order = exchange.create_take_profit_order(
                    SYMBOL, 
                    'limit', 
                    'sell', 
                    actual_size, 
                    price=tp_price, 
                    takeProfitPrice=(tp_price + entry_price) / 2, 
                    params=tp_params
                )
                tp_order_id = tp_order['id']
                logging.info(f"\033[92m限价止盈订单（卖出）已设置，订单ID: {tp_order_id}\033[0m")
            elif TP_MODE == 'trailing':
                trailing_params = {
                    'callbackSpread': str(tp_price - entry_price),  # 回调幅度
                    'activePx': str(tp_price),  # 激活价格
                    'reduceOnly': True
                }
                if not is_simulation:
                    trailing_params['posSide'] = 'long'
                trailing_order = exchange.create_order(
                    SYMBOL,
                    'trailing_stop',
                    'sell',
                    actual_size,
                    params=trailing_params
                )
                trailing_order_id = trailing_order['id']
                logging.info(f"\033[92m移动止盈止损订单（卖出）已设置，订单ID: {trailing_order_id}\033[0m")
            else:
                logging.warning("无效的TP_MODE，跳过止盈设置。")

        elif signal == 'short_entry':
            # 设置止损订单（买入）
            sl_params = {'reduceOnly': True, 'posSide': 'short'} if not is_simulation else {'reduceOnly': True}
            sl_order = exchange.create_stop_loss_order(
                SYMBOL, 
                'market', 
                'buy', 
                actual_size, 
                stopLossPrice=sl_price, 
                params=sl_params
            )
            sl_order_id = sl_order['id']
            logging.info(f"\033[92m止损订单（买入）已设置，订单ID: {sl_order_id}\033[0m")

            # 设置止盈订单
            if TP_MODE == 'limit':
                tp_params = {'reduceOnly': True, 'posSide': 'short'} if not is_simulation else {'reduceOnly': True}
                tp_order = exchange.create_take_profit_order(
                    SYMBOL, 
                    'limit', 
                    'buy', 
                    actual_size, 
                    price=tp_price, 
                    takeProfitPrice=(tp_price + entry_price) / 2, 
                    params=tp_params
                )
                tp_order_id = tp_order['id']
                logging.info(f"\033[92m限价止盈订单（买入）已设置，订单ID: {tp_order_id}\033[0m")
            elif TP_MODE == 'trailing':
                trailing_params = {
                    'callbackSpread': str(entry_price - tp_price),  # 回调幅度
                    'activePx': str(tp_price),  # 激活价格
                    'reduceOnly': True
                }
                if not is_simulation:
                    trailing_params['posSide'] = 'short'
                trailing_order = exchange.create_order(
                    SYMBOL,
                    'trailing_stop',
                    'buy',
                    actual_size,
                    params=trailing_params
                )
                trailing_order_id = trailing_order['id']
                logging.info(f"\033[92m移动止盈止损订单（买入）已设置，订单ID: {trailing_order_id}\033[0m")
            else:
                logging.warning("无效的TP_MODE，跳过止盈设置。")

    except Exception as e:
        logging.error(f"设置止损止盈失败: {e}")

    return sl_order_id, tp_order_id, trailing_order_id