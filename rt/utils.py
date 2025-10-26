import pandas as pd
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from datetime import datetime, timezone, timedelta

def get_ohlcv_data(exchange, symbol='BTC/USDT:USDT', timeframe='15m', limit=100):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# 发送邮件提醒
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
        print("邮件发送成功。")
    except Exception as e:
        print(f"邮件发送失败：{e}")