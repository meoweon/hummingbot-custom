import json
import streamlit as st
from streamlit_elements import elements, mui

from frontend.st_utils import get_backend_api_client
from frontend.utils.i18n import t


def render_config_editor(config_id: str = None):
    """
    渲染配置编辑器组件

    Args:
        config_id: 要编辑的配置ID，如果为None则显示配置选择器
    """
    backend_api_client = get_backend_api_client()

    # 获取所有配置
    all_configs = backend_api_client.get_all_controllers_config()

    # 如果没有指定config_id，显示配置选择器
    if not config_id:
        if not all_configs:
            return
        config_options = [config["id"] for config in all_configs]
        config_id = st.selectbox(t("select_config_to_edit"), config_options)

    # 获取选中的配置
    selected_config = next((config for config in all_configs if config["id"] == config_id), None)

    if not selected_config:
        return

    # 将配置转换为格式化的JSON字符串
    config_str = json.dumps(selected_config, indent=2, ensure_ascii=False)

    # 初始化或更新编辑内容
    if "edited_config_str" not in st.session_state or st.session_state.editing_config_id != config_id:
        st.session_state.edited_config_str = config_str
        st.session_state.editing_config_id = config_id
        st.session_state.config_saved = False

    def handle_close():
        st.session_state.show_config_editor = False
        st.session_state.editing_config_id = None
        st.session_state.need_refresh = True

    def handle_save():
        try:
            # 解析编辑后的JSON
            edited_config = json.loads(st.session_state.edited_config_str)

            # 保存更新后的配置
            backend_api_client.add_controller_config(edited_config)

            # 设置成功状态
            st.session_state.config_saved = True
            st.session_state.show_config_editor = False
            st.session_state.editing_config_id = None
            st.session_state.need_refresh = True

        except json.JSONDecodeError as e:
            st.error(f"{t('invalid_json')}: {str(e)}")
        except Exception as e:
            st.error(f"{t('error_saving_config')}: {str(e)}")

    # 确保弹窗只在 show_config_editor 为 True 时显示
    if st.session_state.show_config_editor:
        with elements(f"config_editor_{config_id}"):
            with mui.Dialog(
                open=True,
                fullWidth=True,
                maxWidth="md",
                onClose=handle_close,
            ):
                mui.DialogTitle(f"编辑配置: {config_id}")

                with mui.DialogContent(dividers=True):
                    mui.TextField(
                        key=f"editor_{config_id}",
                        label="",
                        multiline=True,
                        rows=20,
                        fullWidth=True,
                        defaultValue=st.session_state.edited_config_str,
                        onChange=lambda e: setattr(st.session_state, "edited_config_str", e["target"]["value"]),
                        sx={"fontFamily": "monospace", "& .MuiInputBase-input": {"cursor": "text"}},
                        inputProps={"spellCheck": "false"},
                    )

                with mui.DialogActions():
                    mui.Button("取消", onClick=handle_close, color="inherit")
                    mui.Button(
                        "保存",
                        onClick=handle_save,
                        variant="contained",
                        color="primary",
                    )
