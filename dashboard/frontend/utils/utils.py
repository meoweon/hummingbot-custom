import random
import string
import uuid


def generate_random_name(existing_names_list=None):
    """生成一个随机的有意义的名称

    Args:
        existing_names_list: 已存在名称的列表，避免重复

    Returns:
        生成的随机名称
    """
    # 处理默认参数
    if existing_names_list is None:
        existing_names_list = []

    # 将列表转换为集合以提高查询效率
    existing_names = set(existing_names_list)

    money_related = ["dollar", "coin", "credit", "wealth", "fortune", "cash", "gold", "profit", "rich", "value"]
    trading_related = ["market", "trade", "exchange", "broker", "stock", "bond", "option", "margin", "future", "index"]
    algorithm_related = ["algo", "bot", "code", "script", "logic", "matrix", "compute", "sequence", "data", "binary"]
    science_related = ["quantum", "neuron", "atom", "fusion", "gravity", "particle", "genome", "spectrum", "theory", "experiment"]
    space_related = ["galaxy", "nebula", "star", "planet", "orbit", "cosmos", "asteroid", "comet", "blackhole", "eclipse"]
    bird_related = ["falcon", "eagle", "hawk", "sparrow", "robin", "swallow", "owl", "raven", "dove", "phoenix"]

    categories = [money_related, trading_related, algorithm_related, science_related, space_related, bird_related]

    while True:
        # 从不同类别中选择两个
        first_category = random.choice(categories)
        second_category = random.choice([category for category in categories if category != first_category])

        # 从每个类别中选择一个词
        first_word = random.choice(first_category)
        second_word = random.choice(second_category)

        name = f"{first_word}-{second_word}"

        if name not in existing_names:
            existing_names.add(name)
            existing_names_list.append(name)  # 更新列表以跟踪已使用的名称
            return name


def generate_uuid():
    """生成一个UUID字符串

    Returns:
        UUID字符串
    """
    return str(uuid.uuid4())
