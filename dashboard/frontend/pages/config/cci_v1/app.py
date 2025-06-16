import streamlit as st
from plotly.subplots import make_subplots

from frontend.components.config_loader import get_default_config_loader
from frontend.components.save_config import render_save_config
from frontend.pages.config.cci_v1.user_inputs import user_inputs
from frontend.pages.config.utils import get_candles
from frontend.st_utils import get_backend_api_client, initialize_st_page, t
from frontend.visualization import theme
from frontend.visualization.candles import get_candlestick_trace
from frontend.visualization.indicators import get_cci_traces, get_volume_trace
from frontend.visualization.signals import get_cci_v1_signal_traces
from frontend.visualization.utils import add_traces_to_fig

# Initialize Streamlit page with a clean layout
initialize_st_page(page_title=t("CCI V1 Strategy"), icon="📈", initial_sidebar_state="expanded")

# Setup backend connection
backend_api_client = get_backend_api_client()

# Display header and description
# st.title(t("CCI V1 Strategy Configuration"))
# st.markdown(t("This tool helps you configure and visualize the CCI V1 trading strategy."))

# Load default configuration
get_default_config_loader("cci_v1")

# Get user inputs with the updated configuration
inputs = user_inputs()
st.session_state["default_config"].update(inputs)

# Visualization section
st.markdown(t("### Visualizing Signals"))
with st.container():
    days_to_visualize = st.number_input(t("Days to Visualize"), min_value=1, max_value=365, value=1)

    # Load candle data
    candles = get_candles(
        connector_name=inputs["candles_connector"],
        trading_pair=inputs["candles_trading_pair"],
        interval=inputs["interval"],
        days=days_to_visualize,
    )

    # Check if we have valid candle data
    if candles is None or candles.empty:
        st.warning(t("No candle data available for the selected parameters."))
    else:
        # Create subplots with improved layout
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(t("Price Action & Signals"), t("CCI Indicator"), t("Volume")),
            row_heights=[0.5, 0.3, 0.2],
        )

        # Add candlestick chart
        add_traces_to_fig(fig, [get_candlestick_trace(candles)], row=1, col=1)

        # Add CCI signals
        add_traces_to_fig(
            fig,
            get_cci_v1_signal_traces(
                candles,
                inputs["length"],
                inputs["overbought"],
                inputs["oversold"],
            ),
            row=1,
            col=1,
        )

        # Add CCI indicator
        add_traces_to_fig(
            fig,
            get_cci_traces(candles, inputs["length"], inputs["overbought"], inputs["oversold"]),
            row=2,
            col=1,
        )

        # Add volume
        add_traces_to_fig(fig, [get_volume_trace(candles)], row=3, col=1)

        # Update layout with improved aesthetics
        layout_settings = theme.get_default_layout()
        layout_settings.update(
            {
                "showlegend": True,
                "height": 800,
                "margin": dict(t=30, l=10, r=10, b=10),
                "plot_bgcolor": "rgba(0,0,0,0)",
                "paper_bgcolor": "rgba(0,0,0,0)",
            }
        )
        fig.update_layout(**layout_settings)

        # Update y-axis titles
        fig.update_yaxes(title_text=t("Price"), row=1, col=1)
        fig.update_yaxes(title_text=t("CCI Value"), row=2, col=1)
        fig.update_yaxes(title_text=t("Volume"), row=3, col=1)

        # Display the chart
        st.plotly_chart(fig, use_container_width=True)

# Configuration save section
st.markdown("---")
render_save_config(st.session_state["default_config"]["id"], st.session_state["default_config"])
