import talib
import numpy as np

from backtesting import Backtest, Strategy
from backtesting.lib import crossover

def ema_atr_atrFilter(is_batch_test, data, symbol, interval, backtest_params=None, strategy_params=None, optimize_params=None):
    # 解包 strategy_params 到简单变量名（仅用于单次回测），添加 single_ 前缀
    single_ema_period = strategy_params.get('ema_period', 4)
    single_atr_period = strategy_params.get('atr_period', 18)
    single_multiplier = strategy_params.get('multiplier', 2)
    single_sl_multiplier = strategy_params.get('sl_multiplier', 3)
    single_atr_threshold_pct = strategy_params.get('atr_threshold_pct', 0)
    single_rr = strategy_params.get('rr', 2)

    # 定义策略类
    class EmaAtrStrategy(Strategy):
        # 添加优化参数作为类变量（用于批量回测）
        ema_period = single_ema_period
        atr_period = single_atr_period
        multiplier = single_multiplier
        sl_multiplier = single_sl_multiplier
        atr_threshold_pct = single_atr_threshold_pct
        rr = single_rr

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

    if is_batch_test:
        # 解析 optimize_params 并引用
        ema_period_range = optimize_params.get('ema_period_range', range(2, 302, 30))
        atr_period_range = optimize_params.get('atr_period_range', range(3, 23, 2))  # 转换为list
        multiplier_range = optimize_params.get('multiplier_range', range(3, 23, 2))
        sl_multiplier_range = optimize_params.get('sl_multiplier_range', [1])
        atr_threshold_pct_range = optimize_params.get('atr_threshold_pct_range', list(np.arange(0.00001, 0.00101, 0.0001)))
        rr_range = optimize_params.get('rr_range', [1])
        max_tries = optimize_params.get('max_tries', 6)
        method = optimize_params.get('method', 'sambo')
        return_heatmap = optimize_params.get('return_heatmap', True)
        maximize = optimize_params.get('maximize', None)
        
        stats, heatmap = bt.optimize(
            ema_period=ema_period_range,
            atr_period=atr_period_range,
            multiplier=multiplier_range,
            sl_multiplier=sl_multiplier_range,
            atr_threshold_pct=atr_threshold_pct_range,
            rr=rr_range,
            max_tries=max_tries,
            method=method,
            return_heatmap=return_heatmap,
            maximize=maximize
        )
        print(heatmap)
        return stats, heatmap, bt  # 修改：返回 bt 以便在 process_batch_backtest 中使用
    else:
        stats = bt.run()
        print(stats)
        return stats, bt
