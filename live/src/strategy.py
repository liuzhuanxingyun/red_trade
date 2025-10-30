import pandas as pd
import time
from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from .utils import send_email_notification, setup_logging, time_checker, wait_time
from .signals import ema_atr_filter
from .exit_mechanism import set_stop_loss_and_take_profit


def live_strategy(exchange, SYMBOL, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT, SL_ATR_MULTIPLIER, RR, RISK_USDT, FIXED_LEVERAGE, TP_MODE, CONTRACT_SIZE):
    """
    实盘交易策略：根据EMA和ATR过滤器生成信号，执行交易并设置止盈止损。
    """
    try:
        now = datetime.now(timezone.utc)
        hour = now.hour

        # 获取信号和ATR值
        mark, atr_value = ema_atr_filter(exchange, SYMBOL, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT)

        # strategy_type = time_checker(hour)  # 移到此处，确保始终定义
        strategy_type = 'trend_following'  

        signal = None
        # signal = 'long_entry'

        if mark:
            logging.info(f"当前UTC小时: {hour}, 策略类型: {strategy_type}")
            
            # 根据策略类型调整信号
            if strategy_type == 'counter_trend':
                if mark == 'upper_breakout':
                    signal = 'short_entry'  # 逆势：上突破做空
                elif mark == 'lower_breakout':
                    signal = 'long_entry'   # 逆势：下突破做多
            elif strategy_type == 'trend_following':
                if mark == 'upper_breakout':
                    signal = 'long_entry'  # 顺势：上突破做多
                elif mark == 'lower_breakout':
                    signal = 'short_entry'  # 顺势：下突破做空
        
        if not signal:
            logging.info("无交易信号。")
            return
        else:
            # 发送邮件通知
            subject = "交易信号触发"
            body = f"时间: {now}\n信号: {signal}\n策略类型: {strategy_type}\nATR值: {atr_value}"
            send_email_notification(subject, body)
            
            # 取消当前所有委托
            try:
                open_orders = exchange.fetch_open_orders(SYMBOL)
                if open_orders:
                    ids = [order['id'] for order in open_orders]
                    exchange.cancelOrders(ids, SYMBOL)
                    logging.info("已取消当前所有委托。")
                else:
                    logging.info("无开放委托。")
            except Exception as e:
                logging.error(f"取消委托失败: {e}")
        
        # 计算止损和止盈距离
        sl_distance = atr_value * SL_ATR_MULTIPLIER
        tp_distance = sl_distance * RR

        # 计算交易张数
        size = RISK_USDT * CONTRACT_SIZE / sl_distance
        logging.info(f"计算得张数: {size:.2f}")
        logging.info(f"ATR值: {atr_value}")
            
        entry_price = None
        sl_order_id = None
        tp_order_id = None
        trailing_order_id = None

        if signal == 'long_entry':
            # 多头入场
            order = exchange.create_market_buy_order(SYMBOL, size, params={'posSide': 'long'})
            order_id = order['id']
            logging.info(f"\033[92m市价买入订单已提交，订单ID: {order_id}\033[0m")
            time.sleep(1)
            filled_order = exchange.fetch_order(order_id, SYMBOL)
            if filled_order and filled_order['status'] == 'closed' and filled_order['average']:
                entry_price = filled_order['average']
                logging.info(f"\033[92m订单已成交，实际入场价: {entry_price}\033[0m")
            else:
                logging.error("错误：无法获取订单成交价，取消设置止盈止损。")
                return
            actual_size = float(filled_order.get('filled', filled_order.get('amount', size)))
            if actual_size <= 0:
                logging.error("错误：成交张数为0，取消止损止盈设置。")
                return

            logging.info(f"\033[92m实际张数: {actual_size:.2f}\033[0m")
            # 计算保证金
            margin = (actual_size * 0.01 * entry_price) / FIXED_LEVERAGE
            logging.info(f"\033[92m保证金: {margin:.2f} USDT\033[0m")

            # 设置止盈止损
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
            logging.info(f"\033[92m止损价格: {sl_price}, 止盈价格: {tp_price}\033[0m")
            sl_order_id, tp_order_id, trailing_order_id = set_stop_loss_and_take_profit(exchange, SYMBOL, signal, entry_price, sl_price, tp_price, actual_size, TP_MODE, is_simulation=False)

        elif signal == 'short_entry':
            # 空头入场
            order = exchange.create_market_sell_order(SYMBOL, size, params={'posSide': 'short'})
            order_id = order['id']
            logging.info(f"\033[92m市价卖出订单已提交，订单ID: {order_id}\033[0m")
            time.sleep(1)
            filled_order = exchange.fetch_order(order_id, SYMBOL)
            if filled_order and filled_order['status'] == 'closed' and filled_order['average']:
                entry_price = filled_order['average']
                logging.info(f"\033[92m订单已成交，实际入场价: {entry_price}\033[0m")
            else:
                logging.error("错误：无法获取订单成交价，取消设置止盈止损。")
                return
            actual_size = float(filled_order.get('filled', filled_order.get('amount', size)))
            if actual_size <= 0:
                logging.error("错误：成交张数为0，取消止损止盈设置。")
                return
            
            logging.info(f"\033[92m实际张数: {actual_size:.2f}\033[0m")
            # 计算保证金
            margin = (actual_size * 0.01 * entry_price) / FIXED_LEVERAGE
            logging.info(f"\033[92m保证金: {margin:.2f} USDT\033[0m")
            
            # 设置止盈止损
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance
            logging.info(f"\033[92m止损价格: {sl_price}, 止盈价格: {tp_price}\033[0m")
            sl_order_id, tp_order_id, trailing_order_id = set_stop_loss_and_take_profit(exchange, SYMBOL, signal, entry_price, sl_price, tp_price, actual_size, TP_MODE, is_simulation=False)

    except Exception as e:
        logging.error(f"策略执行失败: {e}")


