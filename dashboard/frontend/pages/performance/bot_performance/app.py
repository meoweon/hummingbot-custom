import asyncio

import streamlit as st

from backend.utils.performance_data_source import PerformanceDataSource
from frontend.st_utils import get_backend_api_client, initialize_st_page
from frontend.utils.i18n import t
from frontend.visualization.bot_performance import (
    display_execution_analysis,
    display_global_results,
    display_performance_summary_table,
    display_tables_section,
)
from frontend.visualization.performance_etl import display_etl_section


async def main():
    initialize_st_page(page_title=t("Bot Performance"), icon="🚀", initial_sidebar_state="collapsed")
    st.session_state["default_config"] = {}
    backend_api = get_backend_api_client()

    st.subheader("🔫 " + t("DATA SOURCE"))
    checkpoint_data = display_etl_section(backend_api)

    # 检查checkpoint_data是否有效
    if checkpoint_data is None:
        st.error(t("Unable to load performance data. Please create a new checkpoint or select a valid one."))
        st.info(t("If you recently deleted a database file, you'll need to create a new checkpoint."))
        st.stop()
        return

    try:
        data_source = PerformanceDataSource(checkpoint_data)
        st.divider()

        st.subheader("📊 " + t("OVERVIEW"))
        display_performance_summary_table(data_source.get_executors_df(), data_source.executors_with_orders)
        st.divider()

        st.subheader("🌎 " + t("GLOBAL RESULTS"))
        display_global_results(data_source)
        st.divider()

        st.subheader("🧨 " + t("EXECUTION"))
        display_execution_analysis(data_source)
        st.divider()

        st.subheader("💾 " + t("EXPORT"))
        display_tables_section(data_source)
    except Exception as e:
        st.error(t(f"An error occurred while processing performance data: {str(e)}"))
        st.info(t("The selected checkpoint may be corrupted or in an incompatible format. Please create a new checkpoint."))
        st.stop()


if __name__ == "__main__":
    asyncio.run(main())
