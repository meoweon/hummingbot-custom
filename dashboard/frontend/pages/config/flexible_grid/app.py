import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from frontend.components.backtesting import backtesting_section
from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.pages.config.flexible_grid.user_inputs import user_inputs
from frontend.pages.config.utils import get_candles
from frontend.st_utils import get_backend_api_client, initialize_st_page
from frontend.utils.i18n import t
from frontend.visualization import theme
from frontend.visualization.backtesting import create_backtesting_figure
from frontend.visualization.backtesting_metrics import render_accuracy_metrics, render_backtesting_metrics, render_close_types
from frontend.visualization.candles import get_candlestick_trace
from frontend.visualization.indicators import get_cci_traces, get_volume_trace
from frontend.visualization.utils import add_traces_to_fig

# Initialize the Streamlit page
initialize_st_page(page_title=t("CCI灵活网格策略"), icon="📈", initial_sidebar_state="expanded")
backend_api_client = get_backend_api_client()
get_default_config_loader("cci_flexible_grid")

# Get user inputs for strategy configuration
inputs = user_inputs()
if inputs is None:
    st.error(t("配置无效，请检查输入并重试。"))
    st.stop()

# 确保关键项不是None
for key in ["profit_target_amount", "loss_target_amount"]:
    if inputs.get(key) is None:
        inputs[key] = None  # 显式设置为None，以避免后续处理时出现问题

st.session_state["default_config"].update(inputs)

# Visualization configuration
st.write(t("### 可视化配置"))
days_to_visualize = st.number_input(t("Days to Visualize"), min_value=1, max_value=365, value=1, help=t("显示的历史数据天数"))

# Load candle data
candles = get_candles(
    connector_name=inputs["candles_connector"],
    trading_pair=inputs["trading_pair"],
    interval=inputs["interval"],
    days=days_to_visualize,
)

if candles.empty:
    st.error(t("无K线数据可用，请检查连接器、交易对或间隔。"))
    st.stop()

# Create subplots
subplot_rows = 3 if inputs["use_cci_signal"] else 2
subplot_titles = [
    f'{t("CCI灵活网格策略")} - {inputs["trading_pair"]} ({inputs["interval"]})',
    t("成交量"),
]
if inputs["use_cci_signal"]:
    subplot_titles.insert(2, t("CCI指标"))

row_heights = [0.7, 0.3] if not inputs["use_cci_signal"] else [0.5, 0.3, 0.2]

fig = make_subplots(
    rows=subplot_rows,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=subplot_titles,
    row_heights=row_heights,
)

# Add candlestick chart
candlestick_trace = get_candlestick_trace(candles)
add_traces_to_fig(fig, [candlestick_trace], row=1, col=1)

# Add volume (always in second row)
add_traces_to_fig(fig, [get_volume_trace(candles)], row=2, col=1)

# Add CCI indicator if enabled (in third row)
if inputs["use_cci_signal"]:
    # 确保所有CCI参数都存在且非None
    cci_params = {
        "cci_length": inputs.get("cci_length", 20),
        "cci_long_threshold": inputs.get("cci_long_threshold", 100),
        "cci_short_threshold": inputs.get("cci_short_threshold", -100),
    }
    add_traces_to_fig(
        fig,
        get_cci_traces(
            candles,
            cci_params["cci_length"],
            cci_params["cci_long_threshold"],
            cci_params["cci_short_threshold"],
        ),
        row=3,
        col=1,
    )

# Get time range and mid price
x_start = candles.index[0]
x_end = candles.index[-1]
mid_price = float(candles["close"].iloc[-1])

# Add grid levels and risk control lines
side = inputs["side"]  # Now using string value directly
n_levels = inputs["n_levels"]

# Grid price calculations
prices = [mid_price]  # Start with mid price
price_calculations = [f"L0: {mid_price} (当前中间价)"]

