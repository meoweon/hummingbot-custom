import json
import os

import streamlit as st

from backend.services.backend_api_client import BackendAPIClient
from frontend.utils.i18n import t


def display_etl_section(backend_api: BackendAPIClient):
    try:
        db_paths = backend_api.list_databases()
        dbs_dict = backend_api.read_databases(db_paths)
        healthy_dbs = [db["db_path"].replace("sqlite:///", "") for db in dbs_dict if db["healthy"]]
        with st.expander(t("ETL Tool")):
            st.markdown(t("In this tool, you can easily fetch and combine different databases. Just follow these simple steps:"))

            steps_html = """
            <ul>
                <li>{0}</li>
                <li>{1}</li>
                <li>{2}</li>
            </ul>
            """.format(
                t("Choose the ones you want to analyze (only non-corrupt databases are available)"),
                t("Merge them into a checkpoint"),
                t("Start analyzing"),
            )
            st.markdown(steps_html, unsafe_allow_html=True)

            if len(healthy_dbs) == 0:
                st.warning(
                    t(
                        "Oops, it looks like there are no databases here. If you uploaded a file and it's not showing up, "
                        "you can check the status report."
                    )
                )
                st.dataframe([db["status"] for db in dbs_dict], use_container_width=True)
            else:
                st.markdown("#### " + t("Select Databases to Merge"))
                selected_dbs = st.multiselect(
                    t("Choose the databases you want to merge"), healthy_dbs, label_visibility="collapsed"
                )
                if len(selected_dbs) == 0:
                    st.warning(t("No databases selected. Please select at least one database."))
                else:
                    st.markdown("#### " + t("Create Checkpoint"))
                    if st.button(t("Save")):
                        response = backend_api.create_checkpoint(selected_dbs)
                        if response and response.get("message") == "Checkpoint created successfully.":
                            st.success(t("Checkpoint created successfully!"))
                        else:
                            st.error(t("Error creating checkpoint. Please try again."))

        checkpoints_list = backend_api.list_checkpoints(full_path=True)
        if not checkpoints_list or len(checkpoints_list) == 0:
            st.warning(t("No checkpoints detected. Please create a new one to continue."))
            st.stop()
            return None
        else:
            selected_checkpoint = st.selectbox(t("Select a checkpoint to load"), checkpoints_list)

            # 重要：不检查本地文件系统，因为dashboard容器内没有挂载bots目录
            # 直接通过API加载检查点数据，让backend-api处理文件访问
            checkpoint_data = fetch_checkpoint_data(backend_api, selected_checkpoint)

            # 验证checkpoint_data是否有效
            if not checkpoint_data or not isinstance(checkpoint_data, dict):
                st.error(t("Failed to load checkpoint data. The checkpoint file may be corrupted or not accessible."))
                st.stop()
                return None

            # 验证必要的字段是否存在
            required_fields = ["executors", "orders", "trade_fill", "controllers"]
            missing_fields = [field for field in required_fields if field not in checkpoint_data]
            if missing_fields:
                st.error(
                    t(
                        f"The checkpoint data is missing required fields: {', '.join(missing_fields)}. Please select another checkpoint."
                    )
                )
                st.stop()
                return None

            # 安全地处理JSON转换
            try:
                checkpoint_data["executors"] = (
                    json.loads(checkpoint_data["executors"])
                    if isinstance(checkpoint_data["executors"], str)
                    else checkpoint_data["executors"]
                )
                checkpoint_data["orders"] = (
                    json.loads(checkpoint_data["orders"])
                    if isinstance(checkpoint_data["orders"], str)
                    else checkpoint_data["orders"]
                )
                checkpoint_data["trade_fill"] = (
                    json.loads(checkpoint_data["trade_fill"])
                    if isinstance(checkpoint_data["trade_fill"], str)
                    else checkpoint_data["trade_fill"]
                )
                checkpoint_data["controllers"] = (
                    json.loads(checkpoint_data["controllers"])
                    if isinstance(checkpoint_data["controllers"], str)
                    else checkpoint_data["controllers"]
                )
            except json.JSONDecodeError:
                st.error(t("Failed to parse checkpoint data. The checkpoint file may be corrupted."))
                st.stop()
                return None

            return checkpoint_data

    except Exception as e:
        st.error(t(f"An error occurred while loading performance data: {str(e)}"))
        st.stop()
        return None


@st.cache_data
def fetch_checkpoint_data(_backend_api: BackendAPIClient, selected_checkpoint: str):
    try:
        if not selected_checkpoint:
            return None

        # 直接加载检查点，不检查本地文件系统
        # backend-api负责查找和访问文件
        checkpoint_data = _backend_api.load_checkpoint(selected_checkpoint)

        if not checkpoint_data:
            st.error(t("Failed to load checkpoint data. The checkpoint file may not exist or is not accessible."))
            return None

        return checkpoint_data
    except Exception as e:
        st.error(t(f"Error loading checkpoint data: {str(e)}"))
        return None
