import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.st_utils import get_backend_api_client, initialize_st_page
from frontend.visualization import theme
from frontend.visualization.utils import add_traces_to_fig
from frontend.utils.i18n import t
from frontend.pages.config.funding_rate_arb_v2.user_inputs import user_inputs

# Initialize the Streamlit page
initialize_st_page(page_title=t("funding_rate_arb_title"), icon="💰", initial_sidebar_state="expanded")
backend_api_client = get_backend_api_client()

get_default_config_loader("v2_funding_rate_arb")

# Get user inputs
inputs = user_inputs()
st.session_state["default_config"].update(inputs)

# 确保包含必要的控制器字段
if "controller_name" not in st.session_state["default_config"]:
    st.session_state["default_config"]["controller_name"] = "funding_rate_arb_v2"
if "controller_type" not in st.session_state["default_config"]:
    st.session_state["default_config"]["controller_type"] = "generic"

# Add save configuration button
render_save_config("v2_funding_rate_arb", st.session_state["default_config"])
