from typing import List, Optional, Dict
from decimal import Decimal

from hummingbot.strategy_v2.executors.position_executor.data_types import TrailingStop
import pandas as pd
import pandas_ta as ta
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from hummingbot.core.data_type.common import TradeType, PositionMode, PriceType, OrderType
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy_v2.controllers.directional_trading_controller_base import (
    DirectionalTradingControllerBase,
    DirectionalTradingControllerConfigBase,
)
from hummingbot.strategy_v2.executors.flexible_grid_executor.data_types import FlexibleGridExecutorConfig
from hummingbot.strategy_v2.models.executor_actions import CreateExecutorAction


class CCIFlexibleGridControllerConfig(DirectionalTradingControllerConfigBase):
    """
    CCI灵活网格控制器的配置类，继承基类配置
    该控制器使用CCI指标或直接信号生成交易信号，并通过灵活网格执行器执行交易
    """

    controller_name: str = "cci_flexible_grid"
    candles_config: List[CandlesConfig] = []

    # 需要用户输入的参数
    connector_name: str = Field(
        default="okx_perpetual",
        description="交易所连接器名称",
        json_schema_extra={"prompt": "输入交易所连接器名称 (如 binance_perpetual): ", "prompt_on_new": True},
    )
    trading_pair: str = Field(
        default="DOGE-USDT",
        description="交易对",
        json_schema_extra={"prompt": "输入交易对 (如 WLD-USDT): ", "prompt_on_new": True},
    )
    total_amount_quote: Decimal = Field(
        default=Decimal("1000"),
        description="总投资金额",
        json_schema_extra={
            "prompt": "输入总投资金额（报价货币，如 1000 USDT）：",
            "prompt_on_new": True,
            "is_updatable": True,
        },
    )
    leverage: int = Field(
        default=10,
        description="交易杠杆",
        json_schema_extra={"prompt": "输入交易杠杆 (如 20 表示 20x 杠杆): ", "prompt_on_new": True},
    )
    stop_loss: Optional[Decimal] = Field(
        default=Decimal("1.0"),
        description="止损比例",
        json_schema_extra={"prompt": "输入止损比例 (如 0.03 表示 3%): ", "prompt_on_new": True, "is_updatable": True},
    )
    take_profit: Optional[Decimal] = Field(
        default=Decimal("1.0"),
        description="止盈比例",
        json_schema_extra={"prompt": "输入止盈比例 (如 0.02 表示 2%): ", "prompt_on_new": True, "is_updatable": True},
    )
    time_limit: Optional[int] = Field(
        default=3600 * 24 * 365,
        description="时间限制",
        json_schema_extra={
            "prompt": "输入时间限制 (秒，如 2700 表示 45 分钟): ",
            "prompt_on_new": True,
            "is_updatable": True,
        },
    )
    trailing_stop: Optional[TrailingStop] = Field(
        default=None,
        description="追踪止损参数",
        json_schema_extra={"prompt": "输入 trailing_stop (如 0.015,0.003): ", "prompt_on_new": True},
    )
    take_profit_order_type: OrderType = Field(
        default=OrderType.MARKET,
        description="止盈订单类型",
        json_schema_extra={"prompt": "输入止盈订单类型 (LIMIT/MARKET): ", "prompt_on_new": True, "is_updatable": True},
    )
    max_executors_per_side: int = Field(
        default=1,
        description="每侧最大执行器数量",
        json_schema_extra={"prompt": "输入每侧最大执行器数量 (如 2): ", "prompt_on_new": True, "is_updatable": True},
    )
    cooldown_time: int = Field(
        default=1,
        gt=0,
        description="冷却时间",
        json_schema_extra={
            "prompt": "在执行信号后输入冷却时间（以秒为单位）:",
            "prompt_on_new": True,
            "is_updatable": True,
        },
    )
    # 不需要用户输入的参数
    candles_connector: str = None
    candles_trading_pair: str = None
    interval: str = "1m"
    update_on_close_only: bool = True
    use_cci_signal: bool = True

    # CCI相关参数，设置为可选
    cci_length: Optional[int] = Field(
        default=14,
        description="CCI指标的周期长度",
        json_schema_extra={"is_updatable": True},
    )
    cci_long_threshold: Optional[float] = Field(
        default=100.0,
        description="CCI做多阈值",
        json_schema_extra={"is_updatable": True},
    )
    cci_short_threshold: Optional[float] = Field(
        default=-100.0,
        description="CCI做空阈值",
        json_schema_extra={"is_updatable": True},
    )
    cci_long_condition: Optional[str] = Field(
        default="<",
        description="CCI做多条件",
        json_schema_extra={"is_updatable": True},
    )
    cci_short_condition: Optional[str] = Field(
        default=">",
        description="CCI做空条件",
        json_schema_extra={"is_updatable": True},
    )

    n_levels: int = 3
    first_level_open: bool = True
    side: Optional[TradeType] = TradeType.RANGE
    open_ratios: List[Decimal] = []
    open_rebound_ratios: List[Decimal] = []
    take_profit_ratios: List[Decimal] = []
    take_profit_rebound_ratios: List[Decimal] = []
    stop_loss_ratios: List[Decimal] = []
    amount_quote_ratios: List[Decimal] = []
    max_open_orders: int = 3
    order_frequency: float = 1.0
    keep_position: bool = False
    min_reopen_interval: int = 10
    min_levels_for_global_barriers: int = 3

    model_config = {
        "arbitrary_types_allowed": True,
        "extra": "allow",  # 允许额外字段
    }

    @field_validator("candles_connector", mode="before")
    @classmethod
    def set_candles_connector(cls, v, validation_info: ValidationInfo):
        return v or validation_info.data.get("connector_name")

    @field_validator("candles_trading_pair", mode="before")
    @classmethod
    def set_candles_trading_pair(cls, v, validation_info: ValidationInfo):
        return v or validation_info.data.get("trading_pair")

    @field_validator("side", mode="before")
    @classmethod
    def parse_side(cls, v, validation_info: ValidationInfo):
        if v is None or isinstance(v, TradeType):
            return v
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper == "BUY":
                return TradeType.BUY
            elif v_upper == "SELL":
                return TradeType.SELL
            elif v_upper == "RANGE":
                return TradeType.RANGE
            elif v_upper in ("1", "2", "3"):
                v = int(v_upper)
            else:
                raise ValueError("输入应为 BUY, SELL, RANGE, 1, 2 或 3")
        if isinstance(v, int):
            try:
                return TradeType(v)
            except Exception:
                raise ValueError("输入应为 1, 2 或 3 (对应 BUY, SELL, RANGE)")
        raise ValueError("输入应为 BUY, SELL, RANGE, 1, 2 或 3")

    @field_validator("cci_length", "cci_long_threshold", "cci_short_threshold", "cci_long_condition", "cci_short_condition")
    @classmethod
    def validate_cci_parameters(cls, v, info: ValidationInfo):
        use_cci_signal = info.data.get("use_cci_signal", True)
        field_name = info.field_name

        # 如果不使用CCI信号，所有CCI相关参数都可以为None
        if not use_cci_signal:
            return None

        # 如果使用CCI信号，验证各个参数
        if v is None:
            if field_name == "cci_length":
                return 14
            elif field_name == "cci_long_threshold":
                return 100.0
            elif field_name == "cci_short_threshold":
                return -100.0
            elif field_name == "cci_long_condition":
                return "<"
            elif field_name == "cci_short_condition":
                return ">"

        # 特定参数的验证
        if field_name in ["cci_long_condition", "cci_short_condition"] and v not in [">", "<"]:
            raise ValueError("CCI条件必须为 '>' 或 '<'")

        return v

    def model_dump(self, **kwargs):
        """重写 model_dump 方法以确保正确序列化"""
        data = super().model_dump(**kwargs)
        # 转换 Decimal 类型为字符串
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, list) and value and isinstance(value[0], Decimal):
                data[key] = [str(v) for v in value]
            elif isinstance(value, TradeType):
                data[key] = value.value
            elif isinstance(value, OrderType):
                data[key] = value.value
        return data


