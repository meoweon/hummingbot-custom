from math import exp

from _decimal import Decimal
from streamlit_elements import mui
from hummingbot.strategy_v2.utils.distributions import Distributions
from frontend.st_utils import t


def normalize(values):
    total = sum(values)
    return [val / total for val in values]


def distribution_inputs(column, dist_type_name, levels=3, default_values=None):
    # 翻译后的分布类型名称
    translated_dist_type_name = t(dist_type_name)

    if dist_type_name == t("Spread"):
        dist_options = ["Manual", "GeoCustom", "Geometric", "Fibonacci", "Logarithmic", "Arithmetic", "Linear"]
        # 翻译选项但保留原始值
        dist_options_translated = [t(option) for option in dist_options]

        selected_option = column.selectbox(
            # 完全汉化格式字符串
            t("Type of {} Distribution").format(translated_dist_type_name),
            dist_options_translated,
            key=f"{column}_{dist_type_name.lower()}_dist_type",
        )
        # 获取原始值
        dist_type = dist_options[dist_options_translated.index(selected_option)]
    else:
        dist_options = ["Manual", "Geometric", "Fibonacci", "Logarithmic", "Arithmetic"]
        # 翻译选项但保留原始值
        dist_options_translated = [t(option) for option in dist_options]

        selected_option = column.selectbox(
            # 完全汉化格式字符串
            t("Type of {} Distribution").format(translated_dist_type_name),
            dist_options_translated,
            key=f"{column}_{dist_type_name.lower()}_dist_type",
        )
        # 获取原始值
        dist_type = dist_options[dist_options_translated.index(selected_option)]

    base, scaling_factor, step, ratio, manual_values = None, None, None, None, None

    if dist_type != "Manual":
        start = column.number_input(
            t("{} Start Value").format(translated_dist_type_name), value=1.0, key=f"{column}_{dist_type_name.lower()}_start"
        )
        if dist_type == "Logarithmic":
            base = column.number_input(
                t("{} Log Base").format(translated_dist_type_name), value=exp(1), key=f"{column}_{dist_type_name.lower()}_base"
            )
            scaling_factor = column.number_input(
                t("{} Scaling Factor").format(translated_dist_type_name),
                value=2.0,
                key=f"{column}_{dist_type_name.lower()}_scaling",
            )
        elif dist_type == "Arithmetic":
            step = column.number_input(
                t("{} Step").format(translated_dist_type_name), value=0.3, key=f"{column}_{dist_type_name.lower()}_step"
            )
        elif dist_type == "Geometric":
            ratio = column.number_input(
                t("{} Ratio").format(translated_dist_type_name), value=2.0, key=f"{column}_{dist_type_name.lower()}_ratio"
            )
        elif dist_type == "GeoCustom":
            ratio = column.number_input(
                t("{} Ratio").format(translated_dist_type_name), value=2.0, key=f"{column}_{dist_type_name.lower()}_ratio"
            )
        elif dist_type == "Linear":
            step = column.number_input(
                t("{} End").format(translated_dist_type_name), value=1.0, key=f"{column}_{dist_type_name.lower()}_end"
            )
    else:
        if default_values:
            manual_values = [
                column.number_input(
                    t("{} for level {}").format(translated_dist_type_name, i + 1),
                    value=value * 100.0,
                    key=f"{column}_{dist_type_name.lower()}_{i}",
                )
                for i, value in enumerate(default_values)
            ]
        else:
            manual_values = [
                column.number_input(
                    t("{} for level {}").format(translated_dist_type_name, i + 1),
                    value=i + 1.0,
                    key=f"{column}_{dist_type_name.lower()}_{i}",
                )
                for i, value in range(levels)
            ]
        start = None  # As start is not relevant for Manual type

    return dist_type, start, base, scaling_factor, step, ratio, manual_values


def get_distribution(dist_type, n_levels, start, base=None, scaling_factor=None, step=None, ratio=None, manual_values=None):
    distribution = []
    if dist_type == "Manual":
        distribution = manual_values
    elif dist_type == "Linear":
        distribution = Distributions.linear(n_levels, start, step)
    elif dist_type == "Fibonacci":
        distribution = Distributions.fibonacci(n_levels, start)
    elif dist_type == "Logarithmic":
        distribution = Distributions.logarithmic(n_levels, base, scaling_factor, start)
    elif dist_type == "Arithmetic":
        distribution = Distributions.arithmetic(n_levels, start, step)
    elif dist_type == "Geometric":
        distribution = Distributions.geometric(n_levels, start, ratio)
    elif dist_type == "GeoCustom":
        distribution = [Decimal("0")] + Distributions.geometric(n_levels - 1, start, ratio)
    return [float(val) for val in distribution]


# 添加清算狙击手策略所需的输入组件函数
def create_number_input(label, value, on_change, min_value=None, max_value=None, step=None):
    """创建数字输入框组件"""
    return mui.TextField(
        label=label,
        type="number",
        value=value,
        onChange=on_change,
        variant="outlined",
        sx={"width": "100%"},
        inputProps={"min": min_value, "max": max_value, "step": step},
    )


def create_text_input(label, value, on_change):
    """创建文本输入框组件"""
    return mui.TextField(label=label, value=value, onChange=on_change, variant="outlined", sx={"width": "100%"})


def create_select_input(label, value, options, on_change):
    """创建下拉选择框组件"""
    with mui.FormControl(sx={"width": "100%"}, variant="outlined"):
        mui.InputLabel(id=f"{label}-select-label")(label)
        with mui.Select(
            labelId=f"{label}-select-label",
            value=value,
            label=label,
            onChange=on_change,
        ):
            for option in options:
                mui.MenuItem(value=option)(option)
