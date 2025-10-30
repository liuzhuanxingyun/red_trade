import os
import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from src.utils import setup_logging, wait_time
from src.strategy import live_strategy, test_strategy  # 假设test_strategy也在src.strategy中

# --- 日志配置 ---
setup_logging()

load_dotenv()

EMAIL_TO = os.getenv('EMAIL_TO')
EMAIL_FROM = os.getenv('EMAIL_FROM')
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# 将单个SYMBOL改为列表
SYMBOLS = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']  # 添加更多品种

# --- 参数配置 ---
TIMEFRAME = '15m'
CONTRACT_SIZES = [100, 10, 1]  # 与SYMBOLS一一对应

EMA_PERIOD = 4
ATR_PERIOD = 18
MULTIPLIER = 2
SL_ATR_MULTIPLIER = 3
RR = 1
ATR_THRESHOLD_PCT = 0

# 杠杆和风险管理
FIXED_LEVERAGE = 20
RISK_USDT = 2.5

# 在全局变量部分添加止盈模式配置
TP_MODE = 'limit'  # 可选值: 'limit' (限价止盈) 或 'trailing' (移动止盈止损)

# 添加模拟交易参数
IS_SIMULATION = True  #  False（实盘），如需模拟改为 True

if IS_SIMULATION:
    API_KEY = os.getenv('OKX_SIM_API_KEY')
    API_SECRET = os.getenv('OKX_SIM_API_SECRET')
    API_PASSPHRASE = os.getenv('OKX_SIM_API_PASSPHRASE')
    SANDBOX = True
else:
    API_KEY = os.getenv('OKX_API_KEY')
    API_SECRET = os.getenv('OKX_API_SECRET')
    API_PASSPHRASE = os.getenv('OKX_API_PASSPHRASE')
    SANDBOX = False

# 初始化交易所
exchange = ccxt.okx({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'password': API_PASSPHRASE,
    'enableRateLimit': True,
    'sandbox': SANDBOX,
    'options': {
        'defaultType': 'swap',
        'marginMode': 'isolated',
    },
    'proxies': {
        'http': 'http://127.0.0.1:7897',
        'https': 'http://127.0.0.1:7897',
    }
})

def main():
    try:
        # 检查余额并设置杠杆
        balance = exchange.fetch_balance()
        logging.info(f"API连接成功，余额: {balance['total']['USDT']}")

        leverage_to_set = int(FIXED_LEVERAGE)
        for symbol in SYMBOLS:  # 为每个品种设置杠杆
            if SANDBOX:
                exchange.set_leverage(leverage_to_set, symbol, {'mgnMode': 'isolated'})
                logging.info(f"当前杠杆为：{leverage_to_set}（模拟环境，品种: {symbol}）")
            else:
                exchange.set_leverage(leverage_to_set, symbol, {'mgnMode': 'isolated', 'posSide': 'long'})
                exchange.set_leverage(leverage_to_set, symbol, {'mgnMode': 'isolated', 'posSide': 'short'})
                logging.info(f"当前杠杆为：{leverage_to_set}（多头和空头，品种: {symbol}）")

    except Exception as e:
        logging.error(f"API连接失败: {e}")
    
    while True:
        try:
            for symbol, contract_size in zip(SYMBOLS, CONTRACT_SIZES):  # 对每个品种运行策略，使用对应的CONTRACT_SIZE
                if SANDBOX:
                    test_strategy(exchange, symbol, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT, SL_ATR_MULTIPLIER, RR, RISK_USDT, FIXED_LEVERAGE, TP_MODE, contract_size)
                else:
                    live_strategy(exchange, symbol, EMA_PERIOD, ATR_PERIOD, MULTIPLIER, ATR_THRESHOLD_PCT, SL_ATR_MULTIPLIER, RR, RISK_USDT, FIXED_LEVERAGE, TP_MODE, contract_size)
                logging.info("-" * 50)
            # 测试用
            # time.sleep(5)
            wait_time()
            
        except KeyboardInterrupt:
            logging.info("用户中断，停止运行。")
            break
        except Exception as e:
            logging.error(f"主循环错误: {e}")

if __name__ == "__main__":
    main()