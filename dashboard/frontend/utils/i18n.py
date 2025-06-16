import os
import sys
import importlib.util
import streamlit as st
import time

# 添加项目根目录到Python路径
# utils位于frontend/utils目录下，所以上上一级目录就是dashboard根目录
dashboard_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(dashboard_root)

# 直接导入根目录下的constants模块
import constants

# 从constants获取国际化相关常量
SUPPORTED_LANGUAGES_LIST = constants.SUPPORTED_LANGUAGES
# 创建语言代码到语言名称的映射
SUPPORTED_LANGUAGES = {"en": "English", "zh": "中文"}
DEFAULT_LANGUAGE = constants.DEFAULT_LANGUAGE
CURRENT_LANGUAGE = constants.CURRENT_LANGUAGE
I18N_DIR = constants.I18N_DIR

# 语言Cookie名称
LANGUAGE_COOKIE_NAME = "hummingbot_language"


# 加载翻译文件
def load_translations():
    """从translation目录加载所有翻译文件"""
    translations = {}

    for lang in SUPPORTED_LANGUAGES:
        try:
            # 尝试直接导入模块
            module_path = os.path.join(dashboard_root, "frontend", "translations", f"{lang}.py")

            if os.path.exists(module_path):
                # 使用importlib动态导入模块
                spec = importlib.util.spec_from_file_location(f"translations.{lang}", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                translations[lang] = module.translations
            else:
                st.warning(f"翻译文件 {module_path} 不存在")
                translations[lang] = {}
        except Exception as e:
            st.warning(f"加载翻译文件 {lang}.py 时出错: {str(e)}")
            translations[lang] = {}

    return translations


# 加载所有翻译
translations = load_translations()


def detect_user_language():
    """尝试检测用户的语言设置"""
    try:
        # 1. 首先检查URL参数中的语言设置 - 最高优先级
        query_params = st.query_params
        if "lang" in query_params:
            requested_lang = query_params["lang"]
            if isinstance(requested_lang, list):
                requested_lang = requested_lang[0]
            requested_lang = requested_lang.lower()
            if requested_lang in SUPPORTED_LANGUAGES_LIST:
                # 发现URL参数中的语言设置，立即返回
                return requested_lang
    except Exception as e:
        st.warning(f"获取语言参数时出错: {str(e)}")

    # 返回默认语言
    return DEFAULT_LANGUAGE


def get_current_language():
    """获取当前语言"""
    if "language" not in st.session_state:
        # 初始化语言时尝试检测用户语言
        detected_lang = detect_user_language()
        st.session_state.language = detected_lang
    return st.session_state.language


def set_language(lang):
    """设置当前语言，同时保存到Cookie和session_state"""
    if lang in SUPPORTED_LANGUAGES_LIST:
        # 1. 设置会话状态
        st.session_state.language = lang

        # 2. 保存到Cookie以便跨页面保持语言设置
        st.session_state[LANGUAGE_COOKIE_NAME] = lang

        # 3. 设置URL参数，这将在页面刷新时生效
        # URL参数的设置发生在页面重载时，不需要在这里处理
        return True
    return False


def t(key, **kwargs):
    """翻译函数，从当前语言获取翻译文本"""
    # 获取当前语言
    current_lang = get_current_language()

    # 获取当前语言的翻译
    lang_translations = translations.get(current_lang, translations.get(DEFAULT_LANGUAGE, {}))

    # 获取键值，如果不存在则返回键本身
    text = lang_translations.get(key, key)

    # 如果有格式化参数，应用它们
    if kwargs:
        text = text.format(**kwargs)

    return text


def render_language_selector():
    """渲染语言选择器，使用最简单直接的方式强制刷新整个页面"""
    current_language = get_current_language()

    # 获取当前页面路径，用于保持用户在同一页面
    current_page = st.query_params.get("streamlit_origin_path", "/")
    if current_page == "" or current_page is None:
        current_page = "/"

    # 为每种语言创建简单的链接按钮
    for lang_code in SUPPORTED_LANGUAGES_LIST:
        if lang_code != current_language:
            lang_name = SUPPORTED_LANGUAGES[lang_code]

            # 创建带时间戳的URL以防止缓存
            timestamp = int(time.time())
            # 使用纯HTML链接，确保整页刷新，保持在同一页面
            html = f"""
            <a href="{current_page}?lang={lang_code}&ts={timestamp}" target="_top" 
               style="text-decoration: none; display: block; margin: 5px 0;">
                <div style="background-color: #f0f2f6; color: #262730; padding: 8px 12px; 
                           border-radius: 4px; text-align: center; width: 100%;">
                    {lang_name}
                </div>
            </a>
            """
            st.markdown(html, unsafe_allow_html=True)


def init_i18n():
    """初始化国际化支持"""
    # 只初始化语言支持，不再显示语言选择器
    # 语言选择器已移至设置页面
    if "language" not in st.session_state:
        # 初始化语言时尝试检测用户语言
        detected_lang = detect_user_language()
        st.session_state.language = detected_lang
