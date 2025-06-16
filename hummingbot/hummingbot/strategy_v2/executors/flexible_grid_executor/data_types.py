from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
import traceback
from typing import Any, Optional, List, Literal, Dict, Callable, Union
import time
import uuid
import logging
import asyncio
from collections import defaultdict
from datetime import datetime

from hummingbot.core.event.events import (
    BuyOrderCompletedEvent,
    BuyOrderCreatedEvent,
    OrderFilledEvent,
    SellOrderCompletedEvent,
    SellOrderCreatedEvent,
    OrderCancelledEvent,
    MarketOrderFailureEvent,
)
from hummingbot.logger.logger import HummingbotLogger
from pydantic import Field, BaseModel
from hummingbot.core.data_type.common import OrderType, TradeType, PositionMode
from hummingbot.strategy_v2.executors.data_types import ExecutorConfigBase
from hummingbot.strategy_v2.executors.position_executor.position_executor import PositionExecutor
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig, TripleBarrierConfig

# 全局日志器，供所有类共享
_global_logger: Optional[HummingbotLogger] = None


def get_global_logger() -> HummingbotLogger:
    """获取全局日志器，延迟初始化并设置为DEBUG级别"""
    global _global_logger
    if _global_logger is None:
        _global_logger = logging.getLogger(__name__)
        # _global_logger.setLevel(logging.DEBUG)
        _global_logger.setLevel(logging.INFO)
    return _global_logger


