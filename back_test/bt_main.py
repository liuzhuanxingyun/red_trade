import numpy as np

from src.acquisition import acquire_data
from src.strategy import ema_atr_atrFilter  # 导入回测函数
from src.processing import process_batch_backtest, process_single_backtest  # 添加导入
from src.utils import send_email_notification, custom_maximize  # 添加导入，用于发送邮件和自定义最大化函数

# 设置参数
symbol = 'LINKUSDT'
interval = '15m'

# --- 新增：统一路径管理 ---
DATA_DIR = 'back_test/data'
RESULTS_DIR = 'back_test/results'
# --- 结束新增 ---

# 设置开关
is_batch_test = False  # 是否进行批量回测

# 新增：选择具体年份和月份进行合并回测（空列表则使用默认单个文件）
selected_years = [2025]  # 示例：选择2025年；可修改为所需年份列表，如 [2024, 2025]
selected_months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # 示例：选择1月、2月、3月；可修改为所需月份列表，如 [1] 或 [1, 4, 7]

# 设置回测参数（可在 main 中调节）
backtest_params = {
    'cash': 1_000_000_000_000,
    'finalize_trades': True  # 新增：关闭开放交易
    # 'commission': 0.0005
}

# 单次回测参数（可在 main 中调节）
strategy_params = {
    'ema_period': 25,
    'atr_period': 24,
    'multiplier': 3,
    'sl_multiplier': 2,  # 止损ATR乘数，用于计算止损距离
    'atr_threshold_pct': 0,  # ATR波动率过滤器阈值（百分比，基于当前价格）
    'rr': 2,  # 风险回报比：止盈距离 = 止损距离 * rr
    'volume_multiplier': 1.3,  # 新增：成交量倍数
    'time_filter_hours': [[23, 1], [8, 10], [3, 4]]  # 修改：禁止交易时段，格式为 [[start1, end1], [start2, end2]]，支持跨天（如23到2点）
}

# 批量回测参数（仅用于批量回测，可在 main 中调节）
optimize_params = {
    'ema_period_range': range(2, 50),  # 默认步长 1，无需指定
    'atr_period_range': range(2, 25),  # 删掉步长 4，改为默认
    'multiplier_range': range(1, 10),  # 删掉步长 2，改为默认
    'sl_multiplier_range': [2, 3],  # 已是列表，无步长
    'atr_threshold_pct_range': [0], 
    #  list(np.arange(0.00001, 0.00101)) 
    'rr_range': [2],  # 已是列表，无步长
    'volume_multiplier_range': [1.0],  # 新增：成交量倍数范围，默认[1.0]
    # 'ema_period_range': [12],  # 默认步长 1，无需指定
    # 'atr_period_range': [9],  # 删掉步长 4，改为默认
    # 'multiplier_range': [1],  # 删掉步长 2，改为默认
    # 'sl_multiplier_range': [2],  # 已是列表，无步长
    # 'atr_threshold_pct_range': list(np.arange(0.00001, 0.00101, 0.0001)),  # 指定步长 0.0001，生成多个值
    # 'rr_range': [2],  # 已是列表，无步长
    
    'max_tries': 10000,
    'method': 'sambo',
    'return_optimization': True,  # 新增：控制是否返回优化结果，默认 True

    'return_heatmap': True,
    'maximize': custom_maximize,
}

is_send_batch_email = False  # 批量回测邮件开关
is_send_single_email = False  # 单次回测邮件开关

# 获取数据
data = acquire_data(symbol=symbol, interval=interval, selected_years=selected_years, selected_months=selected_months, save_dir=DATA_DIR)

# 调用回测函数
if is_batch_test:
    stats, heatmap, bt = ema_atr_atrFilter(  # 接收 bt 仍然是好的，以备后用
        is_batch_test, data, symbol, interval,
        backtest_params, strategy_params, optimize_params
    )
    # 在调用 process_batch_backtest 时传入 RESULTS_DIR
    process_batch_backtest(stats, heatmap, symbol, interval, bt, results_dir=RESULTS_DIR)  # 传递 bt (即使新逻辑可能不用)
    
    if is_send_batch_email:
        # 发送批量回测邮件提醒
        win_rate = stats['Win Rate [%]']
        num_trades = stats['# Trades']
        subject = "批量回测完成提醒"
        body = f"批量回测已完成。最佳胜率: {win_rate}%，交易数量: {num_trades}。"
        send_email_notification(subject, body)
else:
    stats, bt = ema_atr_atrFilter(
        is_batch_test, data, symbol, interval,
        backtest_params, strategy_params
    )
    process_single_backtest(stats, symbol, interval, bt, results_dir=RESULTS_DIR, strategy_params=strategy_params)  # 修复：传递 results_dir
    
    if is_send_single_email:
        # 发送单次回测邮件提醒
        win_rate = stats['Win Rate [%]']
        num_trades = stats['# Trades']
        subject = "单次回测完成提醒"
        body = f"单次回测已完成。胜率: {win_rate}%，交易数量: {num_trades}。"
        send_email_notification(subject, body)


