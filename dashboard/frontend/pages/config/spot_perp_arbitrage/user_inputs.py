import streamlit as st
from hummingbot.core.data_type.common import PositionMode

from frontend.utils.i18n import t


def user_inputs():
    """
    Get user inputs for the spot-perpetual arbitrage strategy.
    """
    # Split the page into two columns
    left_col, right_col = st.columns(2)

    with left_col:
        # Basic Configuration
        with st.expander(t("basic_configuration"), expanded=True):
            # Connector Selection
            spot_connector = st.text_input("现货交易所", value="binance", help="输入现货交易所名称，例如：binance, okx, bybit")
            perp_connector = st.text_input(
                "永续交易所",
                value="binance_perpetual",
                help="输入永续交易所名称，例如：binance_perpetual, okx_perpetual, bybit_perpetual",
            )

            # Trading Pair
            trading_pair = st.text_input(
                t("trading_pair"), value="BTC-USDT", help=t("Enter the trading pair in format: BASE-QUOTE")
            )

            # Position Mode
            position_mode = st.selectbox(t("position_mode"), options=["HEDGE", "ONEWAY"], index=0)

            # Leverage
            leverage = st.number_input(t("leverage"), min_value=1, max_value=100, value=5)

        # Chart Configuration
        with st.expander(t("chart_configuration"), expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                interval = st.selectbox(t("interval"), options=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], index=3)
            with c2:
                days = st.number_input(t("days_to_display"), min_value=1, max_value=30, value=7)

    with right_col:
        # Strategy Parameters
        with st.expander(t("strategy_parameters"), expanded=True):
            # Order Amount Configuration
            order_amount_quote = st.number_input(
                t("order_amount_quote"), min_value=0.0, value=10000.0, help=t("Total amount in quote currency to use for trading")
            )

            # Price Difference Parameters
            min_price_diff_pct = st.number_input(
                t("min_price_diff_pct"),
                min_value=0.0,
                max_value=100.0,
                value=0.1,
                format="%.3f",
                help=t("Minimum price difference percentage to trigger trades"),
            )

            # Time Limit
            time_limit = st.number_input(t("time_limit_hours"), min_value=1, value=24, help=t("Strategy time limit in hours"))

            # Use tabs for advanced settings
            tab1, tab2 = st.tabs([t("advanced_parameters"), t("market_parameters")])

            with tab1:
                c1, c2 = st.columns(2)
                with c1:
                    min_trade_size = st.number_input(
                        t("min_trade_size"),
                        min_value=0.0,
                        value=0.001,
                        format="%.4f",
                        help=t("Minimum trade size in base currency"),
                    )
                    max_trade_size = st.number_input(
                        t("max_trade_size"),
                        min_value=0.0,
                        value=1.0,
                        format="%.4f",
                        help=t("Maximum trade size in base currency"),
                    )
                with c2:
                    max_position_size = st.number_input(
                        t("max_position_size"),
                        min_value=0.0,
                        value=2.0,
                        format="%.4f",
                        help=t("Maximum position size in base currency"),
                    )
                    cooldown_time = st.number_input(
                        t("cooldown_time"), min_value=0, value=300, help=t("Cooldown time between trades in seconds")
                    )

            with tab2:
                c1, c2 = st.columns(2)
                with c1:
                    spot_market_slippage = st.number_input(
                        t("spot_market_slippage"),
                        min_value=0.0,
                        max_value=1.0,
                        value=0.001,
                        format="%.4f",
                        help=t("Maximum allowed slippage for spot market orders"),
                    )
                with c2:
                    perp_market_slippage = st.number_input(
                        t("perp_market_slippage"),
                        min_value=0.0,
                        max_value=1.0,
                        value=0.001,
                        format="%.4f",
                        help=t("Maximum allowed slippage for perpetual market orders"),
                    )

    return {
        "controller_name": "spot_perp_arbitrage",
        "controller_type": "arbitrage",
        "spot_connector": spot_connector,
        "perp_connector": perp_connector,
        "trading_pair": trading_pair,
        "position_mode": PositionMode[position_mode],
        "leverage": leverage,
        "order_amount_quote": order_amount_quote,
        "min_price_diff_pct": min_price_diff_pct / 100,  # Convert to decimal
        "time_limit": time_limit * 60 * 60,  # Convert hours to seconds
        "min_trade_size": min_trade_size,
        "max_trade_size": max_trade_size,
        "max_position_size": max_position_size,
        "cooldown_time": cooldown_time,
        "spot_market_slippage": spot_market_slippage,
        "perp_market_slippage": perp_market_slippage,
        "interval": interval,
        "days_to_visualize": days,
    }
