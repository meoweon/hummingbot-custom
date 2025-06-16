import logging
from decimal import Decimal
from typing import Dict, List, Optional, Union
import asyncio

from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import PriceType, TradeType
from hummingbot.core.event.events import (
    BuyOrderCompletedEvent,
    BuyOrderCreatedEvent,
    MarketOrderFailureEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    SellOrderCompletedEvent,
    SellOrderCreatedEvent,
)
from hummingbot.logger import HummingbotLogger
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.strategy_v2.executors.executor_base import ExecutorBase
from hummingbot.strategy_v2.models.executors import CloseType
from .data_types import FlexibleGridExecutorConfig, FlexibleGridLevelStates, FlexibleGridManager
from hummingbot.strategy_v2.models.base import RunnableStatus


class FlexibleGridExecutor(ExecutorBase):
    """
    灵活网格执行器，管理多个网格层级并协调交易行为，集成全局风控和详细状态监控
    """

    _logger = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
            # cls._logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG以便排查问题
            cls._logger.setLevel(logging.INFO)
        return cls._logger

    def __init__(
        self,
        strategy: ScriptStrategyBase,
        config: FlexibleGridExecutorConfig,
        update_interval: float = 1.0,
        max_retries: int = 3,
    ):
        """
        初始化灵活网格执行器
        :param strategy: 策略实例
        :param config: 网格配置
        :param update_interval: 更新间隔（秒）
        :param max_retries: 最大重试次数
        """
        super().__init__(
            strategy=strategy,
            connectors=[config.connector_name],
            config=config,
            update_interval=update_interval,
        )
        self.config: FlexibleGridExecutorConfig = config
        self._grid_manager = FlexibleGridManager(config=config)
        self._grid_manager.initialize_levels()
        self._current_price: Optional[Decimal] = None

        # 添加交易对资产
        self.base_asset, self.quote_asset = self.config.trading_pair.split("-")

        self.logger().info(
            f"初始化灵活网格执行器 ID: {self.config.id}\n"
            # f"交易对: {self.config.trading_pair}\n"
            # f"交易所: {self.config.connector_name}\n"
            # f"方向: {self.config.side}\n"
            # f"总投资额: {self.config.total_amount_quote}\n"
            # f"网格层级数: {self.config.n_levels}"
            # f"config: {config}"
        )

    async def on_start(self):
        """
        执行器启动时调用，验证余额并记录启动信息
        """
        await super().on_start()
        self.logger().info(f"灵活网格执行器 {self.config.id} 已启动，状态: {self.status}")

    async def validate_sufficient_balance(self):
        """验证是否有足够的余额执行当前配置"""
        logger = self.logger()
        if not self.is_active:
            return

        # 计算所需资金
        connector = self._strategy.connectors[self.config.connector_name]
        trading_pair = self.config.trading_pair
        leverage = self.config.leverage or 1
        base, quote = trading_pair.split("-")

        # 根据投资模式计算所需资金
        if self.config.investment_mode == "amount_quote":
            # 按报价货币金额计算
            total_amount = self.get_total_amount_quote()
            required_quote = total_amount / leverage
            logger.debug(
                f"验证余额(报价货币模式): 交易对={trading_pair}, 杠杆={leverage}, "
                f"总投资额={total_amount} {quote}, 所需报价货币={required_quote} {quote}"
            )

            # 获取当前余额
            quote_balance = connector.get_available_balance(quote)

            # 检查余额是否足够
            if quote_balance < required_quote:
                logger.warning(
                    f"余额不足: 需要 {required_quote} {quote}, 但只有 {quote_balance} {quote} 可用。"
                    f"请充值或减少投资金额。"
                )
                self.early_stop(keep_position=True)
                return False

        else:  # amount_base 模式
            # 按基础货币数量计算
            total_amount_base = self.get_total_amount_base()
            current_price = self._current_price or self.get_price(
                self.config.connector_name, self.config.trading_pair, price_type=PriceType.MidPrice
            )

            if not current_price or current_price <= 0:
                logger.warning(f"无法获取有效价格进行余额验证")
                return False

            # 计算等值的报价货币金额
            total_amount_quote = total_amount_base * current_price
            required_quote = total_amount_quote / leverage

            logger.debug(
                f"验证余额(基础货币模式): 交易对={trading_pair}, 杠杆={leverage}, "
                f"总投资数量={total_amount_base} {base}, 等值金额={total_amount_quote} {quote}, "
                f"所需报价货币={required_quote} {quote}"
            )

            # 检查基础货币模式的特殊情况
            if self.config.side == TradeType.BUY:
                # 做多时，检查报价货币余额
                quote_balance = connector.get_available_balance(quote)
                if quote_balance < required_quote:
                    logger.warning(
                        f"余额不足: 做多需要 {required_quote} {quote}, 但只有 {quote_balance} {quote} 可用。"
                        f"请充值或减少投资金额。"
                    )
                    self.early_stop(keep_position=True)
                    return False
            else:  # TradeType.SELL
                # 做空时，如果是现货交易，需要检查基础货币余额
                # 如果是合约/保证金交易，仍然检查报价货币作为保证金
                if "perpetual" not in self.config.connector_name and "margin" not in self.config.connector_name:
                    base_balance = connector.get_available_balance(base)
                    if base_balance < total_amount_base:
                        logger.warning(
                            f"余额不足: 做空需要 {total_amount_base} {base}, 但只有 {base_balance} {base} 可用。"
                            f"请充值或减少投资数量。"
                        )
                        self.early_stop(keep_position=True)
                        return False
                else:
                    # 合约/保证金交易，检查报价货币
                    quote_balance = connector.get_available_balance(quote)
                    if quote_balance < required_quote:
                        logger.warning(
                            f"余额不足: 做空需要 {required_quote} {quote}, 但只有 {quote_balance} {quote} 可用。"
                            f"请充值或减少投资金额。"
                        )
                        self.early_stop(keep_position=True)
                        return False

        logger.debug(f"余额验证通过")
        return True

    async def control_task(self):
        """
        主控制任务，定期更新价格、层级状态并检查全局风控
        """
        if self.status == RunnableStatus.RUNNING:
            # 更新当前价格
            self._current_price = self.get_price(
                self.config.connector_name, self.config.trading_pair, price_type=PriceType.MidPrice
            )
            if self._current_price is None or self._current_price.is_nan():
                self.logger().error(
                    f"无法获取价格: 交易对={self.config.trading_pair}, 连接器={self.config.connector_name}"
                )
                return
            self.logger().debug(f"主控制任务执行 - 当前价格: {self._current_price}, 交易对: {self.config.trading_pair}")
            # 控制网格层级
            await self._grid_manager.control_levels(self._current_price, self._strategy)
            # 检查全局风控
            self._check_global_barriers()
            # 检查第一层级是否已完成
            self._check_first_level_complete()
            # 格式化信息输出
            self.to_format_status()

        elif self.status == RunnableStatus.SHUTTING_DOWN:
            await self.control_shutdown_process()

    def stop(self):
        """停止执行器并清理资源"""
        try:
            # 记录关闭时间戳
            self.close_timestamp = self._strategy.current_timestamp

            # 停止所有网格
            if hasattr(self, "_grid_manager"):
                self._grid_manager.stop_all(keep_position=self.config.keep_position)

            # 调用父类的stop方法
            super().stop()

            # 注销事件
            self.unregister_events()

            self.logger().info(f"执行器 {self.config.id} 已停止")
        except Exception as e:
            self.logger().error(f"停止执行器时出错: {str(e)}")

    def early_stop(self, keep_position: bool = False):
        """提前停止执行器"""
        try:
            self.logger().info(f"执行器 {self.config.id} 提前停止(平仓)")
            self.config.keep_position = keep_position
            self._status = RunnableStatus.SHUTTING_DOWN
        except Exception as e:
            self.logger().error(f"提前停止执行器时出错: {str(e)}")
            self.stop()

    async def control_shutdown_process(self):
        """
        控制关闭流程，确保所有资源释放
        """
        try:
            # 1. 停止所有网格级别
            self._grid_manager.stop_all(keep_position=self.config.keep_position)

            # 2. 等待所有订单完成
            while not self._all_orders_completed():
                await asyncio.sleep(0.5)

            # 3. 清理网格管理器资源
            self._grid_manager.cleanup()

            # 4. 注销事件并停止执行器
            self.stop()

            # 5. 确保状态正确设置
            self._status = RunnableStatus.TERMINATED

            self.logger().info(f"执行器 {self.config.id} 已完全终止和清理")
        except Exception as e:
            self.logger().error(f"执行器关闭过程出错: {str(e)}", exc_info=True)
            # 确保即使出错也设置终止状态
            self.stop()
            self._status = RunnableStatus.TERMINATED

    def _all_orders_completed(self) -> bool:
        """
        检查所有订单是否已完成
        """
        for level in self._grid_manager.levels:
            if level.executor and level.executor.is_active:
                return False
        return True

    def _check_first_level_complete(self):
        """
        检查第一层级是否已完成，如果是，则结束 FGE
        """
        first_level = self._grid_manager.get_level(0)
        if first_level and first_level.current_state == FlexibleGridLevelStates.COMPLETED:
            self.logger().info(f"第一层级 {first_level.id} 已完成，结束 FGE 执行器 {self.config.id}")
            self.config.keep_position = False
            self.early_stop(keep_position=self.config.keep_position)
            self.close_type = CloseType.COMPLETED

    def get_total_amount_quote(self) -> Decimal:
        """获取所有级别的投资总额（报价货币）

        在 amount_quote 模式下，直接返回所有级别的 amount_quote 之和
        在 amount_base 模式下，将每个级别的 amount_base 乘以当前价格转换为报价货币金额

        Returns:
            Decimal: 所有级别的总投资额（报价货币单位）
        """
        if self.config.investment_mode == "amount_quote":
            return sum(level.amount_quote for level in self._grid_manager.levels)
        else:  # amount_base 模式
            if self._current_price is None or self._current_price <= 0:
                return Decimal("0")
            return sum(level.amount_base * self._current_price for level in self._grid_manager.levels)

    def get_total_amount_base(self) -> Decimal:
        """获取所有级别的投资总额（基础货币）

        在 amount_base 模式下，直接返回所有级别的 amount_base 之和
        在 amount_quote 模式下，将每个级别的 amount_quote 除以当前价格转换为基础货币数量

        Returns:
            Decimal: 所有级别的总投资额（基础货币单位）
        """
        if self.config.investment_mode == "amount_base":
            return sum(level.amount_base for level in self._grid_manager.levels)
        else:  # amount_quote 模式
            if self._current_price is None or self._current_price <= 0:
                return Decimal("0")
            return sum(level.amount_quote / self._current_price for level in self._grid_manager.levels)

    def get_average_position_cost(self) -> Decimal:
        """获取平均持仓成本（报价货币）
        使用精确计算方法，基于每个级别的实际持仓和开仓价格
        """
        position_info = self._grid_manager.calculate_average_position_cost()
        return position_info["total_amount_quote"]

    def get_net_pnl_quote(self) -> Decimal:
        """
        获取所有层级的净盈亏（报价货币）
        """
        position_info = self._grid_manager.calculate_average_position_cost()
        return position_info["total_pnl_quote"]

    def get_net_pnl_pct(self) -> Decimal:
        """
        获取所有层级的净盈亏百分比，基于平均持仓成本
        """
        position_info = self._grid_manager.calculate_average_position_cost()
        net_pnl_pct = (
            position_info["total_pnl_pct"] / 100 if position_info["total_pnl_pct"] != Decimal("0") else Decimal("0")
        )
        return net_pnl_pct

    def get_cum_fees_quote(self) -> Decimal:
        """
        获取所有层级的累计费用（报价货币）
        """
        total_fees = self._grid_manager.get_total_fees()
        # self.logger().debug(f"累计费用: {total_fees} {self.config.trading_pair.split('-')[1]}")
        return total_fees

    def _check_global_barriers(self):
        """
        检查全局风控条件，包括：
        1. 价格止盈/止损 - 通过比较当前市场价格与平均持仓成本
        2. 金额止盈/止损 - 通过比较当前盈亏金额与目标金额
        3. 时间限制
        如果触发任一条件，调用 early_stop 并设置相应的 close_type。
        """
        logger = self.logger()

        # 获取持仓信息
        position_info = self._grid_manager.calculate_average_position_cost()
        trading_levels_count = position_info["trading_levels_count"]

        # 检查活跃层级是否满足全局风控的最小要求
        if trading_levels_count < self.config.min_levels_for_global_barriers:
            logger.debug(
                f"活跃层级数={trading_levels_count}，未达到全局风控最小层级数={self.config.min_levels_for_global_barriers}，跳过检查"
            )
            return

        # 获取持仓信息
        total_amount_base = position_info["total_amount_base"]
        total_amount_quote = position_info["total_amount_quote"]
        avg_entry_price = position_info["average_entry_price"]
        current_value = position_info["current_value"]
        total_pnl_quote = position_info["total_pnl_quote"]

        # 无持仓时跳过检查
        if total_amount_quote == Decimal("0") or avg_entry_price == Decimal("0"):
            logger.debug("无活跃持仓或持仓价格无效，跳过全局风控检查")
            return

        # 获取当前市场价格
        current_price = self._current_price
        if current_price is None or current_price <= 0:
            logger.warning("当前市场价格无效，跳过全局风控检查")
            return

        # 计算价格变化比例
        if self.config.side == TradeType.BUY:
            # 做多时，价格上涨为盈利，下跌为亏损
            price_change_ratio = (current_price / avg_entry_price) - Decimal("1")
        else:
            # 做空时，价格下跌为盈利，上涨为亏损
            price_change_ratio = Decimal("1") - (current_price / avg_entry_price)

        # 获取盈亏和费用信息
        total_fees = self.get_cum_fees_quote()

        logger.debug(
            f"全局风控检查: "
            f"价格变化={price_change_ratio * 100:.2f}% (入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}), "
            f"盈亏金额={total_pnl_quote:.6f}, 持仓成本={total_amount_quote:.6f}, "
            f"费用={total_fees:.6f}, 交易级别数={trading_levels_count}"
        )

        # 1. 检查基于价格的止盈条件
        if self.config.take_profit is not None:
            if self.config.side == TradeType.BUY and price_change_ratio >= self.config.take_profit:
                logger.info(
                    f"触发价格止盈: 价格上涨={price_change_ratio * 100:.2f}%, "
                    f"目标={self.config.take_profit * 100:.2f}%, "
                    f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}, "
                    f"盈亏={total_pnl_quote:.6f}"
                )
                self.config.keep_position = False
                self.close_type = CloseType.TAKE_PROFIT
                self.early_stop(keep_position=self.config.keep_position)
                return
            elif self.config.side == TradeType.SELL and price_change_ratio >= self.config.take_profit:
                logger.info(
                    f"触发价格止盈: 价格下跌={price_change_ratio * 100:.2f}%, "
                    f"目标={self.config.take_profit * 100:.2f}%, "
                    f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}, "
                    f"盈亏={total_pnl_quote:.6f}"
                )
                self.config.keep_position = False
                self.close_type = CloseType.TAKE_PROFIT
                self.early_stop(keep_position=self.config.keep_position)
                return

        # 2. 检查基于价格的止损条件
        if self.config.stop_loss is not None:
            if self.config.side == TradeType.BUY and price_change_ratio <= -self.config.stop_loss:
                logger.info(
                    f"触发价格止损: 价格下跌={price_change_ratio * 100:.2f}%, "
                    f"目标={-self.config.stop_loss * 100:.2f}%, "
                    f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}, "
                    f"盈亏={total_pnl_quote:.6f}"
                )
                self.config.keep_position = False
                self.close_type = CloseType.STOP_LOSS
                self.early_stop(keep_position=self.config.keep_position)
                return
            elif self.config.side == TradeType.SELL and price_change_ratio <= -self.config.stop_loss:
                logger.info(
                    f"触发价格止损: 价格上涨={price_change_ratio * 100:.2f}%, "
                    f"目标={-self.config.stop_loss * 100:.2f}%, "
                    f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}, "
                    f"盈亏={total_pnl_quote:.6f}"
                )
                self.config.keep_position = False
                self.close_type = CloseType.STOP_LOSS
                self.early_stop(keep_position=self.config.keep_position)
                return

        # 3. 检查基于金额的止盈条件
        if (
            self.config.profit_target_amount is not None
            and self.config.profit_target_amount > Decimal("0")
            and total_pnl_quote >= self.config.profit_target_amount
        ):
            logger.info(
                f"触发金额止盈: 当前盈亏={total_pnl_quote:.6f}, "
                f"目标金额={self.config.profit_target_amount:.6f}, "
                f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}"
            )
            self.config.keep_position = False
            self.close_type = CloseType.TAKE_PROFIT
            self.early_stop(keep_position=self.config.keep_position)
            return

        # 4. 检查基于金额的止损条件
        if (
            self.config.loss_target_amount is not None
            and self.config.loss_target_amount > Decimal("0")
            and total_pnl_quote <= -self.config.loss_target_amount
        ):
            logger.info(
                f"触发金额止损: 当前盈亏={total_pnl_quote:.6f}, "
                f"目标金额={-self.config.loss_target_amount:.6f}, "
                f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}"
            )
            self.config.keep_position = False
            self.close_type = CloseType.STOP_LOSS
            self.early_stop(keep_position=self.config.keep_position)
            return

        # 5. 检查时间限制
        if self.config.time_limit is not None:
            elapsed_time = self._strategy.current_timestamp - self.config.timestamp
            if elapsed_time >= self.config.time_limit:
                logger.info(
                    f"触发全局时间限制: 已运行={elapsed_time:.2f}秒, "
                    f"限制={self.config.time_limit}秒, "
                    f"当前盈亏={total_pnl_quote:.6f}, "
                    f"入场价={avg_entry_price:.6f}, 当前价={current_price:.6f}"
                )
                self.config.keep_position = False
                self.close_type = CloseType.TIME_LIMIT
                self.early_stop(keep_position=self.config.keep_position)
                return

        logger.debug("全局风控检查通过，未触发任何条件")

    def get_custom_info(self) -> Dict:
        """获取执行器的自定义信息，包括性能指标和状态数据"""
        if not self.is_active:
            return {}

        try:
            # 获取网格管理器的性能数据
            total_net_pnl = self._grid_manager.get_total_net_pnl_quote()
            total_fees = self._grid_manager.get_total_fees()
            active_levels = self._grid_manager.get_active_levels()
            active_count = len(active_levels)
            total_count = len(self._grid_manager.levels)

            # 获取持仓成本信息
            position_info = self._grid_manager.calculate_average_position_cost()

            # 获取成交量和不平衡度
            volume_traded = self._grid_manager.get_total_volume_traded()
            inventory_imbalance = self.get_inventory_imbalance_for_reporting()

            # 计算胜率
            win_count = sum(level.win_count for level in self._grid_manager.levels)
            loss_count = sum(level.loss_count for level in self._grid_manager.levels)
            total_trades = win_count + loss_count
            win_rate = (win_count / total_trades * 100) if total_trades > 0 else Decimal("0")

            info = {
                # 基本信息
                "executor_type": "flexible_grid_executor",
                "trading_pair": self.config.trading_pair,
                "exchange": self.config.connector_name,
                "side": self.config.side,  # TradeType 对象，不转换为字符串
                "leverage": self.config.leverage,
                "status": self.status,  # RunnableStatus 对象，不转换为字符串
                # 网格状态
                "total_levels": total_count,
                "active_levels": active_count,
                "trading_levels": position_info["trading_levels_count"],
                # 持仓信息
                "total_amount_base": position_info["total_amount_base"],
                "total_amount_quote": position_info["total_amount_quote"],
                "average_entry_price": position_info["average_entry_price"],
                "current_value": position_info["current_value"],
                # 成交和库存 - 确保是原始 Decimal 类型而不是字符串
                "volume_traded": volume_traded,
                "inventory_imbalance": inventory_imbalance,
                # 盈亏统计 - 保持为 Decimal 类型以便计算
                "total_pnl_quote": position_info["total_pnl_quote"],
                "total_pnl_pct": position_info["total_pnl_pct"],
                "total_net_pnl": total_net_pnl,
                "total_fees": total_fees,
                # 交易统计
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": win_rate,
                # 风控设置 - 这些可以是字符串格式
                "take_profit": str(self.config.take_profit * 100) + "%" if self.config.take_profit else "None",
                "stop_loss": str(self.config.stop_loss * 100) + "%" if self.config.stop_loss else "None",
                "profit_target": str(self.config.profit_target_amount) if self.config.profit_target_amount else "None",
                "loss_target": str(self.config.loss_target_amount) if self.config.loss_target_amount else "None",
            }

            # 添加调试打印，显示关键字段
            self.logger().debug(
                f"生成自定义信息 - 关键字段: side={info['side']}, "
                f"volume_traded={info['volume_traded']}, "
                f"inventory_imbalance={info['inventory_imbalance']}"
            )
            return info
        except Exception as e:
            self.logger().error(f"获取自定义信息时出错: {str(e)}", exc_info=True)
            return {}

    def to_format_status(self) -> str:
        """返回格式化状态字符串"""
        status = self._grid_manager.to_format_status()

        # 获取持仓信息
        position_info = self._grid_manager.calculate_average_position_cost()
        total_amount_base = position_info["total_amount_base"]
        total_amount_quote = position_info["total_amount_quote"]
        avg_entry_price = position_info["average_entry_price"]
        total_pnl_quote = position_info["total_pnl_quote"]
        total_pnl_pct = position_info["total_pnl_pct"]
        trading_levels_count = position_info["trading_levels_count"]
        current_value = position_info["current_value"]

        # 计算价格变化比例
        current_price = self._current_price or Decimal("0")
        if avg_entry_price > 0 and current_price > 0:
            if self.config.side == TradeType.BUY:
                # 做多时，价格上涨为盈利，下跌为亏损
                price_change_ratio = (current_price / avg_entry_price) - Decimal("1")
                price_change_pct = price_change_ratio * 100
            else:
                # 做空时，价格下跌为盈利，上涨为亏损
                price_change_ratio = Decimal("1") - (current_price / avg_entry_price)
                price_change_pct = price_change_ratio * 100
        else:
            price_change_pct = Decimal("0")

        # 格式化全局风控阈值
        price_tp_str = f"{self.config.take_profit * 100:.2f}%" if self.config.take_profit else "无"
        price_sl_str = f"{self.config.stop_loss * 100:.2f}%" if self.config.stop_loss else "无"
        amount_tp_str = f"{self.config.profit_target_amount:.6f}" if self.config.profit_target_amount else "无"
        amount_sl_str = f"{self.config.loss_target_amount:.6f}" if self.config.loss_target_amount else "无"

        # 添加投资模式信息
        investment_mode = self.config.investment_mode
        asset_type = self.base_asset if investment_mode == "amount_base" else self.quote_asset

        # 计算总投资额和活跃投资额
        active_levels = self._grid_manager.get_active_levels()

        if investment_mode == "amount_quote":
            total_amount = self.get_total_amount_quote()
            active_amount = sum(level.amount_quote for level in active_levels)
        else:  # amount_base 模式
            total_amount = self.get_total_amount_base()
            active_amount = sum(level.amount_base for level in active_levels)

        # 计算资金使用率
        amount_usage = (active_amount / total_amount * 100) if total_amount > 0 else Decimal("0")

        # 添加全局风控信息
        risk_info = [
            "╔════════════════════════ 全局风控信息 ═══════════════════════╗",
            "║                                                            ║",
            f"║ 投资模式: {investment_mode} (使用 {asset_type})                   ║",
            f"║ 资金使用: {amount_usage:.2f}% ({active_amount:.6f}/{total_amount:.6f} {asset_type})   ║",
            "║                                                            ║",
            f"║ 当前价格: {current_price:.6f}                               ║",
            f"║ 平均持仓价格: {avg_entry_price:.6f}                          ║",
            f"║ 价格变化: {price_change_pct:.2f}%                           ║",
            "║                                                            ║",
            f"║ 盈亏金额: {total_pnl_quote:.6f} {self.quote_asset}          ║",
            f"║ 盈亏比例: {total_pnl_pct:.2f}%                             ║",
            "║                                                            ║",
            "║ 全局风控阈值:                                               ║",
            f"║   价格止盈: {price_tp_str}    价格止损: {price_sl_str}       ║",
            f"║   金额止盈: {amount_tp_str}    金额止损: {amount_sl_str}     ║",
            "║                                                            ║",
            "╚════════════════════════════════════════════════════════════╝",
            "",
        ]

        # 将风控信息添加到网格状态之前
        status = "\n".join(risk_info) + "\n\n" + status
        print(status)
        return status

    def process_order_completed_event(
        self, event_tag: int, market: ConnectorBase, event: Union[BuyOrderCompletedEvent, SellOrderCompletedEvent]
    ):
        """处理订单完成事件"""
        # 构造trading_pair
        trading_pair = f"{event.base_asset}-{event.quote_asset}"
        # 计算成交价格
        price = event.quote_asset_amount / event.base_asset_amount if event.base_asset_amount != 0 else Decimal("0")
        self.logger().info(
            f"订单完成 - 交易对: {trading_pair}, 订单ID: {event.order_id}, "
            f"数量: {event.base_asset_amount} {event.base_asset}, "
            f"总额: {event.quote_asset_amount} {event.quote_asset}, "
            f"价格: {price}, 订单类型: {event.order_type}"
        )

        # 在传递给网格管理器之前，确保事件对象有price属性用于记录平仓
        if not hasattr(event, "price"):
            # 添加price属性以供record_close使用
            event.price = price

        # 更新网格管理器
        self._grid_manager.handle_order_completed(event)

    def process_order_created_event(
        self, event_tag: int, market: ConnectorBase, event: Union[BuyOrderCreatedEvent, SellOrderCreatedEvent]
    ):
        """处理订单创建事件"""
        if not self.is_active:
            return

        # 使用正确的属性获取价格和数量
        price = event.price
        amount = event.amount

        self.logger().info(
            f"订单创建 - 交易对: {event.trading_pair}, "
            f"订单ID: {event.order_id}, "
            f"数量: {amount}, "
            f"价格: {price}, "
            f"订单类型: {event.type}"
        )

        # 更新网格管理器
        self._grid_manager.handle_order_created(event)

    def process_order_filled_event(self, event_tag: int, market: ConnectorBase, event: OrderFilledEvent):
        """处理订单成交事件

        OrderFilledEvent属性:
        - timestamp: float
        - order_id: str
        - trading_pair: str
        - trade_type: TradeType
        - order_type: OrderType
        - price: Decimal
        - amount: Decimal
        - trade_fee: TradeFeeBase
        - exchange_trade_id: str
        - exchange_order_id: str
        - leverage: Optional[int]
        - position: Optional[str]
        """
        self.logger().info(
            f"订单成交 - 交易对: {event.trading_pair}, 订单ID: {event.order_id}, "
            f"类型: {event.trade_type.name}, 价格: {event.price}, 数量: {event.amount}, "
            f"手续费: {event.trade_fee}, 杠杆: {event.leverage}x"
        )
        self._grid_manager.handle_order_filled(event)

    def process_order_canceled_event(self, event_tag: int, market: ConnectorBase, event: OrderCancelledEvent):
        """处理订单取消事件

        OrderCancelledEvent属性:
        - timestamp: float
        - order_id: str
        - exchange_order_id: Optional[str]
        """
        self.logger().info(
            f"订单已取消 - 订单ID: {event.order_id}"
            + (f", 交易所订单ID: {event.exchange_order_id}" if event.exchange_order_id else "")
        )
        self._grid_manager.handle_order_canceled(event)

    def process_order_failed_event(self, event_tag: int, market: ConnectorBase, event: MarketOrderFailureEvent):
        """处理订单失败事件

        MarketOrderFailureEvent属性:
        - timestamp: float
        - order_id: str
        - order_type: OrderType
        """
        self.logger().error(f"订单失败 - 订单ID: {event.order_id}, 订单类型: {event.order_type}")
        self._grid_manager.handle_order_failed(event)

    @property
    def filled_amount_quote(self) -> Decimal:
        """返回以报价货币计价的已成交金额

        在 FlexibleGridExecutor 中，这个值应该是所有网格级别的总成交量
        这个属性对于 ExecutorInfo 和性能报告计算非常重要
        """
        if not self.is_active:
            return Decimal("0")

        total_volume = Decimal("0")
        for level in self._grid_manager.levels:
            if level.executor:
                # 累加每个级别中执行器的成交量
                if hasattr(level.executor, "filled_amount_quote"):
                    total_volume += level.executor.filled_amount_quote
                # 如果执行器是开仓状态，也累加open_filled_amount和close_filled_amount
                elif hasattr(level.executor, "open_filled_amount") and level.executor.open_filled_amount:
                    if level.executor.is_trading:
                        # 获取当前价格（或者最后成交价格）
                        price = level.last_open_price if level.last_open_price > 0 else self._current_price
                        if price and price > 0:
                            total_volume += level.executor.open_filled_amount * price

        self.logger().debug(f"FlexibleGridExecutor {self.config.id} 报告总成交量: {total_volume}")
        return total_volume

    def get_inventory_imbalance_for_reporting(self) -> Decimal:
        """计算库存不平衡度，用于性能报告

        根据ExecutorOrchestrator.generate_performance_report的逻辑:
        - 对做多(BUY)方向，报告已成交的报价货币金额(filled_amount_quote)
        - 对做空(SELL)方向，报告已成交的报价货币金额的负值(-filled_amount_quote)

        Returns:
            Decimal: 不平衡度，正值表示多头偏重，负值表示空头偏重
        """
        # 获取每个级别的持仓信息，计算累计不平衡度
        imbalance = self._grid_manager.get_inventory_imbalance()

        # 将基础货币不平衡转换为报价货币不平衡（如果current_price有效）
        if self._current_price and self._current_price > 0:
            imbalance = imbalance * self._current_price

        self.logger().debug(f"FlexibleGridExecutor {self.config.id} 报告库存不平衡: {imbalance}")
        return imbalance
