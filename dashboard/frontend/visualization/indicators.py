import pandas as pd
import pandas_ta as ta  # noqa: F401
import plotly.graph_objects as go

from frontend.visualization import theme


def get_bbands_traces(df, bb_length, bb_std):
    tech_colors = theme.get_color_scheme()
    # Clone DataFrame to avoid modifying the original
    df_copy = df.copy()
    df_copy.ta.bbands(length=bb_length, std=bb_std, append=True)

    # Check if columns exist, if not calculate with a different approach
    bb_lower = f"BBL_{bb_length}_{bb_std}"
    bb_middle = f"BBM_{bb_length}_{bb_std}"
    bb_upper = f"BBU_{bb_length}_{bb_std}"

    if bb_upper not in df_copy.columns:
        # Alternative calculation
        from pandas import Series

        std = df_copy["close"].rolling(window=bb_length).std()
        middle = df_copy["close"].rolling(window=bb_length).mean()
        upper = middle + (std * bb_std)
        lower = middle - (std * bb_std)

        df_copy[bb_upper] = upper
        df_copy[bb_middle] = middle
        df_copy[bb_lower] = lower

    traces = [
        go.Scatter(x=df_copy.index, y=df_copy[bb_upper], line=dict(color=tech_colors["upper_band"]), name="Upper Band"),
        go.Scatter(x=df_copy.index, y=df_copy[bb_middle], line=dict(color=tech_colors["middle_band"]), name="Middle Band"),
        go.Scatter(x=df_copy.index, y=df_copy[bb_lower], line=dict(color=tech_colors["lower_band"]), name="Lower Band"),
    ]
    return traces


def get_volume_trace(df):
    df_copy = df.copy()
    df_copy.index = pd.to_datetime(df_copy.timestamp, unit="s")
    return go.Bar(
        x=df_copy.index, y=df_copy["volume"], name="Volume", marker_color=theme.get_color_scheme()["volume"], opacity=0.7
    )


def get_macd_traces(df, macd_fast, macd_slow, macd_signal):
    tech_colors = theme.get_color_scheme()
    # Clone DataFrame to avoid modifying the original
    df_copy = df.copy()
    df_copy.ta.macd(fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True)

    macd = f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"
    macd_s = f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"
    macd_hist = f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"

    # Check if columns exist, if not calculate with a different approach
    if macd not in df_copy.columns:
        # Alternative calculation
        ema_fast = df_copy["close"].ewm(span=macd_fast).mean()
        ema_slow = df_copy["close"].ewm(span=macd_slow).mean()
        df_copy[macd] = ema_fast - ema_slow
        df_copy[macd_s] = df_copy[macd].ewm(span=macd_signal).mean()
        df_copy[macd_hist] = df_copy[macd] - df_copy[macd_s]

    traces = [
        go.Scatter(x=df_copy.index, y=df_copy[macd], line=dict(color=tech_colors["macd_line"]), name="MACD Line"),
        go.Scatter(x=df_copy.index, y=df_copy[macd_s], line=dict(color=tech_colors["macd_signal"]), name="MACD Signal"),
        go.Bar(
            x=df_copy.index,
            y=df_copy[macd_hist],
            name="MACD Histogram",
            marker_color=df_copy[macd_hist].apply(lambda x: "#FF6347" if x < 0 else "#32CD32"),
        ),
    ]
    return traces


