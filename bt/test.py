import pandas as pd

def analyze_wins_losses(csv_file, output_file):
    # 读取CSV文件
    df = pd.read_csv(csv_file)
    
    # 将EntryTime转换为datetime格式
    df['EntryTime'] = pd.to_datetime(df['EntryTime'])
    
    # 提取小时
    df['hour'] = df['EntryTime'].dt.hour
    
    # 判断胜负：PnL > 0 为win，否则为loss
    df['result'] = df['PnL'].apply(lambda x: 'win' if x > 0 else 'loss')
    
    # 按小时统计result的计数
    stats = df.groupby('hour')['result'].value_counts().unstack(fill_value=0)
    
    # 确保列名为wins和losses
    stats = stats.reindex(columns=['win', 'loss'], fill_value=0)
    stats.columns = ['wins', 'losses']
    
    # 重置索引，使hour成为列
    stats = stats.reset_index()
    
    # 新增：计算净胜场（wins - losses）
    stats['net_wins'] = stats['wins'] - stats['losses']
    
    # 保存到新CSV文件
    stats.to_csv(output_file, index=False)
    print(f"分析完成，结果已保存到 {output_file}")

# 示例使用（使用完整路径）
analyze_wins_losses(r'D:\tools\vscode\vs\quickearn\result\single_20251024_001834\trades_win47.69897130481863_trades1847.csv', 'hourly_stats1.csv')