if side == "RANGE":
    # RANGE mode: Calculate both long and short grid lines
    buy_prices = [mid_price]
    sell_prices = [mid_price]
    buy_calculations = [f"L0 (BUY): {mid_price} (当前中间价)"]
    sell_calculations = [f"L0 (SELL): {mid_price} (当前中间价)"]
    current_buy_price = mid_price
    current_sell_price = mid_price

    for i in range(n_levels):
        open_ratio = float(inputs["open_ratios"][i])

        # Long (BUY) grid lines: price goes down
        buy_calc = f"L{i+1} (BUY): {current_buy_price} × (1 - {open_ratio}) = "
        active_buy_price = current_buy_price * (1 - open_ratio)
        buy_calc += f"{active_buy_price}"
        buy_prices.append(active_buy_price)
        buy_calculations.append(buy_calc)
        current_buy_price = active_buy_price

        # Short (SELL) grid lines: price goes up
        sell_calc = f"L{i+1} (SELL): {current_sell_price} × (1 + {open_ratio}) = "
        active_sell_price = current_sell_price * (1 + open_ratio)
        sell_calc += f"{active_sell_price}"
        sell_prices.append(active_sell_price)
        sell_calculations.append(sell_calc)
        current_sell_price = active_sell_price

    prices.extend(buy_prices[1:] + sell_prices[1:])
    price_calculations.extend(buy_calculations[1:] + sell_calculations[1:])
else:
    # BUY or SELL mode: Single direction grid lines
    current_price = mid_price
    for i in range(n_levels):
        open_ratio = float(inputs["open_ratios"][i])
        calculation = f"L{i+1}: {current_price} × "

        if side == "BUY":
            calculation += f"(1 - {open_ratio}) = "
            active_op_price = current_price * (1 - open_ratio)
        else:  # SELL
            calculation += f"(1 + {open_ratio}) = "
            active_op_price = current_price * (1 + open_ratio)

        calculation += f"{active_op_price}"
        prices.append(active_op_price)
        price_calculations.append(calculation)
        current_price = active_op_price

# Calculate risk control lines (different for long/short and RANGE mode)
buy_take_profit_price = mid_price * (1 + float(inputs["take_profit"]))
buy_stop_loss_price = mid_price * (1 - float(inputs["stop_loss"]))
sell_take_profit_price = mid_price * (1 - float(inputs["take_profit"]))
sell_stop_loss_price = mid_price * (1 + float(inputs["stop_loss"]))

tp_calculations = []
sl_calculations = []

if side == "BUY":
    tp_calculations.append(f"全局止盈线: {mid_price} × (1 + {inputs['take_profit']}) = {buy_take_profit_price}")
    sl_calculations.append(f"全局止损线: {mid_price} × (1 - {inputs['stop_loss']}) = {buy_stop_loss_price}")
elif side == "SELL":
    tp_calculations.append(f"全局止盈线: {mid_price} × (1 - {inputs['take_profit']}) = {sell_take_profit_price}")
    sl_calculations.append(f"全局止损线: {mid_price} × (1 + {inputs['stop_loss']}) = {sell_stop_loss_price}")
else:  # RANGE
    tp_calculations.append(f"多头全局止盈线: {mid_price} × (1 + {inputs['take_profit']}) = {buy_take_profit_price}")
    tp_calculations.append(f"空头全局止盈线: {mid_price} × (1 - {inputs['take_profit']}) = {sell_take_profit_price}")
    sl_calculations.append(f"多头全局止损线: {mid_price} × (1 - {inputs['stop_loss']}) = {buy_stop_loss_price}")
    sl_calculations.append(f"空头全局止损线: {mid_price} × (1 + {inputs['stop_loss']}) = {sell_stop_loss_price}")

