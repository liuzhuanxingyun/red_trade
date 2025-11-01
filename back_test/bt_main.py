import numpy as np

from src.acquisition import acquire_data
from src.strategy import ema_atr_atrFilter  # 导入回测函数
from src.processing import process_batch_backtest, process_single_backtest  # 添加导入
from src.utils import send_email_notification, custom_maximize  # 添加导入，用于发送邮件和自定义最大化函数

# 设置参数
symbol = 'BTCUSDT'
interval = '15m'

# 设置开关
is_batch_test = True  # 是否进行批量回测

# 新增：选择具体年份和月份进行合并回测（空列表则使用默认单个文件）
selected_years = [2025]  # 示例：选择2025年；可修改为所需年份列表，如 [2024, 2025]
selected_months = [9]  # 示例：选择1月、2月、3月；可修改为所需月份列表，如 [1] 或 [1, 4, 7]

# 设置回测参数（可在 main 中调节）
backtest_params = {
    'cash': 1_000_000_000_000
    # 'commission': 0.0005
}

# 单次回测参数（可在 main 中调节）
strategy_params = {
    'ema_period': 4,
    'atr_period': 18,
    'multiplier': 2,
    'sl_multiplier': 3,  # 止损ATR乘数，用于计算止损距离
    'atr_threshold_pct': 0,  # ATR波动率过滤器阈值（百分比，基于当前价格）
    'rr': 2  # 风险回报比：止盈距离 = 止损距离 * rr
}

# 批量回测参数（仅用于批量回测，可在 main 中调节）
optimize_params = {
    'ema_period_range': range(2, 12, 5),
    'atr_period_range': range(3, 23, 4),
    'multiplier_range': range(3, 23, 4),
    'sl_multiplier_range': [3],  # 止损ATR乘数范围
    'atr_threshold_pct_range': [0],
    # list(np.arange(0.00001, 0.00101, 0.0001))
    'rr_range': [2],
    
    'max_tries': 6,
    'method': 'sambo',
    'return_heatmap': True,
    'maximize': custom_maximize
}

is_send_batch_email = False  # 批量回测邮件开关
is_send_single_email = False  # 单次回测邮件开关

# 获取数据
data = acquire_data(symbol=symbol, interval=interval, selected_years=selected_years, selected_months=selected_months)

# 调用回测函数
if is_batch_test:
    stats, heatmap, bt = ema_atr_atrFilter(  # 接收 bt 仍然是好的，以备后用
        is_batch_test, data, symbol, interval,
        backtest_params, strategy_params, optimize_params
    )
    process_batch_backtest(stats, heatmap, symbol, interval, bt)  # 传递 bt (即使新逻辑可能不用)
    
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
    process_single_backtest(stats, symbol, interval, bt)
    
    if is_send_single_email:
        # 发送单次回测邮件提醒
        win_rate = stats['Win Rate [%]']
        num_trades = stats['# Trades']
        subject = "单次回测完成提醒"
        body = f"单次回测已完成。胜率: {win_rate}%，交易数量: {num_trades}。"
        send_email_notification(subject, body)


