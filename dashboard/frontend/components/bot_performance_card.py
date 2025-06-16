import pandas as pd
from streamlit_elements import mui
import streamlit as st
import json

from frontend.components.dashboard import Dashboard
from frontend.st_utils import get_backend_api_client
from frontend.utils.i18n import t  # 导入翻译函数

TRADES_TO_SHOW = 5
ULTRA_WIDE_COL_WIDTH = 300
WIDE_COL_WIDTH = 160
MEDIUM_COL_WIDTH = 140
SMALL_COL_WIDTH = 110
backend_api_client = get_backend_api_client()


def stop_bot(bot_name):
    backend_api_client.stop_bot(bot_name)


def archive_bot(bot_name):
    try:
        print(f"开始归档机器人: {bot_name}")

        # 尝试停止容器
        try:
            print(f"尝试停止容器: {bot_name}")
            stop_result = backend_api_client.stop_container(bot_name)
            print(f"停止容器结果: {stop_result}")
        except ConnectionError as ce:
            print(f"停止容器时连接错误: {str(ce)}，继续执行后续操作")
        except Exception as e:
            print(f"停止容器时出现异常: {str(e)}，继续执行后续操作")

        # 尝试移除容器
        try:
            print(f"尝试移除容器: {bot_name}")
            remove_result = backend_api_client.remove_container(bot_name)
            print(f"移除容器结果: {remove_result}")
        except ConnectionError as ce:
            print(f"移除容器时连接错误: {str(ce)}")
        except Exception as e:
            print(f"移除容器时出现异常: {str(e)}")

        print(f"机器人 {bot_name} 归档操作完成")

        # 强制刷新页面
        st.experimental_rerun()

    except Exception as e:
        print(f"归档机器人 {bot_name} 时发生未处理异常: {str(e)}")
        # 即使出错也尝试刷新页面
        st.experimental_rerun()


