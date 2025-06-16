from typing import List, Optional, Dict
from decimal import Decimal

from hummingbot.strategy_v2.executors.position_executor.data_types import TrailingStop
from hummingbot.strategy_v2.models.base import RunnableStatus
import pandas as pd
import pandas_ta as ta
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from hummingbot.core.data_type.common import (
    TradeType,
    PositionMode,
    PriceType,
    OrderType,
)
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy_v2.controllers.directional_trading_controller_base import (
    DirectionalTradingControllerBase,
    DirectionalTradingControllerConfigBase,
)
from hummingbot.strategy_v2.executors.flexible_grid_executor.data_types import (
    FlexibleGridExecutorConfig,
)
from hummingbot.strategy_v2.models.executor_actions import (
    CreateExecutorAction,
    ExecutorAction,
    StopExecutorAction,
)


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
        json_schema_extra={
            "prompt": "输入交易所连接器名称 (如 binance_perpetual): ",
            "prompt_on_new": True,
        },
    )
    trading_pair: str = Field(
        default="DOGE-USDT",
        description="交易对",
        json_schema_extra={
            "prompt": "输入交易对 (如 WLD-USDT): ",
            "prompt_on_new": True,
        },
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
        json_schema_extra={
            "prompt": "输入交易杠杆 (如 20 表示 20x 杠杆): ",
            "prompt_on_new": True,
        },
    )
    stop_loss: Optional[Decimal] = Field(
        default=Decimal("1.0"),
        description="止损比例",
        json_schema_extra={
            "prompt": "输入止损比例 (如 0.03 表示 3%): ",
            "prompt_on_new": True,
            "is_updatable": True,
        },
    )
    take_profit: Optional[Decimal] = Field(
        default=Decimal("1.0"),
        description="止盈比例",
        json_schema_extra={
            "prompt": "输入止盈比例 (如 0.02 表示 2%): ",
            "prompt_on_new": True,
            "is_updatable": True,
        },
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
        json_schema_extra={
            "prompt": "输入 trailing_stop (如 0.015,0.003): ",
            "prompt_on_new": True,
        },
    )
    take_profit_order_type: OrderType = Field(
        default=OrderType.MARKET,
        description="止盈订单类型",
        json_schema_extra={
            "prompt": "输入止盈订单类型 (LIMIT/MARKET): ",
            "prompt_on_new": True,
            "is_updatable": True,
        },
    )
    max_executors_per_side: int = Field(
        default=1,
        description="每侧最大执行器数量",
        json_schema_extra={
            "prompt": "输入每侧最大执行器数量 (如 2): ",
            "prompt_on_new": True,
            "is_updatable": True,
        },
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
        default=20,
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

    # 添加缺少的字段
    investment_mode: Optional[str] = Field(
        default="amount_quote",
        description="投资模式 - amount_quote: 按报价货币金额投资; amount_base: 按基础货币数量投资",
    )
    amount_quote: List[Decimal] = Field(
        default_factory=list,
        description="每个级别的投资金额（报价货币）- 在amount_quote模式下使用",
    )
    amount_base: List[Decimal] = Field(
        default_factory=list,
        description="每个级别的投资数量（基础货币）- 在amount_base模式下使用",
    )
    profit_target_amount: Optional[Decimal] = Field(
        default=None,
        description="全局止盈目标金额 - 当总盈利达到此金额时触发，设置为0表示不启用",
    )
    loss_target_amount: Optional[Decimal] = Field(
        default=None,
        description="全局止损目标金额 - 当总亏损达到此金额时触发，设置为0表示不启用",
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

    @field_validator(
        "cci_length",
        "cci_long_threshold",
        "cci_short_threshold",
        "cci_long_condition",
        "cci_short_condition",
    )
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
        if field_name in ["cci_long_condition", "cci_short_condition"] and v not in [
            ">",
            "<",
        ]:
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
        self.max_records = (
            self.config.cci_length + 50 if self.config.use_cci_signal else 50
        )
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
        self.logger().debug(f"【控制器配置】self.config={self.config}")

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
        last_candle_time = (
            df.index[-1].timestamp()
            if isinstance(df.index, pd.DatetimeIndex)
            else df["timestamp"].iloc[-1]
        )
        interval_seconds = self._convert_interval_to_seconds(self.config.interval)

        # 减小容差时间，更精确地判断K线是否已收盘
        tolerance = 1  # 减少到1秒

        is_closed = current_time >= last_candle_time + interval_seconds - tolerance

        # 添加详细日志，记录距离下一根K线开始的时间
        time_diff = interval_seconds - (current_time - last_candle_time)
        self.logger().debug(
            f"【K线检查】当前时间={current_time:.2f}, 最新K线时间={last_candle_time:.2f}, "
            f"时间差={time_diff:.2f}秒, 间隔={interval_seconds}秒, "
            f"容差={tolerance}秒, 已收盘={is_closed}"
        )

        return is_closed

    async def update_processed_data(self):
        if not self.market_data_provider.ready:
            self.logger().debug("市场数据提供者未就绪")
            self.processed_data = {"signal": 0, "features": pd.DataFrame()}
            return

        try:
            df = self._get_candles()
            if df.empty:
                self.logger().debug("K线数据为空")
                self.processed_data = {"signal": 0, "features": pd.DataFrame()}
                return

            # 检查K线是否已关闭（仅在设置为仅在K线关闭时更新时）
            if self.config.update_on_close_only and not self._is_candle_closed(df):
                self.logger().debug("当前K线未关闭，重置信号")
                self.processed_data = {"signal": 0, "features": df}  # 重置信号为 0
                return

            # 检查数据列
            required_columns = ["timestamp", "high", "low", "close"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.logger().error(f"K线数据缺少必要的列: {missing_columns}")
                self.processed_data = {"signal": 0, "features": df}
                return

            # 根据配置选择信号来源
            if self.config.use_cci_signal:
                signal = self._get_cci_signal(df)
                self.logger().debug(f"使用CCI信号: {signal}")
            else:
                signal = self._get_price_signal(df)
                self.logger().debug(f"使用价格信号: {signal}")

            self.processed_data = {"signal": signal, "features": df}
            self.logger().debug(f"数据更新完成: 信号={signal}, 数据形状={df.shape}")

        except Exception as e:
            self.logger().error(f"更新处理数据时发生错误: {str(e)}", exc_info=True)
            self.processed_data = {"signal": 0, "features": pd.DataFrame()}

    def _get_cci_signal(self, df: pd.DataFrame) -> int:
        """根据CCI指标生成信号"""
        try:
            # 确保df包含必要的列
            required_columns = ["high", "low", "close"]
            if not all(col in df.columns for col in required_columns):
                self.logger().error(f"K线数据缺少必要的列: {required_columns}")
                return 0

            # 计算CCI指标
            df["cci"] = ta.cci(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                length=self.config.cci_length,
            )

            # 检查是否成功计算了CCI
            if df["cci"].isna().all():
                self.logger().error("CCI计算失败，所有值都是NaN")
                return 0

            # 获取最新的CCI值
            latest_cci = df["cci"].iloc[-1]
            self.logger().info(f"{self.config.trading_pair} 最新CCI值: {latest_cci}")

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
                    self.logger().debug("【信号过滤】仅保留做多信号")
                elif self.config.side == TradeType.SELL:
                    df.loc[df["signal"] > 0, "signal"] = 0
                    self.logger().debug("【信号过滤】仅保留做空信号")
                elif self.config.side == TradeType.RANGE:
                    self.logger().debug("【信号过滤】启用双向信号（RANGE 模式）")

            signal = df["signal"].iloc[-1]
            self.logger().debug(f"生成信号: {signal}")
            return signal

        except Exception as e:
            self.logger().error(f"计算CCI信号时发生错误: {str(e)}", exc_info=True)
            return 0

    def _get_price_signal(self, df: pd.DataFrame) -> int:
        """根据价格和方向过滤生成信号"""
        if self.config.side is None:
            self.logger().warning("【配置错误】side 未设置，信号设为 0")
            return 0
        elif self.config.side == TradeType.BUY:
            self.logger().debug("【信号生成】直接生成做多信号（side=BUY）")
            return 1
        elif self.config.side == TradeType.SELL:
            self.logger().debug("【信号生成】直接生成做空信号（side=SELL）")
            return -1
        else:  # TradeType.RANGE
            self.logger().warning("【配置错误】RANGE 模式下需启用 CCI 信号，信号设为 0")
            return 0

    def can_create_executor(self, signal: int) -> bool:
        """
        检查是否可以创建执行器
        Args:
            signal: 信号值 (>0 表示买入, <0 表示卖出)
        Returns:
            bool: 是否可以创建执行器
        """
        # 获取所有执行器
        all_executors = list(self.executors_info)

        # 详细记录每个执行器的状态
        for executor in all_executors:
            self.logger().debug(
                f"执行器状态详情:\n"
                f"- ID: {executor.id}\n"
                f"- 状态: {executor.status}\n"
                # f"- 配置: {executor.config}"
            )

        # 按信号方向过滤活跃执行器
        target_side = TradeType.BUY if signal > 0 else TradeType.SELL
        active_executors_by_signal_side = [
            executor
            for executor in all_executors
            if executor.status == RunnableStatus.RUNNING
            and executor.config.side == target_side
        ]

        # 获取最新执行器的时间戳
        executor_timestamps = [
            float(executor.config.timestamp)
            for executor in active_executors_by_signal_side
        ]
        max_timestamp = max(executor_timestamps) if executor_timestamps else 0

        # 检查条件
        active_executors_condition = (
            len(active_executors_by_signal_side) < self.config.max_executors_per_side
        )
        current_time = float(self.market_data_provider.time())
        cooldown_condition = current_time - max_timestamp > self.config.cooldown_time

        # 详细日志
        self.logger().debug(
            f"执行器状态检查:\n"
            f"- 总执行器数量: {len(all_executors)}\n"
            f"- 运行中执行器: {len([e for e in all_executors if e.status == RunnableStatus.RUNNING])}\n"
            f"- 目标方向: {target_side}\n"
            f"- 当前方向活跃数量: {len(active_executors_by_signal_side)}\n"
            f"- 方向上限: {self.config.max_executors_per_side}\n"
            f"- 执行器时间戳列表: {executor_timestamps}\n"
            f"- 最新执行器时间: {max_timestamp}\n"
            f"- 当前时间: {current_time}\n"
            f"- 冷却时间: {self.config.cooldown_time}s\n"
            f"- 时间差: {current_time - max_timestamp}s\n"
            f"- 条件检查结果: active={active_executors_condition}, cooldown={cooldown_condition}"
        )

        return active_executors_condition and cooldown_condition

    def create_actions_proposal(self) -> List[CreateExecutorAction]:
        """
        根据信号创建执行器动作
        Returns:
            List[CreateExecutorAction]: 执行器创建动作列表
        """
        create_actions = []

        # 获取当前信号
        signal = self.processed_data.get("signal", 0)

        if signal != 0 and self.can_create_executor(signal):
            # 获取当前价格
            price = self.market_data_provider.get_price_by_type(
                self.config.connector_name, self.config.trading_pair, PriceType.MidPrice
            )

            if price is None or price <= 0:
                self.logger().warning(f"无法获取有效价格，跳过执行器创建")
                return create_actions

            # 确定交易方向
            trade_type = TradeType.BUY if signal > 0 else TradeType.SELL

            # 获取执行器配置
            executor_config = self.get_executor_config(trade_type, price)

            if executor_config is not None:
                create_actions.append(
                    CreateExecutorAction(
                        controller_id=self.config.id, executor_config=executor_config
                    )
                )
                self.logger().debug(
                    f"创建执行器动作: 方向={trade_type.name}, "
                    f"价格={price}, "
                    f"配置ID={executor_config.id if hasattr(executor_config, 'id') else 'N/A'}"
                )

        return create_actions

    def stop_actions_proposal(self) -> List[ExecutorAction]:
        """停止执行器的动作建议"""
        stop_actions = []
        for executor in self.executors_info:  # 直接遍历列表
            if executor.status == RunnableStatus.TERMINATED:
                stop_actions.append(
                    StopExecutorAction(
                        controller_id=self.config.id, executor_id=executor.id
                    )
                )
        return stop_actions

    async def control_task(self):
        if self.market_data_provider.ready and self.executors_update_event.is_set():
            await self.update_processed_data()
            executor_actions: List[ExecutorAction] = self.determine_executor_actions()

    def _prepare_executor_config_dict(self, side: TradeType) -> Dict:
        """准备FlexibleGridExecutor的配置字典，处理所有参数验证和默认值设置

        Args:
            side: 交易方向

        Returns:
            Dict: 执行器配置字典
        """
        side_display = side.name if hasattr(side, "name") else str(side)
        self.logger().debug(f"准备 FlexibleGridExecutor 配置，方向: {side_display}")

        # 决定级别数量，单向或双向
        if self.config.side == TradeType.RANGE:
            n_levels = self.config.n_levels
            self.logger().debug(f"双向交易，每个方向使用 {n_levels} 个级别")
        elif (self.config.side == TradeType.BUY and side == TradeType.BUY) or (
            self.config.side == TradeType.SELL and side == TradeType.SELL
        ):
            n_levels = self.config.n_levels
            self.logger().debug(f"单向交易 {side_display}，使用 {n_levels} 个级别")
        else:
            self.logger().debug(
                f"方向 {side_display} 与过滤器设置 {self.config.side} 不匹配，跳过"
            )
            return {}

        # 投资模式
        investment_mode = getattr(self.config, "investment_mode", "amount_quote")

        # 处理其他比率参数
        def process_ratio_list(name: str, default_value: float) -> List[Decimal]:
            attr_name = f"{name}_ratios"
            if (
                not hasattr(self.config, attr_name)
                or len(getattr(self.config, attr_name)) < n_levels
            ):
                self.logger().debug(
                    f"{name} 比率没有提供或长度不足，使用默认值 {default_value}: {n_levels} 个级别"
                )
                return [Decimal(str(default_value)) for _ in range(n_levels)]
            return getattr(self.config, attr_name)[:n_levels]

        open_ratios = process_ratio_list("open", 0.01)
        open_rebound_ratios = process_ratio_list("open_rebound", 0.005)
        take_profit_ratios = process_ratio_list("take_profit", 0.02)
        take_profit_rebound_ratios = process_ratio_list("take_profit_rebound", 0.005)
        stop_loss_ratios = process_ratio_list("stop_loss", 0.01)

        if self.config.first_level_open:
            open_ratios[0] = Decimal("0")
            open_rebound_ratios[0] = Decimal("0")

        # 确保所有Decimal类型都转换为字符串
        config_dict = {
            "id": f"cci_flexgrid_{self.config.id}_{int(self.market_data_provider.time())}",
            "timestamp": float(self.market_data_provider.time()),  # 确保是float类型
            "controller_id": self.config.id,
            "connector_name": self.config.connector_name,
            "trading_pair": self.config.trading_pair,
            "side": side.value,  # 使用枚举值
            "n_levels": n_levels,
            "investment_mode": investment_mode,  # 添加投资模式参数
            "open_ratios": [str(r) for r in open_ratios],  # 列表中的Decimal转换为字符串
            "open_rebound_ratios": [str(r) for r in open_rebound_ratios],
            "take_profit_ratios": [str(r) for r in take_profit_ratios],
            "take_profit_rebound_ratios": [str(r) for r in take_profit_rebound_ratios],
            "stop_loss_ratios": [str(r) for r in stop_loss_ratios],
            "max_open_orders": self.config.max_open_orders,
            "order_frequency": float(self.config.order_frequency),  # 确保是float类型
            "keep_position": self.config.keep_position,
            "leverage": self.config.leverage,
            "position_mode": self.config.position_mode.value,
            "take_profit": str(self.config.take_profit),
            "stop_loss": str(self.config.stop_loss),
            "min_levels_for_global_barriers": self.config.min_levels_for_global_barriers,
            "min_reopen_interval": self.config.min_reopen_interval,
            "first_level_open": self.config.first_level_open,
        }

        # 根据投资模式添加相应的参数
        if investment_mode == "amount_quote":
            # 检查amount_quote参数
            if (
                hasattr(self.config, "amount_quote")
                and len(self.config.amount_quote) >= n_levels
            ):
                config_dict["amount_quote"] = [
                    str(a) for a in self.config.amount_quote[:n_levels]
                ]
            else:
                # 如果没有提供amount_quote或长度不足，使用默认值
                self.logger().debug(
                    f"每级别金额没有提供或长度不足，使用默认值: {n_levels} 个级别"
                )
                # 不再依赖total_amount_quote进行分配，直接使用默认值
                config_dict["amount_quote"] = [
                    str(Decimal("10")) for _ in range(n_levels)
                ]
                self.logger().debug("未提供级别金额，使用默认值 10 USDT 每级别")
        else:  # amount_base模式
            # 检查amount_base参数
            if (
                hasattr(self.config, "amount_base")
                and len(self.config.amount_base) >= n_levels
            ):
                config_dict["amount_base"] = [
                    str(a) for a in self.config.amount_base[:n_levels]
                ]
            else:
                # 如果没有提供amount_base或长度不足，使用默认值
                self.logger().debug(
                    f"每级别数量没有提供或长度不足，使用默认值: {n_levels} 个级别"
                )
                # 不再依赖total_amount_base进行分配，直接使用默认值
                config_dict["amount_base"] = [
                    str(Decimal("10.0")) for _ in range(n_levels)
                ]
                self.logger().debug("未提供级别数量，使用默认值 10.0 每级别")

        # 添加可选参数
        if (
            hasattr(self.config, "profit_target_amount")
            and self.config.profit_target_amount is not None
            and float(self.config.profit_target_amount) > 0
        ):
            config_dict["profit_target_amount"] = str(self.config.profit_target_amount)
        if (
            hasattr(self.config, "loss_target_amount")
            and self.config.loss_target_amount is not None
            and float(self.config.loss_target_amount) > 0
        ):
            config_dict["loss_target_amount"] = str(self.config.loss_target_amount)
        if hasattr(self.config, "time_limit") and self.config.time_limit is not None:
            config_dict["time_limit"] = self.config.time_limit

        return config_dict

    def get_executor_config(
        self, side: TradeType, price: Decimal
    ) -> FlexibleGridExecutorConfig:
        """生成FlexibleGridExecutor的配置

        Args:
            side: 交易方向
            price: 当前价格（用于日志记录）

        Returns:
            FlexibleGridExecutorConfig: 执行器配置
        """
        config_dict = self._prepare_executor_config_dict(side)
        side_display = side.name if hasattr(side, "name") else str(side)
        self.logger().debug(
            f"【执行器配置】生成配置: 方向={side_display}, 价格={price}, 配置={config_dict}"
        )
        return FlexibleGridExecutorConfig(**config_dict)
