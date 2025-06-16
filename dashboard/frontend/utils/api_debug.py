import json
import time
from datetime import datetime
import os

import streamlit as st

from CONFIG import BACKEND_API_HOST, BACKEND_API_PORT, BACKEND_API_USERNAME, BACKEND_API_PASSWORD
from frontend.utils.i18n import t


# 在本地实现get_backend_api_client函数
def get_backend_api_client():
    """获取后端API客户端实例"""
    from backend.services.backend_api_client import BackendAPIClient

    try:
        backend_api_client = BackendAPIClient.get_instance(
            host=BACKEND_API_HOST, port=BACKEND_API_PORT, username=BACKEND_API_USERNAME, password=BACKEND_API_PASSWORD
        )
        if not backend_api_client.is_docker_running():
            st.error(t("docker_not_running"))
            st.stop()
        return backend_api_client
    except Exception:
        st.stop()


# API调试相关函数 - 全局API调试系统
def initialize_api_debug():
    """初始化API调试所需的会话状态"""
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = False

    if "api_debug_history" not in st.session_state:
        st.session_state.api_debug_history = []

    if "last_api_request" not in st.session_state:
        st.session_state.last_api_request = None

    if "last_api_response" not in st.session_state:
        st.session_state.last_api_response = None

    if "api_tester_endpoint" not in st.session_state:
        st.session_state.api_tester_endpoint = ""

    if "api_tester_method" not in st.session_state:
        st.session_state.api_tester_method = "GET"

    if "api_tester_params" not in st.session_state:
        st.session_state.api_tester_params = "{}"

    # 添加文件记录开关，默认为关闭状态
    if "enable_debug_file_logging" not in st.session_state:
        st.session_state.enable_debug_file_logging = False

    # 确保api_debug_info已初始化，这是核心存储调试信息的会话状态变量
    if "api_debug_info" not in st.session_state:
        st.session_state.api_debug_info = {"last_request": None, "last_response": None, "history": []}


