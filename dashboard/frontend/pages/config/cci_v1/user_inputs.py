import streamlit as st

from frontend.components.directional_trading_general_inputs import get_directional_trading_general_inputs
from frontend.components.risk_management import get_risk_management_inputs
from frontend.st_utils import t


def user_inputs():
    default_config = st.session_state.get("default_config", {})
    length = default_config.get("length", 20)
    overbought = default_config.get("overbought", 100)
    oversold = default_config.get("oversold", -100)
    use_candle_close = default_config.get("use_candle_close", True)

    (
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
    ) = get_directional_trading_general_inputs()
    sl, tp, time_limit, ts_ap, ts_delta, take_profit_order_type = get_risk_management_inputs()

    with st.expander(t("CCI Configuration"), expanded=True):
        # CCI Length in a single column
        length = st.number_input(
            t("CCI Length"),
            min_value=5,
            max_value=100,
            value=length,
            help=t("Number of periods used to calculate CCI. Common values are 14-20."),
        )

        # Create two columns for overbought and oversold settings
        col1, col2 = st.columns(2)

        # Overbought settings in left column
        with col1:
            st.markdown(f"##### {t('Overbought Settings')}")
            overbought = st.number_input(
                t("Level"),
                min_value=50,
                max_value=500,
                value=overbought,
                help=t(
                    "CCI level to consider market overbought. Traditional value is 100. When CCI crosses above this level, a sell signal is generated."
                ),
                key="overbought_level",
            )

        # Oversold settings in right column
        with col2:
            st.markdown(f"##### {t('Oversold Settings')}")
            oversold = st.number_input(
                t("Level"),
                min_value=-500,
                max_value=-50,
                value=oversold,
                help=t(
                    "CCI level to consider market oversold. Traditional value is -100. When CCI crosses below this level, a buy signal is generated."
                ),
                key="oversold_level",
            )

        # Add validation warnings
        if abs(overbought) < 100:
            st.warning(
                t("Warning: Overbought level is less than the traditional value of 100. This may generate more frequent signals.")
            )
        if abs(oversold) < 100:
            st.warning(
                t("Warning: Oversold level is less than the traditional value of -100. This may generate more frequent signals.")
            )
        if length < 14:
            st.warning(
                t(
                    "Warning: CCI length is less than the traditional value of 14. This may make the indicator more sensitive to price changes."
                )
            )

        # 添加K线收盘时生成信号选项
        st.markdown("---")
        use_candle_close = st.checkbox(
            t("Generate Signals Only at Candle Close"),
            value=use_candle_close,
            help=t("When checked, trading signals will only be generated when a candle closes. This helps reduce false signals."),
        )

    return {
        "controller_name": "cci_v1",
        "controller_type": "directional_trading",
        "connector_name": connector_name,
        "trading_pair": trading_pair,
        "leverage": leverage,
        "total_amount_quote": total_amount_quote,
        "max_executors_per_side": max_executors_per_side,
        "cooldown_time": cooldown_time,
        "position_mode": position_mode,
        "candles_connector": candles_connector_name,
        "candles_trading_pair": candles_trading_pair,
        "interval": interval,
        "length": length,
        "overbought": overbought,
        "oversold": oversold,
        "use_candle_close": use_candle_close,
        "stop_loss": sl,
        "take_profit": tp,
        "time_limit": time_limit,
        "trailing_stop": {"activation_price": ts_ap, "trailing_delta": ts_delta},
        "take_profit_order_type": take_profit_order_type.value,
    }
