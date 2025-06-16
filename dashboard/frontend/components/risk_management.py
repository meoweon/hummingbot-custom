import streamlit as st
from hummingbot.connector.connector_base import OrderType
from frontend.st_utils import t


def get_risk_management_inputs():
    default_config = st.session_state.get("default_config", {})
    sl = default_config.get("stop_loss", 1.00) * 100
    tp = default_config.get("take_profit", 1.00) * 100
    time_limit = default_config.get("time_limit", 60 * 60 * 24 * 365) // 60
    ts_ap = default_config.get("trailing_stop", {}).get("activation_price", 0.018) * 100
    ts_delta = default_config.get("trailing_stop", {}).get("trailing_delta", 0.002) * 100
    take_profit_order_type = OrderType(default_config.get("take_profit_order_type", 2))
    order_types = [OrderType.LIMIT, OrderType.MARKET]
    order_type_index = order_types.index(take_profit_order_type)
    with st.expander(t("Risk Management"), expanded=True):
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        with c1:
            sl = (
                st.number_input(
                    t("Stop Loss (%)"),
                    min_value=0.0,
                    max_value=100.0,
                    value=sl,
                    step=0.1,
                    help=t("Enter the stop loss as a percentage (e.g., 2.0 for 2%)."),
                )
                / 100
            )
        with c2:
            tp = (
                st.number_input(
                    t("Take Profit (%)"),
                    min_value=0.0,
                    max_value=100.0,
                    value=tp,
                    step=0.1,
                    help=t("Enter the take profit as a percentage (e.g., 3.0 for 3%)."),
                )
                / 100
            )
        with c3:
            time_limit = (
                st.number_input(
                    t("Time Limit (minutes)"),
                    min_value=0,
                    value=time_limit,
                    help=t("Enter the time limit in minutes (e.g., 360 for 6 hours)."),
                )
                * 60
            )
        with c4:
            ts_ap = (
                st.number_input(
                    t("Trailing Stop Act. Price (%)"),
                    min_value=0.0,
                    max_value=100.0,
                    value=ts_ap,
                    step=0.1,
                    help=t("Enter the trailing stop activation price as a percentage (e.g., 1.0 for 1%)."),
                )
                / 100
            )
        with c5:
            ts_delta = (
                st.number_input(
                    t("Trailing Stop Delta (%)"),
                    min_value=0.0,
                    max_value=100.0,
                    value=ts_delta,
                    step=0.1,
                    help=t("Enter the trailing stop delta as a percentage (e.g., 0.3 for 0.3%)."),
                )
                / 100
            )
        with c6:
            # 显示翻译的选项名称，但存储原始的OrderType对象
            order_type_labels = [t("LIMIT"), t("MARKET")]
            selected_label = st.selectbox(
                t("Take Profit Order Type"),
                order_type_labels,
                index=order_type_index,
                help=t("Enter the order type for taking profit (LIMIT/MARKET)."),
            )
            # 根据选择的标签获取对应的OrderType对象
            selected_index = order_type_labels.index(selected_label)
            take_profit_order_type = order_types[selected_index]

    return sl, tp, time_limit, ts_ap, ts_delta, take_profit_order_type