def update_api_debug_info(endpoint, method, params, response):
    """更新API调试信息，用于记录最近的请求和响应"""

    # 确保session_state中有api_debug_info
    if "api_debug_info" not in st.session_state:
        st.session_state.api_debug_info = {"last_request": None, "last_response": None, "history": []}

    # 补充API主机和端口信息，构建完整URL
    url = f"http://{BACKEND_API_HOST}:{BACKEND_API_PORT}/{endpoint}"

    # 记录请求信息，去掉无意义的硬编码headers
    request_info = {
        "endpoint": endpoint,
        "method": method,
        "params": params or {},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": url,
    }

    # 处理响应信息，确保处理None和非字典响应
    response_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": {"status": "error", "detail": "无响应", "code": 0},
    }

    if response is not None:
        if isinstance(response, dict):
            response_info["data"] = response
        else:
            # 处理非字典响应
            try:
                # 如果是JSON字符串，尝试解析
                if isinstance(response, str):
                    response_data = json.loads(response)
                    response_info["data"] = response_data
                else:
                    # 其他情况，转为字符串
                    response_info["data"] = {"status": "unknown", "detail": str(response), "code": 0}
            except:
                response_info["data"] = {"status": "unknown", "detail": str(response), "code": 0}

    # 更新最近的请求和响应
    st.session_state.api_debug_info["last_request"] = request_info
    st.session_state.api_debug_info["last_response"] = response_info

    # 添加到历史记录中
    st.session_state.api_debug_info["history"].append((request_info, response_info))

    # 限制历史记录的长度
    max_history = 20
    if len(st.session_state.api_debug_info["history"]) > max_history:
        st.session_state.api_debug_info["history"] = st.session_state.api_debug_info["history"][-max_history:]

    # 检查是否启用文件记录
    if st.session_state.get("enable_debug_file_logging", False):
        # 同时写入文件以确保跨页面持久化
        try:
            # 确保目录存在
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
            os.makedirs(log_dir, exist_ok=True)

            # 将调试信息写入文件
            debug_file = os.path.join(log_dir, "api_debug_info.json")

            # 读取现有数据（如果有）
            existing_data = {"last_request": None, "last_response": None, "history": []}
            try:
                if os.path.exists(debug_file):
                    with open(debug_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
            except Exception:
                pass  # 如果读取失败，使用默认空数据

            # 更新数据
            existing_data["last_request"] = request_info
            existing_data["last_response"] = response_info

            # 更新历史记录
            if "history" not in existing_data:
                existing_data["history"] = []
            existing_data["history"].append((request_info, response_info))

            # 限制历史记录长度
            if len(existing_data["history"]) > max_history:
                existing_data["history"] = existing_data["history"][-max_history:]

            # 写入文件
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 写入文件失败不影响主流程


def render_api_debug_toggle():
    """渲染API调试模式开关

    注意：此函数仍然需要保留以保持向后兼容性，但不再在侧边栏渲染开关
    API调试模式切换将在设置页面中管理
    """
    # 确保已初始化
    initialize_api_debug()
    # 不再在侧边栏显示开关


def display_debug_panel():
    """显示API调试面板"""
    # 确保api_debug_info已初始化
    if "api_debug_info" not in st.session_state:
        st.session_state.api_debug_info = {"last_request": None, "last_response": None, "history": []}

    # 只有在启用文件记录时才尝试从文件加载调试信息
    if st.session_state.get("enable_debug_file_logging", False):
        try:
            import os
            import json

            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
            debug_file = os.path.join(log_dir, "api_debug_info.json")

            if os.path.exists(debug_file):
                with open(debug_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)

                    # 更新会话状态中的调试信息
                    st.session_state.api_debug_info["last_request"] = file_data.get("last_request")
                    st.session_state.api_debug_info["last_response"] = file_data.get("last_response")

                    # 处理历史记录 - 需要确保格式一致性
                    if "history" in file_data and isinstance(file_data["history"], list):
                        st.session_state.api_debug_info["history"] = file_data["history"]
        except Exception:
            # 文件加载失败时继续使用会话状态中的数据
            pass

    if not st.session_state.get("show_debug", False):
        return

    # 使用markdown替代expander
    st.markdown("## 🔍 API调试信息")

    # 添加文件记录开关
    enable_file_logging = st.toggle(
        "启用文件记录 (跨页面持久化)",
        value=st.session_state.get("enable_debug_file_logging", False),
        help="将API调试信息保存到文件系统，以便在不同页面间共享。文件保存在 dashboard/logs/api_debug_info.json",
    )

    # 更新会话状态
    st.session_state.enable_debug_file_logging = enable_file_logging

    # 如果状态改变且开启了文件记录，显示提示信息
    if enable_file_logging and not st.session_state.get("showed_file_logging_info", False):
        st.info("API调试信息将保存到 dashboard/logs/api_debug_info.json 文件中")
        st.session_state.showed_file_logging_info = True
    elif not enable_file_logging:
        st.session_state.showed_file_logging_info = False

    tab1, tab2, tab3 = st.tabs(["当前请求", "历史记录", "API测试器"])

    with tab1:
        # 显示最近的API请求和响应
        if st.session_state.api_debug_info["last_request"] and st.session_state.api_debug_info["last_response"]:
            _render_api_request_response(
                st.session_state.api_debug_info["last_request"], st.session_state.api_debug_info["last_response"]
            )
        else:
            st.info("暂无API调试信息")

    with tab2:
        # 显示API请求历史记录
        if st.session_state.api_debug_info["history"]:
            # 使用选择框来选择历史记录，而不是嵌套expander
            history = st.session_state.api_debug_info["history"]
            history_options = [
                f"请求 {len(history)-i}: {req['method']} {req['endpoint']} - {req['timestamp']}"
                for i, (req, _) in enumerate(reversed(history))
            ]

            selected_history = st.selectbox("选择历史记录", history_options)
            if selected_history:
                # 找到选择的历史记录索引
                selected_index = history_options.index(selected_history)
                # 反向索引，因为我们显示的是reversed列表
                actual_index = len(history) - selected_index - 1

                # 渲染选中的请求和响应
                request, response = history[actual_index]
                _render_api_request_response_with_index(request, response, selected_index)
        else:
            st.info("暂无API请求历史记录")

    with tab3:
        _render_api_tester()


def _render_api_tester():
    """渲染API测试器界面"""
    # API测试器界面
    st.markdown("### API测试器")

    col1, col2 = st.columns([1, 3])
    with col1:
        method = st.selectbox("请求方法", ["GET", "POST"], index=0 if st.session_state.api_tester_method == "GET" else 1)
    with col2:
        endpoint = st.text_input("API端点", value=st.session_state.api_tester_endpoint)

    # 参数输入
    params_text = st.text_area("参数 (JSON格式)", value=st.session_state.api_tester_params, height=150)

    # 发送请求按钮
    if st.button("发送请求"):
        if not endpoint:
            st.error("请输入API端点")
        else:
            try:
                # 解析参数
                params = json.loads(params_text) if params_text.strip() else {}

                # 获取API客户端
                api_client = get_backend_api_client()

                # 发送请求
                if method == "GET":
                    response = api_client.get(endpoint, params=params)
                else:
                    response = api_client.post(endpoint, payload=params)

                # 更新调试信息
                update_api_debug_info(endpoint, method, params, response)

                # 显示响应
                st.success("请求已发送，请查看当前请求选项卡")

            except json.JSONDecodeError:
                st.error("参数格式错误，请确保使用有效的JSON格式")
            except Exception as e:
                st.error(f"发送请求时出错: {str(e)}")

    # 显示API端点列表
    _render_endpoint_list()


def _render_endpoint_list():
    """渲染API端点列表"""
    endpoints_container = st.container()
    with endpoints_container:
        show_endpoints = st.checkbox("显示API端点列表", value=False)
        if show_endpoints:
            # 使用完整的API端点列表，基于OpenAPI文档
            from frontend.utils.api_endpoints import ENDPOINTS

            # 按分类组织端点
            st.markdown("### 按分类查看API端点")
            categories = {
                "Docker管理": [
                    e
                    for e in ENDPOINTS
                    if "container" in e["端点"]
                    or "docker" in e["端点"]
                    or "image" in e["端点"]
                    or "hummingbot-instance" in e["端点"]
                ],
                "机器人管理": [e for e in ENDPOINTS if "bot" in e["端点"] or "strategy" in e["端点"]],
                "文件管理": [e for e in ENDPOINTS if "script" in e["端点"] or "controller" in e["端点"] or "config" in e["端点"]],
                "市场数据": [e for e in ENDPOINTS if "candles" in e["端点"]],
                "回测": [e for e in ENDPOINTS if "backtesting" in e["端点"]],
                "数据库管理": [e for e in ENDPOINTS if "database" in e["端点"] or "checkpoint" in e["端点"]],
                "性能": [e for e in ENDPOINTS if "performance" in e["端点"]],
                "凭证管理": [
                    e for e in ENDPOINTS if "account" in e["端点"] or "connector" in e["端点"] or "credential" in e["端点"]
                ],
            }

            # 选择分类
            category = st.selectbox("选择API分类", list(categories.keys()))

            # 添加排序功能
            sort_option = st.selectbox("排序依据", ["方法", "端点"], index=0)
            endpoints_in_category = sorted(categories[category], key=lambda x: x[sort_option])

            # 选择端点
            endpoint_descriptions = [f"{e['方法']} {e['端点']} - {e['描述']}" for e in endpoints_in_category]
            selected_endpoint = st.selectbox("选择端点", endpoint_descriptions)

            if selected_endpoint:
                # 找到选中的端点
                idx = endpoint_descriptions.index(selected_endpoint)
                endpoint_info = endpoints_in_category[idx]

                st.markdown(f"**端点**: {endpoint_info['端点']}")
                st.markdown(f"**方法**: {endpoint_info['方法']}")
                st.markdown(f"**描述**: {endpoint_info['描述']}")
                st.markdown(f"**参数**: {endpoint_info['参数']}")

                # 添加快速测试按钮
                if st.button("使用此端点"):
                    endpoint_path = endpoint_info["端点"]

                    # 如果有路径参数，进行简单替换
                    if "{" in endpoint_path:
                        # 设置为一个示例值
                        endpoint_path = endpoint_path.replace("{container_name}", "example-container")
                        endpoint_path = endpoint_path.replace("{instance_name}", "example-instance")
                        endpoint_path = endpoint_path.replace("{bot_name}", "example-bot")
                        endpoint_path = endpoint_path.replace("{script_name}", "example-script")
                        endpoint_path = endpoint_path.replace("{controller_name}", "example-controller")
                        endpoint_path = endpoint_path.replace("{controller_id}", "example-controller-id")
                        endpoint_path = endpoint_path.replace("{account_name}", "example-account")
                        endpoint_path = endpoint_path.replace("{connector_name}", "binance")
                        endpoint_path = endpoint_path.replace("{image_name}", "hummingbot")

                    # 设置测试器状态
                    st.session_state.api_tester_endpoint = endpoint_path
                    st.session_state.api_tester_method = endpoint_info["方法"]
                    if endpoint_info["参数"] != "无" and not endpoint_info["参数"].startswith("路径"):
                        st.session_state.api_tester_params = endpoint_info["参数"]
                    else:
                        st.session_state.api_tester_params = "{}"

                    # 切换到测试器选项卡
                    st.rerun()


def _render_api_request_response(request, response):
    """渲染单个API请求和响应"""
    if not request or not response:
        st.info("暂无API调试信息")
        return

    col1, col2 = st.columns(2)

    # 请求信息
    with col1:
        st.markdown("### 请求信息")
        st.markdown(f"**URL**: [{request['method']} {request['url']}]({request['url']})")
        st.markdown(f"**端点**: `{request['endpoint']}`")
        st.markdown(f"**方法**: `{request['method']}`")
        st.markdown(f"**时间**: `{request['timestamp']}`")

        if request["params"]:
            st.markdown("**参数**:")
            st.code(json.dumps(request["params"], indent=2, ensure_ascii=False), language="json")

    # 响应信息
    with col2:
        st.markdown("### 响应信息")
        st.markdown(f"**时间**: `{response['timestamp']}`")

        # 添加响应码显示
        if "code" in response["data"]:
            code = response["data"]["code"]
            code_color = "green" if 200 <= code < 300 else "red"
            st.markdown(f"**响应码**: <span style='color:{code_color}'>{code}</span>", unsafe_allow_html=True)

        try:
            if isinstance(response["data"], dict) and "status" in response["data"]:
                status = response["data"]["status"]
                status_color = "green" if status == "success" else "red"
                st.markdown(f"**状态**: <span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)

            st.markdown("**数据**:")
            st.code(json.dumps(response["data"], indent=2, ensure_ascii=False), language="json")

            # 只添加重试按钮，不再重复显示数据
            # 创建一个唯一的键，包含端点、方法和时间戳的组合
            unique_key = f"retry_{request['endpoint']}_{request['method']}_{request['timestamp']}_{id(request)}"
            if st.button("重试此请求", key=unique_key):
                # 设置测试器状态，准备重试
                st.session_state.api_tester_endpoint = request["endpoint"]
                st.session_state.api_tester_method = request["method"]
                if request["params"]:
                    st.session_state.api_tester_params = json.dumps(request["params"], ensure_ascii=False)
                else:
                    st.session_state.api_tester_params = "{}"
                # 切换到测试器选项卡
                st.rerun()

        except (TypeError, ValueError) as e:
            st.markdown("**数据** (无法格式化为JSON):")
            st.write(response["data"])

            # 重试按钮
            unique_key = f"retry_{request['endpoint']}_{request['method']}_{request['timestamp']}_{id(request)}"
            if st.button("重试此请求", key=unique_key):
                # 设置测试器状态，准备重试
                st.session_state.api_tester_endpoint = request["endpoint"]
                st.session_state.api_tester_method = request["method"]
                if request["params"]:
                    st.session_state.api_tester_params = json.dumps(request["params"], ensure_ascii=False)
                else:
                    st.session_state.api_tester_params = "{}"
                # 切换到测试器选项卡
                st.rerun()


def _render_api_request_response_with_index(request, response, index):
    """渲染单个API请求和响应，带索引以确保唯一键"""
    if not request or not response:
        st.info("暂无API调试信息")
        return

    col1, col2 = st.columns(2)

    # 请求信息
    with col1:
        st.markdown("### 请求信息")
        if "url" in request:
            st.markdown(f"**URL**: [{request['method']} {request['url']}]({request['url']})")
        st.markdown(f"**端点**: `{request['endpoint']}`")
        st.markdown(f"**方法**: `{request['method']}`")
        st.markdown(f"**时间**: `{request['timestamp']}`")

        if request["params"]:
            st.markdown("**参数**:")
            st.code(json.dumps(request["params"], indent=2, ensure_ascii=False), language="json")

    # 响应信息
    with col2:
        st.markdown("### 响应信息")
        st.markdown(f"**时间**: `{response['timestamp']}`")

        # 添加响应码显示
        if "code" in response["data"]:
            code = response["data"]["code"]
            code_color = "green" if 200 <= code < 300 else "red"
            st.markdown(f"**响应码**: <span style='color:{code_color}'>{code}</span>", unsafe_allow_html=True)

        try:
            if isinstance(response["data"], dict) and "status" in response["data"]:
                status = response["data"]["status"]
                status_color = "green" if status == "success" else "red"
                st.markdown(f"**状态**: <span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)

            st.markdown("**数据**:")
            st.code(json.dumps(response["data"], indent=2, ensure_ascii=False), language="json")

            # 使用索引确保唯一键
            unique_key = f"history_retry_{index}_{request['endpoint']}_{request['method']}"
            if st.button("重试此请求", key=unique_key):
                # 设置测试器状态，准备重试
                st.session_state.api_tester_endpoint = request["endpoint"]
                st.session_state.api_tester_method = request["method"]
                if request["params"]:
                    st.session_state.api_tester_params = json.dumps(request["params"], ensure_ascii=False)
                else:
                    st.session_state.api_tester_params = "{}"
                # 切换到测试器选项卡
                st.rerun()

        except (TypeError, ValueError) as e:
            st.markdown("**数据** (无法格式化为JSON):")
            st.write(response["data"])

            # 重试按钮
            unique_key = f"history_retry_{index}_{request['endpoint']}_{request['method']}"
            if st.button("重试此请求", key=unique_key):
                # 设置测试器状态，准备重试
                st.session_state.api_tester_endpoint = request["endpoint"]
                st.session_state.api_tester_method = request["method"]
                if request["params"]:
                    st.session_state.api_tester_params = json.dumps(request["params"], ensure_ascii=False)
                else:
                    st.session_state.api_tester_params = "{}"
                # 切换到测试器选项卡
                st.rerun()


def process_api_response(response, action_name, success_message):
    """处理API响应并显示相应消息

    Args:
        response: API响应
        action_name: 操作名称，用于错误消息
        success_message: 成功消息

    Returns:
        bool: 操作是否成功
    """
    if response is None:
        st.error(f"{action_name}失败：服务器未返回有效响应")
        return False

    if not isinstance(response, dict):
        st.error(f"{action_name}失败：响应格式不正确")
        return False

    # 优先使用HTTP响应码判断请求是否成功
    if "code" in response:
        if 200 <= response["code"] < 300:
            st.success(success_message)
            return True
        else:
            error_detail = ""
            # 检查不同的错误字段
            if "detail" in response:
                error_detail = response["detail"]
            elif "reason" in response:
                error_detail = response["reason"]
            elif "error" in response:
                error_detail = response["error"]
            elif "message" in response:
                error_detail = response["message"]

            error_msg = f"{action_name}失败：HTTP {response['code']}"
            if error_detail:
                error_msg += f" - {error_detail}"

            st.error(error_msg)
            return False

    # 如果没有响应码，检查status字段
    if response.get("status") == "success":
        st.success(success_message)
        return True
    elif response.get("status") == "pending":
        st.info(response.get("detail", f"{action_name}请求已提交，但当前状态未知"))
        return True
    else:
        # 检查不同的错误字段
        error_reason = None
        if "detail" in response:
            error_reason = response["detail"]
        elif "reason" in response:
            error_reason = response["reason"]
        elif "error" in response:
            error_reason = response["error"]
        elif "message" in response:
            error_reason = response["message"]

        if not error_reason:
            error_reason = "未知原因"

        st.error(f"{action_name}失败：{error_reason}")
        return False
