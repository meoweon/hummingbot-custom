import pandas_ta as ta  # noqa: F401
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from frontend.visualization import theme


def get_signal_traces(buy_signals, sell_signals):
    tech_colors = theme.get_color_scheme()
    traces = [
        go.Scatter(
            x=buy_signals.index,
            y=buy_signals["close"],
            mode="markers",
            marker=dict(color=tech_colors["buy_signal"], size=10, symbol="triangle-up"),
            name="Buy Signal",
        ),
        go.Scatter(
            x=sell_signals.index,
            y=sell_signals["close"],
            mode="markers",
            marker=dict(color=tech_colors["sell_signal"], size=10, symbol="triangle-down"),
            name="Sell Signal",
        ),
    ]
    return traces


def get_bollinger_v1_signal_traces(df, bb_length, bb_std, bb_long_threshold, bb_short_threshold):
    # Add Bollinger Bands
    candles = df.copy()
    candles.ta.bbands(length=bb_length, std=bb_std, append=True)

    # 检查BBP列是否存在，如果不存在则手动计算
    bbp_column = f"BBP_{bb_length}_{bb_std}"
    if bbp_column not in candles.columns:
        # 计算BB中轨线
        bb_middle = f"BBM_{bb_length}_{bb_std}"
        if bb_middle not in candles.columns:
            mid = candles["close"].rolling(window=bb_length).mean()
            candles[bb_middle] = mid
        else:
            mid = candles[bb_middle]

        # 计算BB百分比位置 (BBP)
        candles[bbp_column] = (candles["close"] - mid) / (candles["close"].rolling(window=bb_length).std() * bb_std)

    # Generate conditions
    buy_signals = candles[candles[bbp_column] < bb_long_threshold]
    sell_signals = candles[candles[bbp_column] > bb_short_threshold]

    return get_signal_traces(buy_signals, sell_signals)


def get_macd_bb_v1_signal_traces(df, bb_length, bb_std, bb_long_threshold, bb_short_threshold, macd_fast, macd_slow, macd_signal):
    # 准备数据副本
    df_copy = df.copy()

    # 添加布林带
    df_copy.ta.bbands(length=bb_length, std=bb_std, append=True)

    # 检查BBP列是否存在，如果不存在则手动计算
    bbp_column = f"BBP_{bb_length}_{bb_std}"
    if bbp_column not in df_copy.columns:
        # 计算BB中轨线
        bb_middle = f"BBM_{bb_length}_{bb_std}"
        if bb_middle not in df_copy.columns:
            mid = df_copy["close"].rolling(window=bb_length).mean()
            df_copy[bb_middle] = mid
        else:
            mid = df_copy[bb_middle]

        # 计算BB百分比位置 (BBP)
        df_copy[bbp_column] = (df_copy["close"] - mid) / (df_copy["close"].rolling(window=bb_length).std() * bb_std)

    # 添加MACD
    df_copy.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True)

    # 检查MACD列是否存在
    macd_column = f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"
    macdh_column = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"

    if macd_column not in df_copy.columns or macdh_column not in df_copy.columns:
        # 手动计算MACD
        ema_fast = df_copy["close"].ewm(span=macd_fast).mean()
        ema_slow = df_copy["close"].ewm(span=macd_slow).mean()
        df_copy[macd_column] = ema_fast - ema_slow
        signal_line = df_copy[macd_column].ewm(span=macd_signal).mean()
        df_copy[macdh_column] = df_copy[macd_column] - signal_line

    # 决策逻辑
    bbp = df_copy[bbp_column]
    macdh = df_copy[macdh_column]
    macd = df_copy[macd_column]

    buy_signals = df_copy[(bbp < bb_long_threshold) & (macdh > 0) & (macd < 0)]
    sell_signals = df_copy[(bbp > bb_short_threshold) & (macdh < 0) & (macd > 0)]

    return get_signal_traces(buy_signals, sell_signals)