@dataclass
class GridStateEvent:
    """网格事件数据类，用于跟踪状态变化和订单事件

    属性:
        event_type: 事件类型（如状态变化、订单成交、仓位关闭）
        level_id: 级别标识
        old_state: 旧状态（可选）
        new_state: 新状态（可选）
        data: 附加事件数据
    """

    event_type: str
    level_id: str
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GridEventManager:
    """网格事件管理器，负责事件监听和异步分发"""

    listeners: Dict[str, List[Callable]] = field(default_factory=lambda: defaultdict(list))

    def add_listener(self, event_type: str, callback: Callable):
        """添加事件监听器"""
        self.listeners[event_type].append(callback)

    def remove_listener(self, event_type: str, callback: Callable):
        """移除事件监听器"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)

    async def emit_event(self, event: GridStateEvent) -> None:
        """异步发送事件给所有监听器"""
        if event.event_type in self.listeners:
            for callback in self.listeners[event.event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger = get_global_logger()
                    logger.error(f"事件处理错误: {str(e)}")


class FlexibleGridLevelStates(Enum):
    """灵活网格级别状态"""

    WAITING_PREV_OPEN = "waiting_prev_open"
    WAITING_OP_ACTIVE = "waiting_op_active"
    WAITING_OP_REBOUND = "waiting_op_rebound"
    OPEN_ORDER_PLACED = "open_order_placed"
    OPEN_ORDER_FILLED = "open_order_filled"
    WAITING_TP_ACTIVE = "waiting_tp_active"
    WAITING_TP_REBOUND = "waiting_tp_rebound"
    CLOSE_ORDER_PLACED = "close_order_placed"
    CLOSE_ORDER_FILLED = "close_order_filled"
    WAITING_NEXT_CLOSE = "waiting_next_close"
    COMPLETED = "completed"
    FAILED = "failed"


class FlexibleGridExecutorConfig(ExecutorConfigBase):
    """灵活网格执行器配置，定义执行器的整体参数"""

    type: Literal["flexible_grid_executor"] = "flexible_grid_executor"
    id: str
    timestamp: float
    connector_name: str
    trading_pair: str
    side: TradeType
    n_levels: int = Field(default=..., description="网格级别数量")
    position_mode: PositionMode = PositionMode.HEDGE

    # 投资模式
    investment_mode: Literal["amount_quote", "amount_base"] = Field(
        default="amount_quote",
        description="投资模式 - amount_quote: 按报价货币金额投资; amount_base: 按基础货币数量投资",
    )

    # 每层级配置
    amount_quote: List[Decimal] = Field(
        default_factory=list, description="每个级别的投资金额（报价货币）- 在amount_quote模式下使用"
    )
    amount_base: List[Decimal] = Field(
        default_factory=list, description="每个级别的投资数量（基础货币）- 在amount_base模式下使用"
    )
    open_ratios: List[Decimal] = Field(default_factory=list, description="每个级别的开仓价格比率")
    take_profit_ratios: List[Decimal] = Field(default_factory=list, description="每个级别的止盈比率")
    stop_loss_ratios: List[Decimal] = Field(default_factory=list, description="每个级别的止损比率")
    open_rebound_ratios: List[Decimal] = Field(default_factory=list, description="每个级别的开仓反弹比率")
    take_profit_rebound_ratios: List[Decimal] = Field(default_factory=list, description="每个级别的止盈反弹比率")
    max_open_orders: int = Field(default=3, description="最大挂单数量")
    order_frequency: float = Field(default=1.0, description="订单更新频率（秒）")
    leverage: int = 1
    keep_position: bool = Field(default=False, description="停止时是否保持仓位")

    # 全局风控配置
    take_profit: Decimal = Field(
        default=Decimal("1.0"), description="全局止盈价格比率 - 当市场价格达到平均持仓成本的(1±take_profit)倍时触发"
    )
    stop_loss: Decimal = Field(
        default=Decimal("1.0"), description="全局止损价格比率 - 当市场价格达到平均持仓成本的(1±stop_loss)倍时触发"
    )
    profit_target_amount: Optional[Decimal] = Field(
        default=None, description="全局止盈目标金额 - 当总盈利达到此金额时触发，0或None表示不启用"
    )
    loss_target_amount: Optional[Decimal] = Field(
        default=None, description="全局止损目标金额 - 当总亏损达到此金额时触发，0或None表示不启用"
    )
    time_limit: int = None
    min_levels_for_global_barriers: int = 2

    # 层级重复开仓设置
    min_reopen_interval: int = Field(default=10, description="重新开启级别的最小间隔（秒）")
    first_level_open: bool = Field(default=True, description="是否立即开启第一级别")

    model_config = {"arbitrary_types_allowed": True}

    def validate_model(self):
        """验证模型的完整性和一致性"""
        super().validate_model()
        # 验证层级和配置列表长度一致性
        if len(self.open_ratios) != self.n_levels:
            raise ValueError(f"开仓比率列表长度 ({len(self.open_ratios)}) 与网格级别数 ({self.n_levels}) 不匹配")
        if len(self.take_profit_ratios) != self.n_levels:
            raise ValueError(f"止盈比率列表长度 ({len(self.take_profit_ratios)}) 与网格级别数 ({self.n_levels}) 不匹配")
        if len(self.stop_loss_ratios) != self.n_levels:
            raise ValueError(f"止损比率列表长度 ({len(self.stop_loss_ratios)}) 与网格级别数 ({self.n_levels}) 不匹配")
        if len(self.open_rebound_ratios) != self.n_levels:
            raise ValueError(
                f"开仓反弹比率列表长度 ({len(self.open_rebound_ratios)}) 与网格级别数 ({self.n_levels}) 不匹配"
            )
        if len(self.take_profit_rebound_ratios) != self.n_levels:
            raise ValueError(
                f"止盈反弹比率列表长度 ({len(self.take_profit_rebound_ratios)}) 与网格级别数 ({self.n_levels}) 不匹配"
            )

        # 根据投资模式检查相应列表
        if self.investment_mode == "amount_quote":
            if len(self.amount_quote) != self.n_levels:
                raise ValueError(f"投资金额列表长度 ({len(self.amount_quote)}) 与网格级别数 ({self.n_levels}) 不匹配")
        else:  # amount_base模式
            if len(self.amount_base) != self.n_levels:
                raise ValueError(f"投资数量列表长度 ({len(self.amount_base)}) 与网格级别数 ({self.n_levels}) 不匹配")

    def to_dict(self) -> Dict:
        """转换为字典

        Returns:
            Dict: 包含所有相关配置的字典
        """
        result = {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "connector_name": self.connector_name,
            "trading_pair": self.trading_pair,
            "side": self.side.name,
            "n_levels": self.n_levels,
            "position_mode": self.position_mode.name,
            "investment_mode": self.investment_mode,
            "open_ratios": [str(r) for r in self.open_ratios],
            "take_profit_ratios": [str(r) for r in self.take_profit_ratios],
            "stop_loss_ratios": [str(r) for r in self.stop_loss_ratios],
            "open_rebound_ratios": [str(r) for r in self.open_rebound_ratios],
            "take_profit_rebound_ratios": [str(r) for r in self.take_profit_rebound_ratios],
            "max_open_orders": self.max_open_orders,
            "order_frequency": self.order_frequency,
            "leverage": self.leverage,
            "keep_position": self.keep_position,
            "take_profit": str(self.take_profit),
            "stop_loss": str(self.stop_loss),
            "min_levels_for_global_barriers": self.min_levels_for_global_barriers,
            "min_reopen_interval": self.min_reopen_interval,
            "first_level_open": self.first_level_open,
        }

        # 根据投资模式添加相应字段
        if self.investment_mode == "amount_quote":
            result["amount_quote"] = [str(a) for a in self.amount_quote]
        else:  # amount_base模式
            result["amount_base"] = [str(a) for a in self.amount_base]

        # 添加可选字段
        if self.time_limit is not None:
            result["time_limit"] = self.time_limit

        # 处理profit_target_amount: None或0表示不启用
        if self.profit_target_amount is not None and self.profit_target_amount > Decimal("0"):
            result["profit_target_amount"] = str(self.profit_target_amount)

        # 处理loss_target_amount: None或0表示不启用
        if self.loss_target_amount is not None and self.loss_target_amount > Decimal("0"):
            result["loss_target_amount"] = str(self.loss_target_amount)

        return result

    @classmethod
    def logger(cls) -> HummingbotLogger:
        """获取全局日志器"""
        return get_global_logger()


@dataclass
class FlexibleGridLevel:
    """灵活网格层级，管理单个网格级别的状态和执行器生命周期"""

    # 基本信息
    index: int
    id: str
    side: TradeType

    # 层级配置
    open_ratio: Decimal
    take_profit_ratio: Decimal
    stop_loss_ratio: Decimal
    open_rebound_ratio: Decimal
    take_profit_rebound_ratio: Decimal

    # 默认值参数
    amount_quote: Decimal = Decimal("0")  # 投资金额（报价货币）
    amount_base: Decimal = Decimal("0")  # 投资数量（基础货币）

    # 价格状态
    current_price: Decimal = Decimal("0")
    active_op_price: Decimal = Decimal("0")
    trigger_op_price: Decimal = Decimal("0")
    active_tp_price: Decimal = Decimal("0")
    trigger_tp_price: Decimal = Decimal("0")
    highest_price: Decimal = Decimal("0")
    lowest_price: Decimal = Decimal("0")
    last_open_price: Decimal = Decimal("0")
    last_close_price: Decimal = Decimal("0")

    # 时间戳
    level_activation_timestamp: float = field(default_factory=time.time)
    last_update_timestamp: float = field(default_factory=time.time)
    last_closed_timestamp: float = 0.0
    last_order_timestamp: float = 0.0
    last_open_timestamp: float = 0.0

    # 状态管理
    current_state: FlexibleGridLevelStates = FlexibleGridLevelStates.WAITING_PREV_OPEN
    previous_state: Optional[FlexibleGridLevelStates] = None
    state_change_timestamp: float = field(default_factory=time.time)

    # 执行器关联
    executor: Optional[PositionExecutor] = None
    activation_history: List[Dict] = field(default_factory=list)

    # 性能统计
    total_net_pnl_quote: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    win_count: int = 0
    loss_count: int = 0

    # 管理器关联
    manager: "FlexibleGridManager" = field(default=None)

    # 新增属性
    order_history: List[Dict] = field(default_factory=list)
    state_history: List[Dict] = field(default_factory=list)

    @classmethod
    def logger(cls) -> HummingbotLogger:
        """获取全局日志器"""
        return get_global_logger()

    def on_order_filled(self, event: OrderFilledEvent) -> None:
        """处理订单成交事件，更新数据和记录订单信息，但不更新状态"""
        logger = self.logger()
        logger.debug(f"处理订单成交: 级别={self.id}, 订单ID={event.order_id}")

        self.last_order_timestamp = event.timestamp

        try:
            # 记录价格极值和当前价格
            self.update_price_extremes(event.price)

            # 记录订单信息
            self._record_order(event)

            # 发送订单成交事件
            self._emit_order_filled_event(event)

            logger.debug(f"订单成交数据处理完成: 级别={self.id}, 状态={self.current_state.value}")
        except Exception as e:
            logger.error(f"处理订单成交时出错: 级别={self.id}, 错误: {str(e)}", exc_info=True)

    def _record_order(self, event: OrderFilledEvent) -> None:
        """记录订单信息，确保保存所有 OrderFilledEvent 字段

        Args:
            event: OrderFilledEvent 对象，包含订单成交的完整信息
        """
        self.order_history.append(
            {
                # 基本订单信息
                "timestamp": event.timestamp,
                "order_id": event.order_id,
                "trading_pair": event.trading_pair,
                # 交易类型和订单类型
                "trade_type": event.trade_type.name,
                "order_type": event.order_type.name,
                # 价格和数量
                "price": str(event.price),
                "amount": str(event.amount),
                # 交易所相关信息
                "exchange_trade_id": event.exchange_trade_id,
                "exchange_order_id": event.exchange_order_id,
                # 杠杆和仓位信息
                "leverage": event.leverage,
                "position": event.position,
                # 手续费信息
                "trade_fee": event.trade_fee.to_json() if event.trade_fee else None,
            }
        )

    def _emit_order_filled_event(self, event: OrderFilledEvent) -> None:
        """发送订单成交事件"""
        if self.manager and self.manager.event_manager:
            grid_event = GridStateEvent(
                event_type="order_filled",
                level_id=self.id,
                old_state=self.previous_state.value if self.previous_state else None,
                new_state=self.current_state.value,
                data={"order": event},
            )
            asyncio.create_task(self.manager.event_manager.emit_event(grid_event))

    def record_close(
        self, exit_price: Decimal, pnl: Decimal, fees: Decimal = Decimal("0"), order_id: Optional[str] = None
    ) -> None:
        """记录平仓信息"""
        logger = self.logger()
        logger.debug(f"记录平仓: 级别={self.id}, 退出价格={exit_price}, 盈亏={pnl}, 费用={fees}")
        self.last_closed_timestamp = time.time()
        self.last_close_price = exit_price
        self.total_net_pnl_quote += pnl
        self.total_fees += fees
        if pnl > 0:
            self.win_count += 1
        elif pnl < 0:
            self.loss_count += 1

        # 添加新记录到 activation_history
        self.activation_history.append(
            {
                "closed_timestamp": self.last_closed_timestamp,
                "exit_price": str(exit_price),
                "close_order_id": order_id,
                "pnl": str(pnl),
                "fees": str(fees),
                "final_state": self.current_state.value,
            }
        )

        logger.debug(f"平仓记录完成: 级别={self.id}, 总盈亏={self.total_net_pnl_quote}")

    def create_executor(self, strategy, connector_name: str, trading_pair: str, leverage: int) -> PositionExecutor:
        """创建并关联 PositionExecutor，确保正确设置交易方向

        对于做多(side=TradeType.BUY):
            - 开仓是买单(BUY)
            - 平仓是卖单(SELL)
        对于做空(side=TradeType.SELL):
            - 开仓是卖单(SELL)
            - 平仓是买单(BUY)
        """
        logger = self.logger()
        logger.debug(f"创建执行器: 级别={self.id}, 交易对={trading_pair}, 方向={self.side.name}")

        # 更严格地检查执行器是否存在且活跃，避免重复创建
        if self.executor is not None:
            # 检查executor是否为None和is_active属性
            if hasattr(self.executor, "is_active") and self.executor.is_active:
                logger.error(f"级别 {self.id} 已有关联的活跃执行器")
                raise ValueError(f"层级 {self.id} 已有关联的活跃执行器")
            else:
                # 如果执行器存在但不活跃，先清理它
                logger.info(f"级别 {self.id} 存在不活跃执行器，进行清理")
                old_executor_id = self.executor.config.id if hasattr(self.executor, "config") else "未知"
                self.executor = None
                logger.debug(f"清理级别 {self.id} 旧执行器 {old_executor_id}")
                if self.manager:
                    self.manager._clear_level_order_mappings(self.id)

        executor_id = f"pe_{self.id}_{uuid.uuid4().hex[:8]}"

        # 根据投资模式计算下单金额
        if self.manager.config.investment_mode == "amount_quote":
            # 按报价货币金额计算基础货币数量
            order_amount = self.amount_quote / self.current_price
        else:  # amount_base模式
            # 直接使用基础货币数量
            order_amount = self.amount_base

        config = PositionExecutorConfig(
            id=executor_id,
            timestamp=time.time(),
            connector_name=connector_name,
            trading_pair=trading_pair,
            side=self.side,  # 使用级别的交易方向
            amount=order_amount,
            entry_price=self.current_price,
            leverage=leverage,
            level_id=self.id,
            triple_barrier_config=TripleBarrierConfig(
                trailing_stop=None,
                take_profit=self.take_profit_ratio,
                stop_loss=self.stop_loss_ratio,
                time_limit=None,
                open_order_type=OrderType.MARKET,
                take_profit_order_type=OrderType.MARKET,
                stop_loss_order_type=OrderType.MARKET,
                time_limit_order_type=OrderType.MARKET,
            ),
        )
        self.executor = PositionExecutor(strategy=strategy, config=config)
        logger.debug(
            f"执行器创建成功: 执行器ID={executor_id}, 方向={self.side.name}, "
            f"数量={order_amount}, 入场价格={self.current_price}"
        )
        return self.executor

    def early_stop(self, keep_position: bool = False) -> None:
        """强制提前平仓"""
        logger = self.logger()
        logger.debug(f"提前平仓: 级别={self.id}, 保留仓位={keep_position}")
        if self.executor:
            self.executor.early_stop(keep_position)
            logger.debug(f"级别 {self.id} 已发起提前平仓")

    async def control_task(self) -> None:
        """执行执行器的控制逻辑"""
        logger = self.logger()
        logger.debug(f"执行控制任务: 级别={self.id}, 状态={self.current_state.value}")
        if self.executor:
            await self.executor.control_task()

    @property
    def is_trading(self) -> bool:
        """检查是否正在持仓"""
        return self.executor.is_trading if self.executor else False

    @property
    def is_closed(self) -> bool:
        """检查是否已完成平仓"""
        return self.executor.is_closed if self.executor else False

    @property
    def net_pnl_pct(self) -> Decimal:
        """获取当前净盈亏百分比"""
        return self.executor.net_pnl_pct if self.executor else Decimal("0")

    @property
    def net_pnl_quote(self) -> Decimal:
        """获取当前净盈亏（报价货币）"""
        return self.executor.net_pnl_quote if self.executor else Decimal("0")

    @property
    def cum_fees_quote(self) -> Decimal:
        """获取累计费用（报价货币）"""
        return self.executor.cum_fees_quote if self.executor else Decimal("0")

    @property
    def win_rate(self) -> float:
        """计算胜率"""
        total_trades = self.win_count + self.loss_count
        return float(self.win_count) / total_trades if total_trades > 0 else 0.0

    @property
    def average_pnl(self) -> Decimal:
        """计算平均收益"""
        total_trades = self.win_count + self.loss_count
        return self.total_net_pnl_quote / Decimal(total_trades) if total_trades > 0 else Decimal("0")

    def stop_executor(self, keep_position: bool = False) -> None:
        """停止当前执行器并清理资源"""
        logger = self.logger()
        logger.debug(f"停止执行器: 级别={self.id}, 保留仓位={keep_position}")

        if not self.executor:
            logger.debug(f"级别 {self.id} 无执行器，无需停止")
            return

        try:
            # 先停止执行器
            if self.is_pe_active:
                self.executor.early_stop(keep_position=keep_position)

                # 等待最后的状态更新
                if self.current_state in [
                    FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                    FlexibleGridLevelStates.WAITING_TP_REBOUND,
                ]:
                    self.update_state(FlexibleGridLevelStates.CLOSE_ORDER_PLACED)

            # 确保清理资源
            if self.manager:
                self.manager._clear_level_order_mappings(self.id)

            # 清理执行器
            self.executor = None
            logger.debug(f"级别 {self.id} 执行器已停止并清理")
        except Exception as e:
            logger.error(f"停止执行器时出错: {str(e)}", exc_info=True)
            # 即使发生错误，也尝试清理资源
            self.executor = None
            if self.manager:
                self.manager._clear_level_order_mappings(self.id)

    def reset_for_reactivation(self) -> None:
        logger = self.logger()
        logger.debug(f"重置级别以重新激活: 级别={self.id}")

        # 停止并清理当前执行器
        if self.executor:
            # 清理所有与该执行器相关的订单映射
            if self.manager:
                self.manager._clear_level_order_mappings(self.id)
            self.stop_executor(keep_position=False)

        # 重置其他状态
        self.previous_state = None
        self.reset_price_extremes()
        self.last_order_timestamp = 0
        self.last_open_timestamp = 0
        logger.debug(f"级别 {self.id} 已重置完成")

    def cleanup(self) -> None:
        """完全清理级别的所有资源"""
        logger = self.logger()
        logger.debug(f"清理级别资源: 级别={self.id}")

        try:
            # 停止执行器
            if self.executor:
                self.stop_executor(keep_position=False)

            # 清理事件监听器
            if self.manager and self.manager.event_manager:
                self.manager = None

            # 清理数据
            self.order_history.clear()
            self.state_history.clear()
            self.activation_history.clear()

            logger.debug(f"级别 {self.id} 资源清理完成")
        except Exception as e:
            logger.error(f"清理级别资源时出错: {str(e)}", exc_info=True)

    def update_state(self, new_state: FlexibleGridLevelStates) -> None:
        logger = self.logger()
        logger.debug(f"尝试更新状态: 级别={self.id}, 当前={self.current_state.value}, 新={new_state.value}")
        if self.current_state == new_state:
            logger.debug(f"状态未变化，跳过更新: 级别={self.id}, 状态={new_state.value}")
            return
        if self.validate_state_transition(new_state):
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_change_timestamp = time.time()
            self.state_history.append(
                {
                    "timestamp": self.state_change_timestamp,
                    "old_state": self.previous_state.value,
                    "new_state": new_state.value,
                    "price": str(self.current_price),
                }
            )
            logger.info(f"状态更新成功: 从 {self.previous_state.value} 到 {new_state.value}")
            self.manager._emit_event("state_changed", self.id, {"new_state": new_state.value})
        else:
            logger.error(
                f"状态更新失败: 级别={self.id}, 当前={self.current_state.value}, 目标={new_state.value}, "
                f"调用栈=\n{''.join(traceback.format_stack(limit=10))}"
            )

    def _validate_and_update_state(self, new_state: FlexibleGridLevelStates) -> bool:
        """验证并更新状态

        Args:
            new_state: 新的状态

        Returns:
            bool: 是否成功更新状态
        """
        logger = self.logger()
        logger.debug(f"验证状态转换: 级别={self.id}, 当前={self.current_state.value}, 新={new_state.value}")

        # 验证状态转换
        if not self.validate_state_transition(new_state):
            logger.error(f"非法状态转换: {self.current_state.value} -> {new_state.value}")
            return False

        # 特殊状态检查
        if new_state == FlexibleGridLevelStates.OPEN_ORDER_FILLED:
            if not self.executor:
                logger.warning(f"无法更新到 OPEN_ORDER_FILLED: 执行器不存在")
                return False
        elif new_state == FlexibleGridLevelStates.CLOSE_ORDER_FILLED:
            if not self.executor:
                logger.warning(f"无法更新到 CLOSE_ORDER_FILLED: 执行器不存在")
                return False

        # 更新状态
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_change_timestamp = time.time()
        logger.debug(f"状态更新成功: 级别={self.id}, 从 {self.previous_state.value} 到 {new_state.value}")
        return True

    def _emit_state_change_event(self, new_state: FlexibleGridLevelStates) -> None:
        """发送状态变更事件"""
        if self.manager and self.manager.event_manager:
            event = GridStateEvent(
                event_type="state_change",
                level_id=self.id,
                old_state=self.previous_state.value,
                new_state=new_state.value,
                data={
                    "last_open_price": str(self.last_open_price),
                    "last_order_timestamp": self.last_order_timestamp,
                    "current_price": str(self.current_price),
                },
            )
            asyncio.create_task(self.manager.event_manager.emit_event(event))

    def update_price_extremes(self, price: Decimal) -> None:
        """更新价格极值，包含价格验证和日志记录"""
        logger = self.logger()
        if price <= 0 or price != price:  # 检查无效价格和 NaN
            logger.warning(f"无效价格: 级别={self.id}, 价格={price}")
            return

        # 记录更新前的极值，用于日志
        old_highest = self.highest_price
        old_lowest = self.lowest_price

        # 更新极值
        if price > self.highest_price or self.highest_price == Decimal("0"):
            self.highest_price = price
            logger.debug(f"更新最高价: 级别={self.id}, 旧={old_highest}, 新={price}")
        if price < self.lowest_price or self.lowest_price == Decimal("0"):
            self.lowest_price = price
            logger.debug(f"更新最低价: 级别={self.id}, 旧={old_lowest}, 新={price}")

        self.current_price = price
        self.last_update_timestamp = time.time()

    def reset_price_extremes(self) -> None:
        """重置价格极值"""
        self.highest_price = Decimal("0")
        self.lowest_price = Decimal("0")

    def _record_state_change(self, old_state: FlexibleGridLevelStates, new_state: FlexibleGridLevelStates):
        """记录状态变化"""
        self.state_history.append(
            {
                "timestamp": time.time(),
                "old_state": old_state.value,
                "new_state": new_state.value,
                "price": str(self.current_price),
            }
        )

    def validate_state_transition(self, new_state: FlexibleGridLevelStates) -> bool:
        valid_transitions = {
            FlexibleGridLevelStates.WAITING_PREV_OPEN: [
                FlexibleGridLevelStates.WAITING_OP_ACTIVE,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.WAITING_OP_ACTIVE: [
                FlexibleGridLevelStates.WAITING_PREV_OPEN,
                FlexibleGridLevelStates.WAITING_OP_REBOUND,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.WAITING_OP_REBOUND: [
                FlexibleGridLevelStates.OPEN_ORDER_PLACED,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.OPEN_ORDER_PLACED: [
                FlexibleGridLevelStates.OPEN_ORDER_FILLED,
                FlexibleGridLevelStates.WAITING_OP_REBOUND,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.OPEN_ORDER_FILLED: [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.WAITING_TP_ACTIVE: [
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
                FlexibleGridLevelStates.WAITING_NEXT_CLOSE,
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
                FlexibleGridLevelStates.CLOSE_ORDER_FILLED,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.WAITING_TP_REBOUND: [
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.CLOSE_ORDER_PLACED: [
                FlexibleGridLevelStates.CLOSE_ORDER_FILLED,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.CLOSE_ORDER_FILLED: [
                FlexibleGridLevelStates.COMPLETED,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.WAITING_NEXT_CLOSE: [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.FAILED,
            ],
            FlexibleGridLevelStates.COMPLETED: [
                FlexibleGridLevelStates.WAITING_PREV_OPEN,
            ],
        }
        logger = self.logger()

        # 特殊处理第一层级
        if self.index == 0:
            # 如果第一层级已经是COMPLETE状态，不允许任何状态转换
            if self.current_state == FlexibleGridLevelStates.COMPLETED:
                logger.warning(f"第一级别 {self.id} 已完成，不允许任何状态转换")
                return False

        is_valid = new_state in valid_transitions.get(self.current_state, [])
        if not is_valid:
            logger.error(
                f"非法状态转换: {self.current_state.value} -> {new_state.value}, "
                f"允许的转换: {[s.value for s in valid_transitions.get(self.current_state, [])]}"
            )
        return is_valid

    @property
    def is_level_active(self) -> bool:
        """检查级别是否处于活跃状态"""
        active_states = [
            FlexibleGridLevelStates.WAITING_OP_ACTIVE,
            FlexibleGridLevelStates.WAITING_OP_REBOUND,
            FlexibleGridLevelStates.OPEN_ORDER_PLACED,
            FlexibleGridLevelStates.OPEN_ORDER_FILLED,
            FlexibleGridLevelStates.WAITING_TP_ACTIVE,
            FlexibleGridLevelStates.WAITING_TP_REBOUND,
            FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
        ]
        return self.current_state in active_states

    @property
    def is_pe_active(self) -> bool:
        """检查执行器是否处于活跃状态"""
        return self.executor is not None and self.executor.is_active

    def to_format_status(self) -> str:
        """返回格式化的级别状态信息

        Returns:
            str: 格式化后的状态字符串
        """
        logger = self.logger()
        logger.debug(f"生成级别状态: 级别={self.id}")

        # 获取基本信息
        state_desc = (
            self._get_state_description() if hasattr(self, "_get_state_description") else self.current_state.value
        )

        # 计算盈亏和持仓信息
        if self.is_trading and self.executor:
            net_pnl = self.net_pnl_quote
            net_pnl_pct = self.net_pnl_pct * 100
            pnl_str = f"{net_pnl:.6f} ({net_pnl_pct:.2f}%)"

            amount_base = self.executor.open_filled_amount
            entry_price = self.last_open_price if self.last_open_price else Decimal("0")
            current_price = self.current_price if self.current_price else Decimal("0")
            price_change_pct = ((current_price / entry_price) - 1) * 100 if entry_price else Decimal("0")

            # 根据多空方向调整价格变化
            if self.side == TradeType.SELL:
                price_change_pct = -price_change_pct

            position_str = f"持仓: {amount_base:.6f} @ {entry_price:.6f}"
            price_str = f"当前: {current_price:.6f} ({price_change_pct:.2f}%)"

            # 执行器状态
            executor_status = self.executor.status if hasattr(self.executor, "status") else "未知"
            executor_id = self.executor.config.id[-8:] if hasattr(self.executor, "config") else "无ID"

            # 获取执行器的手续费和报价货币
            cum_fees = self.executor.get_cum_fees_quote() if self.executor else Decimal("0")
            quote_asset = self.side.name if isinstance(self.side, TradeType) else str(self.side)
            if "-" in self.manager.config.trading_pair:
                quote_asset = self.manager.config.trading_pair.split("-")[1]
        else:
            pnl_str = "无持仓"
            position_str = "未开仓"
            price_str = f"当前: {self.current_price:.6f}"
            executor_status = "无执行器"
            executor_id = "N/A"
            cum_fees = Decimal("0")
            quote_asset = ""

        # 历史统计
        if self.win_count or self.loss_count:
            total_trades = self.win_count + self.loss_count
            win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
            history_str = (
                f"历史: {self.win_count}胜/{self.loss_count}负 ({win_rate:.1f}%), 盈亏: {self.total_net_pnl_quote:.6f}"
            )
        else:
            history_str = "无交易历史"

        # 计算下一步条件
        next_action_str = self._get_next_action_info()

        # 构建状态输出
        lines = [
            f"┌─────────────────── 级别 {self.index} ({self.id[:8]}...) ───────────────────┐",
            f"│ 状态: {self.current_state.value:<15} 描述: {state_desc:<25} │",
            f"│ {position_str:<35} {price_str:<25} │",
            f"│ 盈亏: {pnl_str:<50} │",
            f"│ 执行器: {executor_id} 状态: {executor_status:<24} │",
        ]

        # 添加PE执行器的详细信息
        if self.is_trading and self.executor:
            # 提取PE执行器的详细信息
            tp_ratio = (
                self.executor.config.triple_barrier_config.take_profit * 100
                if hasattr(self.executor.config, "triple_barrier_config")
                else 0
            )
            sl_ratio = (
                self.executor.config.triple_barrier_config.stop_loss * 100
                if hasattr(self.executor.config, "triple_barrier_config")
                else 0
            )
            take_profit_price = (
                (
                    entry_price * (1 + self.executor.config.triple_barrier_config.take_profit)
                    if self.side == TradeType.BUY
                    else entry_price * (1 - self.executor.config.triple_barrier_config.take_profit)
                )
                if hasattr(self.executor.config, "triple_barrier_config")
                else Decimal("0")
            )

            stop_loss_price = (
                (
                    entry_price * (1 - self.executor.config.triple_barrier_config.stop_loss)
                    if self.side == TradeType.BUY
                    else entry_price * (1 + self.executor.config.triple_barrier_config.stop_loss)
                )
                if hasattr(self.executor.config, "triple_barrier_config")
                else Decimal("0")
            )

            lines.extend(
                [
                    f"│ 止盈/止损: {tp_ratio:.2f}% / {sl_ratio:.2f}% │ 止盈价: {take_profit_price:.6f} │ 止损价: {stop_loss_price:.6f} │",
                    f"│ 手续费: {cum_fees:.6f} {quote_asset:<5} │ 开仓时间: {datetime.fromtimestamp(self.last_open_timestamp).strftime('%Y-%m-%d %H:%M:%S') if self.last_open_timestamp else '未记录'} │",
                ]
            )

        lines.extend(
            [
                f"│ {history_str:<62} │",
            ]
        )

        if next_action_str:
            lines.append(f"│ {next_action_str:<62} │")

        lines.append("└────────────────────────────────────────────────────────────┘")

        return "\n".join(lines)

    def _get_next_action_info(self) -> str:
        """获取下一步操作的相关信息"""
        if self.current_state == FlexibleGridLevelStates.WAITING_OP_ACTIVE:
            target_price = self.active_op_price
            current = self.current_price
            if target_price and current:
                diff_pct = abs((current - target_price) / current * 100)
                direction = "下跌" if self.side == TradeType.BUY else "上涨"
                return f"开仓激活条件: 价格{direction}至 {target_price:.6f} (还需{diff_pct:.2f}%)"

        elif self.current_state == FlexibleGridLevelStates.WAITING_TP_ACTIVE:
            if self.is_trading and self.last_open_price:
                if self.side == TradeType.BUY:
                    tp_price = self.last_open_price * (1 + self.take_profit_ratio)
                    direction = "上涨"
                else:
                    tp_price = self.last_open_price * (1 - self.take_profit_ratio)
                    direction = "下跌"

                diff_pct = abs((self.current_price - tp_price) / self.current_price * 100)
                return f"止盈激活条件: 价格{direction}至 {tp_price:.6f} (还需{diff_pct:.2f}%)"

        elif self.current_state == FlexibleGridLevelStates.WAITING_OP_REBOUND:
            if self.side == TradeType.BUY and self.lowest_price:
                trigger_price = self.lowest_price * (1 + self.open_rebound_ratio)
                diff_pct = abs((self.current_price - trigger_price) / self.current_price * 100)
                if self.current_price < trigger_price:
                    return f"开仓反弹条件: 价格上涨至 {trigger_price:.6f} (还需{diff_pct:.2f}%)"
            elif self.side == TradeType.SELL and self.highest_price:
                trigger_price = self.highest_price * (1 - self.open_rebound_ratio)
                diff_pct = abs((self.current_price - trigger_price) / self.current_price * 100)
                if self.current_price > trigger_price:
                    return f"开仓反弹条件: 价格下跌至 {trigger_price:.6f} (还需{diff_pct:.2f}%)"

        elif self.current_state == FlexibleGridLevelStates.WAITING_TP_REBOUND:
            if self.side == TradeType.BUY and self.highest_price:
                trigger_price = self.highest_price * (1 - self.take_profit_rebound_ratio)
                diff_pct = abs((self.current_price - trigger_price) / self.current_price * 100)
                if self.current_price > trigger_price:
                    return f"止盈回落条件: 价格下跌至 {trigger_price:.6f} (还需{diff_pct:.2f}%)"
            elif self.side == TradeType.SELL and self.lowest_price:
                trigger_price = self.lowest_price * (1 + self.take_profit_rebound_ratio)
                diff_pct = abs((self.current_price - trigger_price) / self.current_price * 100)
                if self.current_price < trigger_price:
                    return f"止盈反弹条件: 价格上涨至 {trigger_price:.6f} (还需{diff_pct:.2f}%)"

        return ""

    def _get_state_description(self) -> str:
        """获取当前状态的人类可读描述"""
        descriptions = {
            FlexibleGridLevelStates.WAITING_PREV_OPEN: "等待前一级开仓",
            FlexibleGridLevelStates.WAITING_OP_ACTIVE: "等待激活开仓",
            FlexibleGridLevelStates.WAITING_OP_REBOUND: "等待回弹开仓",
            FlexibleGridLevelStates.OPEN_ORDER_PLACED: "开仓单已下",
            FlexibleGridLevelStates.OPEN_ORDER_FILLED: "开仓单已成交",
            FlexibleGridLevelStates.WAITING_TP_ACTIVE: "等待止盈激活",
            FlexibleGridLevelStates.WAITING_TP_REBOUND: "等待止盈回落",
            FlexibleGridLevelStates.CLOSE_ORDER_PLACED: "平仓单已下",
            FlexibleGridLevelStates.CLOSE_ORDER_FILLED: "平仓单已成交",
            FlexibleGridLevelStates.WAITING_NEXT_CLOSE: "等待后一级止盈",
            FlexibleGridLevelStates.COMPLETED: "交易已完成",
            FlexibleGridLevelStates.FAILED: "交易失败",
        }
        return descriptions.get(self.current_state, "未知状态")

    def _find_level_for_new_order(self, price: Decimal) -> Optional["FlexibleGridLevel"]:
        """根据当前活跃状态和执行器状态查找对应的级别

        对于做多(side=TradeType.BUY):
            - 开仓是买单(BUY)，等待状态为 WAITING_OP_REBOUND
            - 平仓是卖单(SELL)，等待状态为 WAITING_TP_ACTIVE, WAITING_TP_REBOUND
        对于做空(side=TradeType.SELL):
            - 开仓是卖单(SELL)，等待状态为 WAITING_OP_REBOUND
            - 平仓是买单(BUY)，等待状态为 WAITING_TP_ACTIVE, WAITING_TP_REBOUND
        """
        logger = self.logger()
        logger.debug("查找新订单对应的级别")

        # 遍历所有级别，查找符合条件的级别
        for level in self.levels:
            # 检查级别状态
            if level.executor and level.executor.is_active:
                # 检查是否为开仓状态
                if level.current_state in [
                    FlexibleGridLevelStates.WAITING_OP_REBOUND,
                    FlexibleGridLevelStates.OPEN_ORDER_PLACED,
                ]:
                    if not level.executor.is_trading:
                        logger.debug(f"找到准备开仓的级别: {level.id}, 方向={self.config.side.name}")
                        return level

                # 检查是否为平仓状态
                elif level.current_state in [
                    FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                    FlexibleGridLevelStates.WAITING_TP_REBOUND,
                    FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
                ]:
                    if level.executor.is_trading:
                        logger.debug(f"找到准备平仓的级别: {level.id}, 方向={self.config.side.name}")
                        return level

            # 检查等待开仓状态
            elif level.current_state == FlexibleGridLevelStates.WAITING_OP_REBOUND:
                logger.debug(f"找到等待创建执行器的级别: {level.id}, 方向={self.config.side.name}")
                return level

        logger.debug(f"未找到合适的级别处理新订单，方向={self.config.side.name}")
        return None

    def _emit_event(self, event_type: str, level_id: str, data: Dict[str, Any]):
        """发送事件"""
        if self.event_manager:
            event = GridStateEvent(event_type=event_type, level_id=level_id, data=data)
            asyncio.create_task(self.event_manager.emit_event(event))

    def to_dict(self) -> Dict:
        """获取级别的字典表示"""
        result = {
            "index": self.index,
            "id": self.id,
            "side": self.side.name,
            "state": self.current_state.value,
            "is_level_active": self.is_level_active,
            "is_pe_active": self.is_pe_active,
            "open_ratio": str(self.open_ratio),
            "take_profit_ratio": str(self.take_profit_ratio),
            "stop_loss_ratio": str(self.stop_loss_ratio),
            "open_rebound_ratio": str(self.open_rebound_ratio),
            "take_profit_rebound_ratio": str(self.take_profit_rebound_ratio),
            "current_price": str(self.current_price),
            "last_open_price": str(self.last_open_price) if self.last_open_price else None,
            "last_close_price": str(self.last_close_price) if self.last_close_price else None,
            "last_open_timestamp": self.last_open_timestamp,
            "last_closed_timestamp": self.last_closed_timestamp,
            "net_pnl_quote": str(self.net_pnl_quote),
            "total_net_pnl_quote": str(self.total_net_pnl_quote),
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.win_rate,
        }

        # 根据投资模式设置相应字段
        if self.manager and self.manager.config.investment_mode == "amount_quote":
            result["amount_quote"] = str(self.amount_quote)
        else:  # amount_base模式
            result["amount_base"] = str(self.amount_base)

        if self.executor:
            result["executor_id"] = self.executor.config.id
            result["executor_status"] = self.executor.status
        return result

    def _validate_tp_state_transition(self, level: "FlexibleGridLevel", new_state: FlexibleGridLevelStates) -> bool:
        """验证止盈相关的状态转换"""
        valid_transitions = {
            FlexibleGridLevelStates.WAITING_TP_ACTIVE: [
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
            ],
            FlexibleGridLevelStates.WAITING_TP_REBOUND: [
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
            ],
        }
        return new_state in valid_transitions.get(level.current_state, [])

    def get_tp_activation_price(self) -> Decimal:
        """获取止盈激活价格"""
        if not self.executor or not self.executor._open_order:
            return Decimal("0")
        last_open_price = self.executor._open_order.average_executed_price
        if last_open_price <= 0:
            return Decimal("0")
        return (
            last_open_price * (1 + self.take_profit_ratio)
            if self.side == TradeType.BUY
            else last_open_price * (1 - self.take_profit_ratio)
        )

    def get_tp_trigger_price(self) -> Decimal:
        """获取止盈触发价格"""
        if self.side == TradeType.BUY:
            return self.highest_price * (1 - self.take_profit_rebound_ratio)
        return self.lowest_price * (1 + self.take_profit_rebound_ratio)

    def get_position_info(self) -> Dict:
        """获取当前持仓信息

        Returns:
            Dict: 包含以下信息的字典：
                - amount_base: 持仓数量（基础货币）
                - amount_quote: 持仓金额（报价货币）
                - entry_price: 开仓价格
                - current_price: 当前价格
                - current_value: 当前市值
                - pnl_quote: 浮动盈亏（报价货币）
                - pnl_pct: 浮动盈亏百分比
        """
        logger = self.logger()
        logger.debug(f"获取级别持仓信息: 级别={self.id}")

        # 默认返回空持仓
        default_info = {
            "amount_base": Decimal("0"),
            "amount_quote": Decimal("0"),
            "entry_price": Decimal("0"),
            "current_price": Decimal("0"),
            "current_value": Decimal("0"),
            "pnl_quote": Decimal("0"),
            "pnl_pct": Decimal("0"),
        }

        # 如果没有执行器或不在交易中，返回默认值
        if not self.executor or not self.executor.is_trading:
            return default_info

        try:
            # 获取基本持仓信息
            amount_base = self.executor.open_filled_amount
            entry_price = self.last_open_price if self.last_open_price else Decimal("0")
            amount_quote = amount_base * entry_price if amount_base and entry_price else Decimal("0")
            current_price = self.current_price

            # 计算当前市值和盈亏
            current_value = amount_base * current_price if amount_base and current_price else Decimal("0")
            pnl_quote = current_value - amount_quote

            # 根据做多/做空方向调整盈亏
            if self.side == TradeType.SELL:
                pnl_quote = -pnl_quote

            # 计算盈亏百分比
            pnl_pct = (pnl_quote / amount_quote * 100) if amount_quote > 0 else Decimal("0")

            logger.debug(
                f"持仓信息: 级别={self.id}, 数量={amount_base}, "
                f"金额={amount_quote}, 开仓价格={entry_price}, "
                f"当前价格={current_price}, 当前市值={current_value}, "
                f"盈亏={pnl_quote}({pnl_pct:.2f}%)"
            )

            return {
                "amount_base": amount_base,
                "amount_quote": amount_quote,
                "entry_price": entry_price,
                "current_price": current_price,
                "current_value": current_value,
                "pnl_quote": pnl_quote,
                "pnl_pct": pnl_pct,
            }
        except Exception as e:
            logger.error(f"获取持仓信息时出错: {str(e)}", exc_info=True)
            return default_info

    def can_reactivate(self, config: FlexibleGridExecutorConfig) -> bool:
        """检查级别是否可以重新激活"""
        logger = self.logger()

        # 第一层级永远不能重新激活
        if self.index == 0:
            logger.debug(f"第一级别 {self.id} 不允许重新激活")
            return False

        # 如果配置中的最小重启间隔为0，则不重新激活
        if not config.min_reopen_interval or config.min_reopen_interval <= 0:
            logger.debug(f"级别 {self.id} 不可重新激活: 最小重启间隔未设置或为0")
            return False

        # 计算上次关闭后经过的时间
        time_since_last_closure = time.time() - self.last_closed_timestamp
        if time_since_last_closure < config.min_reopen_interval:
            logger.debug(
                f"级别 {self.id} 不可重新激活: 上次关闭后经过{time_since_last_closure:.1f}秒，"
                f"小于最小间隔{config.min_reopen_interval}秒"
            )
            return False

        # 检查前一层级状态
        prev_level = self.manager.get_level(self.index - 1)
        if prev_level and prev_level.current_state == FlexibleGridLevelStates.COMPLETED:
            logger.debug(f"级别 {self.id} 不可重新激活: 前一层级已完成")
            return False

        return True


@dataclass
class FlexibleGridManager:
    """灵活网格管理器，管理多个网格层级"""

    config: FlexibleGridExecutorConfig
    levels: List[FlexibleGridLevel] = field(default_factory=list)
    _order_level_mapping: Dict[str, str] = field(default_factory=dict)
    event_manager: GridEventManager = field(default_factory=GridEventManager)

    @classmethod
    def logger(cls) -> HummingbotLogger:
        """获取全局日志器"""
        return get_global_logger()

    def __post_init__(self):
        """初始化后处理"""
        self._setup_event_listeners()
        for level in self.levels:
            level.manager = self

    def initialize_levels(self) -> None:
        """初始化所有网格级别"""
        logger = self.logger()
        logger.debug(f"初始化网格级别: 总级别数={self.config.n_levels}")
        self.levels.clear()
        for i in range(self.config.n_levels):
            level_id = f"level_{self.config.id}_{i}"

            # 根据投资模式设置金额或数量
            amount_quote = Decimal("0")
            amount_base = Decimal("0")

            if self.config.investment_mode == "amount_quote":
                amount_quote = self.config.amount_quote[i]
            else:  # amount_base模式
                amount_base = self.config.amount_base[i]

            level = FlexibleGridLevel(
                index=i,
                id=level_id,
                side=self.config.side,
                amount_quote=amount_quote,
                amount_base=amount_base,
                open_ratio=self.config.open_ratios[i],
                take_profit_ratio=self.config.take_profit_ratios[i],
                stop_loss_ratio=self.config.stop_loss_ratios[i],
                open_rebound_ratio=self.config.open_rebound_ratios[i],
                take_profit_rebound_ratio=self.config.take_profit_rebound_ratios[i],
            )
            level.manager = self
            self.levels.append(level)

            # 特殊处理第一层级状态
            if i == 0 and self.config.first_level_open:
                level.current_state = FlexibleGridLevelStates.WAITING_OP_REBOUND
                logger.debug(f"第一级别 {level.id} 设置初始状态为 WAITING_OP_REBOUND")

        logger.debug("网格级别初始化完成")

    async def control_levels(self, current_price: Decimal, strategy) -> None:
        """控制所有级别的状态和执行器

        Args:
            current_price: 当前市场价格
            strategy: 交易策略对象
        """
        logger = self.logger()
        if current_price <= 0 or current_price != current_price:
            logger.warning(f"无效价格: {current_price}, 跳过控制")
            return
        self._update_prices(current_price)
        for level in reversed(self.levels):
            await self._control_level(level, current_price, strategy)
        logger.debug("网格级别控制完成")

    def _update_prices(self, current_price: Decimal) -> None:
        """更新所有级别的价格极值"""
        for level in self.levels:
            level.update_price_extremes(current_price)

    async def _control_level(self, level: FlexibleGridLevel, current_price: Decimal, strategy) -> None:
        """控制单个网格级别的状态和执行器逻辑"""
        logger = self.logger()
        logger.debug(f"控制级别: {level.id}, 状态={level.current_state.value}")

        # 如果该级别已有执行器，则先进行控制
        if level.executor:
            await level.control_task()  # 执行器控制任务

        self.check_level_status(level)

        # 检查级别状态并获取操作结果
        should_act = self.check_level_status(level)

        # 基于状态检查结果执行操作
        if should_act:
            if level.current_state in [
                FlexibleGridLevelStates.WAITING_OP_REBOUND,  # 等待反弹开仓信号
            ]:
                # 创建并启动执行器
                logger.debug(f"级别 {level.id} 触发开仓: 价格={current_price}")
                executor = level.create_executor(
                    strategy,
                    self.config.connector_name,
                    self.config.trading_pair,
                    self.config.leverage,
                )
                executor.start()
                level.update_state(FlexibleGridLevelStates.OPEN_ORDER_PLACED)

            elif level.current_state in [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
            ]:
                # 触发平仓
                logger.debug(f"级别 {level.id} 触发止盈")
                level.early_stop(keep_position=False)

        # 处理已关闭级别的重新激活
        if level.is_closed and level.can_reactivate(self.config):
            level.reset_for_reactivation()
            logger.debug(f"级别 {level.id} 已关闭并重置以重新激活")

    def _setup_event_listeners(self):
        """设置事件监听器"""
        logger = self.logger()
        logger.debug("设置事件监听器")
        self.event_manager.add_listener("state_change", self._handle_state_change)
        self.event_manager.add_listener("order_filled", self._handle_order_filled)
        logger.debug("事件监听器设置完成")

    def _handle_state_change(self, event: GridStateEvent):
        """处理状态变化事件，集中处理所有状态转换导致的后续操作"""
        logger = self.logger()
        logger.debug(f"处理状态变化: 级别={event.level_id}, 新状态={event.new_state}")

        # 获取级别对象
        level = self._get_level_by_id(event.level_id)
        if not level:
            logger.warning(f"未找到级别: {event.level_id}")
            return

        # 解析状态
        new_state = FlexibleGridLevelStates(event.new_state)
        old_state = FlexibleGridLevelStates(event.old_state) if event.old_state else None

        # 处理不同状态转换的逻辑
        if new_state == FlexibleGridLevelStates.OPEN_ORDER_FILLED:
            # 处理开仓成功
            self._handle_position_opened(level)

        elif new_state == FlexibleGridLevelStates.CLOSE_ORDER_FILLED:
            # 处理平仓成功
            self._handle_position_closed(level)

        elif new_state == FlexibleGridLevelStates.COMPLETED:
            # 处理交易完成
            self._handle_level_completed(level)

    def _handle_level_completed(self, level: FlexibleGridLevel):
        """处理级别完成逻辑"""
        logger = self.logger()
        logger.debug(f"处理级别完成: 级别={level.id}")

        # 清理级别相关资源
        self._clear_level_order_mappings(level.id)

        # 通知相邻级别
        prev_level = self.get_level(level.index - 1)
        prev_level.update_state(FlexibleGridLevelStates.WAITING_TP_ACTIVE)

    def _handle_op_activated(self, level: FlexibleGridLevel):
        """处理开仓激活状态"""
        logger = self.logger()
        logger.debug(f"处理开仓激活: 级别={level.id}")

        # 第一层级特殊处理
        if level.index == 0:
            if self.config.first_level_open:
                # 第一层级且配置为立即开仓，直接进入等待反弹状态
                logger.debug(f"第一级别 {level.id} 配置为立即开仓，直接进入等待反弹状态")
                level.update_state(FlexibleGridLevelStates.WAITING_OP_REBOUND)
                return
            elif self.config.open_ratios[0] == 0:
                # 第一层级且开仓比率为0，也直接进入等待反弹状态
                logger.debug(f"第一级别 {level.id} 开仓比率为0，直接进入等待反弹状态")
                level.update_state(FlexibleGridLevelStates.WAITING_OP_REBOUND)
                return
            else:
                # 第一层级但需要等待价格触发
                if level.current_price > 0:
                    # 使用当前价格作为基准价格
                    level.active_op_price = (
                        level.current_price * (1 - level.open_ratio)
                        if self.config.side == TradeType.BUY
                        else level.current_price * (1 + level.open_ratio)
                    )
                    logger.debug(
                        f"第一级别 {level.id} 设置激活价格: {level.active_op_price}, "
                        f"基准价格={level.current_price}, 开仓比率={level.open_ratio}"
                    )
                else:
                    logger.warning(f"第一级别 {level.id} 无法设置激活价格: 当前价格无效")
                return

        # 其他层级处理
        prev_level = self.get_level(level.index - 1)
        if not prev_level:
            logger.error(f"级别 {level.id} 无法找到前一层级")
            return

        # 检查前一层级状态和交易状态
        if not prev_level.is_trading or not prev_level.executor:
            logger.warning(f"prev_level.is_trading={prev_level.is_trading} prev_level.executor={prev_level.executor}")
            logger.warning(f"级别 {level.id} 前一层级 {prev_level.id} 未在交易中")
            return

        # 获取基准价格
        base_price = (
            prev_level.last_open_price
            if prev_level.last_open_price > 0
            else (
                prev_level.executor._open_order.average_executed_price
                if prev_level.executor._open_order
                else Decimal("0")
            )
        )

        if base_price <= 0:
            logger.warning(f"级别 {level.id} 无法设置激活价格: 前一层级无有效开仓价格")
            return

        # 根据交易方向计算激活价格
        level.active_op_price = (
            base_price * (1 - level.open_ratio)
            if self.config.side == TradeType.BUY
            else base_price * (1 + level.open_ratio)
        )

        logger.debug(
            f"级别 {level.id} 设置激活价格: {level.active_op_price}, "
            f"前一层级={prev_level.id}, 基准价格={base_price}, 开仓比率={level.open_ratio}"
        )

        # 重置价格极值，为后续的反弹判断做准备
        level.reset_price_extremes()
        level.update_price_extremes(level.current_price)

    def _handle_tp_activated(self, level: FlexibleGridLevel):
        """处理止盈激活状态"""
        logger = self.logger()
        logger.debug(f"处理止盈激活: 级别={level.id}")

        # 1. 首先计算止盈激活价格
        if level.executor and level.executor.is_trading:
            # 使用开仓价格计算止盈价格
            entry_price = (
                level.last_open_price
                if level.last_open_price > 0
                else level.executor._open_order.average_executed_price
            )

            if entry_price > 0:
                # 根据交易方向计算止盈激活价格
                if level.side == TradeType.BUY:
                    level.active_tp_price = entry_price * (1 + level.take_profit_ratio)
                else:
                    level.active_tp_price = entry_price * (1 - level.take_profit_ratio)
                logger.debug(
                    f"级别 {level.id} 设置止盈激活价格: {level.active_tp_price}, "
                    f"开仓价格: {entry_price}, 止盈比率: {level.take_profit_ratio}"
                )
            else:
                logger.warning(f"级别 {level.id} 无法计算止盈价格: 无效的开仓价格")
                return

    def _handle_order_filled(self, event: GridStateEvent):
        """处理订单成交事件"""
        logger = self.logger()
        logger.debug(f"处理订单成交: 级别={event.level_id}")
        level = self._get_level_by_id(event.level_id)
        if level:
            order_filled_event = event.data.get("order")
            if not isinstance(order_filled_event, OrderFilledEvent):
                logger.error(f"无效的订单成交事件数据: {event.data}")
                return

            level._record_order(order_filled_event)

            if level.current_state == FlexibleGridLevelStates.OPEN_ORDER_PLACED:
                level.update_state(FlexibleGridLevelStates.OPEN_ORDER_FILLED)
            elif level.current_state == FlexibleGridLevelStates.CLOSE_ORDER_PLACED:
                level.update_state(FlexibleGridLevelStates.CLOSE_ORDER_FILLED)

    def _handle_position_closed(self, level: FlexibleGridLevel):
        """处理级别平仓成功"""
        logger = self.logger()
        logger.debug(f"处理级别平仓: 级别={level.id}")

        # 通知前一级别（如果在等待此级别关闭）
        prev_level = self.get_level(level.index - 1)
        if prev_level and prev_level.current_state == FlexibleGridLevelStates.WAITING_NEXT_CLOSE:
            prev_level.update_state(FlexibleGridLevelStates.WAITING_TP_ACTIVE)

        # 第一层级特殊处理 - 直接设置为COMPLETE而不考虑重新激活
        if level.index == 0:
            level.update_state(FlexibleGridLevelStates.COMPLETED)
            logger.info(f"第一级别 {level.id} 平仓后完成交易，状态更新为 COMPLETED 并永久保持")
        elif level.can_reactivate(self.config):
            level.reset_for_reactivation()
        else:
            level.update_state(FlexibleGridLevelStates.COMPLETED)

    def _handle_position_opened(self, level: FlexibleGridLevel):
        """处理级别开仓成功"""
        logger = self.logger()
        logger.debug(f"处理级别开仓: 级别={level.id}")
        next_level = self.get_level(level.index + 1)
        if next_level:
            next_level.update_state(FlexibleGridLevelStates.WAITING_OP_ACTIVE)
        level.update_state(FlexibleGridLevelStates.WAITING_TP_ACTIVE)

    def _get_level_by_id(self, level_id: str) -> Optional[FlexibleGridLevel]:
        """根据ID获取级别"""
        for level in self.levels:
            if level.id == level_id:
                return level
        return None

    def check_open_trigger(self, level: FlexibleGridLevel, current_price: Decimal) -> bool:
        """检查开仓触发条件，需要正确处理多空方向

        Args:
            level: 网格级别
            current_price: 当前市场价格

        Returns:
            bool: 是否触发开仓
        """
        logger = self.logger()
        if current_price <= 0 or current_price != current_price:
            logger.warning(f"级别 {level.id}: 无效价格 {current_price}")
            return False

        if level.current_state == FlexibleGridLevelStates.WAITING_OP_ACTIVE:
            # 处理开仓激活
            self._handle_op_activated(level)

        # 第一级别特殊处理
        if level.index == 0 and (
            self.config.first_level_open
            or (self.config.open_ratios[0] == 0 and self.config.open_rebound_ratios[0] == 0)
        ):
            if level.current_state == FlexibleGridLevelStates.WAITING_OP_REBOUND:
                logger.debug(f"第一级别 {level.id} 触发立即开仓")
                return True
            return False

        # 检查前一个级别状态
        prev_level = self.get_level(level.index - 1)
        if not prev_level:
            logger.warning(f"级别 {level.id} 无法找到前一层级别")
            return False

        # 检查前一层级别是否处于有效状态
        valid_prev_states = [
            FlexibleGridLevelStates.OPEN_ORDER_FILLED,
            FlexibleGridLevelStates.WAITING_TP_ACTIVE,
            FlexibleGridLevelStates.WAITING_TP_REBOUND,
        ]

        if prev_level.current_state not in valid_prev_states:
            logger.debug(
                f"级别 {level.id} 前一层级别状态 {prev_level.current_state.value} 不在有效状态列表中: {[s.value for s in valid_prev_states]}"
            )
            return False

        # 检查前一层级别是否正在交易
        if not prev_level.executor or not prev_level.executor.is_trading:
            logger.debug(f"级别 {level.id} 前一层级别未持仓或执行器无效")
            return False

        # 处理等待前一级别开仓状态
        if level.current_state == FlexibleGridLevelStates.WAITING_PREV_OPEN:
            base_price = (
                prev_level.last_open_price
                if prev_level and prev_level.last_open_price > 0
                else (
                    prev_level.executor._open_order.average_executed_price
                    if prev_level.executor and prev_level.executor._open_order
                    else Decimal("0")
                )
            )
            if base_price <= 0:
                logger.warning(f"级别 {level.id}: 无效基准价格 {base_price}")
                return False

            # 根据做多做空方向计算激活价格
            level.active_op_price = (
                base_price * (1 - level.open_ratio)
                if self.config.side == TradeType.BUY
                else base_price * (1 + level.open_ratio)
            )
            level.update_state(FlexibleGridLevelStates.WAITING_OP_ACTIVE)
            logger.debug(f"级别 {level.id} 更新激活价格: {level.active_op_price}")
            return False

        # 处理等待激活状态
        if level.current_state == FlexibleGridLevelStates.WAITING_OP_ACTIVE:
            # 根据做多做空方向判断是否达到激活价格
            if (self.config.side == TradeType.BUY and current_price <= level.active_op_price) or (
                self.config.side == TradeType.SELL and current_price >= level.active_op_price
            ):
                level.update_state(FlexibleGridLevelStates.WAITING_OP_REBOUND)
                logger.debug(f"级别 {level.id} 达到激活价格，转为等待反弹状态")
                return False

        # 处理等待反弹状态
        if level.current_state == FlexibleGridLevelStates.WAITING_OP_REBOUND:
            # 根据做多做空方向计算触发价格
            if self.config.side == TradeType.BUY:
                level.trigger_op_price = level.lowest_price * (1 + level.open_rebound_ratio)
                should_trigger = current_price >= level.trigger_op_price
            else:  # TradeType.SELL
                level.trigger_op_price = level.highest_price * (1 - level.open_rebound_ratio)
                should_trigger = current_price <= level.trigger_op_price

            if should_trigger:
                logger.debug(
                    f"级别 {level.id} 满足反弹条件，触发开仓: "
                    f"方向={self.config.side.name}, 当前价格={current_price}, 触发价格={level.trigger_op_price}"
                )
                return True

        return False

    def check_take_profit(self, level: FlexibleGridLevel, current_price: Decimal) -> bool:
        """检查止盈条件，需要正确处理多空方向

        对于做多(side=TradeType.BUY):
            - 价格上涨到止盈激活价格时，进入等待回落状态
            - 价格回落到触发价格时，执行止盈
        对于做空(side=TradeType.SELL):
            - 价格下跌到止盈激活价格时，进入等待反弹状态
            - 价格反弹到触发价格时，执行止盈

        Args:
            level: 网格级别
            current_price: 当前市场价格

        Returns:
            bool: 是否触发止盈
        """
        logger = self.logger()
        if not level.is_trading or not level.executor or not level.executor._open_order:
            logger.debug(f"级别 {level.id} 未持仓或执行器无效")
            return False

        if level.current_state == FlexibleGridLevelStates.WAITING_TP_ACTIVE:
            # 处理止盈激活
            self._handle_tp_activated(level)

        last_open_price = level.executor._open_order.average_executed_price
        if last_open_price <= 0:
            logger.warning(f"级别 {level.id}: 无效开仓价格 {last_open_price}")
            last_open_price = current_price

        # 检查下一级别状态
        next_level = self.get_level(level.index + 1)
        if next_level and next_level.is_trading:
            # 如果下一层还在交易，当前层应该进入等待状态
            if level.current_state != FlexibleGridLevelStates.WAITING_NEXT_CLOSE:
                level.update_state(FlexibleGridLevelStates.WAITING_NEXT_CLOSE)
            return False

        # 根据做多做空方向计算止盈激活价格
        if self.config.side == TradeType.BUY:
            tp_active_price = last_open_price * (1 + level.take_profit_ratio)
            is_tp_activated = current_price >= tp_active_price
        else:  # TradeType.SELL
            tp_active_price = last_open_price * (1 - level.take_profit_ratio)
            is_tp_activated = current_price <= tp_active_price

        # 处理止盈激活状态
        if level.current_state == FlexibleGridLevelStates.WAITING_TP_ACTIVE:
            if is_tp_activated:
                level.reset_price_extremes()
                level.update_price_extremes(current_price)
                level.update_state(FlexibleGridLevelStates.WAITING_TP_REBOUND)
                logger.info(
                    f"级别 {level.id} 达到止盈激活价格: 方向={self.config.side.name}, "
                    f"激活价格={tp_active_price}, 当前价格={current_price}"
                )
                return False

        # 处理止盈回落/反弹状态
        if level.current_state == FlexibleGridLevelStates.WAITING_TP_REBOUND:
            # 根据做多做空方向计算触发价格
            if self.config.side == TradeType.BUY:
                trigger_tp_price = level.highest_price * (1 - level.take_profit_rebound_ratio)
                should_trigger = current_price <= trigger_tp_price
                direction = "回落"
            else:  # TradeType.SELL
                trigger_tp_price = level.lowest_price * (1 + level.take_profit_rebound_ratio)
                should_trigger = current_price >= trigger_tp_price
                direction = "反弹"

            if should_trigger:
                logger.info(
                    f"级别 {level.id} 满足{direction}条件，触发止盈平仓: "
                    f"方向={self.config.side.name}, 触发价格={trigger_tp_price}, 当前价格={current_price}"
                )
                level.last_closed_timestamp = time.time()
                return True

        return False

    def stop_all(self, keep_position: bool = False) -> None:
        """停止所有级别的执行器"""
        logger = self.logger()
        logger.debug(f"停止所有级别: 保留仓位={keep_position}")
        for level in self.levels:
            try:
                level.stop_executor(keep_position=keep_position)
            except Exception as e:
                logger.error(f"停止级别 {level.id} 时出错: {str(e)}", exc_info=True)
        logger.debug("所有级别停止完成")

    def get_level(self, index: int) -> Optional[FlexibleGridLevel]:
        """获取指定索引的级别"""
        return self.levels[index] if 0 <= index < len(self.levels) else None

    def get_total_net_pnl_quote(self) -> Decimal:
        """获取所有级别的总盈亏"""
        return sum(level.net_pnl_quote for level in self.levels)

    def get_total_fees(self) -> Decimal:
        """获取所有级别的总费用"""
        return sum(level.cum_fees_quote for level in self.levels)

    def get_active_levels(self) -> List[FlexibleGridLevel]:
        """获取所有活跃级别"""
        return [level for level in self.levels if level.is_level_active]

    def map_order_to_level(self, order_id: str, level_id: str):
        """映射订单ID到网格层级"""
        self._order_level_mapping[order_id] = level_id
        self.logger().debug(f"订单 {order_id} 映射到网格层级 {level_id}")

    def check_level_status(self, level: FlexibleGridLevel) -> None:
        """检查并更新层级状态，这是唯一一个定期检查状态的方法"""
        logger = self.logger()
        logger.debug(f"检查级别状态: 级别={level.id}, 状态={level.current_state.value}")
        # 获取执行器状态
        executor_is_closed = level.executor.is_closed if level.executor else False
        executor_is_trading = level.executor.is_trading if level.executor else False
        executor_status = level.executor.status if level.executor else None
        current_price = level.current_price
        next_level = self.get_level(level.index + 1)
        prev_level = self.get_level(level.index - 1)

        if next_level and next_level.is_trading:
            logger.debug(f"级别 {level.id} 等待下一级别 {next_level.id} 平仓")
            level.update_state(FlexibleGridLevelStates.WAITING_NEXT_CLOSE)

        if prev_level and not prev_level.is_trading:
            level.update_state(FlexibleGridLevelStates.WAITING_PREV_OPEN)

        if level.current_state == FlexibleGridLevelStates.WAITING_NEXT_CLOSE:
            if next_level and not next_level.is_trading and level.is_trading:
                logger.debug(f"级别 {level.id} 下一层已平仓，转为等待止盈")
                level.update_state(FlexibleGridLevelStates.WAITING_TP_ACTIVE)

        if level.current_state == FlexibleGridLevelStates.OPEN_ORDER_FILLED:
            logger.debug(f"级别 {level.id} 处于 OPEN_ORDER_FILLED 状态，处理后续状态转换")
            level.update_state(FlexibleGridLevelStates.WAITING_TP_ACTIVE)

        # 处理 CLOSE_ORDER_FILLED 状态
        if level.current_state == FlexibleGridLevelStates.CLOSE_ORDER_FILLED:
            logger.debug(f"级别 {level.id} 处于 CLOSE_ORDER_FILLED 状态，处理后续状态转换")
            level.update_state(FlexibleGridLevelStates.COMPLETED)

        # 对于其他层级，如果是COMPLETED状态，检查是否可以重新激活
        if level.current_state == FlexibleGridLevelStates.COMPLETED:
            if level.can_reactivate(self.config):
                logger.debug(f"级别 {level.id} 可以重新激活")
                level.reset_for_reactivation()
                level.update_state(FlexibleGridLevelStates.WAITING_PREV_OPEN)
            else:
                logger.debug(f"级别 {level.id} 已完成且不能重新激活")

        if level.current_state == FlexibleGridLevelStates.WAITING_PREV_OPEN:
            if prev_level and prev_level.is_trading and not level.is_trading:
                level.update_state(FlexibleGridLevelStates.WAITING_OP_ACTIVE)

        # 处理正在交易的情况
        if executor_is_trading:
            self._handle_executor_trading(level)
        # 处理执行器正在关闭的情况
        elif executor_status == "SHUTTING_DOWN":
            self._handle_executor_shutting_down(level)

        # 检查开仓条件
        if level.current_state in [
            FlexibleGridLevelStates.WAITING_OP_ACTIVE,
            FlexibleGridLevelStates.WAITING_OP_REBOUND,
        ]:
            if self.check_open_trigger(level, current_price):
                logger.debug(f"级别 {level.id} 触发开仓条件")
                # 状态更新由调用方负责，这里只返回检查结果
                return True

        # 检查平仓条件
        elif level.current_state in [
            FlexibleGridLevelStates.WAITING_TP_ACTIVE,
            FlexibleGridLevelStates.WAITING_TP_REBOUND,
        ]:
            if self.check_take_profit(level, current_price):
                logger.debug(f"级别 {level.id} 触发平仓条件")
                # 状态更新由调用方负责，这里只返回检查结果
                return True

        return False

    def _handle_executor_trading(self, level: FlexibleGridLevel) -> None:
        """处理执行器正在交易的情况"""
        logger = self.logger()

        # 更新开仓价格（如果未记录）
        if level.executor._open_order and level.last_open_price == 0:
            executed_price = level.executor._open_order.average_executed_price
            if executed_price > 0:
                level.last_open_price = executed_price
                level.last_open_timestamp = level.executor._open_order.last_update_timestamp or time.time()
                logger.debug(f"级别 {level.id} 更新开仓价格: {level.last_open_price}")

    def _handle_executor_shutting_down(self, level: FlexibleGridLevel) -> None:
        """处理执行器正在关闭的情况"""
        logger = self.logger()

        if level.current_state == FlexibleGridLevelStates.WAITING_TP_REBOUND:
            logger.debug(f"级别 {level.id} 执行器正在关闭，从 WAITING_TP_REBOUND 更新为 CLOSE_ORDER_PLACED")
            level.update_state(FlexibleGridLevelStates.CLOSE_ORDER_PLACED)

    def _record_close_information(self, level: FlexibleGridLevel) -> None:
        """记录平仓信息"""
        logger = self.logger()

        last_order_id = None
        active_orders = level.executor.get_active_orders(self.config.connector_name)
        if active_orders:
            last_order_id = active_orders[-1].client_order_id

        level.record_close(
            exit_price=level.executor.close_price,
            pnl=level.executor.get_net_pnl_quote(),
            fees=level.executor.get_cum_fees_quote(),
            order_id=last_order_id,
        )
        logger.debug(f"级别 {level.id} 记录平仓信息: 价格={level.executor.close_price}")

    def _clear_level_resources(self, level: FlexibleGridLevel) -> None:
        """清理级别资源"""
        logger = self.logger()

        # 清理订单映射
        self._clear_level_order_mappings(level.id)

        # 清理执行器
        old_executor_id = level.executor.config.id if level.executor else "无执行器"
        level.executor = None
        logger.debug(f"级别 {level.id} 执行器 {old_executor_id} 已清理")

    def get_level_by_order_id(self, order_id: str) -> Optional[FlexibleGridLevel]:
        logger = self.logger()
        logger.debug(f"查找订单对应的级别: 订单ID={order_id}, 映射表={self._order_level_mapping}")

        # 优先检查映射表
        level_id = self._order_level_mapping.get(order_id)
        if level_id:
            level = self._get_level_by_id(level_id)
            if level:
                logger.debug(
                    f"通过映射找到级别: 订单ID={order_id}, 级别ID={level_id}, 级别状态={level.current_state.value}"
                )
                if level.index == 0 or (
                    level.executor and self._check_order_belongs_to_executor(level.executor, order_id)
                ):
                    return level
                else:
                    logger.warning(f"映射无效，级别 {level_id} 无有效执行器或订单不匹配，移除映射: 订单ID={order_id}")
                    self._order_level_mapping.pop(order_id, None)
            else:
                logger.warning(f"映射中的级别ID {level_id} 不存在，移除映射: 订单ID={order_id}")
                self._order_level_mapping.pop(order_id, None)

        # 如果映射失败，遍历所有级别
        logger.debug(f"映射查找失败，遍历所有级别以查找订单: 订单ID={order_id}")
        for level in self.levels:
            if level.executor and self._check_order_belongs_to_executor(level.executor, order_id):
                logger.debug(
                    f"通过执行器找到级别: 订单ID={order_id}, 级别ID={level.id}, 状态={level.current_state.value}"
                )
                self.map_order_to_level(order_id, level.id)
                return level

        logger.warning(f"未找到订单对应的级别: 订单ID={order_id}")
        return None

    def _find_level_for_new_order(
        self,
    ) -> Optional[FlexibleGridLevel]:
        """根据当前活跃状态和执行器状态查找对应的级别

        对于做多(side=TradeType.BUY):
            - 开仓是买单(BUY)，等待状态为 WAITING_OP_REBOUND
            - 平仓是卖单(SELL)，等待状态为 WAITING_TP_ACTIVE, WAITING_TP_REBOUND
        对于做空(side=TradeType.SELL):
            - 开仓是卖单(SELL)，等待状态为 WAITING_OP_REBOUND
            - 平仓是买单(BUY)，等待状态为 WAITING_TP_ACTIVE, WAITING_TP_REBOUND
        """
        logger = self.logger()
        logger.debug("查找新订单对应的级别")

        # 遍历所有级别，查找符合条件的级别
        for level in self.levels:
            # 检查级别状态
            if level.executor and level.executor.is_active:
                # 检查是否为开仓状态
                if level.current_state in [
                    FlexibleGridLevelStates.WAITING_OP_REBOUND,
                    FlexibleGridLevelStates.OPEN_ORDER_PLACED,
                ]:
                    if not level.executor.is_trading:
                        logger.debug(f"找到准备开仓的级别: {level.id}, 方向={self.config.side.name}")
                        return level

                # 检查是否为平仓状态
                elif level.current_state in [
                    FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                    FlexibleGridLevelStates.WAITING_TP_REBOUND,
                    FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
                ]:
                    if level.executor.is_trading:
                        logger.debug(f"找到准备平仓的级别: {level.id}, 方向={self.config.side.name}")
                        return level

            # 检查等待开仓状态
            elif level.current_state == FlexibleGridLevelStates.WAITING_OP_REBOUND:
                logger.debug(f"找到等待创建执行器的级别: {level.id}, 方向={self.config.side.name}")
                return level

        logger.debug(f"未找到合适的级别处理新订单，方向={self.config.side.name}")
        return None

    def _emit_event(self, event_type: str, level_id: str, data: Dict[str, Any]):
        """发送事件"""
        if self.event_manager:
            event = GridStateEvent(event_type=event_type, level_id=level_id, data=data)
            asyncio.create_task(self.event_manager.emit_event(event))

    def _check_order_belongs_to_executor(self, executor: PositionExecutor, order_id: str) -> bool:
        """检查订单是否属于执行器

        Args:
            executor: 执行器实例
            order_id: 订单ID

        Returns:
            bool: 订单是否属于该执行器
        """
        logger = self.logger()
        has_found = False
        reason = "未找到"

        # 检查开仓订单
        if executor._open_order and executor._open_order.order_id == order_id:
            has_found = True
            reason = "是开仓订单"
            logger.debug(f"订单 {order_id} 属于执行器 {executor.config.id} 的开仓订单")
            return True

        # 检查平仓订单
        if executor._close_order and executor._close_order.order_id == order_id:
            has_found = True
            reason = "是平仓订单"
            logger.debug(f"订单 {order_id} 属于执行器 {executor.config.id} 的平仓订单")
            return True

        # 检查止盈限价单
        if executor._take_profit_limit_order and executor._take_profit_limit_order.order_id == order_id:
            has_found = True
            reason = "是止盈限价单"
            logger.debug(f"订单 {order_id} 属于执行器 {executor.config.id} 的止盈限价单")
            return True

        # 检查执行器的活跃订单
        active_orders = executor.get_active_orders(self.config.connector_name)
        if active_orders:
            for order in active_orders:
                if order.client_order_id == order_id:
                    has_found = True
                    reason = "是活跃订单"
                    logger.debug(f"订单 {order_id} 属于执行器 {executor.config.id} 的活跃订单")
                    return True

        # 检查失败的订单
        if hasattr(executor, "_failed_orders") and executor._failed_orders:
            for order in executor._failed_orders:
                if order.order_id == order_id:
                    has_found = True
                    reason = "是失败订单"
                    logger.debug(f"订单 {order_id} 属于执行器 {executor.config.id} 的失败订单")
                    return True

        if not has_found:
            logger.debug(f"订单 {order_id} 不属于执行器 {executor.config.id}，原因: {reason}")

        return has_found

    def handle_order_created(self, event: Union[BuyOrderCreatedEvent, SellOrderCreatedEvent]):
        """处理订单创建事件，需要正确处理多空方向

        对于做多(side=BUY):
            - 开仓是买单(BUY)
            - 平仓是卖单(SELL)
        对于做空(side=SELL):
            - 开仓是卖单(SELL)
            - 平仓是买单(BUY)
        """
        logger = self.logger()
        logger.debug(f"处理订单创建: 订单ID={event.order_id}, 类型={type(event).__name__}")

        # 在所有级别中查找订单所属的级别
        level = None
        for l in self.levels:
            if l.executor and self._check_order_belongs_to_executor(l.executor, event.order_id):
                level = l
                logger.debug(
                    f"找到订单所属级别: 订单ID={event.order_id}, 级别ID={l.id}, 执行器ID={l.executor.config.id}"
                )
                break

        if level is None:
            logger.warning(f"未找到订单 {event.order_id} 对应的级别，检查执行器状态")
            for l in self.levels:
                if l.executor:
                    logger.debug(
                        f"级别 {l.id} 执行器状态: 订单={l.executor.get_active_orders(self.config.connector_name)}"
                    )
            return

        # 确定订单类型（开仓或平仓）- 使用级别的交易方向而不是网格的交易方向
        is_open_order = (isinstance(event, BuyOrderCreatedEvent) and level.side == TradeType.BUY) or (
            isinstance(event, SellOrderCreatedEvent) and level.side == TradeType.SELL
        )

        # 根据订单类型确定预期状态和目标状态
        if is_open_order:
            valid_states = [FlexibleGridLevelStates.WAITING_OP_REBOUND, FlexibleGridLevelStates.OPEN_ORDER_PLACED]
            target_state = FlexibleGridLevelStates.OPEN_ORDER_PLACED
            logger.debug(f"处理开仓订单: 订单ID={event.order_id}, 方向={level.side.name}")
        else:
            valid_states = [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
            ]
            target_state = FlexibleGridLevelStates.CLOSE_ORDER_PLACED
            logger.debug(f"处理平仓订单: 订单ID={event.order_id}, 方向={level.side.name}")

        # 严格检查状态有效性并更新
        if level.current_state in valid_states:
            # 记录订单与级别的映射
            self.map_order_to_level(event.order_id, level.id)
            logger.debug(f"订单 {event.order_id} 映射到网格层级 {level.id}, 映射表={self._order_level_mapping}")

            # 仅在需要时更新状态
            if level.current_state != target_state:
                level.update_state(target_state)
                logger.debug(f"级别 {level.id} 状态已更新为 {target_state.value}")

            # 发送订单创建事件
            self._emit_event("order_created", level.id, {"order": event})
        else:
            logger.warning(
                f"订单 {event.order_id} 属于级别 {level.id}, "
                f"但状态不匹配: 当前={level.current_state.value}, 期望={[s.value for s in valid_states]}"
            )

    def handle_order_filled(self, event: Union[OrderFilledEvent, BuyOrderCompletedEvent, SellOrderCompletedEvent]):
        logger = self.logger()
        logger.debug(f"处理订单成交: 订单ID={event.order_id}, 类型={type(event).__name__}, 成交数量={event.amount}")

        # 查找订单对应的级别
        level = self.get_level_by_order_id(event.order_id)
        if level is None:
            logger.warning(f"未找到订单 {event.order_id} 对应的级别，映射表={self._order_level_mapping}")
            return

        # 如果级别已完成，跳过处理
        if level.current_state == FlexibleGridLevelStates.COMPLETED:
            logger.debug(f"级别 {level.id} 已完成，跳过成交事件处理")
            return

        # 确定订单类型（开仓或平仓）- 修改：使用级别的交易方向
        is_open_order = (
            (isinstance(event, BuyOrderCompletedEvent) or event.trade_type == TradeType.BUY)
            and level.side == TradeType.BUY
        ) or (
            (isinstance(event, SellOrderCompletedEvent) or event.trade_type == TradeType.SELL)
            and level.side == TradeType.SELL
        )

        # 根据订单类型确定预期状态和目标状态
        if is_open_order:
            expected_states = [FlexibleGridLevelStates.OPEN_ORDER_PLACED]
            target_state = FlexibleGridLevelStates.OPEN_ORDER_FILLED
            logger.debug(f"处理开仓订单成交: 级别={level.id}, 订单ID={event.order_id}, 数量={event.amount}")
        else:
            expected_states = [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
            ]
            target_state = FlexibleGridLevelStates.CLOSE_ORDER_FILLED
            logger.debug(f"处理平仓订单成交: 级别={level.id}, 订单ID={event.order_id}, 数量={event.amount}")

        # 严格检查并在合适情况下更新状态
        if level.current_state in expected_states:
            # 更新状态 - 这是唯一更新状态的地方
            level.update_state(target_state)

            # 记录订单信息 - 而不是通过on_order_filled再次触发状态更新
            level._record_order(event)

            # 记录交易相关信息
            if is_open_order:
                level.last_open_price = event.price
                level.last_open_timestamp = event.timestamp
                logger.debug(
                    f"级别 {level.id} 记录开仓价格: {level.last_open_price}, 时间: {level.last_open_timestamp}"
                )

            # 发送事件
            self._emit_event("order_filled", level.id, {"order": event})
            logger.debug(f"级别 {level.id} 成交事件处理完成, 新状态={target_state.value}")
        else:
            logger.warning(
                f"订单 {event.order_id} 状态不匹配: 级别={level.id}, "
                f"当前={level.current_state.value}, 期望={[s.value for s in expected_states]}"
            )

    def handle_order_completed(self, event: Union[BuyOrderCompletedEvent, SellOrderCompletedEvent]):
        logger = self.logger()
        logger.debug(
            f"处理订单完成: 订单ID={event.order_id}, 类型={type(event).__name__}, 总成交数量={event.base_asset_amount}"
        )

        # 查找订单对应的级别
        level = self.get_level_by_order_id(event.order_id)
        if level is None:
            logger.warning(f"未找到订单 {event.order_id} 对应的级别，映射表={self._order_level_mapping}")
            return

        # 如果级别已完成，跳过处理
        if level.current_state == FlexibleGridLevelStates.COMPLETED:
            logger.debug(f"级别 {level.id} 已完成，跳过完成事件处理")
            return

        # 确定订单类型（开仓或平仓）
        is_open_order = (isinstance(event, BuyOrderCompletedEvent) and level.side == TradeType.BUY) or (
            isinstance(event, SellOrderCompletedEvent) and level.side == TradeType.SELL
        )

        # 根据订单类型处理
        if is_open_order:
            # 记录开仓价格
            if level.last_open_price <= 0:
                price = (
                    Decimal(str(event.quote_asset_amount / event.base_asset_amount))
                    if event.base_asset_amount > 0
                    else Decimal("0")
                )
                level.last_open_price = price
                level.last_open_timestamp = event.timestamp
                logger.debug(f"级别 {level.id} 记录开仓价格: {level.last_open_price}")

            # 发送事件
            self._emit_event("order_completed", level.id, {"order": event})
        else:
            # 记录平仓信息
            if level.last_close_price <= 0:
                # 确定平仓价格
                exit_price = level.current_price  # 默认使用当前价格

                # 如果事件有price属性，则优先使用
                if hasattr(event, "price"):
                    exit_price = Decimal(str(event.price))
                # 如果没有但可以计算，则计算平均成交价格
                elif event.base_asset_amount > 0:
                    exit_price = Decimal(str(event.quote_asset_amount / event.base_asset_amount))

                # 记录平仓，不发送position_closed事件
                level.record_close(
                    exit_price=exit_price,
                    pnl=level.executor.get_net_pnl_quote() if level.executor else Decimal("0"),
                    fees=level.executor.get_cum_fees_quote() if level.executor else Decimal("0"),
                    order_id=event.order_id,
                )

            # 发送事件
            self._emit_event("order_completed", level.id, {"order": event})

        # 清理订单映射
        self._order_level_mapping.pop(event.order_id, None)
        logger.debug(f"订单 {event.order_id} 映射已清理，当前映射表={self._order_level_mapping}")

    def handle_order_canceled(self, event: OrderCancelledEvent):
        """处理订单取消事件"""
        logger = self.logger()
        logger.debug(f"处理订单取消: {event.order_id}")
        level = self.get_level_by_order_id(event.order_id)
        if level:
            new_state = (
                FlexibleGridLevelStates.WAITING_OP_REBOUND
                if level.current_state == FlexibleGridLevelStates.OPEN_ORDER_PLACED
                else FlexibleGridLevelStates.WAITING_TP_REBOUND
            )
            level.update_state(new_state)
            self._emit_event("order_canceled", level.id, {"order": event})

    def handle_order_failed(self, event: MarketOrderFailureEvent):
        """处理订单失败事件"""
        logger = self.logger()
        logger.debug(f"处理订单失败: {event.order_id}")
        level = self.get_level_by_order_id(event.order_id)
        if level:
            # 根据当前级别状态，确定合适的新状态
            if level.current_state == FlexibleGridLevelStates.OPEN_ORDER_PLACED:
                # 开仓失败，回到等待反弹状态
                new_state = FlexibleGridLevelStates.WAITING_OP_REBOUND
                logger.info(f"级别 {level.id} 开仓失败，重置到 {new_state.value}")

                # 关键修改：当开仓失败时，清理执行器实例
                if level.executor:
                    logger.info(
                        f"级别 {level.id} 开仓失败，清理执行器实例 {level.executor.config.id if hasattr(level.executor, 'config') else '未知'}"
                    )
                    level.executor = None
                    # 清理订单映射
                    self._clear_level_order_mappings(level.id)

            elif level.current_state in [
                FlexibleGridLevelStates.WAITING_TP_ACTIVE,
                FlexibleGridLevelStates.WAITING_TP_REBOUND,
                FlexibleGridLevelStates.CLOSE_ORDER_PLACED,
            ]:
                # 平仓失败，回到等待反弹止盈状态
                new_state = FlexibleGridLevelStates.WAITING_TP_REBOUND
                logger.info(f"级别 {level.id} 平仓失败，重置到 {new_state.value}")
            else:
                # 其他状态，保持不变
                logger.warning(
                    f"订单 {event.order_id} 失败，但级别 {level.id} 状态 {level.current_state.value} 无需更改"
                )
                self._emit_event("order_failed", level.id, {"order": event})
                return

            # 确保状态转换有效，再进行状态更新
            if level.validate_state_transition(new_state):
                level.update_state(new_state)
                self._emit_event("order_failed", level.id, {"order": event})
            else:
                logger.error(
                    f"无法将级别 {level.id} 从 {level.current_state.value} 更新到 {new_state.value}，状态转换无效"
                )
        else:
            logger.warning(f"未找到订单 {event.order_id} 对应的级别，订单失败事件无法处理")

        # 清理失败订单的映射
        self._order_level_mapping.pop(event.order_id, None)
        logger.debug(f"已清理失败订单 {event.order_id} 的映射")

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "config": self.config.to_dict(),
            "levels": [level.to_dict() for level in self.levels],
            "total_net_pnl_quote": str(self.get_total_net_pnl_quote()),
            "total_fees": str(self.get_total_fees()),
            "active_levels": len(self.get_active_levels()),
        }

    def calculate_average_position_cost(self) -> Dict:
        """计算所有级别的平均持仓成本和相关信息

        Returns:
            Dict: 包含持仓信息的字典
                {
                    "total_amount_base": 总持仓数量（基础货币）
                    "total_amount_quote": 总持仓金额（报价货币）
                    "average_entry_price": 平均开仓价格
                    "current_value": 当前总价值（按当前价格计算）
                    "total_pnl_quote": 总浮动盈亏（报价货币）
                    "total_pnl_pct": 总浮动盈亏百分比
                    "trading_levels_count": 正在交易的级别数量
                }
        """
        logger = self.logger()
        logger.debug("计算平均持仓成本")

        # 获取所有交易中的级别
        trading_levels = [level for level in self.levels if level.is_trading]
        trading_levels_count = len(trading_levels)

        if trading_levels_count == 0:
            logger.debug("没有活跃的交易级别")
            return {
                "total_amount_base": Decimal("0"),
                "total_amount_quote": Decimal("0"),
                "average_entry_price": Decimal("0"),
                "current_value": Decimal("0"),
                "total_pnl_quote": Decimal("0"),
                "total_pnl_pct": Decimal("0"),
                "trading_levels_count": 0,
            }

        # 获取每个级别的持仓信息
        position_info_list = [level.get_position_info() for level in trading_levels]

        # 计算总数量和总金额
        total_amount_base = sum(info["amount_base"] for info in position_info_list)
        total_amount_quote = sum(info["amount_quote"] for info in position_info_list)
        current_value = sum(info["current_value"] for info in position_info_list)
        total_pnl_quote = sum(info["pnl_quote"] for info in position_info_list)

        # 计算平均开仓价格和盈亏率
        average_entry_price = total_amount_quote / total_amount_base if total_amount_base > 0 else Decimal("0")
        total_pnl_pct = total_pnl_quote / total_amount_quote * 100 if total_amount_quote > 0 else Decimal("0")

        logger.debug(
            f"平均持仓计算结果: "
            f"总数量={total_amount_base}, 总金额={total_amount_quote}, "
            f"平均价格={average_entry_price}, 当前价值={current_value}, "
            f"总盈亏={total_pnl_quote}({total_pnl_pct:.2f}%), 交易级别数={trading_levels_count}"
        )

        return {
            "total_amount_base": total_amount_base,
            "total_amount_quote": total_amount_quote,
            "average_entry_price": average_entry_price,
            "current_value": current_value,
            "total_pnl_quote": total_pnl_quote,
            "total_pnl_pct": total_pnl_pct,
            "trading_levels_count": trading_levels_count,
        }

    def to_format_status(self) -> str:
        """返回格式化的网格状态信息

        Returns:
            str: 格式化后的状态字符串
        """
        logger = self.logger()
        logger.debug("生成网格状态格式化输出")

        # 计算基本统计信息
        total_net_pnl = self.get_total_net_pnl_quote()
        total_fees = self.get_total_fees()
        active_levels = self.get_active_levels()
        active_count = len(active_levels)
        total_count = len(self.levels)
        win_count = sum(level.win_count for level in self.levels)
        loss_count = sum(level.loss_count for level in self.levels)
        total_trades = win_count + loss_count
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        # 计算持仓信息
        position_info = self.calculate_average_position_cost()
        total_amount_base = position_info["total_amount_base"]
        total_amount_quote = position_info["total_amount_quote"]
        avg_entry_price = position_info["average_entry_price"]
        total_pnl_quote = position_info["total_pnl_quote"]
        total_pnl_pct = position_info["total_pnl_pct"]
        trading_levels_count = position_info["trading_levels_count"]

        # 获取交易中的级别（已持有仓位的级别）
        trading_levels = [level for level in self.levels if level.is_trading]

        # 格式化显示金额
        if self.config.investment_mode == "amount_quote":
            investment_type = "报价货币"
            amount_total = sum(level.amount_quote for level in self.levels)
            # 修改：使用交易中的级别而不是活跃级别
            amount_active = sum(level.amount_quote for level in trading_levels)
            currency = self.config.trading_pair.split("-")[1]  # 报价货币
        else:
            investment_type = "基础货币"
            amount_total = sum(level.amount_base for level in self.levels)
            # 修改：使用交易中的级别而不是活跃级别
            amount_active = sum(level.amount_base for level in trading_levels)
            currency = self.config.trading_pair.split("-")[0]  # 基础货币

        investment_usage = (amount_active / amount_total * 100) if amount_total > 0 else Decimal("0")

        # 构建网格总体状态
        header = [
            "╔══════════════════════════ 网格状态信息 ══════════════════════════╗",
            "║                                                                ║",
            f"║ 交易方向: {'做多 (BUY)' if self.config.side == TradeType.BUY else '做空 (SELL)':<41} ║",
            f"║ 投资模式: {self.config.investment_mode} ({investment_type}){' ':<31} ║",
            f"║ 资金使用: {investment_usage:.2f}% ({amount_active:.6f}/{amount_total:.6f} {currency}) ║",
            "║                                                                ║",
            f"║ 总级别数: {total_count:<6}   活跃级别: {active_count:<6}   交易中级别: {trading_levels_count:<6} ║",
            f"║ 平均持仓价格: {avg_entry_price:.6f}{' ':<34} ║",
            f"║ 当前持仓总盈亏: {total_pnl_quote:.6f} ({total_pnl_pct:.2f}%){' ':<22} ║",
            f"║ 历史总盈亏: {total_net_pnl:.6f}   总手续费: {total_fees:.6f}{' ':<13} ║",
            f"║ 交易统计: {win_count}胜/{loss_count}负 ({win_rate:.1f}%){' ':<30} ║",
            "║                                                                ║",
        ]

        if (
            self.config.take_profit
            or self.config.stop_loss
            or self.config.profit_target_amount
            or self.config.loss_target_amount
        ):
            header.extend(
                [
                    "║ 全局风控设置:                                                 ║",
                    f"║   价格止盈: {self.config.take_profit*100:.2f}%   价格止损: {self.config.stop_loss*100:.2f}%{' ':<19} ║",
                ]
            )

            if self.config.profit_target_amount or self.config.loss_target_amount:
                profit_str = f"{self.config.profit_target_amount}" if self.config.profit_target_amount else "未设置"
                loss_str = f"{self.config.loss_target_amount}" if self.config.loss_target_amount else "未设置"
                header.append(f"║   金额止盈: {profit_str:<10}   金额止损: {loss_str:<10}{' ':<19} ║")

            header.append("║                                                                ║")

        # 添加分隔线
        header.append("╠════════════════════════════════════════════════════════════════╣")
        header.append("║                                                                ║")
        header.append("║                     *** 网格级别详情 ***                         ║")
        header.append("║                                                                ║")
        header.append("╠════════════════════════════════════════════════════════════════╣")

        # 获取每个级别的格式化状态
        level_statuses = []
        for level in sorted(self.levels, key=lambda x: x.index):
            level_statuses.append(level.to_format_status())

        # 合并所有输出
        footer = ["╚════════════════════════════════════════════════════════════════╝"]
        return "\n".join(header + level_statuses + footer)

    def cleanup(self) -> None:
        """清理所有网格级别和资源"""
        logger = self.logger()
        logger.info("开始清理网格管理器资源")

        try:
            # 停止所有级别的执行器
            logger.debug("停止所有网格级别")
            for level in self.levels:
                try:
                    # 确保清理每个级别的订单映射
                    self._clear_level_order_mappings(level.id)
                    level.cleanup()
                except Exception as e:
                    logger.error(f"级别 {level.id} 清理时出错: {str(e)}", exc_info=True)

            # 清理事件监听器
            logger.debug("清理事件监听器")
            if hasattr(self, "event_manager") and self.event_manager:
                # 移除所有事件监听
                if hasattr(self, "_handle_state_change"):
                    self.event_manager.remove_listener("state_change", self._handle_state_change)
                if hasattr(self, "_handle_order_filled"):
                    self.event_manager.remove_listener("order_filled", self._handle_order_filled)

            # 清理映射表 - 确保即使有异常也能清理
            logger.debug(f"清理订单映射表，共有 {len(self._order_level_mapping)} 个映射")
            self._order_level_mapping.clear()

            # 清理级别列表
            logger.debug("清理级别列表")
            self.levels.clear()

            logger.info("网格管理器资源清理完成")
        except Exception as e:
            logger.error(f"网格管理器清理时出错: {str(e)}", exc_info=True)
            # 尝试强制清理关键资源
            self._order_level_mapping.clear()
            self.levels.clear()

    def _clear_level_order_mappings(self, level_id: str) -> None:
        """清理与特定级别相关的所有订单映射"""
        logger = self.logger()

        try:
            # 找出所有映射到此级别的订单ID
            orders_to_remove = [order_id for order_id, lid in self._order_level_mapping.items() if lid == level_id]

            # 从映射表中移除这些订单
            for order_id in orders_to_remove:
                self._order_level_mapping.pop(order_id, None)

            if orders_to_remove:
                logger.debug(f"已清理级别 {level_id} 的 {len(orders_to_remove)} 个订单映射: {orders_to_remove}")
            else:
                logger.debug(f"级别 {level_id} 无需清理订单映射")
        except Exception as e:
            logger.error(f"清理级别 {level_id} 订单映射时出错: {str(e)}", exc_info=True)

    def get_total_volume_traded(self) -> Decimal:
        """获取总成交量（基础货币）"""
        total_volume = Decimal("0")
        for level in self.levels:
            if level.executor:
                total_volume += level.executor.open_filled_amount
        return total_volume

    def get_inventory_imbalance(self) -> Decimal:
        """获取库存不平衡度

        计算方法：
        1. 对于做多(BUY)：已买入数量 - 已卖出数量
        2. 对于做空(SELL)：已卖出数量 - 已买入数量

        Returns:
            Decimal: 不平衡度，正值表示多头偏重，负值表示空头偏重
        """
        buy_volume = Decimal("0")
        sell_volume = Decimal("0")

        for level in self.levels:
            if level.executor:
                if level.side == TradeType.BUY:
                    buy_volume += level.executor.open_filled_amount
                else:
                    sell_volume += level.executor.open_filled_amount

        # 根据网格整体方向计算不平衡度
        if self.config.side == TradeType.BUY:
            return buy_volume - sell_volume
        else:
            return sell_volume - buy_volume
