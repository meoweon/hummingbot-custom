import os
import sys
import streamlit as st

# 添加项目根目录到Python路径
# main.py在dashboard根目录下，所以当前目录就是根目录
dashboard_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(dashboard_root)

# 从constants导入需要的常量
import constants
from frontend.utils.i18n import detect_user_language
from frontend.st_utils import auth_system, initialize_st_page
from frontend.utils.i18n import t

# 设置页面配置，确保侧边栏展开
initialize_st_page(page_title="Hummingbot Dashboard", icon="🦉", layout="wide", initial_sidebar_state="expanded")

# 语言初始化 - 采用最简单的方式
if "language" not in st.session_state:
    # 通过URL参数检测语言，如果没有则使用默认语言
    detected_lang = detect_user_language()
    st.session_state.language = detected_lang


def main():
    # readme section
    st.markdown(f"{t('dashboard_description')} " f"[Hummingbot](http://hummingbot.org)")
    st.write("---")
    st.header(t("watch_tutorial"))
    st.video("https://youtu.be/7eHiMPRBQLQ?si=PAvCq0D5QDZz1h1D")
    st.header(t("feedback_and_issues"))
    st.write(t("please_give_feedback"))
    st.write(t("if_encounter_bugs"))


# 认证系统和导航
auth_system()
# 主页内容
main()
