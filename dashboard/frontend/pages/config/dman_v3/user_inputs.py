import streamlit as st

from frontend.components.directional_trading_general_inputs import get_directional_trading_general_inputs
from frontend.components.risk_management import get_risk_management_inputs
from frontend.st_utils import t


def user_inputs():
    default_config = st.session_state.get("default_config", {})
    bb_length = default_config.get("bb_length", 20)
    bb_std = default_config.get("bb_std", 2.0)
    bb_long_threshold = default_config.get("bb_long_threshold", 0.2)
    bb_short_threshold = default_config.get("bb_short_threshold", 0.8)
    dca_spreads = default_config.get("dca_spreads", "0.001,0.018,0.15,0.25")
    dca_amounts_pct = default_config.get("dca_amounts_pct", "0.25,0.25,0.25,0.25")
    dynamic_order_spread = default_config.get("dynamic_order_spread", True)
    dynamic_target = default_config.get("dynamic_target", True)
    activation_bounds = default_config.get("activation_bounds", "0.01,0.01,0.01")

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

    with st.expander(t("Bollinger Bands Configuration"), expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            bb_length = st.number_input(t("Bollinger Bands Length"), min_value=5, max_value=1000, value=bb_length)
        with c2:
            bb_std = st.number_input(t("Standard Deviation Multiplier"), min_value=0.5, max_value=5.0, value=bb_std)
        with c3:
            bb_long_threshold = st.number_input(
                t("Long Threshold"),
                min_value=0.0,
                max_value=0.5,
                value=bb_long_threshold,
                help="触发做多的布林带位置阈值，小于此值时做多",
            )
        with c4:
            bb_short_threshold = st.number_input(
                t("Short Threshold"),
                min_value=0.5,
                max_value=1.0,
                value=bb_short_threshold,
                help="触发做空的布林带位置阈值，大于此值时做空",
            )

    with st.expander(t("DCA Configuration"), expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            dca_spreads = st.text_input(
                t("DCA Spreads"), value=dca_spreads, help="DCA级别的价差，用逗号分隔，例如: 0.001,0.018,0.15,0.25"
            )
            dynamic_order_spread = st.checkbox(
                t("Dynamic Order Spread"), value=dynamic_order_spread, help="是否根据布林带宽度动态调整订单价差"
            )
        with c2:
            dca_amounts_pct = st.text_input(
                t("DCA Amounts Percentage"),
                value=dca_amounts_pct,
                help="每个DCA级别的金额百分比，用逗号分隔，例如: 0.25,0.25,0.25,0.25",
            )
            dynamic_target = st.checkbox(t("Dynamic Target"), value=dynamic_target, help="是否根据市场波动动态调整目标价")

        activation_bounds = st.text_input(
            t("Activation Bounds"),
            value=activation_bounds,
            help="激活下一个订单的价格边界，例如：0.01表示当价格接近1%时激活下一个订单",
        )

    return {
        "controller_name": "dman_v3",
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
        "bb_length": bb_length,
        "bb_std": bb_std,
        "bb_long_threshold": bb_long_threshold,
        "bb_short_threshold": bb_short_threshold,
        "dca_spreads": dca_spreads,
        "dca_amounts_pct": dca_amounts_pct,
        "dynamic_order_spread": dynamic_order_spread,
        "dynamic_target": dynamic_target,
        "activation_bounds": activation_bounds,
        "stop_loss": sl,
        "take_profit": tp,
        "time_limit": time_limit,
        "trailing_stop": {"activation_price": ts_ap, "trailing_delta": ts_delta},
        "take_profit_order_type": take_profit_order_type.value,
    }
