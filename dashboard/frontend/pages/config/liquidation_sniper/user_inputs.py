import streamlit as st
import time
from frontend.st_utils import initialize_st_page, t
from frontend.utils.i18n import get_current_language, set_language, SUPPORTED_LANGUAGES
from frontend.utils.api_debug import display_debug_panel


def app():
    # 初始化页面
    initialize_st_page(page_title=t("settings_title"), icon="⚙️")

    st.title(t("settings_title"))

    # 创建两个选项卡：一个用于应用设置，一个用于API调试
    tab1, tab2 = st.tabs([t("app_settings"), t("api_debug")])

    with tab1:
        st.header(t("language_settings"))

        # 获取当前语言
        current_lang = get_current_language()

        # 显示当前语言状态
        st.info(f"**{t('Current')}: {SUPPORTED_LANGUAGES[current_lang]}**")

        # 直接显示语言切换链接 - 最简单粗暴的方法
        st.markdown("### 点击下面的链接直接切换语言:")

        # 获取当前页面路径
        current_page = st.query_params.get("streamlit_origin_path", "/")
        if current_page == "" or current_page is None:
            current_page = "/"

        # 直接为每种语言创建一个链接按钮
        timestamp = int(time.time())

        # 创建链接的容器，使用CSS网格布局
        st.markdown(
            """
        <style>
        .language-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }
        .language-btn {
            background-color: #f0f2f6;
            color: #262730;
            padding: 10px 15px;
            border-radius: 5px;
            text-align: center;
            display: block;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .language-btn:hover {
            background-color: #e0e2e6;
        }
        .language-btn.active {
            background-color: #00ACEE;
            color: white;
        }
        </style>
        <div class="language-grid">
        """,
            unsafe_allow_html=True,
        )

        # 为每种语言创建链接按钮
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            active_class = "active" if lang_code == current_lang else ""
            html = f"""
            <a href="{current_page}?lang={lang_code}&ts={timestamp}" target="_top" class="language-btn {active_class}">
                {lang_name}
            </a>
            """
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # 添加解释说明
        st.caption("点击链接后整个应用将重新加载并应用新的语言设置")

    with tab2:
        # 添加API调试模式开关
        st.header("开发选项")
        # 确保session_state中有show_debug
        if "show_debug" not in st.session_state:
            st.session_state.show_debug = False

        # 添加API调试模式开关
        st.session_state.show_debug = st.toggle(
            "🔍 API调试模式", value=st.session_state.show_debug, help="显示API请求和响应的详细信息"
        )

        # 只有当调试模式开启时才显示调试面板
        if st.session_state.show_debug:
            # 显示API调试面板
            display_debug_panel()
        else:
            st.info("请开启API调试模式以查看API请求和响应信息")


def user_inputs():
    """获取清算狙击手策略的用户输入参数"""

    # 基础配置
    st.markdown("## " + t("Basic Configuration"))

    # 交易设置
    st.markdown("### " + t("Trading Settings"))
    col1, col2 = st.columns(2)
    with col1:
        connector_name = st.text_input(
            t("Trading Connector"),
            value="okx_perpetual",
            help="输入交易所连接器名称，例如: binance_perpetual, bitget_perpetual, okx_perpetual 等",
        )
    with col2:
        trading_pair = st.text_input(t("Trading Pair"), value="BTC-USDT")

    # 清算设置
    st.markdown("### " + t("Liquidation Settings"))
    col1, col2 = st.columns(2)
    with col1:
        liquidation_side = st.selectbox(t("Liquidation Side"), options=["LONG", "SHORT"], index=0)
        liquidations_pair = st.text_input(t("Liquidations Pair"), value="BTC-USDT")
    with col2:
        liquidations_interval_seconds = st.number_input(t("Liquidations Interval (seconds)"), min_value=1, value=15)
        liquidations_trigger_usd_amount = st.number_input(
            t("Liquidations Trigger Amount (USD)"), min_value=100000, value=10000000
        )

    # DCA设置
    st.markdown("### " + t("DCA Settings"))
    col1, col2 = st.columns(2)
    with col1:
        total_amount_quote = st.number_input(t("Total Amount Quote"), min_value=10.0, value=100.0)
    with col2:
        dca_levels_percent = st.text_input(t("DCA Levels Percent (comma separated)"), value="0.01,0.02,0.03,0.05")
        dca_amounts_percent = st.text_input(t("DCA Amounts Percent (comma separated)"), value="0.1,0.2,0.3,0.4")

    # 风险管理
    st.markdown("### " + t("Risk Management"))
    col1, col2, col3 = st.columns(3)
    with col1:
        stop_loss = st.number_input(t("Stop Loss (%)"), min_value=0.1, max_value=100.0, value=3.0) / 100
    with col2:
        take_profit = st.number_input(t("Take Profit (%)"), min_value=0.1, max_value=100.0, value=1.0) / 100
    with col3:
        time_limit = st.number_input(t("Time Limit (seconds)"), min_value=60, value=1800)

    # 永续合约设置
    st.markdown("### " + t("Perpetual Settings"))
    col1, col2 = st.columns(2)
    with col1:
        leverage = st.number_input(t("Leverage"), min_value=1, max_value=100, value=5)
    with col2:
        position_mode = st.selectbox(t("Position Mode"), options=["HEDGE", "ONEWAY"], index=0)

    # 返回配置字典
    return {
        "id": f"liquidation_sniper_{connector_name}_{trading_pair}",
        "controller_name": "liquidations_sniper",
        "controller_type": "generic",
        "connector_name": connector_name,
        "trading_pair": trading_pair,
        "liquidation_side": liquidation_side,
        "liquidations_pair": liquidations_pair,
        "liquidations_interval_seconds": liquidations_interval_seconds,
        "liquidations_trigger_usd_amount": liquidations_trigger_usd_amount,
        "total_amount_quote": total_amount_quote,
        "dca_levels_percent": dca_levels_percent,
        "dca_amounts_percent": dca_amounts_percent,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "time_limit": time_limit,
        "leverage": leverage,
        "position_mode": position_mode,
    }


if __name__ == "__main__":
    app()
