import pandas as pd
import talib
import numpy as np
import os

from datetime import datetime
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, plot_heatmaps
from back_test.src.utils import load_and_process_data, merge_csv_files, send_email_notification, download_binance_data, unzip_binance_data, create_3d_heatmap_cube, merge_csv_files_by_years_months, custom_maximize
from back_test.src.acquisition import acquire_data

# 设置开关
is_download_data = False  # 是否下载数据
is_batch_test = False  # 是否进行批量回测
is_send_batch_email = False  # 批量回测邮件开关
is_send_single_email = False  # 单次回测邮件开关

# 新增：选择具体年份和月份进行合并回测（空列表则使用默认单个文件）
selected_years = [2025]  # 示例：选择2025年；可修改为所需年份列表，如 [2024, 2025]
selected_months = [7, 8, 9]  # 示例：选择1月、2月、3月；可修改为所需月份列表，如 [1] 或 [1, 4, 7]

# 设置参数
symbol = 'BTCUSDT'
interval = '1m'
is_download_data = False

# 获取数据
data = acquire_data(symbol=symbol, interval=interval, selected_years=selected_years, selected_months=selected_months, is_download_data=is_download_data)

# 修改：根据 selected_years 和 selected_months 决定加载数据
if selected_years and selected_months:
    # 如果指定了年月，则合并并加载合并文件
    merged_data = merge_csv_files_by_years_months(symbol='BTCUSDT', interval='1m', years=selected_years, months=selected_months)
    data = load_and_process_data(f'data/merged_BTCUSDT-1m.csv')  # 假设输出文件为默认路径
else:
    # 否则，使用默认单个文件
    data = load_and_process_data('data/BCHUSDT-15m/BCHUSDT-15m-2025-01.csv')
# data/BCHUSDT-15m/BCHUSDT-15m-2025-01.csv
# data/ETHUSDT-15m/ETHUSDT-15m-2025-09.csv
# data/merged_ETHUSDT-15m.csv
# 测试用

print(data.head())

class EmaAtrStrategy(Strategy):
    ema_period = 21
    atr_period = 10
    multiplier = 4
    atr_threshold_pct = 0  # ATR波动率过滤器阈值（百分比，基于当前价格）
    rr = 1  # 风险回报比：止盈距离 = 止损距离 * rr

    def init(self):
        price = self.data.Close
        self.ema = self.I(talib.EMA, price, timeperiod=self.ema_period)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=self.atr_period)

    def next(self):
        # 检查ATR波动率过滤器（基于当前价格的百分比）
        if self.atr[-1] / self.data.Close[-1] < self.atr_threshold_pct:
            return  # 如果ATR低于阈值百分比，不执行交易
        
        upper = self.ema + self.atr * self.multiplier
        lower = self.ema - self.atr * self.multiplier
        
        # 计算止损和止盈距离
        sl_distance = self.atr
        tp_distance = sl_distance * self.rr  # 止盈距离 = 止损距离 * rr
        
        # 只有在空仓时才能开仓
        if self.position.size == 0:
            if crossover(self.data.Close, upper):
                self.buy(tp=self.data.Close + tp_distance, sl=self.data.Close - sl_distance)
            elif crossover(lower, self.data.Close):
                self.sell(tp=self.data.Close - tp_distance, sl=self.data.Close + sl_distance)

bt = Backtest(data, EmaAtrStrategy, cash=1_000_000_000_000)  
# , commission=0.0005