def test_strategy(exchange, SYMBOL, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT, SL_ATR_MULTIPLIER, RR, RISK_USDT, FIXED_LEVERAGE, TP_MODE, CONTRACT_SIZE):
    """
    模拟交易策略：与实盘类似，但不指定posSide。
    """
    try:
        now = datetime.now(timezone.utc)
        hour = now.hour

        # 获取信号和ATR值
        mark, atr_value = ema_atr_filter(exchange, SYMBOL, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT)

        # strategy_type = time_checker(hour)  # 移到此处，确保始终定义
        strategy_type = 'trend_following'  

        # signal = None
        signal = 'long_entry'

        if mark:
            logging.info(f"当前UTC小时: {hour}, 策略类型: {strategy_type}")
            
            # 根据策略类型调整信号
            if strategy_type == 'counter_trend':
                if mark == 'upper_breakout':
                    signal = 'short_entry'  # 逆势：上突破做空
                elif mark == 'lower_breakout':
                    signal = 'long_entry'   # 逆势：下突破做多
            elif strategy_type == 'trend_following':
                if mark == 'upper_breakout':
                    signal = 'long_entry'  # 顺势：上突破做多
                elif mark == 'lower_breakout':
                    signal = 'short_entry'  # 顺势：下突破做空
        
        if not signal:
            logging.info("无交易信号。")
            return
        else:
            # 发送邮件通知
            subject = "交易信号触发"
            body = f"时间: {now}\n信号: {signal}\n策略类型: {strategy_type}\nATR值: {atr_value}"
            send_email_notification(subject, body)
            
            # 取消当前所有委托
            try:
                open_orders = exchange.fetch_open_orders(SYMBOL)
                if open_orders:
                    ids = [order['id'] for order in open_orders]
                    exchange.cancelOrders(ids, SYMBOL)
                    logging.info("已取消当前所有委托。")
                else:
                    logging.info("无开放委托。")
            except Exception as e:
                logging.error(f"取消委托失败: {e}")
        
        # 计算止损和止盈距离
        sl_distance = atr_value * SL_ATR_MULTIPLIER
        tp_distance = sl_distance * RR

        # 计算交易张数
        size = RISK_USDT * CONTRACT_SIZE / sl_distance
        logging.info(f"计算得张数: {size:.2f}")
        logging.info(f"ATR值: {atr_value}")
            
        entry_price = None
        sl_order_id = None
        tp_order_id = None
        trailing_order_id = None

        if signal == 'long_entry':
            # 多头入场
            order = exchange.create_market_buy_order(SYMBOL, size)
            order_id = order['id']
            logging.info(f"\033[92m市价买入订单已提交，订单ID: {order_id}\033[0m")
            time.sleep(1)
            filled_order = exchange.fetch_order(order_id, SYMBOL)
            if filled_order and filled_order['status'] == 'closed' and filled_order['average']:
                entry_price = filled_order['average']
                logging.info(f"\033[92m订单已成交，实际入场价: {entry_price}\033[0m")
            else:
                logging.error("错误：无法获取订单成交价，取消设置止盈止损。")
                return
            actual_size = float(filled_order.get('filled', filled_order.get('amount', size)))
            if actual_size <= 0:
                logging.error("错误：成交张数为0，取消止损止盈设置。")
                return

            logging.info(f"\033[92m实际张数: {actual_size:.2f}\033[0m")
            # 计算保证金
            margin = (actual_size * 0.01 * entry_price) / FIXED_LEVERAGE
            logging.info(f"\033[92m保证金: {margin:.2f} USDT\033[0m")

            # 设置止盈止损
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
            logging.info(f"\033[92m止损价格: {sl_price}, 止盈价格: {tp_price}\033[0m")
            sl_order_id, tp_order_id, trailing_order_id = set_stop_loss_and_take_profit(exchange, SYMBOL, signal, entry_price, sl_price, tp_price, actual_size, TP_MODE, is_simulation=True)

        elif signal == 'short_entry':
            # 空头入场
            order = exchange.create_market_sell_order(SYMBOL, size)
            order_id = order['id']
            logging.info(f"\033[92m市价卖出订单已提交，订单ID: {order_id}\033[0m")
            time.sleep(1)
            filled_order = exchange.fetch_order(order_id, SYMBOL)
            if filled_order and filled_order['status'] == 'closed' and filled_order['average']:
                entry_price = filled_order['average']
                logging.info(f"\033[92m订单已成交，实际入场价: {entry_price}\033[0m")
            else:
                logging.error("错误：无法获取订单成交价，取消设置止盈止损。")
                return
            actual_size = float(filled_order.get('filled', filled_order.get('amount', size)))
            if actual_size <= 0:
                logging.error("错误：成交张数为0，取消止损止盈设置。")
                return
            
            logging.info(f"\033[92m实际张数: {actual_size:.2f}\033[0m")
            # 计算保证金
            margin = (actual_size * 0.01 * entry_price) / FIXED_LEVERAGE
            logging.info(f"\033[92m保证金: {margin:.2f} USDT\033[0m")
            
            # 设置止盈止损
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance
            logging.info(f"\033[92m止损价格: {sl_price}, 止盈价格: {tp_price}\033[0m")
            sl_order_id, tp_order_id, trailing_order_id = set_stop_loss_and_take_profit(exchange, SYMBOL, signal, entry_price, sl_price, tp_price, actual_size, TP_MODE, is_simulation=True)

    except Exception as e:
        logging.error(f"策略执行失败: {e}")


