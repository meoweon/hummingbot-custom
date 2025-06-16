import pandas_ta as ta  # noqa: F401
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from frontend.components.backtesting import backtesting_section
from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.pages.config.dman_v3.user_inputs import user_inputs
from frontend.pages.config.utils import get_candles
from frontend.st_utils import get_backend_api_client, initialize_st_page, t
from frontend.visualization import theme
from frontend.visualization.backtesting import create_backtesting_figure
from frontend.visualization.backtesting_metrics import render_accuracy_metrics, render_backtesting_metrics, render_close_types
from frontend.visualization.candles import get_candlestick_trace
from frontend.visualization.indicators import get_bbands_traces, get_volume_trace
from frontend.visualization.utils import add_traces_to_fig


def get_dman_v3_signal_traces(df, bb_length, bb_std, bb_long_threshold, bb_short_threshold):
    """生成DMAN V3策略的交易信号"""
    # 计算布林带指标
    df.ta.bbands(length=bb_length, std=bb_std, append=True)

    # 生成信号
    long_condition = df[f"BBP_{bb_length}_{bb_std}"] < bb_long_threshold
    short_condition = df[f"BBP_{bb_length}_{bb_std}"] > bb_short_threshold

    # 创建信号标记
    long_signals = go.Scatter(
        x=df[long_condition].index,
        y=df[long_condition]["low"] * 0.999,
        mode="markers",
        marker=dict(symbol="triangle-up", size=10, color="green"),
        name=t("Long Signal"),
    )

    short_signals = go.Scatter(
        x=df[short_condition].index,
        y=df[short_condition]["high"] * 1.001,
        mode="markers",
        marker=dict(symbol="triangle-down", size=10, color="red"),
        name=t("Short Signal"),
    )

    return [long_signals, short_signals]


# Initialize the Streamlit page
initialize_st_page(page_title=t("DMAN V3"), icon="🤖", initial_sidebar_state="expanded")
backend_api_client = get_backend_api_client()

st.text(t("This tool will let you create a config for DMAN V3 and visualize the strategy."))
get_default_config_loader("dman_v3")

inputs = user_inputs()
st.session_state["default_config"].update(inputs)

st.write(t("### Visualizing DMAN V3 Strategy"))
days_to_visualize = st.number_input(t("Days to Visualize"), min_value=1, max_value=365, value=7)

# Load candle data
candles = get_candles(
    connector_name=inputs["candles_connector"],
    trading_pair=inputs["candles_trading_pair"],
    interval=inputs["interval"],
    days=days_to_visualize,
)

# Create a subplot with 2 rows
fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    subplot_titles=(t("Candlestick with Bollinger Bands"), t("Volume")),
    row_heights=[0.8, 0.2],
)

add_traces_to_fig(fig, [get_candlestick_trace(candles)], row=1, col=1)
add_traces_to_fig(fig, get_bbands_traces(candles, inputs["bb_length"], inputs["bb_std"]), row=1, col=1)
add_traces_to_fig(
    fig,
    get_dman_v3_signal_traces(
        candles, inputs["bb_length"], inputs["bb_std"], inputs["bb_long_threshold"], inputs["bb_short_threshold"]
    ),
    row=1,
    col=1,
)
add_traces_to_fig(fig, [get_volume_trace(candles)], row=2, col=1)

fig.update_layout(**theme.get_default_layout())
# Use Streamlit's functionality to display the plot
st.plotly_chart(fig, use_container_width=True)

# Run backtesting
bt_results = backtesting_section(inputs, backend_api_client)
if bt_results:
    fig = create_backtesting_figure(df=bt_results["processed_data"], executors=bt_results["executors"], config=inputs)
    c1, c2 = st.columns([0.9, 0.1])
    with c1:
        render_backtesting_metrics(bt_results["results"])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        render_accuracy_metrics(bt_results["results"])
        st.write("---")
        render_close_types(bt_results["results"])

st.write("---")
render_save_config(st.session_state["default_config"]["id"], st.session_state["default_config"])
