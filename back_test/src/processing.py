import os

from datetime import datetime
from backtesting.lib import plot_heatmaps
from .utils import create_3d_heatmap_cube

def process_batch_backtest(stats, heatmap, symbol, interval, bt, results_dir='back_test/results'):
    """
    处理批量回测结果：保存文件、生成图表。
    
    参数:
    - stats: 回测统计结果
    - heatmap: 热力图数据
    - symbol: 交易对符号
    - interval: 时间间隔
    - bt: Backtest 对象 (此处不再需要)
    - results_dir: 结果保存目录
    """
    # 将 heatmap 转换为 DataFrame
    heatmap_df = heatmap.reset_index()
    
    # 从 heatmap._full_stats 中高效提取交易数量，避免重新运行回测
    if hasattr(heatmap, '_full_stats'):
        trades_list = [s['# Trades'] for s in heatmap._full_stats]
        heatmap_df['# Trades'] = trades_list
    else:
        # 如果 _full_stats 不可用，则保留原有逻辑作为后备，但会很慢
        print("警告: heatmap._full_stats 不可用，将重新运行回测以获取交易数量，这会非常耗时。")
        trades_list = []
        for params in heatmap.index:
            param_dict = dict(zip(heatmap.index.names, params))
            temp_stats = bt.run(**param_dict)
            trades_list.append(temp_stats['# Trades'])
        heatmap_df['# Trades'] = trades_list

    # 重命名列
    new_columns = list(heatmap.index.names) + ['win_rate', '# Trades']
    heatmap_df.columns = new_columns
    
    # 聚合：对 ema_period, atr_period, multiplier 分组，取 win_rate 的最大值（或平均）
    aggregated = heatmap_df.groupby(['ema_period', 'atr_period', 'multiplier'])['win_rate'].max().reset_index()
    
    # 生成时间戳并创建新文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_folder = f"{results_dir}/batch_{timestamp}"
    os.makedirs(batch_folder, exist_ok=True)
    
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

def process_single_backtest(stats, symbol, interval, bt, results_dir='back_test/results', strategy_params=None):
    """
    处理单次回测结果：保存文件、生成图表。
    
    参数:
    - stats: 回测统计结果
    - symbol: 交易对符号
    - interval: 时间间隔
    - bt: Backtest 对象，用于生成图表
    - results_dir: 结果保存目录
    - strategy_params: 策略参数，用于获取 rr
    """
    # 生成时间戳并创建新文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    single_folder = f"{results_dir}/single_{timestamp}"
    os.makedirs(single_folder, exist_ok=True)
    
    # 修改文件名以包含胜率和交易数量
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']
    trades_filename = f'{single_folder}/trades_win{win_rate}_trades{num_trades}.csv'
    plot_filename = f'{single_folder}/ema_atr_win{win_rate}_trades{num_trades}.html'
    
    stats._trades.to_csv(trades_filename, index=True)
    bt.plot(filename=plot_filename, plot_trades=True, open_browser=True)

    # 新增：计算不同小时的胜率
    rr = strategy_params.get('rr', 2) if strategy_params else 2
    calculate_hourly_win_rate(stats, single_folder, rr)

    # 新增：计算做多和做空的胜率
    calculate_long_short_win_rate(stats, single_folder)

def calculate_hourly_win_rate(stats, folder_path, rr=2):
    """
    计算当前参数在不同小时时间的净胜次数（胜利次数乘以rr减去失败次数）。
    
    参数:
    - stats: 回测统计结果，包含 _trades
    - folder_path: 保存结果的文件夹路径
    - rr: 风险回报比，默认 2
    """
    import pandas as pd
    
    # 获取交易数据
    trades = stats._trades
    if trades.empty:
        print("无交易数据，无法计算小时净胜次数。")
        return
    
    # 假设时间戳列名为 'EntryTime' 或类似，提取小时
    if 'EntryTime' not in trades.columns:
        print("交易数据中无时间戳列，无法计算小时净胜次数。")
        return
    
    # 提取小时（0-23）
    trades['Hour'] = pd.to_datetime(trades['EntryTime']).dt.hour
    
    # 计算每个小时的统计
    hourly_stats = []
    for hour in range(24):
        hour_trades = trades[trades['Hour'] == hour]
        if not hour_trades.empty:
            total_trades = len(hour_trades)
            winning_trades = (hour_trades['PnL'] > 0).sum()  # 盈利交易数
            losing_trades = total_trades - winning_trades  # 失败次数
            net_wins = winning_trades * rr - losing_trades  # 净胜次数：胜次数 * rr - 败次数
            hourly_stats.append({
                'Hour': hour,
                'Total Trades': total_trades,
                'Winning Trades': winning_trades,
                'Losing Trades': losing_trades,
                'Net Wins': net_wins
            })
        else:
            hourly_stats.append({
                'Hour': hour,
                'Total Trades': 0,
                'Winning Trades': 0,
                'Losing Trades': 0,
                'Net Wins': 0
            })
    
    # 转换为 DataFrame 并保存
    hourly_df = pd.DataFrame(hourly_stats)
    hourly_filename = f'{folder_path}/hourly_net_wins.csv'
    hourly_df.to_csv(hourly_filename, index=False)
    print(f"小时净胜次数结果已保存到: {hourly_filename}")
    print(hourly_df)

def calculate_long_short_win_rate(stats, folder_path):
    """
    计算做多和做空的胜率。
    
    参数:
    - stats: 回测统计结果，包含 _trades
    - folder_path: 保存结果的文件夹路径
    """
    import pandas as pd
    
    # 获取交易数据
    trades = stats._trades
    if trades.empty:
        print("无交易数据，无法计算做多做空胜率。")
        return
    
    # 使用 'Size' 列判断：正数为做多，负数为做空
    if 'Size' not in trades.columns:
        print("交易数据中无 'Size' 列，无法计算做多做空胜率。")
        return
    
    # 统计做多交易（Size > 0）
    long_trades = trades[trades['Size'] > 0]
    long_total = len(long_trades)
    long_winning = (long_trades['PnL'] > 0).sum()
    long_win_rate = (long_winning / long_total * 100) if long_total > 0 else 0
    
    # 统计做空交易（Size < 0）
    short_trades = trades[trades['Size'] < 0]
    short_total = len(short_trades)
    short_winning = (short_trades['PnL'] > 0).sum()
    short_win_rate = (short_winning / short_total * 100) if short_total > 0 else 0
    
    # 创建 DataFrame
    ls_df = pd.DataFrame({
        'Type': ['Long', 'Short'],
        'Total Trades': [long_total, short_total],
        'Winning Trades': [long_winning, short_winning],
        'Win Rate (%)': [long_win_rate, short_win_rate]
    })
    
    # 保存到 CSV
    ls_filename = f'{folder_path}/long_short_win_rate.csv'
    ls_df.to_csv(ls_filename, index=False)
    print(f"做多做空胜率结果已保存到: {ls_filename}")
    print(ls_df)