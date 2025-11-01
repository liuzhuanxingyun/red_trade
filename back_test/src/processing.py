import os

from datetime import datetime
from backtesting.lib import plot_heatmaps
from .utils import create_3d_heatmap_cube

def process_batch_backtest(stats, heatmap, symbol, interval, bt):
    """
    处理批量回测结果：保存文件、生成图表。
    
    参数:
    - stats: 回测统计结果
    - heatmap: 热力图数据
    - symbol: 交易对符号
    - interval: 时间间隔
    - bt: Backtest 对象 (此处不再需要)
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
    batch_folder = f"back_test/results/batch_{timestamp}"
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

def process_single_backtest(stats, symbol, interval, bt):
    """
    处理单次回测结果：保存文件、生成图表。
    
    参数:
    - stats: 回测统计结果
    - symbol: 交易对符号
    - interval: 时间间隔
    - bt: Backtest 对象，用于生成图表
    """
    # 生成时间戳并创建新文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    single_folder = f"back_test/results/single_{timestamp}"
    os.makedirs(single_folder, exist_ok=True)
    
    # 修改文件名以包含胜率和交易数量
    win_rate = stats['Win Rate [%]']
    num_trades = stats['# Trades']
    trades_filename = f'{single_folder}/trades_win{win_rate}_trades{num_trades}.csv'
    plot_filename = f'{single_folder}/ema_atr_win{win_rate}_trades{num_trades}.html'
    
    stats._trades.to_csv(trades_filename, index=True)
    bt.plot(filename=plot_filename, plot_trades=True, open_browser=True)