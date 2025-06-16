from hummingbot.core.data_type.common import OrderType, PositionMode, TradeType
from hummingbot.strategy_v2.executors.position_executor.data_types import TrailingStop
import streamlit as st
import uuid

from frontend.components.directional_trading_general_inputs import get_directional_trading_general_inputs
from frontend.components.risk_management import get_risk_management_inputs
from frontend.pages.config.utils import get_candles
from frontend.utils.i18n import t


def get_price_range_defaults(connector_name: str, trading_pair: str, interval: str, days: int = 1):
    """获取默认价格范围"""
    try:
        candles = get_candles(connector_name=connector_name, trading_pair=trading_pair, interval=interval, days=days)
        if candles is None or candles.empty:
            return 40000.0, 60000.0 if "BTC" in trading_pair else (0.08, 0.12)
        current_price = float(candles["close"].iloc[-1])
        min_price = current_price * 0.9
        max_price = current_price * 1.1
        return round(min_price, 4), round(max_price, 4)
    except Exception as e:
        st.warning(f"{t('无法获取价格数据')}: {str(e)}, {t('使用默认值')}")
        return 60000.0, 100000.0 if "BTC" in trading_pair else (0.08, 0.12)


def user_inputs():
    default_config = st.session_state.get("default_config", {})

    # Set default time limit to 1 year (525600 minutes)
    if "time_limit" not in default_config:
        default_config["time_limit"] = 525600 * 60  # Convert to seconds
    st.session_state["default_config"] = default_config

    # Get general trading inputs
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

    # Get risk management inputs
    sl, tp, time_limit, ts_ap, ts_delta, take_profit_order_type = get_risk_management_inputs()

    # 添加投资模式选择
    with st.expander(t("投资模式配置"), expanded=True):
        investment_mode = st.selectbox(
            t("投资模式"),
            options=["amount_base", "amount_quote"],
            index=0 if default_config.get("investment_mode", "amount_base") == "amount_base" else 1,
            help=t("选择投资模式 - amount_base: 按基础货币数量投资; amount_quote: 按报价货币金额投资"),
        )

    # 获取全局风控目标金额配置
    with st.expander(t("全局风控目标金额配置"), expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            profit_target_amount = st.number_input(
                t("全局止盈目标金额"),
                min_value=0.0,
                value=float(default_config.get("profit_target_amount", 0.0) or 0.0),
                help=t("当总盈利达到此金额时触发止盈，设置为0表示不启用"),
            )
            if profit_target_amount == 0.0:
                profit_target_amount = None
        with c2:
            loss_target_amount = st.number_input(
                t("全局止损目标金额"),
                min_value=0.0,
                value=float(default_config.get("loss_target_amount", 0.0) or 0.0),
                help=t("当总亏损达到此金额时触发止损，设置为0表示不启用"),
            )
            if loss_target_amount == 0.0:
                loss_target_amount = None

    # Get CCI signal inputs
    with st.expander(t("CCI信号配置"), expanded=True):
        # 使用唯一的键名以确保状态正确保存
        use_cci_signal = st.checkbox(
            t("使用CCI信号"), value=default_config.get("use_cci_signal", True), key="use_cci_signal_checkbox"
        )

        # 初始化必要的变量，以防止在禁用时丢失值
        cci_length = default_config.get("cci_length", 20)
        cci_long_threshold = default_config.get("cci_long_threshold", 100)
        cci_short_threshold = default_config.get("cci_short_threshold", -100)
        cci_long_condition = default_config.get("cci_long_condition", "<")
        cci_short_condition = default_config.get("cci_short_condition", ">")
        update_on_close_only = default_config.get("update_on_close_only", True)

        if use_cci_signal:
            update_on_close_only = st.checkbox(
                t("仅在K线收盘时更新"), value=update_on_close_only, help=t("仅在K线收盘时更新信号")
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                cci_length = st.number_input(t("CCI周期"), min_value=5, max_value=1000, value=cci_length)
            with c2:
                cci_long_threshold = st.number_input(t("CCI做多阈值"), value=cci_long_threshold)
            with c3:
                cci_short_threshold = st.number_input(t("CCI做空阈值"), value=cci_short_threshold)
            c1, c2 = st.columns(2)
            with c1:
                cci_long_condition = st.selectbox(
                    t("CCI做多条件"),
                    options=["<", ">"],
                    index=0 if cci_long_condition == "<" else 1,
                )
            with c2:
                cci_short_condition = st.selectbox(
                    t("CCI做空条件"),
                    options=["<", ">"],
                    index=0 if cci_short_condition == "<" else 1,
                )
        else:
            # 不显示CCI相关的输入框，但保持变量有效
            update_on_close_only = True

    # Get grid configuration
    with st.expander(t("网格配置"), expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            side_value = st.selectbox(
                t("交易方向"),
                options=["BUY", "SELL"],
                index=0 if default_config.get("side", "BUY") == "BUY" else 1,
            )
        with c2:
            n_levels = st.number_input(t("网格层级数"), min_value=1, max_value=200, value=default_config.get("n_levels", 2))
        with c3:
            first_level_open = st.checkbox(t("立即开仓第一层级"), value=default_config.get("first_level_open", True))

        # Additional grid settings
        c1, c2 = st.columns(2)
        with c1:
            min_levels_for_global_barriers = st.number_input(
                t("全局风控最小层级数"),
                min_value=1,
                max_value=n_levels,
                value=min(default_config.get("min_levels_for_global_barriers", n_levels), n_levels),
                help=t("触发全局风控所需的最小层级数"),
            )
            min_reopen_interval = st.number_input(
                t("最小重开间隔（秒）"),
                min_value=1,
                value=default_config.get("min_reopen_interval", 1),
                help=t("重新开仓的最小时间间隔"),
            )
        with c2:
            max_open_orders = st.number_input(
                t("最大开仓订单数"),
                min_value=1,
                value=default_config.get("max_open_orders", 1),
                help=t("同时允许的最大开仓订单数量"),
            )
            order_frequency = st.number_input(
                t("订单频率（秒）"),
                min_value=0.0,
                value=default_config.get("order_frequency", 1.0),
                help=t("下单之间的最小时间间隔"),
            )
        keep_position = st.checkbox(
            t("停止时保持仓位"), value=default_config.get("keep_position", False), help=t("策略停止时是否保留仓位")
        )

        # Grid level configuration
        open_ratios = []
        open_rebound_ratios = []
        take_profit_ratios = []
        take_profit_rebound_ratios = []
        stop_loss_ratios = []
        amount_quote_ratios = []  # 用于amount_quote模式
        amount_base_values = []  # 用于amount_base模式

        for i in range(n_levels):
            st.write(f"#### {t('层级')} {i+1}")
            c1, c2, c3 = st.columns(3)
            with c1:
                open_ratios.append(
                    st.number_input(
                        t("开仓比率"),
                        min_value=0.0001,
                        max_value=1.0,
                        value=0.01,
                        step=0.0001,
                        format="%0.4f",
                        key=f"open_ratio_{i}",
                    )
                )
                take_profit_ratios.append(
                    st.number_input(
                        t("止盈比率"),
                        min_value=0.0001,
                        max_value=1.0,
                        value=0.01,
                        step=0.0001,
                        format="%0.4f",
                        key=f"take_profit_ratio_{i}",
                    )
                )
            with c2:
                open_rebound_ratios.append(
                    st.number_input(
                        t("开仓反弹比率"),
                        min_value=0.00001,
                        max_value=1.0,
                        value=0.001,
                        step=0.00001,
                        format="%0.5f",
                        key=f"open_rebound_ratio_{i}",
                    )
                )
                take_profit_rebound_ratios.append(
                    st.number_input(
                        t("止盈反弹比率"),
                        min_value=0.00001,
                        max_value=1.0,
                        value=0.001,
                        step=0.00001,
                        format="%0.5f",
                        key=f"take_profit_rebound_ratio_{i}",
                    )
                )
            with c3:
                stop_loss_ratios.append(
                    st.number_input(
                        t("止损比率"),
                        min_value=0.001,
                        max_value=1.0,
                        value=1.0,
                        step=0.001,
                        format="%0.3f",
                        key=f"stop_loss_ratio_{i}",
                    )
                )

                # 根据投资模式显示不同的输入控件
                if investment_mode == "amount_quote":
                    amount_quote_ratios.append(
                        st.number_input(
                            t("金额 (报价货币)"),
                            min_value=0.0,
                            value=10.0,
                            step=0.1,
                            format="%0.2f",
                            key=f"amount_quote_{i}",
                        )
                    )
                    amount_base_values.append(0.0)
                else:  # amount_base模式
                    base_currency = trading_pair.split("-")[0]
                    amount_base = st.number_input(
                        t(f"数量 ({base_currency})"),
                        min_value=0.0,
                        value=0.01,
                        step=0.0001,
                        format="%0.4f",
                        key=f"amount_base_{i}",
                    )
                    amount_base_values.append(amount_base)
                    amount_quote_ratios.append(0.0)

    # 移除金额分配比率检查，修改为总金额显示
    if investment_mode == "amount_quote":
        total_quote = sum(amount_quote_ratios)
        quote_currency = trading_pair.split("-")[1]
        st.info(t(f"每级别金额总和: {total_quote:.4f} {quote_currency}"))
    else:  # amount_base模式
        total_base = sum(amount_base_values)
        base_currency = trading_pair.split("-")[0]
        st.info(t(f"每级别数量总和: {total_base:.6f} {base_currency}"))

    # Return configuration
    config_dict = {
        "id": default_config.get("id", str(uuid.uuid4())),
        "controller_name": "cci_flexible_grid",
        "controller_type": "directional_trading",
        "connector_name": connector_name,
        "trading_pair": trading_pair,
        "leverage": leverage,
        "max_executors_per_side": max_executors_per_side,
        "cooldown_time": cooldown_time,
        "position_mode": position_mode,
        "candles_connector": candles_connector_name,
        "candles_trading_pair": candles_trading_pair,
        "interval": interval,
        "use_cci_signal": use_cci_signal,
        "update_on_close_only": update_on_close_only,
        "cci_length": cci_length,
        "cci_long_threshold": cci_long_threshold,
        "cci_short_threshold": cci_short_threshold,
        "cci_long_condition": cci_long_condition,
        "cci_short_condition": cci_short_condition,
        "side": side_value,
        "n_levels": n_levels,
        "first_level_open": first_level_open,
        "min_levels_for_global_barriers": min_levels_for_global_barriers,
        "min_reopen_interval": min_reopen_interval,
        "max_open_orders": max_open_orders,
        "order_frequency": order_frequency,
        "keep_position": keep_position,
        "open_ratios": open_ratios,
        "open_rebound_ratios": open_rebound_ratios,
        "take_profit_ratios": take_profit_ratios,
        "take_profit_rebound_ratios": take_profit_rebound_ratios,
        "stop_loss_ratios": stop_loss_ratios,
        "stop_loss": sl,
        "take_profit": tp,
        "time_limit": time_limit,
        "trailing_stop": {"activation_price": ts_ap, "trailing_delta": ts_delta},
        "take_profit_order_type": take_profit_order_type.value,
        "profit_target_amount": profit_target_amount,
        "loss_target_amount": loss_target_amount,
        "candles_config": [],
        "manual_kill_switch": False,
        "investment_mode": investment_mode,
        "total_amount_quote": total_amount_quote,  # 保留总金额参数以兼容旧配置
    }

    # 根据投资模式添加相应的字段
    if investment_mode == "amount_quote":
        config_dict["amount_quote"] = amount_quote_ratios
    else:  # amount_base模式
        config_dict["amount_base"] = amount_base_values

    return config_dict
