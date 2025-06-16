# frontend/utils package

# 导入本地模块中的函数
from .i18n import t, init_i18n, get_current_language, set_language
from .utils import generate_random_name, generate_uuid

# 注意：如果有循环导入问题，可以考虑在使用时动态导入
