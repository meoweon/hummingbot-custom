from decimal import Decimal

import plotly.graph_objs as go
import streamlit as st
from hummingbot.core.data_type.common import OrderType, PositionMode, TradeType

from frontend.pages.config.utils import get_candles
from frontend.utils.i18n import t


def get_price_range_defaults(connector_name: str, trading_pair: str, interval: str, days: int = 7):
    """Fetch candles and compute default price range based on recent min/max prices."""
    try:
        candles = get_candles(connector_name=connector_name, trading_pair=trading_pair, interval=interval, days=days)

        # 确保DataFrame有数据且包含需要的列
        if candles is None or candles.empty or "low" not in candles.columns or "high" not in candles.columns:
            # 根据交易对猜测合理的默认值
            if "BTC" in trading_pair:
                return 40000.0, 60000.0
            elif "ETH" in trading_pair:
                return 2000.0, 3500.0
            else:
                return 100.0, 1000.0  # 通用默认值

        # 计算价格范围
        try:
            min_price = float(candles["low"].quantile(0.05))
            max_price = float(candles["high"].quantile(0.95))

            # 验证计算值的合理性
            if min_price <= 0 or max_price <= 0 or min_price >= max_price:
                raise ValueError("Invalid price range calculated")

            return round(min_price, 2), round(max_price, 2)
        except Exception as e:
            # 如果计算分位数失败，尝试使用最小值和最大值
            min_price = float(candles["low"].min())
            max_price = float(candles["high"].max())
            if min_price > 0 and max_price > 0 and min_price < max_price:
                return round(min_price, 2), round(max_price, 2)
            else:
                raise ValueError(f"Invalid min/max prices: {min_price}, {max_price}")
    except Exception as e:
        st.warning(f"Could not fetch price data: {str(e)}. Using default values.")
        # 根据交易对猜测合理的默认值
        if "BTC" in trading_pair:
            return 40000.0, 60000.0
        elif "ETH" in trading_pair:
            return 2000.0, 3500.0
        else:
            return 100.0, 1000.0  # 通用默认值


def get_grid_range_traces(grid_ranges):
    """Generate horizontal line traces for grid ranges with different colors."""
    dash_styles = ["solid", "dash", "dot", "dashdot", "longdash"]  # 5 different styles
    traces = []
    buy_count = 0
    sell_count = 0
    for i, grid_range in enumerate(grid_ranges):
        # Set color based on trade type
        if grid_range["side"] == TradeType.BUY:
            color = "rgba(0, 255, 0, 1)"  # Bright green for buy
            dash_style = dash_styles[buy_count % len(dash_styles)]
            buy_count += 1
        else:
            color = "rgba(255, 0, 0, 1)"  # Bright red for sell
            dash_style = dash_styles[sell_count % len(dash_styles)]
            sell_count += 1
        # Start price line
        traces.append(
            go.Scatter(
                x=[],  # Will be set to full range when plotting
                y=[float(grid_range["start_price"]), float(grid_range["start_price"])],
                mode="lines",
                line=dict(color=color, width=1.5, dash=dash_style),
                name=f'{t("range")} {i} {t("start")}: {float(grid_range["start_price"]):,.2f} ({grid_range["side"].name})',
                hoverinfo="name",
            )
        )
        # End price line
        traces.append(
            go.Scatter(
                x=[],  # Will be set to full range when plotting
                y=[float(grid_range["end_price"]), float(grid_range["end_price"])],
                mode="lines",
                line=dict(color=color, width=1.5, dash=dash_style),
                name=f'{t("range")} {i} {t("end")}: {float(grid_range["end_price"]):,.2f} ({grid_range["side"].name})',
                hoverinfo="name",
            )
        )
    return traces