class BotPerformanceCardV2(Dashboard.Item):
    DEFAULT_COLUMNS = [
        {"field": "id", "headerName": t("ID"), "width": WIDE_COL_WIDTH},
        {"field": "controller", "headerName": t("Controller"), "width": SMALL_COL_WIDTH, "editable": False},
        {"field": "connector", "headerName": t("Connector"), "width": SMALL_COL_WIDTH, "editable": False},
        {"field": "trading_pair", "headerName": t("Trading Pair"), "width": SMALL_COL_WIDTH, "editable": False},
        {"field": "realized_pnl_quote", "headerName": t("Realized PNL ($)"), "width": MEDIUM_COL_WIDTH, "editable": False},
        {"field": "unrealized_pnl_quote", "headerName": t("Unrealized PNL ($)"), "width": MEDIUM_COL_WIDTH, "editable": False},
        {"field": "global_pnl_quote", "headerName": t("NET PNL ($)"), "width": MEDIUM_COL_WIDTH, "editable": False},
        {"field": "volume_traded", "headerName": t("Volume ($)"), "width": SMALL_COL_WIDTH, "editable": False},
        {"field": "open_order_volume", "headerName": t("Liquidity Placed ($)"), "width": MEDIUM_COL_WIDTH, "editable": False},
        {"field": "imbalance", "headerName": t("Imbalance ($)"), "width": SMALL_COL_WIDTH, "editable": False},
        {"field": "close_types", "headerName": t("Close Types"), "width": ULTRA_WIDE_COL_WIDTH, "editable": False},
    ]
    _active_controller_config_selected = []
    _stopped_controller_config_selected = []
    _error_controller_config_selected = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backend_api_client = get_backend_api_client()

    def _handle_stopped_row_selection(self, params, _):
        self._stopped_controller_config_selected = params

    def _handle_active_row_selection(self, params, _):
        self._active_controller_config_selected = params

    def _handle_errors_row_selection(self, params, _):
        self._error_controller_config_selected = params

    def stop_active_controllers(self, bot_name):
        for controller in self._active_controller_config_selected:
            self._backend_api_client.stop_controller_from_bot(bot_name, controller)

    def stop_errors_controllers(self, bot_name):
        for controller in self._error_controller_config_selected:
            self._backend_api_client.stop_controller_from_bot(bot_name, controller)

    def start_controllers(self, bot_name):
        for controller in self._stopped_controller_config_selected:
            self._backend_api_client.start_controller_from_bot(bot_name, controller)

    def edit_controller_config(self, bot_name, controller_id):
        """
        打开控制器配置编辑对话框
        """
        # 获取当前控制器的配置
        controller_configs = self._backend_api_client.get_all_configs_from_bot(bot_name)

        if not controller_configs:
            st.error(t("Failed to get controller configuration"))
            return

        # 找到对应的控制器配置
        controller_config = None
        for config in controller_configs:
            if config.get("id") == controller_id:
                controller_config = config
                break

        if not controller_config:
            st.error(t(f"Could not find configuration for controller {controller_id}"))
            return

        # 设置编辑状态，供弹窗使用
        st.session_state.editing_controller = {"bot_name": bot_name, "controller_id": controller_id, "config": controller_config}

        # 重置配置编辑字符串，确保每次编辑都使用最新的配置
        st.session_state.edited_config_str = ""

        # 显示弹窗编辑器
        st.session_state.show_editor = True

    def save_controller_config(self, bot_name, controller_id, updated_config):
        """
        保存控制器配置

        Args:
            bot_name: 机器人名称
            controller_id: 控制器ID
            updated_config: 更新后的配置

        Returns:
            API响应对象
        """
        try:
            # 调用API更新配置
            response = self._backend_api_client.update_controller_config(bot_name, controller_id, updated_config)
            return response
        except Exception as e:
            # 返回错误对象而不是直接显示错误
            import traceback

            return {"status": "error", "detail": f"Error saving configuration: {str(e)}", "traceback": traceback.format_exc()}

    def __call__(self, bot_name: str):
        try:
            controller_configs = backend_api_client.get_all_configs_from_bot(bot_name)
            controller_configs = controller_configs if controller_configs else []
            bot_status = backend_api_client.get_bot_status(bot_name)
            # Controllers Table
            active_controllers_list = []
            stopped_controllers_list = []
            error_controllers_list = []
            total_global_pnl_quote = 0
            total_volume_traded = 0
            total_open_order_volume = 0
            total_imbalance = 0
            total_unrealized_pnl_quote = 0
            bot_data = bot_status.get("data")
            error_logs = bot_data.get("error_logs", [])
            general_logs = bot_data.get("general_logs", [])
            if bot_status.get("status") == "error":
                with mui.Card(
                    key=self._key,
                    sx={"display": "flex", "flexDirection": "column", "borderRadius": 2, "overflow": "auto"},
                    elevation=2,
                ):
                    mui.CardHeader(
                        title=bot_name,
                        subheader=t("Not Available"),
                        avatar=mui.Avatar("🤖", sx={"bgcolor": "red"}),
                        className=self._draggable_class,
                    )
                    mui.Alert(
                        t("An error occurred while fetching bot status of the bot")
                        + f" {bot_name}. "
                        + t("Please check the bot client."),
                        severity="error",
                    )
            else:
                is_running = bot_data.get("status") == "running"
                performance = bot_data.get("performance")
                if is_running:
                    for controller, inner_dict in performance.items():
                        controller_status = inner_dict.get("status")
                        if controller_status == "error":
                            error_controllers_list.append({"id": controller, "error": inner_dict.get("error")})
                            continue
                        controller_performance = inner_dict.get("performance", {})

                        # 添加数据类型检查和转换函数
                        def safe_numeric(value, default=0):
                            """确保值是数值类型"""
                            if isinstance(value, (int, float)):
                                return float(value)
                            try:
                                return float(value) if value is not None else default
                            except (ValueError, TypeError):
                                return default

                        # 安全地获取和转换性能指标
                        realized_pnl_quote = safe_numeric(controller_performance.get("realized_pnl_quote"))
                        unrealized_pnl_quote = safe_numeric(controller_performance.get("unrealized_pnl_quote"))
                        global_pnl_quote = safe_numeric(controller_performance.get("global_pnl_quote"))
                        volume_traded = safe_numeric(controller_performance.get("volume_traded"))
                        open_order_volume = safe_numeric(controller_performance.get("open_order_volume"))
                        imbalance = safe_numeric(controller_performance.get("inventory_imbalance"))

                        # 添加错误检查
                        metrics_error = None
                        for metric_name, metric_value in controller_performance.items():
                            if metric_name not in ["close_type_counts", "positions_summary"]:
                                # 如果是字符串类型，检查是否可以转换为数字
                                if isinstance(metric_value, str):
                                    try:
                                        float(metric_value)  # 尝试转换，不保存结果
                                    except (ValueError, TypeError):
                                        metrics_error = f"Invalid metric value for {metric_name}: '{metric_value}' - not a valid number string"
                                        break
                                # 非字符串类型，检查是否为数值或None
                                elif not isinstance(metric_value, (int, float, type(None))):
                                    metrics_error = f"Invalid metric type for {metric_name}: {type(metric_value)}"
                                    break

                        if metrics_error:
                            error_controllers_list.append({"id": controller, "error": f"Metrics type error: {metrics_error}"})
                            continue

                        # 获取当前控制器的配置
                        controller_config = {}
                        for config in controller_configs:
                            if config.get("id") == controller:
                                controller_config = config
                                break

                        # 检查控制器是否启用了kill_switch
                        kill_switch_status = True if controller_config.get("manual_kill_switch") is True else False

                        close_types = controller_performance.get("close_type_counts", {})
                        tp = safe_numeric(close_types.get("CloseType.TAKE_PROFIT"))
                        sl = safe_numeric(close_types.get("CloseType.STOP_LOSS"))
                        time_limit = safe_numeric(close_types.get("CloseType.TIME_LIMIT"))
                        ts = safe_numeric(close_types.get("CloseType.TRAILING_STOP"))
                        refreshed = safe_numeric(close_types.get("CloseType.EARLY_STOP"))
                        failed = safe_numeric(close_types.get("CloseType.FAILED"))
                        close_types_str = f"TP: {tp} | SL: {sl} | TS: {ts} | TL: {time_limit} | ES: {refreshed} | F: {failed}"
                        controller_info = {
                            "id": controller,
                            "controller": controller_config.get("controller_name", controller),
                            "connector": controller_config.get("connector_name", "NaN"),
                            "trading_pair": controller_config.get("trading_pair", "NaN"),
                            "realized_pnl_quote": round(realized_pnl_quote, 2),
                            "unrealized_pnl_quote": round(unrealized_pnl_quote, 2),
                            "global_pnl_quote": round(global_pnl_quote, 2),
                            "volume_traded": round(volume_traded, 2),
                            "open_order_volume": round(open_order_volume, 2),
                            "imbalance": round(imbalance, 2),
                            "close_types": close_types_str,
                        }
                        if kill_switch_status:
                            stopped_controllers_list.append(controller_info)
                        else:
                            active_controllers_list.append(controller_info)
                        total_global_pnl_quote += global_pnl_quote
                        total_volume_traded += volume_traded
                        total_open_order_volume += open_order_volume
                        total_imbalance += imbalance
                        total_unrealized_pnl_quote += unrealized_pnl_quote
                total_global_pnl_pct = total_global_pnl_quote / total_volume_traded if total_volume_traded > 0 else 0

                if is_running:
                    status = t("Running")
                    color = "green"
                else:
                    status = t("Stopped")
                    color = "red"

                with mui.Card(
                    key=self._key,
                    sx={"display": "flex", "flexDirection": "column", "borderRadius": 2, "overflow": "auto"},
                    elevation=2,
                ):
                    mui.CardHeader(
                        title=bot_name,
                        subheader=status,
                        avatar=mui.Avatar("🤖", sx={"bgcolor": color}),
                        action=(
                            mui.IconButton(mui.icon.Stop, onClick=lambda: stop_bot(bot_name))
                            if is_running
                            else mui.IconButton(
                                mui.icon.Archive,
                                onClick=lambda: archive_bot(bot_name),
                                sx={"color": "#ff9800"},
                                title=t("Archive this bot"),
                            )
                        ),
                        className=self._draggable_class,
                    )
                    if is_running:
                        with mui.CardContent(sx={"flex": 1}):
                            with mui.Grid(container=True, spacing=2, sx={"padding": "10px 15px 10px 15px"}):
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("🏦 NET PNL"), variant="h6")
                                        mui.Typography(
                                            f"$ {total_global_pnl_quote:.3f}", variant="h6", sx={"padding": "10px 15px 10px 15px"}
                                        )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("📊 NET PNL (%)"), variant="h6")
                                        mui.Typography(
                                            f"{total_global_pnl_pct:.3%}", variant="h6", sx={"padding": "10px 15px 10px 15px"}
                                        )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("💸 Volume Traded"), variant="h6")
                                        mui.Typography(
                                            f"$ {total_volume_traded:.2f}", variant="h6", sx={"padding": "10px 15px 10px 15px"}
                                        )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("📖 Liquidity Placed"), variant="h6")
                                        mui.Typography(
                                            f"$ {total_open_order_volume:.2f}",
                                            variant="h6",
                                            sx={"padding": "10px 15px 10px 15px"},
                                        )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("💹 Unrealized PNL"), variant="h6")
                                        mui.Typography(
                                            f"$ {total_unrealized_pnl_quote:.2f}",
                                            variant="h6",
                                            sx={"padding": "10px 15px 10px 15px"},
                                        )
                                with mui.Grid(item=True, xs=2):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("⚖️ Imbalance"), variant="h6")
                                        mui.Typography(
                                            f"$ {total_imbalance:.2f}", variant="h6", sx={"padding": "10px 15px 10px 15px"}
                                        )

                            with mui.Grid(container=True, spacing=1, sx={"padding": "10px 15px 10px 15px"}):
                                with mui.Grid(item=True, xs=11):
                                    with mui.Paper(
                                        key=self._key,
                                        sx={
                                            "display": "flex",
                                            "flexDirection": "column",
                                            "borderRadius": 3,
                                            "overflow": "hidden",
                                        },
                                        elevation=1,
                                    ):
                                        with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                            mui.Typography(t("🚀 Active Controllers"), variant="h6")
                                        mui.DataGrid(
                                            rows=active_controllers_list,
                                            columns=self.DEFAULT_COLUMNS,
                                            autoHeight=True,
                                            density="compact",
                                            checkboxSelection=True,
                                            disableSelectionOnClick=True,
                                            onSelectionModelChange=self._handle_active_row_selection,
                                            hideFooter=True,
                                        )
                                with mui.Grid(container=True, item=True, xs=1, spacing=1):
                                    with mui.Grid(item=True, xs=12):
                                        with mui.Button(
                                            onClick=lambda x: self.stop_active_controllers(bot_name),
                                            variant="outlined",
                                            color="warning",
                                            sx={"width": "100%", "height": "100%", "marginBottom": "8px"},
                                        ):
                                            mui.icon.Stop()
                                            mui.Typography(t("Stop"))
                                    with mui.Grid(item=True, xs=12):
                                        with mui.Button(
                                            onClick=lambda x: (
                                                self.edit_controller_config(bot_name, self._active_controller_config_selected[0])
                                                if self._active_controller_config_selected
                                                and len(self._active_controller_config_selected) == 1
                                                else None
                                            ),
                                            variant="outlined",
                                            color="info",
                                            disabled=not self._active_controller_config_selected
                                            or len(self._active_controller_config_selected) != 1,
                                            sx={"width": "100%", "height": "100%"},
                                        ):
                                            mui.icon.Edit()
                                            mui.Typography(t("编辑"))
                            if len(stopped_controllers_list) > 0:
                                with mui.Grid(container=True, spacing=1, sx={"padding": "10px 15px 10px 15px"}):
                                    with mui.Grid(item=True, xs=11):
                                        with mui.Paper(
                                            key=self._key,
                                            sx={
                                                "display": "flex",
                                                "flexDirection": "column",
                                                "borderRadius": 3,
                                                "overflow": "hidden",
                                            },
                                            elevation=1,
                                        ):
                                            with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                                mui.Typography(t("💤 Stopped Controllers"), variant="h6")
                                            mui.DataGrid(
                                                rows=stopped_controllers_list,
                                                columns=self.DEFAULT_COLUMNS,
                                                autoHeight=True,
                                                density="compact",
                                                checkboxSelection=True,
                                                disableSelectionOnClick=True,
                                                onSelectionModelChange=self._handle_stopped_row_selection,
                                                hideFooter=True,
                                            )
                                    with mui.Grid(container=True, item=True, xs=1, spacing=1):
                                        with mui.Grid(item=True, xs=12):
                                            with mui.Button(
                                                onClick=lambda x: self.start_controllers(bot_name),
                                                variant="outlined",
                                                color="success",
                                                sx={"width": "100%", "height": "100%", "marginBottom": "8px"},
                                            ):
                                                mui.icon.PlayArrow()
                                                mui.Typography(t("Start"))
                                        with mui.Grid(item=True, xs=12):
                                            with mui.Button(
                                                onClick=lambda x: (
                                                    self.edit_controller_config(
                                                        bot_name, self._stopped_controller_config_selected[0]
                                                    )
                                                    if self._stopped_controller_config_selected
                                                    and len(self._stopped_controller_config_selected) == 1
                                                    else None
                                                ),
                                                variant="outlined",
                                                color="info",
                                                disabled=not self._stopped_controller_config_selected
                                                or len(self._stopped_controller_config_selected) != 1,
                                                sx={"width": "100%", "height": "100%"},
                                            ):
                                                mui.icon.Edit()
                                                mui.Typography(t("编辑"))
                            if len(error_controllers_list) > 0:
                                with mui.Grid(container=True, spacing=1, sx={"padding": "10px 15px 10px 15px"}):
                                    with mui.Grid(item=True, xs=11):
                                        with mui.Paper(
                                            key=self._key,
                                            sx={
                                                "display": "flex",
                                                "flexDirection": "column",
                                                "borderRadius": 3,
                                                "overflow": "hidden",
                                            },
                                            elevation=1,
                                        ):
                                            with self.title_bar(padding="10px 15px 10px 15px", dark_switcher=False):
                                                mui.Typography(t("💀 Controllers with errors"), variant="h6")
                                            mui.DataGrid(
                                                rows=error_controllers_list,
                                                columns=self.DEFAULT_COLUMNS,
                                                autoHeight=True,
                                                density="compact",
                                                checkboxSelection=True,
                                                disableSelectionOnClick=True,
                                                onSelectionModelChange=self._handle_errors_row_selection,
                                                hideFooter=True,
                                            )
                                    with mui.Grid(item=True, xs=1):
                                        with mui.Button(
                                            onClick=lambda x: self.stop_errors_controllers(bot_name),
                                            variant="outlined",
                                            color="warning",
                                            sx={"width": "100%", "height": "100%", "marginBottom": "8px"},
                                        ):
                                            mui.icon.Stop()
                                            mui.Typography(t("Stop"))
                                        with mui.Grid(item=True, xs=12):
                                            with mui.Button(
                                                onClick=lambda x: (
                                                    self.edit_controller_config(
                                                        bot_name, self._error_controller_config_selected[0]
                                                    )
                                                    if self._error_controller_config_selected
                                                    and len(self._error_controller_config_selected) == 1
                                                    else None
                                                ),
                                                variant="outlined",
                                                color="info",
                                                disabled=not self._error_controller_config_selected
                                                or len(self._error_controller_config_selected) != 1,
                                                sx={"width": "100%", "height": "100%"},
                                            ):
                                                mui.icon.Edit()
                                                mui.Typography(t("编辑"))
                            with mui.Accordion(sx={"padding": "10px 15px 10px 15px"}):
                                with mui.AccordionSummary(expandIcon=mui.icon.ExpandMoreIcon()):
                                    mui.Typography(t("Error Logs"))
                                with mui.AccordionDetails(sx={"display": "flex", "flexDirection": "column"}):
                                    if len(error_logs) > 0:
                                        for log in error_logs[:50]:
                                            # Convert timestamp to datetime with timezone
                                            timestamp = (
                                                pd.to_datetime(int(log.get("timestamp")), unit="s")
                                                .tz_localize("UTC")
                                                .tz_convert("Asia/Shanghai")
                                            )
                                            message = log.get("msg")
                                            logger_name = log.get("logger_name")
                                            mui.Typography(f"{timestamp} - {logger_name}: {message}")
                                    else:
                                        mui.Typography(t("No error logs available."))
                            with mui.Accordion(sx={"padding": "10px 15px 10px 15px"}):
                                with mui.AccordionSummary(expandIcon=mui.icon.ExpandMoreIcon()):
                                    mui.Typography(t("General Logs"))
                                with mui.AccordionDetails(sx={"display": "flex", "flexDirection": "column"}):
                                    if len(general_logs) > 0:
                                        for log in general_logs[:50]:
                                            # Convert timestamp to datetime with timezone
                                            timestamp = (
                                                pd.to_datetime(int(log.get("timestamp")), unit="s")
                                                .tz_localize("UTC")
                                                .tz_convert("Asia/Shanghai")
                                            )
                                            message = log.get("msg")
                                            logger_name = log.get("logger_name")
                                            mui.Typography(f"{timestamp} - {logger_name}: {message}")
                                    else:
                                        mui.Typography(t("No general logs available."))
        except Exception as e:
            print(e)
            with mui.Card(
                key=self._key,
                sx={"display": "flex", "flexDirection": "column", "borderRadius": 2, "overflow": "auto"},
                elevation=2,
            ):
                mui.CardHeader(
                    title=bot_name,
                    subheader=t("Error"),
                    avatar=mui.Avatar("🤖", sx={"bgcolor": "red"}),
                    action=mui.IconButton(mui.icon.Stop, onClick=lambda: stop_bot(bot_name)),
                    className=self._draggable_class,
                )
                with mui.CardContent(sx={"flex": 1}):
                    mui.Typography(t("An error occurred while fetching bot status."), sx={"padding": "10px 15px 10px 15px"})
                    mui.Typography(str(e), sx={"padding": "10px 15px 10px 15px"})