# Display strategy configuration summary
with st.expander(t("策略配置概要"), expanded=False):
    st.write("### 基本配置")
    st.write(f"- 交易所: {inputs['connector_name']}")
    st.write(f"- 交易对: {inputs['trading_pair']}")

    # 根据投资模式显示不同的投资信息
    investment_mode = inputs.get("investment_mode", "amount_quote")
    st.write(f"- 投资模式: {'按报价货币金额' if investment_mode == 'amount_quote' else '按基础货币数量'}")
    st.write(f"- 网格级别数: {inputs['n_levels']}")

    # 不再显示总投资金额/数量的摘要

    st.write(f"- 杠杆倍数: {float(inputs['leverage'])}x")
    st.write(f"- 交易方向: {side}")

    st.write("### 信号配置")
    st.write(f"- 使用CCI信号: {'是' if inputs['use_cci_signal'] else '否'}")
    if inputs["use_cci_signal"]:
        # 确保CCI参数存在，提供默认值
        cci_params = {
            "cci_length": inputs.get("cci_length", 20),
            "cci_long_threshold": inputs.get("cci_long_threshold", 100),
            "cci_short_threshold": inputs.get("cci_short_threshold", -100),
            "cci_long_condition": inputs.get("cci_long_condition", "<"),
            "cci_short_condition": inputs.get("cci_short_condition", ">"),
            "update_on_close_only": inputs.get("update_on_close_only", True),
        }

        st.write(f"- CCI周期: {float(cci_params['cci_length'])}")
        st.write(f"- CCI做多阈值: {float(cci_params['cci_long_threshold'])}")
        st.write(f"- CCI做空阈值: {float(cci_params['cci_short_threshold'])}")
        st.write(f"- CCI做多条件: {cci_params['cci_long_condition']}")
        st.write(f"- CCI做空条件: {cci_params['cci_short_condition']}")
        st.write(f"- 仅在K线收盘时更新: {'是' if cci_params['update_on_close_only'] else '否'}")

    st.write("### 网格配置")
    st.write(f"- 网格层级数: {inputs['n_levels']}")
    st.write(f"- 立即开仓第一层级: {'是' if inputs['first_level_open'] else '否'}")
    st.write(f"- 每侧最大执行器数量: {float(inputs['max_executors_per_side'])}")
    st.write(f"- 全局风控最小层级数: {inputs['min_levels_for_global_barriers']}")
    st.write(f"- 最小重开间隔: {inputs['min_reopen_interval']}秒")
    st.write(f"- 最大开仓订单数: {inputs['max_open_orders']}")
    st.write(f"- 订单频率: {inputs['order_frequency']}秒")
    st.write(f"- 停止时保持仓位: {'是' if inputs['keep_position'] else '否'}")

    # Add grid level details
    st.write("\n#### 网格层级详细配置")
    for i in range(inputs["n_levels"]):
        st.write(f"\n**层级 {i+1}** {'(立即开仓)' if i == 0 and inputs['first_level_open'] else ''}")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- 开仓比率: {float(inputs['open_ratios'][i]):.4f}")
            st.write(f"- 开仓反弹比率: {float(inputs['open_rebound_ratios'][i]):.4f}")
            st.write(f"- 止盈比率: {float(inputs['take_profit_ratios'][i]):.4f}")
        with col2:
            st.write(f"- 止盈反弹比率: {float(inputs['take_profit_rebound_ratios'][i]):.4f}")
            st.write(f"- 止损比率: {float(inputs['stop_loss_ratios'][i]):.4f}")

            # 根据投资模式显示不同的投资信息
            if investment_mode == "amount_quote":
                quote_currency = inputs["trading_pair"].split("-")[1]
                quote_amounts = inputs.get("amount_quote", [0] * inputs["n_levels"])
                if i < len(quote_amounts) and quote_amounts[i] is not None:
                    st.write(f"- 投资金额: {float(quote_amounts[i]):.6f} {quote_currency}")
                else:
                    st.write(f"- 投资金额: 0.000000 {quote_currency}")
            else:  # amount_base 模式
                base_currency = inputs["trading_pair"].split("-")[0]
                base_amounts = inputs.get("amount_base", [0] * inputs["n_levels"])
                if i < len(base_amounts) and base_amounts[i] is not None:
                    st.write(f"- 投资数量: {float(base_amounts[i]):.6f} {base_currency}")
                else:
                    st.write(f"- 投资数量: 0.000000 {base_currency}")

    st.write("### 风控配置")
    st.write(f"- 止损比例: {float(inputs['stop_loss'])}")
    st.write(f"- 止盈比例: {float(inputs['take_profit'])}")
    st.write(f"- 追踪止损: {inputs['trailing_stop']['activation_price']}, {inputs['trailing_stop']['trailing_delta']}")
    profit_target_display = "不启用" if inputs["profit_target_amount"] is None else f"{float(inputs['profit_target_amount'])}"
    loss_target_display = "不启用" if inputs["loss_target_amount"] is None else f"{float(inputs['loss_target_amount'])}"
    st.write(f"- 全局止盈目标金额: {profit_target_display}")
    st.write(f"- 全局止损目标金额: {loss_target_display}")

