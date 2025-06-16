import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 控制器配置文件路径
CONTROLLERS_PATH = "bots/conf/controllers"

# 控制器模块的导入路径(Python模块路径)
CONTROLLERS_MODULE = "bots.controllers"

# 配置密码，从环境变量获取，默认值为"a"
CONFIG_PASSWORD = os.getenv("CONFIG_PASSWORD", "a")

# MQTT代理服务器主机地址，从环境变量获取，默认localhost
BROKER_HOST = os.getenv("BROKER_HOST", "emqx")

# MQTT代理服务器端口，从环境变量获取并转为整数，默认1883
BROKER_PORT = int(os.getenv("BROKER_PORT", 1883))

# MQTT代理用户名，从环境变量获取，默认admin
BROKER_USERNAME = os.getenv("BROKER_USERNAME", "admin")

# MQTT代理密码，从环境变量获取，默认password
BROKER_PASSWORD = os.getenv("BROKER_PASSWORD", "public")

# 密码验证文件路径
PASSWORD_VERIFICATION_PATH = "bots/credentials/master_account/.password_verification"

# 禁止交易的代币列表，从环境变量获取，默认"NAV,ARS,ETHW,ETHF"，并以逗号分隔为列表
BANNED_TOKENS = os.getenv("BANNED_TOKENS", "NAV,ARS,ETHW,ETHF").split(",")
