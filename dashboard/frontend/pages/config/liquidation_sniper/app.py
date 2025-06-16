import json
import time
import streamlit as st
from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.st_utils import get_backend_api_client, initialize_st_page, t

# Import submodules
from frontend.pages.config.liquidation_sniper.user_inputs import user_inputs

# Initialize the Streamlit page
initialize_st_page(page_title=t("Liquidation Sniper Strategy"), icon="🎯")

# 初始化后端API客户端
backend_api_client = get_backend_api_client()

# 加载默认配置
get_default_config_loader("liquidation_sniper")

# 获取用户输入
inputs = user_inputs()

# 更新会话状态中的配置
st.session_state["default_config"].update(inputs)

# 创建配置总结部分
with st.expander(t("Configuration Summary"), expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**{t('Trading Connector')}:** {inputs['connector_name']}")
        st.markdown(f"**{t('Trading Pair')}:** {inputs['trading_pair']}")
        st.markdown(f"**{t('Liquidation Side')}:** {inputs['liquidation_side']}")
        st.markdown(f"**{t('Liquidations Pair')}:** {inputs['liquidations_pair']}")

    with col2:
        st.markdown(f"**{t('Liquidations Interval')}:** {inputs['liquidations_interval_seconds']} {t('seconds')}")
        st.markdown(f"**{t('Trigger Amount')}:** ${inputs['liquidations_trigger_usd_amount']}")
        st.markdown(f"**{t('Total Amount')}:** ${inputs['total_amount_quote']}")
        st.markdown(f"**{t('Leverage')}:** {inputs['leverage']}x")

    with col3:
        st.markdown(f"**{t('Stop Loss')}:** {inputs['stop_loss'] * 100}%")
        st.markdown(f"**{t('Take Profit')}:** {inputs['take_profit'] * 100}%")
        st.markdown(f"**{t('Time Limit')}:** {inputs['time_limit']} {t('seconds')}")
        st.markdown(f"**{t('Position Mode')}:** {inputs['position_mode']}")

st.write("---")

# 保存配置
render_save_config(st.session_state["default_config"]["id"], st.session_state["default_config"])