def user_inputs():
    # Split the page into two columns for the expanders
    left_col, right_col = st.columns(2)
    with left_col:
        # Basic trading parameters
        with st.expander(t("basic_configuration"), expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                connector_name = st.text_input(t("connector_name"), value="okx_perpetual")
            with c2:
                trading_pair = st.text_input(t("trading_pair"), value="BTC-USDT")
            with c3:
                leverage = st.number_input(t("leverage"), min_value=1, value=20)
        # Visualization Configuration
        with st.expander(t("chart_configuration"), expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                candles_connector = st.text_input(
                    t("candles_connector"),
                    value=connector_name,  # Use same connector as trading by default
                    help=t("Connector to fetch price data from"),
                )
            with c2:
                interval = st.selectbox(
                    t("interval"),
                    options=["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"],
                    index=10,  # Default to 30m
                    help=t("Candlestick interval"),
                )
            with c3:
                days_to_visualize = st.number_input(
                    t("days_to_display"),
                    min_value=1,
                    max_value=365,
                    value=180,
                    help=t("Number of days of historical data to display"),
                )

        # Get default price ranges based on current market data
        default_min, default_max = get_price_range_defaults(candles_connector, trading_pair, interval, days_to_visualize)
        # Grid Ranges Configuration
        with st.expander(t("grid_ranges"), expanded=True):
            grid_ranges = []
            c1, c2 = st.columns(2)
            with c1:
                num_ranges = st.number_input(t("number_of_grid_ranges"), min_value=1, max_value=100, value=1)
            with c2:
                decimals = st.number_input(t("decimals_to_display"), min_value=0, max_value=20, value=4)
            fmt = f"%.{decimals}f"
            for i in range(num_ranges):
                st.markdown(f"#### {t('range')} {i}")
                # Price configuration
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    # Set default start price based on side
                    side = st.selectbox(f"{t('side')} {i}", options=[TradeType.BUY.name, TradeType.SELL.name], key=f"side_{i}")
                with c2:
                    # Set default start price based on side
                    start_price = st.number_input(
                        f"{t('start_price')} {i}", value=default_min, key=f"start_price_{i}", format=fmt
                    )
                with c3:
                    # Set default end price based on side
                    end_price = st.number_input(f"{t('end_price')} {i}", value=default_max, key=f"end_price_{i}", format=fmt)
                with c4:
                    total_amount_pct = st.number_input(
                        f"{t('amount')} % {i}", min_value=0.0, max_value=100.0, value=50.0, key=f"amount_pct_{i}"
                    )
                st.markdown("---")
                grid_ranges.append(
                    {
                        "id": f"R{i}",
                        "start_price": Decimal(str(start_price)),
                        "end_price": Decimal(str(end_price)),
                        "total_amount_pct": Decimal(str(total_amount_pct / 100)),
                        "side": TradeType[side],
                        "open_order_type": OrderType.LIMIT_MAKER,
                        "take_profit_order_type": OrderType.LIMIT,
                    }
                )
    with right_col:
        # Amount configuration
        with st.expander(t("amount_configuration"), expanded=True):
            total_amount_quote = st.number_input(
                t("total_amount_quote"), min_value=0.0, value=100.0, help=t("Total amount in quote currency to use for trading")
            )
            min_order_amount = st.number_input(
                t("minimum_order_amount"), min_value=1.0, value=10.0, help=t("Minimum amount for each order")
            )
        # Advanced Configuration
        with st.expander(t("advanced_configuration"), expanded=True):
            position_mode = st.selectbox(t("position_mode"), options=["HEDGE", "ONEWAY"], index=0, format_func=lambda x: t(x))
            c1, c2 = st.columns(2)
            with c1:
                time_limit = st.number_input(t("time_limit_hours"), min_value=1, value=48, help=t("Strategy time limit in hours"))
                min_spread = st.number_input(
                    t("min_spread_between_orders"),
                    min_value=0.0000,
                    value=0.0001,
                    format="%.4f",  # Show 3 decimal places
                    help=t("Minimum price difference between orders"),
                    step=0.0001,
                )
                activation_bounds = st.number_input(
                    t("activation_bounds"), min_value=0.0, value=0.01, format="%.4f", help=t("Price deviation to trigger updates")
                )
            with c2:
                max_open_orders = st.number_input(
                    t("maximum_open_orders"), min_value=1, value=5, help=t("Maximum number of open orders")
                )
                grid_update_interval = st.number_input(
                    t("grid_update_interval"), min_value=1, value=60, help=t("How often to update grid ranges")
                )

    return {
        "controller_name": "grid_strike",
        "controller_type": "generic",
        "connector_name": connector_name,
        "candles_connector": candles_connector,
        "trading_pair": trading_pair,
        "interval": interval,
        "days_to_visualize": days_to_visualize,
        "leverage": leverage,
        "total_amount_quote": float(total_amount_quote),
        "grid_ranges": grid_ranges,
        "position_mode": PositionMode[position_mode],
        "time_limit": time_limit * 60 * 60,
        "activation_bounds": float(activation_bounds),
        "min_spread_between_orders": float(min_spread) if min_spread > 0 else None,
        "min_order_amount": float(min_order_amount),
        "max_open_orders": max_open_orders,
        "grid_range_update_interval": grid_update_interval,
        "extra_balance_base_usd": 10.0,
    }