def get_supertrend_traces(df, length, multiplier):
    tech_colors = theme.get_color_scheme()
    # Clone DataFrame to avoid modifying the original
    df_copy = df.copy()
    df_copy.ta.supertrend(length=length, multiplier=multiplier, append=True)

    supertrend_d = f"SUPERTd_{length}_{multiplier}"
    supertrend = f"SUPERT_{length}_{multiplier}"

    # Check if columns exist, if not calculate with a different approach
    if supertrend not in df_copy.columns:
        # Basic calculation of SuperTrend
        import numpy as np

        # Calculate ATR
        high_low = df_copy["high"] - df_copy["low"]
        high_close = np.abs(df_copy["high"] - df_copy["close"].shift())
        low_close = np.abs(df_copy["low"] - df_copy["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(length).mean()

        # Calculate SuperTrend
        hl2 = (df_copy["high"] + df_copy["low"]) / 2

        # Upper and lower bands
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)

        # Initialize SuperTrend values
        supertrend_values = pd.Series([0] * len(df_copy), index=df_copy.index)
        direction = pd.Series([0] * len(df_copy), index=df_copy.index)

        # Set first value
        supertrend_values.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1

        # Calculate SuperTrend values
        for i in range(1, len(df_copy)):
            if df_copy["close"].iloc[i - 1] <= supertrend_values.iloc[i - 1]:
                supertrend_values.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend_values.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1

            # Adjust based on previous direction
            if (direction.iloc[i] == 1 and lower_band.iloc[i] > supertrend_values.iloc[i - 1]) or (
                direction.iloc[i] == -1 and upper_band.iloc[i] < supertrend_values.iloc[i - 1]
            ):
                supertrend_values.iloc[i] = supertrend_values.iloc[i - 1]
                direction.iloc[i] = direction.iloc[i - 1]

        df_copy[supertrend] = supertrend_values
        df_copy[supertrend_d] = direction

    df_filtered = df_copy[df_copy[supertrend] > 0]

    if len(df_filtered) == 0:
        # If no data after filtering, return empty trace
        return [go.Scatter(x=[], y=[], mode="lines", name="SuperTrend")]

    # Create segments for line with different colors
    segments = []
    current_segment = {"x": [], "y": [], "color": None}

    for i in range(len(df_filtered)):
        if i == 0 or df_filtered[supertrend_d].iloc[i] == df_filtered[supertrend_d].iloc[i - 1]:
            current_segment["x"].append(df_filtered.index[i])
            current_segment["y"].append(df_filtered[supertrend].iloc[i])
            current_segment["color"] = tech_colors["buy"] if df_filtered[supertrend_d].iloc[i] == 1 else tech_colors["sell"]
        else:
            segments.append(current_segment)
            current_segment = {
                "x": [df_filtered.index[i - 1], df_filtered.index[i]],
                "y": [df_filtered[supertrend].iloc[i - 1], df_filtered[supertrend].iloc[i]],
                "color": tech_colors["buy"] if df_filtered[supertrend_d].iloc[i] == 1 else tech_colors["sell"],
            }

    segments.append(current_segment)

    # Create traces from segments
    traces = [
        go.Scatter(x=segment["x"], y=segment["y"], mode="lines", line=dict(color=segment["color"], width=2), name="SuperTrend")
        for segment in segments
        if len(segment["x"]) > 0
    ]

    return traces


def get_cci_traces(df, length, overbought=100, oversold=-100):
    tech_colors = theme.get_color_scheme()
    # 复制DataFrame避免修改原始数据
    df_copy = df.copy()

    # 计算CCI指标
    df_copy.ta.cci(length=length, append=True)
    cci_col = f"CCI_{length}"

    # 如果CCI列不存在，手动计算
    if cci_col not in df_copy.columns:
        # 手动CCI计算
        typical_price = (df_copy["high"] + df_copy["low"] + df_copy["close"]) / 3
        sma_tp = typical_price.rolling(window=length).mean()
        mean_deviation = abs(typical_price - sma_tp).rolling(window=length).mean()
        df_copy[cci_col] = (typical_price - sma_tp) / (0.015 * mean_deviation)

    # 创建CCI指标的主线迹线
    cci_trace = go.Scatter(
        x=df_copy.index,
        y=df_copy[cci_col],
        mode="lines",
        line=dict(color=tech_colors["macd_line"], width=1.5),
        name=f"CCI({length})",
    )

    # 添加超买超卖水平线
    overbought_trace = go.Scatter(
        x=[df_copy.index[0], df_copy.index[-1]],
        y=[overbought, overbought],
        mode="lines",
        line=dict(color=tech_colors["sell"], width=1, dash="dash"),
        name=f"Overbought ({overbought})",
    )

    oversold_trace = go.Scatter(
        x=[df_copy.index[0], df_copy.index[-1]],
        y=[oversold, oversold],
        mode="lines",
        line=dict(color=tech_colors["buy"], width=1, dash="dash"),
        name=f"Oversold ({oversold})",
    )

    zero_line_trace = go.Scatter(
        x=[df_copy.index[0], df_copy.index[-1]],
        y=[0, 0],
        mode="lines",
        line=dict(color="gray", width=0.5, dash="dot"),
        name="Zero Line",
    )

    traces = [cci_trace, overbought_trace, oversold_trace, zero_line_trace]

    return traces
