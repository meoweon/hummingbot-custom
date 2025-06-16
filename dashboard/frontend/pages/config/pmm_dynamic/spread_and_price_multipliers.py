import pandas_ta as ta  # noqa: F401
import pandas as pd
import numpy as np


def get_pmm_dynamic_multipliers(df, macd_fast, macd_slow, macd_signal, natr_length):
    """
    Get the spread and price multipliers for PMM Dynamic
    """
    # 使用安全的方式计算NATR
    df_copy = df.copy()

    # 尝试使用pandas_ta计算natr
    natr_result = ta.natr(df_copy["high"], df_copy["low"], df_copy["close"], length=natr_length)

    # 如果结果为None，使用手动计算
    if natr_result is None:
        # 计算ATR
        high_low = df_copy["high"] - df_copy["low"]
        high_close = np.abs(df_copy["high"] - df_copy["close"].shift())
        low_close = np.abs(df_copy["low"] - df_copy["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(natr_length).mean()

        # 计算NATR (标准化ATR)
        natr = atr / df_copy["close"] * 100
        natr = natr / 100  # 转换为小数
    else:
        natr = natr_result / 100

    # 安全计算MACD
    try:
        macd_output = ta.macd(df_copy["close"], fast=macd_fast, slow=macd_slow, signal=macd_signal)
        macd = macd_output[f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"]
        macdh = macd_output[f"MACDh_{macd_fast}_{macd_slow}_{macd_signal}"]
    except Exception as e:
        # 如果MACD计算失败，使用手动计算
        ema_fast = df_copy["close"].ewm(span=macd_fast).mean()
        ema_slow = df_copy["close"].ewm(span=macd_slow).mean()
        macd = ema_fast - ema_slow
        macd_signal_line = macd.ewm(span=macd_signal).mean()
        macdh = macd - macd_signal_line

    # 确保有有效数据再进行标准化
    if len(macd) > 0 and macd.std() != 0:
        macd_signal_val = -(macd - macd.mean()) / macd.std()
    else:
        macd_signal_val = pd.Series(0, index=df_copy.index)

    macdh_signal = macdh.apply(lambda x: 1 if x > 0 else -1)
    max_price_shift = natr / 2
    price_multiplier = (0.5 * macd_signal_val + 0.5 * macdh_signal) * max_price_shift

    return price_multiplier, natr
