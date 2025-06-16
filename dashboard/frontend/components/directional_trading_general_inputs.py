import streamlit as st
from frontend.st_utils import t


def get_directional_trading_general_inputs():
    with st.expander(t("General Settings"), expanded=True):
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        default_config = st.session_state.get("default_config", {})
        connector_name = default_config.get("connector_name", "okx_perpetual")
        trading_pair = default_config.get("trading_pair", "DOGE-USDT")
        leverage = default_config.get("leverage", 10)
        total_amount_quote = default_config.get("total_amount_quote", 100)
        max_executors_per_side = default_config.get("max_executors_per_side", 1)
        cooldown_time = default_config.get("cooldown_time", 60 * 1) / 60
        position_mode_value = default_config.get("position_mode", "HEDGE")
        position_mode_index = 0 if position_mode_value == "HEDGE" else 1
        candles_connector_name = default_config.get(
            "candles_connector", default_config.get("candles_connector_name", "okx_perpetual")
        )
        candles_trading_pair = default_config.get("candles_trading_pair", "DOGE-USDT")
        interval = default_config.get("interval", "1m")
        intervals = ["1m", "3m", "5m", "15m", "1h", "4h", "1d", "1s"]
        interval_index = intervals.index(interval) if interval in intervals else 0

        with c1:
            connector_name = st.text_input(
                t("Connector"),
                value=connector_name,
                help=t("Enter the name of the exchange to trade on (e.g., binance_perpetual)."),
            )
            candles_connector_name = st.text_input(
                t("Candles Connector"),
                value=candles_connector_name,
                help=t("Enter the name of the exchange to get candles from(e.g., binance_perpetual)."),
            )
        with c2:
            trading_pair = st.text_input(
                t("Trading Pair"), value=trading_pair, help=t("Enter the trading pair to trade on (e.g., WLD-USDT).")
            )
            candles_trading_pair = st.text_input(
                t("Candles Trading Pair"),
                value=candles_trading_pair,
                help=t("Enter the trading pair to get candles for (e.g., WLD-USDT)."),
            )
        with c3:
            leverage = st.number_input(
                t("Leverage"),
                value=leverage,
                help=t("Set the leverage to use for trading (e.g., 20 for 20x leverage). Set it to 1 for spot trading."),
            )
            interval = st.selectbox(
                t("Candles Interval"),
                ("1m", "3m", "5m", "15m", "1h", "4h", "1d"),
                index=interval_index,
                help=t("Enter the interval for candles (e.g., 1m)."),
            )
        with c4:
            total_amount_quote = st.number_input(
                t("Total amount of quote"),
                value=total_amount_quote,
                help=t("Enter the total amount in quote asset to use for trading (e.g., 1000)."),
            )
        with c5:
            max_executors_per_side = st.number_input(
                t("Max Executors Per Side"),
                value=max_executors_per_side,
                help=t("Enter the maximum number of executors per side (e.g., 5)."),
            )
        with c6:
            cooldown_time = (
                st.number_input(
                    t("Cooldown Time (minutes)"),
                    value=cooldown_time,
                    help=t("Time between accepting a new signal in minutes (e.g., 60)."),
                )
                * 60
            )
        with c7:
            position_mode_options = ["HEDGE", "ONEWAY"]
            position_mode_display = [t("HEDGE"), t("ONEWAY")]

            position_mode_index = st.selectbox(
                t("Position Mode"),
                options=range(len(position_mode_options)),
                format_func=lambda i: position_mode_display[i],
                index=position_mode_index,
                help=t("Enter the position mode (HEDGE/ONEWAY)."),
            )
            position_mode = position_mode_options[position_mode_index]
    return (
        connector_name,
        trading_pair,
        leverage,
        total_amount_quote,
        max_executors_per_side,
        cooldown_time,
        position_mode,
        candles_connector_name,
        candles_trading_pair,
        interval,
    )
