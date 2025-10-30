import pandas as pd
import os
import smtplib
import logging
import time

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta

# 设置日志配置，包括文件轮转和控制台输出
def setup_logging():
    """
    设置日志配置，包括文件轮转和控制台输出。
    
    此函数创建日志目录（如果不存在），并配置日志记录器以将日志写入轮转文件和控制台。
    日志文件基于当前时间戳命名，并使用RotatingFileHandler来限制文件大小和保留备份。
    """
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_filename = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.log")
    # 使用 RotatingFileHandler 来自动轮转日志文件
    handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 每个日志文件最大10MB
        backupCount=5,  # 保留5个备份文件
        encoding='utf-8'
    )
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            handler,
            logging.StreamHandler()
        ]
    )

# 获取OHLCV数据并转换为Pandas DataFrame
def get_ohlcv_data(exchange, symbol='BTC/USDT:USDT', timeframe='15m', limit=100):
    """
    获取OHLCV数据并转换为Pandas DataFrame。
    
    参数:
    exchange: ccxt交易所对象
    symbol (str): 交易对符号，默认 'BTC/USDT:USDT'
    timeframe (str): 时间框架，默认 '15m'
    limit (int): 获取的K线数量，默认 100
    
    返回:
    pd.DataFrame: 包含OHLCV数据的DataFrame，索引为时间戳
    """
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# 发送邮件通知
def send_email_notification(
    subject,
    body,
    to_email=None,
    from_email=None,
    smtp_server='smtp.qq.com',
    smtp_port=587,
    smtp_user=None,
    smtp_password=None
):
    """
    发送邮件通知。
    使用SMTP发送邮件，支持从环境变量读取配置信息。
    
    参数:
    subject (str): 邮件主题
    body (str): 邮件正文
    to_email (str): 收件人邮箱，默认从环境变量EMAIL_TO读取
    from_email (str): 发件人邮箱，默认从环境变量EMAIL_FROM读取
    smtp_server (str): SMTP服务器，默认 'smtp.qq.com'
    smtp_port (int): SMTP端口，默认 587
    smtp_user (str): SMTP用户名，默认从环境变量SMTP_USER读取
    smtp_password (str): SMTP密码，默认从环境变量SMTP_PASSWORD读取
    
    返回:
    无
    """
    # 从环境变量读取敏感信息
    if to_email is None:
        to_email = os.getenv('EMAIL_TO')
    if from_email is None:
        from_email = os.getenv('EMAIL_FROM')
    if smtp_user is None:
        smtp_user = os.getenv('SMTP_USER')
    if smtp_password is None:
        smtp_password = os.getenv('SMTP_PASSWORD')
        if smtp_password is None:
            raise ValueError("SMTP_PASSWORD 环境变量未设置，无法发送邮件。")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        logging.info("邮件发送成功。")
    except Exception as e:
        logging.error(f"邮件发送失败：{e}")

# 根据UTC小时决定交易策略类型
def time_checker(hour):
    """
    根据UTC小时决定交易策略类型。
    
    参数:
    hour (int): UTC小时 (0-23)
    
    返回:
    str: 'counter_trend' 或 'trend_following'
    """
    if 4 <= hour <= 11:
        return 'counter_trend'
    elif 12 <= hour <= 23 or 0 <= hour <= 3:
        return 'trend_following'
    else:
        return 'trend_following'

# 等待到下一个指定时间间隔整点
def wait_time(interval='15m'):
    """
    等待到下一个指定时间间隔整点。
    
    参数:
    interval (str): 时间间隔字符串，如 '15m' (15分钟), '60s' (60秒), '1h' (1小时)，默认 '15m'
    """
    now = datetime.now(timezone.utc)
    
    if interval.endswith('m'):
        minutes = int(interval[:-1])
        wait_seconds = (minutes - (now.minute % minutes)) * 60 - now.second
        if wait_seconds <= 0:
            wait_seconds += minutes * 60
    elif interval.endswith('s'):
        seconds = int(interval[:-1])
        wait_seconds = seconds - (now.second % seconds)
        if wait_seconds <= 0:
            wait_seconds += seconds
    elif interval.endswith('h'):
        hours = int(interval[:-1])
        wait_seconds = (hours - (now.hour % hours)) * 3600 - now.minute * 60 - now.second
        if wait_seconds <= 0:
            wait_seconds += hours * 3600
    else:
        raise ValueError("Invalid interval format. Use 'Xm', 'Xs', or 'Xh' where X is a number.")
    
    logging.info(f"等待 {wait_seconds} 秒到下一个 {interval} 整点")
    time.sleep(wait_seconds)