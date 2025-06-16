import streamlit as st
from frontend.st_utils import t


def get_market_making_general_inputs(custom_candles=False):
    with st.expander(t("General Settings"), expanded=True):
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        default_config = st.session_state.get("default_config", {})
        connector_name = default_config.get("connector_name", "kucoin")
        trading_pair = default_config.get("trading_pair", "WLD-USDT")
        leverage = default_config.get("leverage", 20)
        total_amount_quote = default_config.get("total_amount_quote", 1000)
        position_mode = 0 if default_config.get("position_mode", "HEDGE") == "HEDGE" else 1
        cooldown_time = default_config.get("cooldown_time", 60 * 60) / 60
        executor_refresh_time = default_config.get("executor_refresh_time", 60 * 60) / 60
        candles_connector = None
        candles_trading_pair = None
        interval = None
        with c1:
            connector_name = st.text_input(
                t("Connector"),
                value=connector_name,
                help=t("Enter the name of the exchange to trade on (e.g., binance_perpetual)."),
            )
        with c2:
            trading_pair = st.text_input(
                t("Trading Pair"), value=trading_pair, help=t("Enter the trading pair to trade on (e.g., WLD-USDT).")
            )
        with c3:
            leverage = st.number_input(
                t("Leverage"),
                value=leverage,
                help=t("Set the leverage to use for trading (e.g., 20 for 20x leverage). Set it to 1 for spot trading."),
            )
        with c4:
            total_amount_quote = st.number_input(
                t("Total amount of quote"),
                value=total_amount_quote,
                help=t("Enter the total amount in quote asset to use for trading (e.g., 1000)."),
            )
        with c5:
            position_mode_options = ["HEDGE", "ONEWAY"]
            position_mode_labels = [t("HEDGE"), t("ONEWAY")]
            selected_label = st.selectbox(
                t("Position Mode"), position_mode_labels, index=position_mode, help=t("Enter the position mode (HEDGE/ONEWAY).")
            )
            position_mode = position_mode_options[position_mode_labels.index(selected_label)]
        with c6:
            cooldown_time = (
                st.number_input(
                    t("Stop Loss Cooldown Time (minutes)"),
                    value=cooldown_time,
                    help=t("Specify the cooldown time in minutes after having a stop loss (e.g., 60)."),
                )
                * 60
            )
        with c7:
            executor_refresh_time = (
                st.number_input(
                    t("Executor Refresh Time (minutes)"),
                    value=executor_refresh_time,
                    help=t("Enter the refresh time in minutes for executors (e.g., 60)."),
                )
                * 60
            )
        if custom_candles:
            candles_connector = default_config.get("candles_connector", "kucoin")
            candles_trading_pair = default_config.get("candles_trading_pair", "WLD-USDT")
            interval = default_config.get("interval", "3m")
            intervals = ["1m", "3m", "5m", "15m", "1h", "4h", "1d"]
            interval_index = intervals.index(interval)
            with c1:
                candles_connector = st.text_input(
                    t("Candles Connector"),
                    value=candles_connector,
                    help=t("Enter the name of the exchange to get candles from(e.g., binance_perpetual)."),
                )
            with c2:
                candles_trading_pair = st.text_input(
                    t("Candles Trading Pair"),
                    value=candles_trading_pair,
                    help=t("Enter the trading pair to get candles for (e.g., WLD-USDT)."),
                )
            with c3:
                interval = st.selectbox(
                    t("Candles Interval"), intervals, index=interval_index, help=t("Enter the interval for candles (e.g., 1m).")
                )
    return (
        connector_name,
        trading_pair,
        leverage,
        total_amount_quote,
        position_mode,
        cooldown_time,
        executor_refresh_time,
        candles_connector,
        candles_trading_pair,
        interval,
    )
