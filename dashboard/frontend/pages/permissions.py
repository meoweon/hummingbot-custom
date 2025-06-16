from st_pages import Page, Section
from frontend.utils.i18n import t


def main_page():
    return [Page("main.py", t("hummingbot_dashboard"), "🦉")]


def public_pages():
    return [
        Section(t("config_generator_nav"), "🎛️"),
        Page("frontend/pages/config/grid_strike/app.py", t("grid_strike_nav"), "📉"),
        Page("frontend/pages/config/pmm_simple/app.py", t("pmm_simple_nav"), "🤹"),
        Page("frontend/pages/config/pmm_dynamic/app.py", t("pmm_dynamic_nav"), "🔄"),
        Page("frontend/pages/config/dman_maker_v2/app.py", t("d_man_maker_v2_nav"), "🧙‍♂️"),
        Page("frontend/pages/config/dman_v3/app.py", t("dman_v3_title"), "🔮"),
        Page("frontend/pages/config/flexible_grid/app.py", t("flexible_grid_nav"), "📊"),
        Page("frontend/pages/config/spot_perp_arbitrage/app.py", t("spot_perp_arb_title"), "⚖️"),
        Page("frontend/pages/config/funding_rate_arb_v2/app.py", t("funding_rate_arb_title"), "💸"),
        Page("frontend/pages/config/bollinger_v1/app.py", t("bollinger_v1_nav"), "💼"),
        Page("frontend/pages/config/macd_bb_v1/app.py", t("macd_bb_v1_nav"), "📈"),
        Page("frontend/pages/config/supertrend_v1/app.py", t("supertrend_v1_nav"), "🌊"),
        Page("frontend/pages/config/cci_v1/app.py", t("cci_v1_nav"), "📊"),
        Page("frontend/pages/config/xemm_controller/app.py", t("xemm_controller_nav"), "🔀"),
        Page("frontend/pages/config/liquidation_sniper/app.py", t("liquidation_sniper_nav"), "🎯"),
        Section(t("data_nav"), "💾"),
        Page("frontend/pages/data/download_candles/app.py", t("download_candles_nav"), "📥"),
        Section(t("community_pages"), "👨‍👩‍👧‍👦"),
        Page("frontend/pages/data/token_spreads/app.py", t("token_spreads_nav"), "↔️"),
        Page("frontend/pages/data/tvl_vs_mcap/app.py", t("tvl_vs_mcap_nav"), "📊"),
        Page("frontend/pages/performance/bot_performance/app.py", t("strategy_performance"), "📋"),
    ]


def private_pages():
    return [
        Section(t("bot_orchestration"), "🐙"),
        Page("frontend/pages/orchestration/instances/app.py", t("instances_nav"), "🖥️"),
        Page("frontend/pages/orchestration/launch_bot_v2/app.py", t("deploy_v2_nav"), "🚀"),
        Page("frontend/pages/orchestration/credentials/app.py", t("credentials_nav"), "🔑"),
        Page("frontend/pages/orchestration/portfolio/app.py", t("portfolio_nav"), "💰"),
        Section(t("user_management"), "👤"),
        Page("frontend/pages/user_management/settings.py", t("settings"), "⚙️"),
    ]