# Display calculation process
with st.expander(t("网格计算过程"), expanded=False):
    st.write(f"**{t('方向')}: {side}**")
    st.write(f"**{t('中间价')}: {mid_price}**")
    st.write("### 网格价格计算过程")
    for calc in price_calculations:
        st.write(calc)
    st.write("### 风控线计算")
    for calc in tp_calculations:
        st.write(calc)
    for calc in sl_calculations:
        st.write(calc)

# Add checkboxes to control take profit and stop loss line display (in same row)
col1, col2 = st.columns(2)
with col1:
    show_take_profit = st.checkbox(t("显示止盈线"), value=False)
with col2:
    show_stop_loss = st.checkbox(t("显示止损线"), value=False)

# Draw grid level lines
if side == "RANGE":
    # RANGE mode: Draw both long and short grid lines
    for i, price in enumerate(buy_prices):
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(price), float(price)],
                mode="lines",
                line=dict(color="green", dash="dash"),
                name=f"L{i}_Open (BUY)",
                showlegend=True,
            ),
            row=1,
            col=1,
        )
    for i, price in enumerate(sell_prices):
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(price), float(price)],
                mode="lines",
                line=dict(color="red", dash="dash"),
                name=f"L{i}_Open (SELL)",
                showlegend=True,
            ),
            row=1,
            col=1,
        )
else:
    # BUY or SELL mode
    line_color = "green" if side == "BUY" else "red"
    for i, price in enumerate(prices):
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(price), float(price)],
                mode="lines",
                line=dict(color=line_color, dash="dash"),
                name=f"L{i}_Open ({side})",
                showlegend=True,
            ),
            row=1,
            col=1,
        )

# Draw risk control lines (based on checkbox control)
if side == "BUY":
    if show_take_profit:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(buy_take_profit_price), float(buy_take_profit_price)],
                mode="lines",
                line=dict(color="blue", dash="dot"),
                name=t("全局止盈线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
    if show_stop_loss:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(buy_stop_loss_price), float(buy_stop_loss_price)],
                mode="lines",
                line=dict(color="red", dash="dot"),
                name=t("全局止损线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
elif side == "SELL":
    if show_take_profit:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(sell_take_profit_price), float(sell_take_profit_price)],
                mode="lines",
                line=dict(color="blue", dash="dot"),
                name=t("全局止盈线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
    if show_stop_loss:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(sell_stop_loss_price), float(sell_stop_loss_price)],
                mode="lines",
                line=dict(color="red", dash="dot"),
                name=t("全局止损线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
else:  # RANGE
    if show_take_profit:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(buy_take_profit_price), float(buy_take_profit_price)],
                mode="lines",
                line=dict(color="blue", dash="dot"),
                name=t("多头全局止盈线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(sell_take_profit_price), float(sell_take_profit_price)],
                mode="lines",
                line=dict(color="blue", dash="dot"),
                name=t("空头全局止盈线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
    if show_stop_loss:
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(buy_stop_loss_price), float(buy_stop_loss_price)],
                mode="lines",
                line=dict(color="red", dash="dot"),
                name=t("多头全局止损线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=[x_start, x_end],
                y=[float(sell_stop_loss_price), float(sell_stop_loss_price)],
                mode="lines",
                line=dict(color="red", dash="dot"),
                name=t("空头全局止损线"),
                showlegend=True,
            ),
            row=1,
            col=1,
        )

# Update chart layout
layout_settings = theme.get_default_layout()
layout_settings.update(
    {
        "showlegend": True,
        "height": 800,
        "margin": dict(t=30, l=10, r=10, b=10),
        "plot_bgcolor": "rgba(0,0,0,0)",
        "paper_bgcolor": "rgba(0,0,0,0)",
    }
)
fig.update_layout(**layout_settings)

# Update y-axis titles
fig.update_yaxes(title_text=t("价格"), row=1, col=1)
if inputs["use_cci_signal"]:
    fig.update_yaxes(title_text=t("CCI值"), row=3, col=1)
fig.update_yaxes(title_text=t("成交量"), row=2, col=1)

# Display chart
st.plotly_chart(fig, use_container_width=True)

# Configuration save section
st.markdown("---")
render_save_config(st.session_state["default_config"]["id"], st.session_state["default_config"])
