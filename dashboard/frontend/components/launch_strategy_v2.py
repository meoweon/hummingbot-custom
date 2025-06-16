import time

import streamlit as st
from streamlit_elements import lazy, mui, elements

from ..st_utils import get_backend_api_client
from ..utils.i18n import t
from .dashboard import Dashboard
from .config_editor import render_config_editor


class LaunchStrategyV2(Dashboard.Item):
    DEFAULT_ROWS = []
    DEFAULT_COLUMNS = [
        {
            "field": "config_base",
            "headerName": t("Config Base"),
            "minWidth": 160,
            "editable": False,
        },
        {
            "field": "version",
            "headerName": t("Version"),
            "minWidth": 100,
            "editable": False,
        },
        {
            "field": "controller_name",
            "headerName": t("Controller Name"),
            "width": 150,
            "editable": False,
        },
        {
            "field": "controller_type",
            "headerName": t("Controller Type"),
            "width": 150,
            "editable": False,
        },
        {
            "field": "connector_name",
            "headerName": t("Connector"),
            "width": 150,
            "editable": False,
        },
        {
            "field": "trading_pair",
            "headerName": t("Trading pair"),
            "width": 140,
            "editable": False,
        },
        {
            "field": "total_amount_quote",
            "headerName": t("Total amount ($)"),
            "width": 140,
            "editable": False,
        },
        {
            "field": "max_loss_quote",
            "headerName": t("Max loss ($)"),
            "width": 120,
            "editable": False,
        },
        {
            "field": "stop_loss",
            "headerName": t("SL (%)"),
            "width": 100,
            "editable": False,
        },
        {
            "field": "take_profit",
            "headerName": t("TP (%)"),
            "width": 100,
            "editable": False,
        },
        {
            "field": "trailing_stop",
            "headerName": t("TS (%)"),
            "width": 120,
            "editable": False,
        },
        {
            "field": "time_limit",
            "headerName": t("Time limit"),
            "width": 100,
            "editable": False,
        },
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend_api_client = get_backend_api_client()
        self._controller_configs_available = self._backend_api_client.get_all_controllers_config()
        self._controller_config_selected = None
        self._bot_name = None
        self._image_name = "hummingbot/hummingbot:latest"
        self._credentials = "master_account"
        self._max_global_drawdown = None
        self._max_controller_drawdown = None
        self._rebalance_interval = None
        self._asset_to_rebalance = "USDT"
        self._max_active_controllers = None

        # 初始化或重置配置选择状态
        st.session_state["config_selection_status"] = "None"

        # 初始化编辑器状态
        if "show_config_editor" not in st.session_state:
            st.session_state.show_config_editor = False
        if "editing_config_id" not in st.session_state:
            st.session_state.editing_config_id = None
        if "need_refresh" not in st.session_state:
            st.session_state.need_refresh = False

    def _set_bot_name(self, event):
        self._bot_name = event.target.value

    def _set_image_name(self, _, childs):
        self._image_name = childs.props.value

    def _set_credentials(self, _, childs):
        self._credentials = childs.props.value

    def _set_controller(self, event):
        self._controller_selected = event.target.value

    def _handle_row_selection(self, params, _):
        """处理行选择事件，在MUI DataGrid中，params是选中行的ID列表"""
        if params and len(params) > 0:
            self._controller_config_selected = [f"{str(param)}.yml" for param in params]
            st.session_state["config_selection_status"] = f"{len(params)}"
        else:
            self._controller_config_selected = []
            st.session_state["config_selection_status"] = "0"

    def _set_max_global_drawdown(self, event):
        self._max_global_drawdown = event.target.value

    def _set_max_controller_drawdown(self, event):
        self._max_controller_drawdown = event.target.value

    def _set_rebalance_interval(self, event):
        self._rebalance_interval = event.target.value

    def _set_asset_to_rebalance(self, event):
        self._asset_to_rebalance = event.target.value

    def _set_max_active_controllers(self, event):
        """设置最大活跃控制器数量"""
        self._max_active_controllers = event.target.value

    def launch_new_bot(self):
        if not self._bot_name:
            st.warning(t("You need to define the bot name."))
            return
        if not self._image_name:
            st.warning(t("You need to select the hummingbot image."))
            return
        if not self._controller_config_selected or len(self._controller_config_selected) == 0:
            st.warning(
                t(
                    "You need to select the controllers configs. Please select at least one controller config by clicking on the checkbox."
                )
            )
            return

        try:
            with st.spinner("正在准备配置..."):
                start_time_str = time.strftime("%Y.%m.%d_%H.%M")
                bot_name = f"{self._bot_name}-{self._credentials}-{start_time_str}"
                script_config = {
                    "name": bot_name,
                    "content": {
                        "markets": {},
                        "candles_config": [],
                        "controllers_config": self._controller_config_selected,
                        "config_update_interval": 10,
                        "script_file_name": "v2_with_controllers.py",
                        "time_to_cash_out": None,
                    },
                }
                if self._max_global_drawdown:
                    script_config["content"]["max_global_drawdown"] = self._max_global_drawdown
                if self._max_controller_drawdown:
                    script_config["content"]["max_controller_drawdown"] = self._max_controller_drawdown
                if self._rebalance_interval:
                    script_config["content"]["rebalance_interval"] = self._rebalance_interval
                    if self._asset_to_rebalance and "USD" in self._asset_to_rebalance:
                        script_config["content"]["asset_to_rebalance"] = self._asset_to_rebalance
                    else:
                        st.error(t("You need to define the asset to rebalance in USD like token."))
                        return
                if self._max_active_controllers:
                    script_config["content"]["max_active_controllers"] = int(self._max_active_controllers)

            with st.spinner("正在清理旧配置..."):
                delete_response = self._backend_api_client.delete_all_script_configs()
                if delete_response and delete_response.get("status") == "error":
                    st.error(f"清理旧配置失败: {delete_response.get('detail', '未知错误')}")
                    return

            with st.spinner("正在添加新配置..."):
                st.session_state["last_script_config"] = script_config
                add_config_response = self._backend_api_client.add_script_config(script_config)

                if not add_config_response:
                    st.error("配置添加失败: API返回空响应")
                    return

                if add_config_response.get("status") == "error":
                    st.error(f"配置添加失败: {add_config_response.get('detail', '未知错误')}")
                    return

            with st.spinner("正在创建机器人实例..."):
                deploy_config = {
                    "instance_name": bot_name,
                    "script": "v2_with_controllers.py",
                    "script_config": bot_name + ".yml",
                    "image": self._image_name,
                    "credentials_profile": self._credentials,
                }

                st.session_state["last_deploy_config"] = deploy_config
                create_response = self._backend_api_client.create_hummingbot_instance(deploy_config)

                if not create_response:
                    st.error("实例创建失败: API返回空响应")
                    return

                if create_response.get("status") == "error":
                    st.error(f"实例创建失败: {create_response.get('detail', '未知错误')}")
                    return

            with st.spinner(t("Starting Bot... This process may take a few seconds")):
                time.sleep(3)

            st.success("机器人已成功部署！您可以在实例页面查看其状态。")

            self._controller_config_selected = None
            self._bot_name = None
            st.session_state["config_selection_status"] = "None"

        except Exception as e:
            st.error(f"部署过程中发生错误: {str(e)}")
            st.session_state["deploy_error"] = str(e)

    def delete_selected_configs(self):
        if self._controller_config_selected:
            for config in self._controller_config_selected:
                response = self._backend_api_client.delete_controller_config(config)
                st.success(response)
            self._controller_configs_available = self._backend_api_client.get_all_controllers_config()
        else:
            st.warning(t("You need to select the controllers configs that you want to delete."))

    def __call__(self):
        # 检查是否需要刷新
        if st.session_state.get("need_refresh", False):
            st.session_state.need_refresh = False
            st.rerun()

        # 初始化配置选择状态，如果不存在
        if "config_selection_status" not in st.session_state:
            st.session_state["config_selection_status"] = "None"

        # 显示成功消息
        if st.session_state.get("config_saved", False):
            st.success(t("config_saved_successfully"))
            st.session_state.config_saved = False

        # 如果启用了编辑器，显示编辑器组件
        if st.session_state.show_config_editor and st.session_state.editing_config_id:
            render_config_editor(st.session_state.editing_config_id)

        with mui.Paper(
            key=self._key, sx={"display": "flex", "flexDirection": "column", "borderRadius": 3, "overflow": "hidden"}, elevation=1
        ):
            with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                mui.Typography("🎛️ " + t("Bot Configuration"), variant="h5")

            with mui.Grid(container=True, spacing=2, sx={"padding": "10px 15px 10px 15px"}):
                with mui.Grid(item=True, xs=3):
                    mui.TextField(
                        label=t("Instance Name"), variant="outlined", onChange=lazy(self._set_bot_name), sx={"width": "100%"}
                    )
                with mui.Grid(item=True, xs=3):
                    available_images = self._backend_api_client.get_available_images("hummingbot")
                    with mui.FormControl(variant="standard", sx={"width": "100%"}):
                        mui.FormHelperText(t("Available Images"))
                        with mui.Select(
                            label=t("Hummingbot Image"),
                            defaultValue="hummingbot/hummingbot:latest",
                            variant="standard",
                            onChange=lazy(self._set_image_name),
                        ):
                            for image in available_images:
                                mui.MenuItem(image, value=image)
                    available_credentials = self._backend_api_client.get_accounts()
                    with mui.FormControl(variant="standard", sx={"width": "100%"}):
                        mui.FormHelperText(t("Credentials"))
                        with mui.Select(
                            label=t("Credentials"),
                            defaultValue="master_account",
                            variant="standard",
                            onChange=lazy(self._set_credentials),
                        ):
                            for master_config in available_credentials:
                                mui.MenuItem(master_config, value=master_config)
                with mui.Grid(item=True, xs=3):
                    with mui.FormControl(variant="standard", sx={"width": "100%"}):
                        mui.FormHelperText(t("Risk Management"))
                        mui.TextField(
                            label=t("Max Global Drawdown (%)"),
                            variant="outlined",
                            type="number",
                            onChange=lazy(self._set_max_global_drawdown),
                            sx={"width": "100%"},
                        )
                        mui.TextField(
                            label=t("Max Controller Drawdown (%)"),
                            variant="outlined",
                            type="number",
                            onChange=lazy(self._set_max_controller_drawdown),
                            sx={"width": "100%"},
                        )
                        mui.TextField(
                            label=t("Max Active Controllers"),
                            variant="outlined",
                            type="number",
                            onChange=lazy(self._set_max_active_controllers),
                            sx={"width": "100%"},
                        )

                with mui.Grid(item=True, xs=3):
                    with mui.FormControl(variant="standard", sx={"width": "100%"}):
                        mui.FormHelperText(t("Rebalance Configuration"))
                        mui.TextField(
                            label=t("Rebalance Interval (minutes)"),
                            variant="outlined",
                            type="number",
                            onChange=lazy(self._set_rebalance_interval),
                            sx={"width": "100%"},
                        )
                        mui.TextField(
                            label=t("Asset to Rebalance"),
                            variant="outlined",
                            onChange=lazy(self._set_asset_to_rebalance),
                            sx={"width": "100%"},
                            default="USDT",
                        )
                all_controllers_config = self._backend_api_client.get_all_controllers_config()

                data = []
                for config in all_controllers_config:
                    connector_name = config.get("connector_name", "Unknown")
                    trading_pair = config.get("trading_pair", "Unknown")

                    total_amount_quote = config.get("total_amount_quote", 0)
                    if isinstance(total_amount_quote, str):
                        try:
                            total_amount_quote = float(total_amount_quote)
                        except (ValueError, TypeTypeError):
                            total_amount_quote = 0

                    stop_loss = config.get("stop_loss", 0)
                    if isinstance(stop_loss, str):
                        try:
                            stop_loss = float(stop_loss)
                        except (ValueError, TypeError):
                            stop_loss = 0

                    take_profit = config.get("take_profit", 0)
                    if isinstance(take_profit, str):
                        try:
                            take_profit = float(take_profit)
                        except (ValueError, TypeError):
                            take_profit = 0

                    trailing_stop = config.get("trailing_stop", {"activation_price": 0, "trailing_delta": 0})
                    time_limit = config.get("time_limit", 0)
                    if isinstance(time_limit, str):
                        try:
                            time_limit = float(time_limit)
                        except (ValueError, TypeError):
                            time_limit = 0

                    config_version = config["id"].split("_")
                    if len(config_version) > 1:
                        config_base = config_version[0]
                        version = config_version[1]
                    else:
                        config_base = config["id"]
                        version = "NaN"
                    ts_text = str(trailing_stop["activation_price"]) + " / " + str(trailing_stop["trailing_delta"])
                    data.append(
                        {
                            "id": config["id"],
                            "config_base": config_base,
                            "version": version,
                            "controller_name": config["controller_name"],
                            "controller_type": config.get("controller_type", "generic"),
                            "connector_name": connector_name,
                            "trading_pair": trading_pair,
                            "total_amount_quote": total_amount_quote,
                            "max_loss_quote": total_amount_quote * stop_loss,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "trailing_stop": ts_text,
                            "time_limit": time_limit,
                        }
                    )

                with mui.Grid(item=True, xs=12):
                    with mui.Paper(
                        key=self._key,
                        sx={
                            "display": "flex",
                            "flexDirection": "column",
                            "borderRadius": 3,
                            "overflow": "hidden",
                            "height": 1000,
                        },
                        elevation=2,
                    ):
                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                            with mui.Grid(container=True, spacing=2):
                                with mui.Grid(item=True, xs=8):
                                    selected_configs = st.session_state.get("config_selection_status", "0")
                                    mui.Typography(
                                        "🗄️ "
                                        + t("Available Configurations")
                                        + (f": 已选 {selected_configs} 个" if selected_configs != "0" else ""),
                                        variant="h6",
                                    )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Button(
                                        onClick=lambda: self.show_config_editor(),
                                        variant="outlined",
                                        color="primary",
                                        sx={"width": "100%", "height": "100%"},
                                        disabled=not self._controller_config_selected
                                        or len(self._controller_config_selected) != 1,
                                    ):
                                        mui.icon.Edit()
                                        mui.Typography(t("Edit"))
                                with mui.Grid(item=True, xs=1):
                                    with mui.Button(
                                        onClick=self.delete_selected_configs,
                                        variant="outlined",
                                        color="error",
                                        sx={"width": "100%", "height": "100%"},
                                    ):
                                        mui.icon.Delete()
                                        mui.Typography(t("Delete"))
                                with mui.Grid(item=True, xs=1):
                                    with mui.Button(
                                        onClick=self.launch_new_bot,
                                        variant="outlined",
                                        color="success",
                                        sx={"width": "100%", "height": "100%"},
                                    ):
                                        mui.icon.AddCircleOutline()
                                        mui.Typography(t("Launch Bot"))
                        with mui.Box(sx={"flex": 1, "minHeight": 3, "width": "100%"}):
                            mui.DataGrid(
                                columns=self.DEFAULT_COLUMNS,
                                rows=data,
                                pageSize=15,
                                rowsPerPageOptions=[15],
                                checkboxSelection=True,
                                disableSelectionOnClick=True,
                                disableColumnResize=False,
                                onSelectionModelChange=self._handle_row_selection,
                                autoHeight=True,
                            )

    def show_config_editor(self):
        """显示配置编辑器"""
        if self._controller_config_selected and len(self._controller_config_selected) == 1:
            config_id = self._controller_config_selected[0].replace(".yml", "")
            st.session_state.show_config_editor = True
            st.session_state.editing_config_id = config_id
            st.session_state.need_refresh = True