def get_supertrend_v1_signal_traces(df, length, multiplier, percentage_threshold):
    # 准备数据副本
    df_copy = df.copy()

    # 添加SuperTrend指标
    df_copy.ta.supertrend(length=length, multiplier=multiplier, append=True)

    # 检查SuperTrend列是否存在
    supertrend_column = f"SUPERT_{length}_{multiplier}"
    supertrend_direction_column = f"SUPERTd_{length}_{multiplier}"

    if supertrend_column not in df_copy.columns or supertrend_direction_column not in df_copy.columns:
        # 手动计算SuperTrend
        # 计算ATR
        high_low = df_copy["high"] - df_copy["low"]
        high_close = np.abs(df_copy["high"] - df_copy["close"].shift())
        low_close = np.abs(df_copy["low"] - df_copy["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(length).mean()

        # 计算基本带
        hl2 = (df_copy["high"] + df_copy["low"]) / 2

        # 上下带
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # 初始化SuperTrend值
        supertrend_values = pd.Series(index=df_copy.index)
        direction = pd.Series(index=df_copy.index)

        # 设置初始值
        supertrend_values.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1

        # 计算SuperTrend值
        for i in range(1, len(df_copy)):
            if df_copy["close"].iloc[i - 1] <= supertrend_values.iloc[i - 1]:
                supertrend_values.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend_values.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1

            # 基于先前方向调整
            if (direction.iloc[i] == 1 and lower_band.iloc[i] > supertrend_values.iloc[i - 1]) or (
                direction.iloc[i] == -1 and upper_band.iloc[i] < supertrend_values.iloc[i - 1]
            ):
                supertrend_values.iloc[i] = supertrend_values.iloc[i - 1]
                direction.iloc[i] = direction.iloc[i - 1]

        df_copy[supertrend_column] = supertrend_values
        df_copy[supertrend_direction_column] = direction

    # 计算价格与SuperTrend的百分比距离
    df_copy["percentage_distance"] = abs(df_copy["close"] - df_copy[supertrend_column]) / df_copy["close"]

    # 生成多空条件
    buy_signals = df_copy[(df_copy[supertrend_direction_column] == 1) & (df_copy["percentage_distance"] < percentage_threshold)]
    sell_signals = df_copy[(df_copy[supertrend_direction_column] == -1) & (df_copy["percentage_distance"] < percentage_threshold)]

    return get_signal_traces(buy_signals, sell_signals)


def get_cci_v1_signal_traces(
    df,
    length,
    overbought,
    oversold,
):
    # 准备数据副本
    df_copy = df.copy()

    # 添加CCI指标
    df_copy.ta.cci(length=length, append=True)
    cci_col = f"CCI_{length}"

    # 如果CCI列不存在，手动计算
    if cci_col not in df_copy.columns:
        # 手动CCI计算
        typical_price = (df_copy["high"] + df_copy["low"] + df_copy["close"]) / 3
        sma_tp = typical_price.rolling(window=length).mean()
        mean_deviation = abs(typical_price - sma_tp).rolling(window=length).mean()
        df_copy[cci_col] = (typical_price - sma_tp) / (0.015 * mean_deviation)

    # 计算跨越信号
    df_copy["cci_prev"] = df_copy[cci_col].shift(1)

    # 初始化信号数据帧
    buy_signals = pd.DataFrame()
    sell_signals = pd.DataFrame()

    # 买入信号：当CCI向下穿过超卖水平时触发
    oversold_cond = (df_copy["cci_prev"] >= oversold) & (df_copy[cci_col] < oversold)
    buy_signals = df_copy[oversold_cond]

    # 卖出信号：当CCI向上穿过超买水平时触发
    overbought_cond = (df_copy["cci_prev"] <= overbought) & (df_copy[cci_col] > overbought)
    sell_signals = df_copy[overbought_cond]

    return get_signal_traces(buy_signals, sell_signals)
