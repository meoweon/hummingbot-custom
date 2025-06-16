import streamlit as st
import time
from frontend.st_utils import initialize_st_page
from frontend.utils.i18n import t, get_current_language, set_language, SUPPORTED_LANGUAGES
from frontend.utils.api_debug import display_debug_panel


def app():
    # 初始化页面
    initialize_st_page(page_title=t("settings_title"), icon="⚙️")

    st.title(t("settings_title"))

    # 创建两个选项卡：一个用于应用设置，一个用于API调试
    tab1, tab2 = st.tabs([t("app_settings"), t("api_debug")])

    with tab1:
        st.header(t("language_settings"))

        # 获取当前语言
        current_lang = get_current_language()

        # 显示当前语言状态
        st.info(f"**{t('Current')}: {SUPPORTED_LANGUAGES[current_lang]}**")

        # 直接显示语言切换链接 - 最简单粗暴的方法
        st.markdown("### 点击下面的链接直接切换语言:")

        # 获取当前页面路径
        current_page = st.query_params.get("streamlit_origin_path", "/")
        if current_page == "" or current_page is None:
            current_page = "/"

        # 直接为每种语言创建一个链接按钮
        timestamp = int(time.time())

        # 创建链接的容器，使用CSS网格布局
        st.markdown(
            """
        <style>
        .language-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }
        .language-btn {
            background-color: #f0f2f6;
            color: #262730;
            padding: 10px 15px;
            border-radius: 5px;
            text-align: center;
            display: block;
            text-decoration: none;
            font-weight: bold;
            transition: background-color 0.3s;
        }
        .language-btn:hover {
            background-color: #e0e2e6;
        }
        .language-btn.active {
            background-color: #00ACEE;
            color: white;
        }
        </style>
        <div class="language-grid">
        """,
            unsafe_allow_html=True,
        )

        # 为每种语言创建链接按钮
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            active_class = "active" if lang_code == current_lang else ""
            html = f"""
            <a href="{current_page}?lang={lang_code}&ts={timestamp}" target="_top" class="language-btn {active_class}">
                {lang_name}
            </a>
            """
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # 添加解释说明
        st.caption("点击链接后整个应用将重新加载并应用新的语言设置")

    with tab2:
        # 添加API调试模式开关
        st.header("开发选项")
        # 确保session_state中有show_debug
        if "show_debug" not in st.session_state:
            st.session_state.show_debug = False

        # 添加API调试模式开关
        st.session_state.show_debug = st.toggle(
            "🔍 API调试模式", value=st.session_state.show_debug, help="显示API请求和响应的详细信息"
        )

        # 只有当调试模式开启时才显示调试面板
        if st.session_state.show_debug:
            # 显示API调试面板
            display_debug_panel()
        else:
            st.info("请开启API调试模式以查看API请求和响应信息")


if __name__ == "__main__":
    app()
