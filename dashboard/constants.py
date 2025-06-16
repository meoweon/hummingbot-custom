import os

CANDLES_DATA_PATH = "data/candles"
DOWNLOAD_CANDLES_CONFIG_YML = "hummingbot_files/scripts_configs/data_downloader_config.yml"
BOTS_FOLDER = "hummingbot_files/bots"
CONTROLLERS_PATH = "quants_lab/controllers"
CONTROLLERS_CONFIG_PATH = "hummingbot_files/controller_configs"
OPTIMIZATIONS_PATH = "quants_lab/optimizations"
HUMMINGBOT_TEMPLATES = "hummingbot_files/templates"

# 定义可用语言
SUPPORTED_LANGUAGES = ["en", "zh"]

# 默认语言
DEFAULT_LANGUAGE = "zh"

# 用户当前选择的语言（初始为默认语言）
CURRENT_LANGUAGE = DEFAULT_LANGUAGE

# 获取i18n翻译的路径
I18N_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "translations")