class CCIFlexibleGridController(DirectionalTradingControllerBase):
    """
    CCI灵活网格控制器，基于CCI信号或直接触发FlexibleGridExecutor
    支持两种信号更新模式：每次K线更新或仅K线收盘更新
    """

    def __init__(self, config: CCIFlexibleGridControllerConfig, *args, **kwargs):
        super().__init__(config, *args, **kwargs)
        self.config = config
        self.max_records = self.config.cci_length + 50 if self.config.use_cci_signal else 50
        self.last_processed_timestamp = 0.0
        self.processed_data = {"signal": 0, "features": None}
        if not config.candles_config:
            self.config.candles_config = [
                CandlesConfig(
                    connector=config.candles_connector or config.connector_name,
                    trading_pair=config.candles_trading_pair or config.trading_pair,
                    interval=config.interval,
                    max_records=self.max_records,
                )
            ]
        self.logger().info(f"【控制器配置】self.config={self.config}")

    def _get_candles(self) -> pd.DataFrame:
        """获取K线数据"""
        df = self.market_data_provider.get_candles_df(
            connector_name=self.config.candles_connector or self.config.connector_name,
            trading_pair=self.config.candles_trading_pair or self.config.trading_pair,
            interval=self.config.interval,
            max_records=self.max_records,
        )
        return df

    def _convert_interval_to_seconds(self, interval: str) -> int:
        """将K线间隔转换为秒数"""
        unit = interval[-1]
        value = int(interval[:-1])
        if unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600
        elif unit == "d":
            return value * 86400
        return value

    def _is_candle_closed(self, df: pd.DataFrame) -> bool:
        """检查当前K线是否已收盘"""
        if df.empty:
            self.logger().warning("【K线错误】K线数据为空")
            return False

        current_time = self.market_data_provider.time()
        last_candle_time = df.index[-1].timestamp() if isinstance(df.index, pd.DatetimeIndex) else df["timestamp"].iloc[-1]
        interval_seconds = self._convert_interval_to_seconds(self.config.interval)

        # 减小容差时间，更精确地判断K线是否已收盘
        tolerance = 2  # 减少到2秒

        is_closed = current_time >= last_candle_time + interval_seconds - tolerance

        # 添加详细日志，记录距离下一根K线开始的时间
        time_diff = interval_seconds - (current_time - last_candle_time)
        self.logger().info(
            f"【K线检查】当前时间={current_time:.2f}, 最新K线时间={last_candle_time:.2f}, "
            f"时间差={time_diff:.2f}秒, 间隔={interval_seconds}秒, "
            f"容差={tolerance}秒, 已收盘={is_closed}"
        )

        return is_closed

    def _check_candles(self, df: pd.DataFrame) -> Optional[float]:
        """检查K线数据是否有效并返回最新时间戳"""
        if df.empty:
            self.logger().warning("【K线错误】K线数据为空")
            return None

        current_timestamp = df.index[-1].timestamp() if isinstance(df.index, pd.DatetimeIndex) else df["timestamp"].iloc[-1]

        self.logger().info(f"【K线检查】当前最新K线时间戳={current_timestamp:.2f}")

        if self.config.update_on_close_only:
            # 严格检查K线是否已收盘
            if not self._is_candle_closed(df):
                current_time = self.market_data_provider.time()
                last_candle_time = current_timestamp
                interval_seconds = self._convert_interval_to_seconds(self.config.interval)
                self.logger().info(
                    f"【信号跳过】K线未收盘，当前时间={current_time:.2f}, "
                    f"最新K线时间={last_candle_time:.2f}, "
                    f"预期收盘时间={last_candle_time + interval_seconds:.2f}"
                )
                return None

            # 检查是否已处理过该K线
            if current_timestamp <= self.last_processed_timestamp:
                self.logger().info(
                    f"【信号跳过】已处理该K线，当前时间戳={current_timestamp:.2f}, "
                    f"上次处理时间戳={self.last_processed_timestamp:.2f}, "
                    f"K线数量={len(df)}, 最新5条时间戳={[t for t in df['timestamp'].tail(5)]}"
                )
                return None

            self.logger().info(f"【K线更新】发现新的已收盘K线，时间戳={current_timestamp:.2f}")
            return current_timestamp

        self.logger().info(f"【K线更新】update_on_close_only为False，直接处理，时间戳={current_timestamp:.2f}")
        return current_timestamp

    def _calculate_cci_and_signal(self, df: pd.DataFrame) -> int:
        """计算CCI指标并生成信号"""
        if self.config.use_cci_signal:
            df["cci"] = ta.cci(df["high"], df["low"], df["close"], length=self.config.cci_length)
            signal = self._get_cci_signal(df)
        else:
            signal = self._get_price_signal(df)

        cci_value = df["cci"].iloc[-1] if self.config.use_cci_signal and "cci" in df else "无CCI"
        self.logger().info(f"【信号更新】CCI={cci_value}, 信号={signal}, K线数量={len(df)}")
        return signal

    async def update_processed_data(self):
        """更新处理数据，检查K线并计算CCI信号"""
        # 获取K线数据
        df = self._get_candles()
        if df.empty:
            self.logger().warning("【K线错误】K线数据为空，设置默认信号为 0")
            self.processed_data["signal"] = 0
            self.processed_data["features"] = pd.DataFrame()
            return

        # 检查K线状态
        current_timestamp = self._check_candles(df)
        if current_timestamp is None:
            return

        # 更新最后处理时间戳
        self.last_processed_timestamp = current_timestamp

        # 计算CCI和信号
        signal = self._calculate_cci_and_signal(df)

        # 更新处理数据
        self.processed_data["signal"] = signal
        self.processed_data["features"] = df

    def _get_cci_signal(self, df: pd.DataFrame) -> int:
        """根据CCI指标生成信号"""
        # 根据配置动态设置CCI比较条件
        if self.config.cci_long_condition == ">":
            long_condition = df["cci"] > self.config.cci_long_threshold
        else:  # <
            long_condition = df["cci"] < self.config.cci_long_threshold

        if self.config.cci_short_condition == ">":
            short_condition = df["cci"] > self.config.cci_short_threshold
        else:  # <
            short_condition = df["cci"] < self.config.cci_short_threshold

        df["signal"] = 0
        df.loc[long_condition, "signal"] = 1
        df.loc[short_condition, "signal"] = -1

        # 应用方向过滤
        if self.config.side is not None:
            if self.config.side == TradeType.BUY:
                df.loc[df["signal"] < 0, "signal"] = 0
                self.logger().info("【信号过滤】仅保留做多信号")
            elif self.config.side == TradeType.SELL:
                df.loc[df["signal"] > 0, "signal"] = 0
                self.logger().info("【信号过滤】仅保留做空信号")
            elif self.config.side == TradeType.RANGE:
                self.logger().info("【信号过滤】启用双向信号（RANGE 模式）")

        return df["signal"].iloc[-1]

    def _get_price_signal(self, df: pd.DataFrame) -> int:
        """根据价格和方向过滤生成信号"""
        if self.config.side is None:
            self.logger().warning("【配置错误】side 未设置，信号设为 0")
            return 0
        elif self.config.side == TradeType.BUY:
            self.logger().info("【信号生成】直接生成做多信号（side=BUY）")
            return 1
        elif self.config.side == TradeType.SELL:
            self.logger().info("【信号生成】直接生成做空信号（side=SELL）")
            return -1
        else:  # TradeType.RANGE
            self.logger().warning("【配置错误】RANGE 模式下需启用 CCI 信号，信号设为 0")
            return 0

    def create_actions_proposal(self) -> List[CreateExecutorAction]:
        """根据信号创建FlexibleGridExecutor"""
        actions = []

        # 基本检查：确保有信号数据
        if "signal" not in self.processed_data:
            self.logger().info("【执行器跳过】无信号数据")
            return actions

        signal = self.processed_data["signal"]

        # 信号为0表示不交易
        if signal == 0:
            self.logger().info("【执行器跳过】信号为0，不触发交易")
            return actions

        # 获取信号对应的交易方向
        side = TradeType.BUY if signal > 0 else TradeType.SELL

        # 确认信号方向与策略配置兼容
        if self.config.side != TradeType.RANGE and self.config.side != side:
            self.logger().info(f"【执行器跳过】信号方向({side})与策略配置方向({self.config.side})不匹配")
            return actions

        # 获取当前市场价格
        price = self.market_data_provider.get_price_by_type(
            connector_name=self.config.connector_name,
            trading_pair=self.config.trading_pair,
            price_type=PriceType.MidPrice,
        )

        if price is None or price <= Decimal("0"):
            self.logger().warning(f"【价格错误】无法获取有效价格: {price}")
            return actions

        # 检查活跃执行器状态
        active_executors = self.filter_executors(executors=self.executors_info, filter_func=lambda x: x.is_active)
        if active_executors:
            # 已有活跃执行器，使用can_create_executor进行检查
            if not self.can_create_executor(signal):
                self.logger().info("【执行器跳过】不满足创建条件")
                return actions
            self.logger().info(f"【执行器创建】当前活跃执行器数量: {len(active_executors)}，准备创建新执行器")
        else:
            # 没有活跃执行器，可以直接创建
            self.logger().info("【执行器创建】没有活跃的执行器，将创建新执行器")

        # 创建执行器配置并生成动作
        executor_config = self.get_executor_config(side, price)

        # 创建执行器动作
        action = CreateExecutorAction(
            controller_id=self.config.id,
            executor_type="flexible_grid_executor",
            executor_config=executor_config,
        )
        actions.append(action)

        self.logger().info(
            f"【执行器创建】请求创建执行器: 方向={side.name}, 价格={price}, 执行器ID={executor_config.id}, "
            f"当前时间={self.market_data_provider.time():.2f}"
        )

        return actions

    def can_create_executor(self, signal: int) -> bool:
        """
        检查是否可以创建执行器
        """
        # 获取所有活跃的执行器，而不只是同方向的
        all_active_executors = self.filter_executors(
            executors=self.executors_info,
            filter_func=lambda x: x.is_active,
        )

        # 检查是否存在任何活跃执行器
        if all_active_executors:
            # 当前有活跃执行器，检查该方向的活跃执行器数量
            active_executors_by_signal_side = self.filter_executors(
                executors=self.executors_info,
                filter_func=lambda x: x.is_active and (x.side == TradeType.BUY if signal > 0 else TradeType.SELL),
            )

            self.logger().info(
                f"活跃执行器数量: 总共={len(all_active_executors)}, 当前信号方向={len(active_executors_by_signal_side)}, "
                f"上限({self.config.max_executors_per_side})"
            )

            # 检查同方向的活跃执行器数量是否已达上限
            if len(active_executors_by_signal_side) >= self.config.max_executors_per_side:
                self.logger().info(
                    f"活跃执行器数量({len(active_executors_by_signal_side)})已达到每侧上限({self.config.max_executors_per_side})"
                )
                return False

            # 获取最近一次该方向执行器的创建时间
            max_timestamp = max(
                [executor.timestamp for executor in active_executors_by_signal_side],
                default=0,
            )
            current_time = self.market_data_provider.time()
            time_since_last_creation = current_time - max_timestamp

            self.logger().info(
                f"冷却时间检查: 上次创建={max_timestamp:.2f}, 当前时间={current_time:.2f}, "
                f"经过时间={time_since_last_creation:.2f}秒, 需要等待={self.config.cooldown_time}秒, "
                f"剩余等待时间={max(0, self.config.cooldown_time - time_since_last_creation):.2f}秒"
            )

            # 检查冷却时间
            if time_since_last_creation < self.config.cooldown_time:
                self.logger().info(f"冷却时间未到，还需等待 {self.config.cooldown_time - time_since_last_creation:.2f} 秒")
                return False
        else:
            self.logger().info("没有活跃的执行器，可以创建新执行器")

        self.logger().info("【执行器创建】can_create_executor检查通过")
        return True

    def _prepare_executor_config_dict(self, side: TradeType) -> Dict:
        """准备FlexibleGridExecutor的配置字典，处理所有参数验证和默认值设置

        Args:
            side: 交易方向

        Returns:
            Dict: 执行器配置字典
        """
        self.logger().info(f"准备 FlexibleGridExecutor 配置，方向: {side.name}")

        n_levels = self.config.n_levels
        # 定义各属性的默认值
        default_values = {
            "open_ratios": Decimal("0.005"),
            "open_rebound_ratios": Decimal("0.0005"),
            "take_profit_ratios": Decimal("0.005"),
            "take_profit_rebound_ratios": Decimal("0.0005"),
            "stop_loss_ratios": Decimal("1.0"),
            "amount_quote_ratios": Decimal("1") / n_levels,  # 特殊处理，均分
        }

        # 验证和填充比率列表
        for attr in [
            "open_ratios",
            "open_rebound_ratios",
            "take_profit_ratios",
            "take_profit_rebound_ratios",
            "stop_loss_ratios",
            "amount_quote_ratios",
        ]:
            ratios = getattr(self.config, attr)
            if len(ratios) != n_levels:
                if len(ratios) > 0:  # 如果用户提供了一些值
                    if len(ratios) > n_levels:
                        # 如果提供的值过多，截取需要的部分
                        new_ratios = ratios[:n_levels]
                    else:
                        # 如果提供的值不够，使用最后一个值填充
                        last_value = ratios[-1]
                        new_ratios = ratios + [last_value] * (n_levels - len(ratios))
                else:
                    # 如果没有提供任何值，使用默认值
                    default_value = default_values[attr]
                    new_ratios = [default_value] * n_levels

                setattr(self.config, attr, new_ratios)
                self.logger().info(f"【配置修正】{attr} 长度从 {len(ratios)} 调整为 {n_levels}: {[float(r) for r in new_ratios]}")

        # 特殊检查金额分配比率总和
        if abs(sum(self.config.amount_quote_ratios) - Decimal("1")) > Decimal("0.01"):
            self.logger().warning(f"【配置警告】金额分配比率总和为 {sum(self.config.amount_quote_ratios)}，应接近 1")

        if self.config.first_level_open:
            self.config.open_ratios[0] = Decimal("0")
            self.config.open_rebound_ratios[0] = Decimal("0")

        # 确保所有Decimal类型都转换为字符串
        config_dict = {
            "id": f"cci_flexgrid_{self.config.id}_{int(self.market_data_provider.time())}",
            "timestamp": float(self.market_data_provider.time()),  # 确保是float类型
            "controller_id": self.config.id,
            "connector_name": self.config.connector_name,
            "trading_pair": self.config.trading_pair,
            "side": side.value,  # 使用枚举值
            "total_amount_quote": str(self.config.total_amount_quote),  # 转换为字符串
            "n_levels": n_levels,
            "open_ratios": [str(r) for r in self.config.open_ratios],  # 列表中的Decimal转换为字符串
            "open_rebound_ratios": [str(r) for r in self.config.open_rebound_ratios],
            "take_profit_ratios": [str(r) for r in self.config.take_profit_ratios],
            "take_profit_rebound_ratios": [str(r) for r in self.config.take_profit_rebound_ratios],
            "stop_loss_ratios": [str(r) for r in self.config.stop_loss_ratios],
            "amount_quote_ratios": [str(r) for r in self.config.amount_quote_ratios],
            "max_open_orders": self.config.max_open_orders,
            "order_frequency": float(self.config.order_frequency),  # 确保是float类型
            "keep_position": self.config.keep_position,
            "leverage": self.config.leverage,
            "position_mode": self.config.position_mode.value,  # 使用枚举值
            "min_reopen_interval": self.config.min_reopen_interval,
            "take_profit": str(self.config.take_profit) if self.config.take_profit else None,  # 处理可选值
            "stop_loss": str(self.config.stop_loss) if self.config.stop_loss else None,
            "time_limit": self.config.time_limit,
            "min_levels_for_global_barriers": n_levels,
            "first_level_open": self.config.first_level_open,
        }

        return config_dict

    def get_executor_config(self, side: TradeType, price: Decimal) -> FlexibleGridExecutorConfig:
        """生成FlexibleGridExecutor的配置

        Args:
            side: 交易方向
            price: 当前价格（用于日志记录）

        Returns:
            FlexibleGridExecutorConfig: 执行器配置
        """
        config_dict = self._prepare_executor_config_dict(side)
        self.logger().info(f"【执行器配置】生成配置: 方向={side.name}, 价格={price}, 配置={config_dict}")
        return FlexibleGridExecutorConfig(**config_dict)
