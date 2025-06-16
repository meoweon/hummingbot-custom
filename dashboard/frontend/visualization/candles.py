import pandas as pd
import plotly.graph_objects as go

from frontend.visualization import theme
from frontend.utils.i18n import t


def get_candlestick_trace(df):
    return go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name=t("Candlesticks"),
        increasing_line_color="#2ECC71",
        decreasing_line_color="#E74C3C",
        hovertext=[
            f"{t('open')}: {row['open']}<br>"
            + f"{t('high')}: {row['high']}<br>"
            + f"{t('low')}: {row['low']}<br>"
            + f"{t('close')}: {row['close']}"
            for _, row in df.iterrows()
        ],
    )


def get_bt_candlestick_trace(df):
    df.index = pd.to_datetime(df.timestamp, unit="s")
    return go.Scatter(
        x=df.index,
        y=df["close"],
        mode="lines",
        name=t("Candlestick"),
        line=dict(color=theme.get_color_scheme()["price"]),
    )
