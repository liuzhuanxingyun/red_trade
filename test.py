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


import talib
import numpy as np

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

def ema_atr_atrFilter(is_batch_test, data, symbol, interval, backtest_params=None, strategy_params=None, optimize_params=None):
    if is_batch_test:
        return batch_ema_atr_atrFilter(data, symbol, interval, backtest_params, optimize_params)
    else:
        return single_ema_atr_atrFilter(data, symbol, interval, backtest_params, strategy_params)

def single_ema_atr_atrFilter(data, symbol, interval, backtest_params=None, strategy_params=None):
    # 解包 strategy_params 到简单变量名
    ema_period = strategy_params.get('ema_period', 4)
    atr_period = strategy_params.get('atr_period', 18)
    multiplier = strategy_params.get('multiplier', 2)
    sl_multiplier = strategy_params.get('sl_multiplier', 3)
    atr_threshold_pct = strategy_params.get('atr_threshold_pct', 0)
    rr = strategy_params.get('rr', 2)

    # 定义策略类
    class EmaAtrStrategy(Strategy):
        def init(self):
            price = self.data.Close
            self.ema = self.I(talib.EMA, price, timeperiod=ema_period)
            self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=atr_period)

        def next(self):
            # 检查ATR波动率过滤器（基于当前价格的百分比）
            if self.atr[-1] / self.data.Close[-1] < atr_threshold_pct:
                return  # 如果ATR低于阈值百分比，不执行交易

            upper = self.ema + self.atr * multiplier
            lower = self.ema - self.atr * multiplier

            # 计算止损和止盈距离
            sl_distance = self.atr * sl_multiplier
            tp_distance = sl_distance * rr  # 止盈距离 = 止损距离 * rr

            # 只有在空仓时才能开仓
            if self.position.size == 0:
                if crossover(self.data.Close, upper):
                    self.buy(tp=self.data.Close + tp_distance, sl=self.data.Close - sl_distance)
                elif crossover(lower, self.data.Close):
                    self.sell(tp=self.data.Close - tp_distance, sl=self.data.Close + sl_distance)
    
    bt = Backtest(data, EmaAtrStrategy, **backtest_params)
    stats = bt.run()
    print(stats)
    return stats, bt

def batch_ema_atr_atrFilter(data, symbol, interval, backtest_params=None, optimize_params=None):
    # 解析 optimize_params 到变量
    ema_period_range = optimize_params.get('ema_period_range', range(3, 23, 2))
    atr_period_range = optimize_params.get('atr_period_range', range(3, 23, 2))
    multiplier_range = optimize_params.get('multiplier_range', range(3, 23, 2))
    atr_threshold_pct_range = optimize_params.get('atr_threshold_pct_range', list(np.arange(0.00001, 0.00101, 0.0001)))
    rr_range = optimize_params.get('rr_range', [1])
    sl_multiplier_range = optimize_params.get('sl_multiplier_range', [1])

    # 定义策略类
    class EmaAtrStrategy(Strategy):
        # 添加优化参数作为类变量
        ema_period = 21
        atr_period = 10
        multiplier = 4
        atr_threshold_pct = 0  # ATR波动率过滤器阈值（百分比，基于当前价格）
        sl_multiplier = 1  # 止损ATR乘数，用于计算止损距离
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
            sl_distance = self.atr * self.sl_multiplier
            tp_distance = sl_distance * self.rr  # 止盈距离 = 止损距离 * rr

            # 只有在空仓时才能开仓
            if self.position.size == 0:
                if crossover(self.data.Close, upper):
                    self.buy(tp=self.data.Close + tp_distance, sl=self.data.Close - sl_distance)
                elif crossover(lower, self.data.Close):
                    self.sell(tp=self.data.Close - tp_distance, sl=self.data.Close + sl_distance)
    
    bt = Backtest(data, EmaAtrStrategy, **backtest_params)
    stats, heatmap = bt.optimize(
        ema_period=ema_period_range,
        atr_period=atr_period_range,
        multiplier=multiplier_range,
        atr_threshold_pct=atr_threshold_pct_range,
        rr=rr_range,
        sl_multiplier=sl_multiplier_range,
        **{k: v for k, v in optimize_params.items() if k not in ['ema_period_range', 'atr_period_range', 'multiplier_range', 'atr_threshold_pct_range', 'rr_range', 'sl_multiplier_range']}
    )
    print(heatmap)
    return stats, heatmap