if is_batch_test:
    # 定义优化参数
    ema_period_range = range(2, 302, 30)
    atr_period_range = range(3, 23, 2)  # 转换为list
    multiplier_range = range(3, 23, 2)
    # list(np.arange(1, 21, 10))
    atr_threshold_pct_range = list(np.arange(0.00001, 0.00101, 0.0001))
    rr_range = [1]
    
    # 自动计算组合总数
    total_combinations = (len(ema_period_range) * len(atr_period_range) * 
                          len(multiplier_range) * len(atr_threshold_pct_range) * len(rr_range))
    print(f"优化参数组合总数: {total_combinations}")

    stats, heatmap= bt.optimize(
        ema_period=ema_period_range,
        atr_period=atr_period_range,
        multiplier=multiplier_range,
        atr_threshold_pct=atr_threshold_pct_range,  # 调整ATR阈值百分比范围
        rr=rr_range,  # 新增rr优化参数

        max_tries=6000,
        method='sambo', 
        # method='grid',

        # return_optimization=True,
        return_heatmap=True,

        # maximize='Win Rate [%]'
        maximize=custom_maximize
    )
    print(heatmap)
    
    # 新增：为 heatmap 添加交易数量列
    trades_list = []
    for params in heatmap.index:
        param_dict = dict(zip(heatmap.index.names, params))
        temp_stats = bt.run(**param_dict)
        trades_list.append(temp_stats['# Trades'])
    
    # 将 heatmap 转换为 DataFrame 并添加交易数量
    heatmap_df = heatmap.reset_index()
    heatmap_df.columns = ['ema_period', 'atr_period', 'multiplier', 'atr_threshold_pct', 'rr', 'win_rate']
    heatmap_df['# Trades'] = trades_list
    
    # 生成时间戳并创建新文件夹（移到此处，确保在 3D 热力图前定义）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_folder = f"results/batch_{timestamp}"
    os.makedirs(batch_folder, exist_ok=True)
    
    # 新增：创建三维热力图魔方（基于 ema_period, atr_period, multiplier）
    # 假设其他参数固定或聚合（例如，取 atr_threshold_pct 和 rr 的最佳或平均）
    # 这里我们聚合 heatmap 到这三个参数的平均胜率
    
    # 聚合：对 ema_period, atr_period, multiplier 分组，取 win_rate 的最大值（或平均）
    aggregated = heatmap_df.groupby(['ema_period', 'atr_period', 'multiplier'])['win_rate'].max().reset_index()
    
    # 调试：打印 aggregated 以确认数据
    print("Aggregated DataFrame:")
    print(aggregated.head())
    
    # 调用函数创建 3D 热力图
    try:
        create_3d_heatmap_cube(aggregated, batch_folder)
    except Exception as e:
        print(f"3D 热力图生成失败: {e}")
    
    # 修改文件名以包含最佳胜率和交易数量
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']
    heatmap_filename = f'{batch_folder}/heatmap_win{win_rate}_trades{num_trades}.csv'
    plot_filename = f'{batch_folder}/heatmap_win{win_rate}_trades{num_trades}.html'
    plot_heatmaps(heatmap, filename=plot_filename, open_browser=True)
    heatmap_df.to_csv(heatmap_filename, index=False)  # 使用 heatmap_df 保存，包含 # Trades 列
    
    if is_send_batch_email:
        # 发送邮件提醒
        subject = "批量回测完成提醒"
        body = f"批量回测已完成。最佳胜率: {win_rate}%，交易数量: {num_trades}。"
        send_email_notification(subject, body)

else:

    stats = bt.run()
    print(stats)
    print(stats._trades)
    # 生成时间戳并创建新文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    single_folder = f"results/single_{timestamp}"
    os.makedirs(single_folder, exist_ok=True)
    
    # 修改文件名以包含胜率和交易数量
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']
    trades_filename = f'{single_folder}/trades_win{win_rate}_trades{num_trades}.csv'
    plot_filename = f'{single_folder}/ema_atr_win{win_rate}_trades{num_trades}.html'
    stats._trades.to_csv(trades_filename, index=True)
    bt.plot(filename=plot_filename, plot_trades=True, open_browser=True)
    
    if is_send_single_email:
        # 发送邮件提醒
        subject = "单次回测完成提醒"
        body = f"单次回测已完成。胜率: {win_rate}%，交易数量: {num_trades}。"
        send_email_notification(subject, body)

