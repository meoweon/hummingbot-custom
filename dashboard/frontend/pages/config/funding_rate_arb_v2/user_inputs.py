import streamlit as st
from frontend.utils.i18n import t


def user_inputs():
    """
    Get user inputs for the funding rate arbitrage strategy.
    """
    inputs = {}

    # Add controller name and type
    inputs["controller_name"] = "funding_rate_arb_v2"
    inputs["controller_type"] = "generic"

    # Basic Configuration
    with st.expander("基本配置", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            # Tokens
            inputs["tokens"] = st.text_input("交易对", value="BTC,ETH", help="输入交易对，用逗号分隔").split(",")

            # Connectors
            inputs["connectors"] = st.multiselect(
                "交易所",
                ["binance_perpetual", "bitget_perpetual", "okx_perpetual", "bybit_perpetual", "gateio_perpetual"],
                default=["binance_perpetual", "okx_perpetual"],
            )

            # Position Mode
            inputs["position_mode"] = st.selectbox(
                "持仓模式",
                ["HEDGE", "ONEWAY"],
                help="HEDGE允许同时持有多空仓位，ONEWAY只允许持有一个方向的仓位",
            )

        with col2:
            # Leverage
            inputs["leverage"] = st.number_input("杠杆", min_value=1, max_value=100, value=20, help="设置杠杆倍数")

            # Position Size
            inputs["position_size_quote"] = float(
                st.number_input("仓位大小 (USDT)", min_value=10.0, value=100.0, step=10.0, help="每个交易对的仓位资金量")
            )

            # Trade Profitability
            inputs["trade_profitability_condition"] = st.checkbox(
                "启用交易盈利条件", value=False, help="勾选后，只有资金费率预计可以盈利才会开仓"
            )

    # Advanced Configuration
    with st.expander("高级配置", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            # Min Funding Rate
            inputs["min_funding_rate_profitability"] = float(
                st.number_input(
                    "最小资金费率盈利阈值",
                    min_value=0.0001,
                    value=0.001,
                    format="%.4f",
                    step=0.0001,
                    help="当资金费率超过此阈值时才会开仓",
                )
            )

            # Funding Rate Stop Loss
            inputs["funding_rate_diff_stop_loss"] = float(
                st.number_input(
                    "资金费率差止损",
                    min_value=-0.01,
                    max_value=0.0,
                    value=-0.001,
                    format="%.4f",
                    step=0.0001,
                    help="当资金费率差小于此值时会平仓",
                )
            )

        with col2:
            # Take Profit Condition
            inputs["profitability_to_take_profit"] = float(
                st.number_input(
                    "获利平仓条件",
                    min_value=0.001,
                    value=0.01,
                    format="%.4f",
                    step=0.001,
                    help="当盈利达到此百分比时平仓",
                )
            )

    return inputs
