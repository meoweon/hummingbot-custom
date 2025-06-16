import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.pages.config.utils import get_candles
from frontend.st_utils import get_backend_api_client, initialize_st_page
from frontend.visualization import theme
from frontend.visualization.candles import get_candlestick_trace
from frontend.visualization.utils import add_traces_to_fig
from frontend.utils.i18n import t
from frontend.pages.config.spot_perp_arbitrage.user_inputs import user_inputs

# Initialize the Streamlit page
initialize_st_page(page_title=t("spot_perp_arb_title"), icon="💹", initial_sidebar_state="expanded")
backend_api_client = get_backend_api_client()

get_default_config_loader("spot_perp_arbitrage")

# Get user inputs
inputs = user_inputs()
st.session_state["default_config"].update(inputs)

# Load candle data for both spot and perpetual markets
spot_candles = get_candles(
    connector_name=inputs["spot_connector"],
    trading_pair=inputs["trading_pair"],
    interval=inputs["interval"],
    days=inputs["days_to_visualize"],
)

perp_candles = get_candles(
    connector_name=inputs["perp_connector"],
    trading_pair=inputs["trading_pair"],
    interval=inputs["interval"],
    days=inputs["days_to_visualize"],
)

# Create visualization
fig = make_subplots(
    rows=2,
    cols=1,
    subplot_titles=(
        f'{t("spot_perp_arb_title")} - {inputs["trading_pair"]} ({inputs["interval"]})',
        t("price_difference"),
    ),
    row_heights=[0.7, 0.3],
    vertical_spacing=0.05,
)

# Add spot market line chart
spot_line = go.Scatter(
    x=spot_candles.index,
    y=spot_candles["close"],
    mode="lines",
    name=f"Spot ({inputs['spot_connector']})",
    line=dict(color="#3498DB", width=1.5),  # 蓝色
    hovertemplate="时间: %{x}<br>" + "价格: %{y:,.2f}<br>" + "<extra></extra>",
)
add_traces_to_fig(fig, [spot_line], row=1, col=1)

# Add perpetual market line chart
perp_line = go.Scatter(
    x=perp_candles.index,
    y=perp_candles["close"],
    mode="lines",
    name=f"Perp ({inputs['perp_connector']})",
    line=dict(color="#F1C40F", width=1.5),  # 黄色
    hovertemplate="时间: %{x}<br>" + "价格: %{y:,.2f}<br>" + "<extra></extra>",
)
add_traces_to_fig(fig, [perp_line], row=1, col=1)

# Calculate and plot price difference
if spot_candles is not None and perp_candles is not None and not spot_candles.empty and not perp_candles.empty:
    # Calculate price difference percentage
    spot_close = spot_candles["close"]
    perp_close = perp_candles["close"]
    price_diff_pct = ((perp_close - spot_close) / spot_close) * 100

    # Add price difference scatter plot
    price_diff_scatter = go.Scatter(
        x=spot_candles.index,
        y=price_diff_pct,
        mode="lines",
        name=t("price_difference"),
        line=dict(color="#E67E22", width=1.5),  # 橙色
        hovertemplate="时间: %{x}<br>" + "价差: %{y:.4f}%<br>" + "<extra></extra>",
    )
    add_traces_to_fig(fig, [price_diff_scatter], row=2, col=1)

    # Add minimum price difference threshold lines
    threshold_lines = [
        go.Scatter(
            x=[spot_candles.index[0], spot_candles.index[-1]],
            y=[inputs["min_price_diff_pct"] * 100, inputs["min_price_diff_pct"] * 100],
            mode="lines",
            name=t("min_price_diff_upper"),
            line=dict(color="#E74C3C", dash="dash", width=1),  # 红色虚线
            hovertemplate="阈值: %{y:.4f}%<br><extra></extra>",
        ),
        go.Scatter(
            x=[spot_candles.index[0], spot_candles.index[-1]],
            y=[-inputs["min_price_diff_pct"] * 100, -inputs["min_price_diff_pct"] * 100],
            mode="lines",
            name=t("min_price_diff_lower"),
            line=dict(color="#E74C3C", dash="dash", width=1),  # 红色虚线
            hovertemplate="阈值: %{y:.4f}%<br><extra></extra>",
        ),
    ]
    add_traces_to_fig(fig, threshold_lines, row=2, col=1)

# Update layout
layout_updates = {
    "height": 1000,
    "showlegend": True,
    "legend": dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)"),
    "xaxis_gridcolor": "rgba(128, 128, 128, 0.2)",
    "yaxis_gridcolor": "rgba(128, 128, 128, 0.2)",
    "xaxis2_gridcolor": "rgba(128, 128, 128, 0.2)",
    "yaxis2_gridcolor": "rgba(128, 128, 128, 0.2)",
    "hoverlabel": dict(bgcolor="rgba(0,0,0,0.8)", font_size=14, font_family="Arial"),
}

# Merge the default theme with our updates
fig.update_layout(**(theme.get_default_layout() | layout_updates))

# Display the plot
st.plotly_chart(fig, use_container_width=True)

# Add save configuration button
render_save_config("spot_perp_arbitrage", st.session_state["default_config"])
