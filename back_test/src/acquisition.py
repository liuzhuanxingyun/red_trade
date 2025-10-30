import pandas as pd
import os
from back_test.src.utils import load_and_process_data, merge_csv_files, download_binance_data, unzip_binance_data, merge_csv_files_by_years_months

def acquire_data(symbol='BTCUSDT', interval='1m', selected_years=None, selected_months=None, is_download_data=False, save_dir='./data'):
    """
    数据获取函数：下载、解压、合并和加载数据。
    
    参数:
    - symbol: 交易对符号，如 'BTCUSDT'
    - interval: 时间间隔，如 '1m'
    - selected_years: 年份列表，如 [2025]
    - selected_months: 月份列表，如 [7, 8, 9]
    - is_download_data: 是否下载数据
    - save_dir: 保存目录
    
    返回:
    - data: 处理后的DataFrame
    """
    if is_download_data:
        download_binance_data(symbol=symbol, interval=interval, years=selected_years or [2025], months=range(1, 10), save_dir=save_dir)
        unzip_binance_data(symbol=symbol, interval=interval, save_dir=save_dir)
        merge_csv_files(symbol=symbol, interval=interval)
    
    if selected_years and selected_months:
        merged_data = merge_csv_files_by_years_months(symbol=symbol, interval=interval, years=selected_years, months=selected_months)
        data = load_and_process_data(f'{save_dir}/merged_{symbol}-{interval}.csv')
    else:
        # 默认使用单个文件（需要根据实际情况调整）
        data = load_and_process_data(f'{save_dir}/{symbol}-{interval}/{symbol}-{interval}-2025-01.csv')
    
    return data