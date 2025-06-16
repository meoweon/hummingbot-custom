import os
import time
from decimal import Decimal
from typing import Dict, List, Optional, Set

from hummingbot.client.hummingbot_application import HummingbotApplication
from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.clock import Clock
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.remote_iface.mqtt import ETopicPublisher
from hummingbot.strategy.strategy_v2_base import StrategyV2Base, StrategyV2ConfigBase
from hummingbot.strategy_v2.models.base import RunnableStatus
from hummingbot.strategy_v2.models.executor_actions import (
    CreateExecutorAction,
    ExecutorAction,
    StopExecutorAction,
)


class GenericV2StrategyWithCashOutConfig(StrategyV2ConfigBase):
    """
    策略配置类，定义了策略运行所需的各种参数。
    """

    script_file_name: str = os.path.basename(__file__)  # 脚本文件名，用于标识当前脚本
    candles_config: List[CandlesConfig] = []  # 蜡烛图配置列表，用于市场数据分析
    markets: Dict[str, Set[str]] = {}  # 市场配置，键为连接器名称，值为交易对集合
    time_to_cash_out: Optional[int] = None  # 自动退出时间（秒），到达该时间后停止策略
    max_global_drawdown: Optional[float] = None  # 全局最大回撤，超过此值停止整个策略
    max_controller_drawdown: Optional[float] = (
        None  # 控制器最大回撤，超过此值停止特定控制器
    )
    rebalance_interval: Optional[int] = None  # 再平衡间隔（秒），定期调整持仓
    extra_inventory: Optional[float] = 0.02  # 额外库存比例，用于安全余量
    min_amount_to_rebalance_usd: Decimal = Decimal(
        "8"
    )  # 再平衡最小金额（美元），低于此值不调整
    asset_to_rebalance: str = "USDT"  # 再平衡资产，通常为基础货币
    config_update_interval: int = 10  # 配置更新间隔（秒），定期检查配置变化
    max_active_controllers: Optional[int] = (
        None  # 最大同时持仓的控制器数量，None表示不限制
    )


class GenericV2StrategyWithCashOut(StrategyV2Base):
    """
    通用策略类，带有退出功能。支持自动和手动退出，并定期检查控制器配置更新。
    - 自动退出：通过 time_to_cash_out 参数设置，时间到达后停止所有控制器。
    - 手动退出：通过控制器配置中的 manual_kill_switch 参数触发，停止特定控制器。
    - 最大回撤：监控全局和控制器级别的回撤，超出限制时停止运行。
    """

    performance_report_interval: int = 1  # 性能报告间隔（秒），控制报告生成频率

    def __init__(
        self,
        connectors: Dict[str, ConnectorBase],
        config: GenericV2StrategyWithCashOutConfig,
    ):
        """
        初始化策略，设置配置和初始状态。
        :param connectors: 连接器字典，提供市场交易接口
        :param config: 策略配置对象，包含所有参数
        """
        super().__init__(connectors, config)
        self.config = config  # 保存配置对象
        self.cashing_out = False  # 是否正在退出，控制退出流程
        self.max_pnl_by_controller = {}  # 每个控制器的最大利润，用于回撤计算
        self.performance_reports = {}  # 性能报告，存储每个控制器的表现
        self.max_global_pnl = Decimal("0")  # 全局最大利润，用于全局回撤计算
        self.drawdown_exited_controllers = []  # 因回撤退出的控制器列表
        self.closed_executors_buffer: int = 30  # 关闭执行器的缓冲时间（秒）
        self.rebalance_interval: int = (
            self.config.rebalance_interval
        )  # 再平衡间隔，从配置中获取
        self._last_performance_report_timestamp = 0  # 上次性能报告时间戳
        self._last_rebalance_check_timestamp = 0  # 上次再平衡检查时间戳
        hb_app = HummingbotApplication.main_application()
        self.mqtt_enabled = hb_app._mqtt is not None  # 是否启用 MQTT，用于性能报告发布
        self._pub: Optional[ETopicPublisher] = None  # MQTT 发布器对象
        if self.config.time_to_cash_out:
            self.cash_out_time = (
                self.config.time_to_cash_out + time.time()
            )  # 计算退出时间
        else:
            self.cash_out_time = None  # 未设置退出时间

    def start(self, clock: Clock, timestamp: float) -> None:
        """
        启动策略，设置初始时间并应用初始设置。
        :param clock: 时钟对象，用于时间管理
        :param timestamp: 当前时间戳
        """
        self._last_timestamp = timestamp  # 记录启动时间
        self.apply_initial_setting()  # 应用初始设置，如杠杆和仓位模式
        if self.mqtt_enabled:
            self._pub = ETopicPublisher(
                "performance", use_bot_prefix=True
            )  # 初始化 MQTT 发布器

    async def on_stop(self):
        """
        停止策略，清理资源。
        """
        await super().on_stop()  # 调用父类的停止方法
        if self.mqtt_enabled:
            self._pub(
                {controller_id: {} for controller_id in self.controllers.keys()}
            )  # 发送空的性能报告
            self._pub = None  # 清理发布器

    def on_tick(self):
        """
        每 tick 执行，生成性能报告并控制再平衡、退出和最大回撤。
        """
        super().on_tick()  # 调用父类的 tick 方法
        self.performance_reports = {
            controller_id: self.executor_orchestrator.generate_performance_report(
                controller_id=controller_id
            ).dict()
            for controller_id in self.controllers.keys()
        }  # 生成每个控制器的性能报告
        self.control_rebalance()  # 检查并执行再平衡
        self.control_cash_out()  # 控制退出逻辑
        self.control_max_drawdown()  # 控制最大回撤
        self.send_performance_report()  # 发送性能报告

    def control_rebalance(self):
        """
        控制再平衡，定期检查并调整持仓以满足需求。
        """
        if (
            self.rebalance_interval
            and self._last_rebalance_check_timestamp + self.rebalance_interval
            <= self.current_timestamp
        ):
            balance_required = {}  # 存储每个连接器的余额需求
            for controller_id, controller in self.controllers.items():
                connector_name = controller.config.model_dump().get("connector_name")
                if connector_name and "perpetual" in connector_name:
                    continue  # 跳过永续合约连接器
                if connector_name not in balance_required:
                    balance_required[connector_name] = {}
                tokens_required = controller.get_balance_requirements()  # 获取余额需求
                for token, amount in tokens_required:
                    if token not in balance_required[connector_name]:
                        balance_required[connector_name][token] = amount
                    else:
                        balance_required[connector_name][token] += amount
            for connector_name, balance_requirements in balance_required.items():
                connector = self.connectors[connector_name]
                for token, amount in balance_requirements.items():
                    if token == self.config.asset_to_rebalance:
                        continue  # 跳过再平衡资产本身
                    balance = connector.get_balance(token)  # 获取当前余额
                    trading_pair = f"{token}-{self.config.asset_to_rebalance}"  # 交易对
                    mid_price = connector.get_mid_price(trading_pair)  # 中间价格
                    trading_rule = connector.trading_rules[trading_pair]  # 交易规则
                    amount_with_safe_margin = amount * (
                        1 + Decimal(self.config.extra_inventory)
                    )  # 带安全余量的需求量
                    active_executors_for_pair = self.filter_executors(
                        executors=self.get_all_executors(),
                        filter_func=lambda x: x.is_active
                        and x.trading_pair == trading_pair
                        and x.connector_name == connector_name,
                    )  # 筛选活跃执行器
                    unmatched_amount = sum(
                        [
                            executor.filled_amount_quote
                            for executor in active_executors_for_pair
                            if executor.side == TradeType.SELL
                        ]
                    ) - sum(
                        [
                            executor.filled_amount_quote
                            for executor in active_executors_for_pair
                            if executor.side == TradeType.BUY
                        ]
                    )  # 计算未匹配金额
                    balance += unmatched_amount / mid_price  # 调整余额
                    base_balance_diff = balance - amount_with_safe_margin  # 余额差
                    abs_balance_diff = abs(base_balance_diff)  # 绝对差值
                    trading_rules_condition = (
                        abs_balance_diff > trading_rule.min_order_size
                        and abs_balance_diff * mid_price
                        > trading_rule.min_notional_size
                        and abs_balance_diff * mid_price
                        > self.config.min_amount_to_rebalance_usd
                    )  # 检查交易规则条件
                    order_type = OrderType.MARKET  # 订单类型为市价单
                    if base_balance_diff > 0:  # 余额过多，卖出
                        if trading_rules_condition:
                            self.logger().info(
                                f"再平衡：卖出 {amount_with_safe_margin} {token} 至 {self.config.asset_to_rebalance}。余额：{balance} | 执行器未匹配余额 {unmatched_amount / mid_price}"
                            )
                            connector.sell(
                                trading_pair=trading_pair,
                                amount=abs_balance_diff,
                                order_type=order_type,
                                price=mid_price,
                            )
                        else:
                            self.logger().info(
                                "由于卖出金额过低可能导致未来不平衡，跳过再平衡"
                            )
                    else:  # 余额不足，买入
                        if not trading_rules_condition:
                            amount = max(
                                [
                                    self.config.min_amount_to_rebalance_usd / mid_price,
                                    trading_rule.min_order_size,
                                    trading_rule.min_notional_size / mid_price,
                                ]
                            )
                            self.logger().info(
                                f"再平衡：买入更高价值以避免未来不平衡 {amount} {token} 至 {self.config.asset_to_rebalance}。余额：{balance} | 执行器未匹配余额 {unmatched_amount}"
                            )
                        else:
                            amount = abs_balance_diff
                            self.logger().info(
                                f"再平衡：买入 {amount} {token} 至 {self.config.asset_to_rebalance}。余额：{balance} | 执行器未匹配余额 {unmatched_amount}"
                            )
                        connector.buy(
                            trading_pair=trading_pair,
                            amount=amount,
                            order_type=order_type,
                            price=mid_price,
                        )
            self._last_rebalance_check_timestamp = self.current_timestamp  # 更新时间戳

    def control_max_drawdown(self):
        """
        控制最大回撤，检查控制器和全局回撤并采取行动。
        """
        if self.config.max_controller_drawdown:
            self.check_max_controller_drawdown()  # 检查控制器回撤
        if self.config.max_global_drawdown:
            self.check_max_global_drawdown()  # 检查全局回撤

    def check_max_controller_drawdown(self):
        """
        检查每个控制器的回撤，超出限制时停止控制器。
        """
        for controller_id, controller in self.controllers.items():
            if controller.status != RunnableStatus.RUNNING:
                continue  # 跳过非运行状态的控制器
            controller_pnl = self.performance_reports[controller_id][
                "global_pnl_quote"
            ]  # 当前利润
            last_max_pnl = self.max_pnl_by_controller[controller_id]  # 历史最大利润
            if controller_pnl > last_max_pnl:
                self.max_pnl_by_controller[controller_id] = (
                    controller_pnl  # 更新最大利润
                )
            else:
                current_drawdown = last_max_pnl - controller_pnl  # 计算当前回撤
                if current_drawdown > self.config.max_controller_drawdown:
                    self.logger().info(
                        f"控制器 {controller_id} 达到最大回撤，停止该控制器。"
                    )
                    controller.stop()  # 停止控制器
                    executors_order_placed = self.filter_executors(
                        executors=self.executors_info[controller_id],
                        filter_func=lambda x: x.is_active and not x.is_trading,
                    )  # 筛选待停止的执行器
                    self.executor_orchestrator.execute_actions(
                        actions=[
                            StopExecutorAction(
                                controller_id=controller_id, executor_id=executor.id
                            )
                            for executor in executors_order_placed
                        ]
                    )  # 执行停止动作
                    self.drawdown_exited_controllers.append(
                        controller_id
                    )  # 记录退出控制器

    def check_max_global_drawdown(self):
        """
        检查全局回撤，超出限制时停止整个策略。
        """
        current_global_pnl = sum(
            [report["global_pnl_quote"] for report in self.performance_reports.values()]
        )  # 计算当前全局利润
        if current_global_pnl > self.max_global_pnl:
            self.max_global_pnl = current_global_pnl  # 更新全局最大利润
        else:
            current_global_drawdown = (
                self.max_global_pnl - current_global_pnl
            )  # 计算全局回撤
            if current_global_drawdown > self.config.max_global_drawdown:
                self.drawdown_exited_controllers.extend(
                    list(self.controllers.keys())
                )  # 记录所有控制器
                self.logger().info("全局回撤达到限制，停止策略。")
                HummingbotApplication.main_application().stop()  # 停止应用

    def send_performance_report(self):
        """
        发送性能报告，通过 MQTT 发布。
        """
        if (
            self.current_timestamp - self._last_performance_report_timestamp
            >= self.performance_report_interval
            and self.mqtt_enabled
        ):
            self._pub(self.performance_reports)  # 发布性能报告
            self._last_performance_report_timestamp = (
                self.current_timestamp
            )  # 更新时间戳

    def control_cash_out(self):
        """
        控制退出逻辑，处理自动和手动退出。
        """
        self.evaluate_cash_out_time()  # 评估自动退出时间
        if self.cashing_out:
            self.check_executors_status()  # 检查执行器状态
        else:
            self.check_manual_cash_out()  # 检查手动退出

    def evaluate_cash_out_time(self):
        """
        评估自动退出时间，到达时停止所有控制器。
        """
        if (
            self.cash_out_time
            and self.current_timestamp >= self.cash_out_time
            and not self.cashing_out
        ):
            self.logger().info("到达退出时间，停止所有控制器。")
            for controller_id, controller in self.controllers.items():
                if controller.status == RunnableStatus.RUNNING:
                    self.logger().info(f"退出控制器 {controller_id}。")
                    controller.stop()  # 停止运行中的控制器
            self.cashing_out = True  # 标记为退出状态

    def check_manual_cash_out(self):
        """
        检查手动退出，处理控制器的手动停止和重启。
        """
        for controller_id, controller in self.controllers.items():
            if (
                controller.config.manual_kill_switch
                and controller.status == RunnableStatus.RUNNING
            ):
                self.logger().info(f"手动退出控制器 {controller_id}。")
                controller.stop()  # 停止控制器
                executors_to_stop = self.get_executors_by_controller(
                    controller_id
                )  # 获取相关执行器
                self.executor_orchestrator.execute_actions(
                    [
                        StopExecutorAction(
                            executor_id=executor.id,
                            controller_id=executor.controller_id,
                        )
                        for executor in executors_to_stop
                    ]
                )  # 执行停止动作
            if (
                not controller.config.manual_kill_switch
                and controller.status == RunnableStatus.TERMINATED
            ):
                if controller_id in self.drawdown_exited_controllers:
                    continue  # 跳过因回撤退出的控制器
                self.logger().info(f"重启控制器 {controller_id}。")
                controller.start()  # 重启控制器

    def check_executors_status(self):
        """
        检查执行器状态，所有执行器完成后停止策略。
        """
        active_executors = self.filter_executors(
            executors=self.get_all_executors(),
            filter_func=lambda executor: executor.status == RunnableStatus.RUNNING,
        )  # 筛选活跃执行器
        if not active_executors:
            self.logger().info("所有执行器已完成执行，停止策略。")
            HummingbotApplication.main_application().stop()  # 停止应用
        else:
            non_trading_executors = self.filter_executors(
                executors=active_executors,
                filter_func=lambda executor: not executor.is_trading,
            )  # 筛选非交易执行器
            self.executor_orchestrator.execute_actions(
                [
                    StopExecutorAction(
                        executor_id=executor.id, controller_id=executor.controller_id
                    )
                    for executor in non_trading_executors
                ]
            )  # 停止非交易执行器

    def create_actions_proposal(self) -> List[CreateExecutorAction]:
        """
        创建行动提案，目前为空实现。
        :return: 创建执行器动作列表
        """
        return []

    def stop_actions_proposal(self) -> List[StopExecutorAction]:
        """
        停止行动提案，目前为空实现。
        :return: 停止执行器动作列表
        """
        return []

    def determine_executor_actions(self) -> List[ExecutorAction]:
        """
        决定执行器动作，实现最大活跃控制器数量限制。
        收集所有控制器的动作建议，并根据最大活跃控制器数量限制过滤创建新执行器的动作。
        """
        # 详细日志：打印所有控制器及其执行器的状态
        self.logger().debug("===== 执行器状态详细日志 =====")
        all_executors_count = 0
        potentially_active_controllers = set()

        for (
            controller_id,
            executors,
        ) in self.executor_orchestrator.active_executors.items():
            if not executors:
                self.logger().debug(f"控制器 {controller_id}: 无执行器")
                continue

            potentially_active_controllers.add(controller_id)
            self.logger().debug(
                f"控制器 {controller_id}: 共有 {len(executors)} 个执行器"
            )
            all_executors_count += len(executors)

            # 详细打印每个执行器的状态
            for i, e in enumerate(executors):
                if e:
                    executor_id = (
                        getattr(e, "id", "未知ID")
                        if hasattr(e, "id")
                        else (
                            getattr(e.config, "id", "未知ID")
                            if hasattr(e, "config")
                            else "未知ID"
                        )
                    )
                    is_active = getattr(e, "is_active", False)
                    is_trading = getattr(e, "is_trading", False)
                    self.logger().debug(
                        f"  - 执行器[{i}] ID: {executor_id}, 活跃: {is_active}, 交易中: {is_trading}"
                    )
                else:
                    self.logger().debug(f"  - 执行器[{i}]: None (可能是空引用)")

        self.logger().debug(
            f"系统中共有 {len(potentially_active_controllers)} 个潜在活跃控制器, {all_executors_count} 个执行器"
        )

        # 获取当前活跃控制器数量 - 只计算真正有活跃执行器的控制器
        active_controllers = set()
        for (
            controller_id,
            executors,
        ) in self.executor_orchestrator.active_executors.items():
            # 仅当有非空且活跃的执行器时才将该控制器视为活跃
            active_executors = [
                e for e in executors if e and e.is_active and e.is_trading
            ]
            if active_executors:  # 如果该控制器有活跃执行器
                active_controllers.add(controller_id)
                self.logger().debug(
                    f"控制器 {controller_id} 有 {len(active_executors)} 个真正活跃的执行器"
                )
            else:
                if executors:
                    self.logger().debug(
                        f"控制器 {controller_id} 有执行器但没有真正活跃的交易执行器"
                    )

        # 记录实际活跃的控制器数量用于调试
        self.logger().debug(
            f"真正活跃控制器数量: {len(active_controllers)}, 活跃控制器列表: {active_controllers}"
        )

        # 获取配置的最大活跃控制器数量
        max_active = self.config.max_active_controllers
        self.logger().debug(f"最大活跃控制器数量限制: {max_active}")

        actions = []
        # 处理每个控制器的建议动作
        for controller_id, controller in self.controllers.items():
            self.logger().debug(
                f"控制器 {controller_id} 初始化状态: {controller.status}"
            )
            # 获取控制器的动作建议
            controller_actions = controller.determine_executor_actions()

            # 打印每个控制器的建议动作
            create_actions = [
                a for a in controller_actions if isinstance(a, CreateExecutorAction)
            ]
            stop_actions = [
                a for a in controller_actions if isinstance(a, StopExecutorAction)
            ]
            self.logger().debug(
                f"控制器 {controller_id} 建议动作: {len(create_actions)} 创建, {len(stop_actions)} 停止"
            )

            # 如果已达上限且该控制器当前无活跃执行器，过滤掉创建新执行器的动作
            if (
                max_active is not None
                and len(active_controllers) >= max_active
                and controller_id not in active_controllers
            ):
                # 过滤掉CreateExecutorAction，保留其他动作如StopExecutorAction
                filtered_actions = [
                    action
                    for action in controller_actions
                    if not isinstance(action, CreateExecutorAction)
                ]

                # 记录被过滤掉的创建动作
                filtered_out = len(controller_actions) - len(filtered_actions)
                self.logger().debug(
                    f"控制器 {controller_id}: 过滤掉 {filtered_out} 个创建动作，保留 {len(filtered_actions)} 个其他动作"
                )

                actions.extend(filtered_actions)
                # 记录日志，表明由于达到最大控制器数量而过滤了该控制器的开仓信号
                self.logger().debug(
                    f"过滤控制器 {controller_id} 的开仓信号 - 已达到最大活跃控制器数量限制 {max_active}，"
                    f"当前活跃控制器: {active_controllers}"
                )
            else:
                # 否则，保留所有动作建议
                self.logger().debug(
                    f"控制器 {controller_id}: 全部保留 {len(controller_actions)} 个动作建议"
                )
                actions.extend(controller_actions)

        # 添加策略自身的动作建议
        strategy_create = self.create_actions_proposal()
        strategy_stop = self.stop_actions_proposal()
        if strategy_create or strategy_stop:
            self.logger().debug(
                f"策略自身建议: {len(strategy_create)} 创建, {len(strategy_stop)} 停止"
            )

        actions.extend(strategy_create)
        actions.extend(strategy_stop)

        self.logger().debug(f"最终决定执行 {len(actions)} 个动作")
        self.logger().debug("===== 执行器状态详细日志结束 =====")

        return actions

    def apply_initial_setting(self):
        """
        应用初始设置，设置杠杆和仓位模式。
        """
        connectors_position_mode = {}  # 存储连接器的仓位模式
        for controller_id, controller in self.controllers.items():
            self.max_pnl_by_controller[controller_id] = Decimal("0")  # 初始化最大利润
            config_dict = controller.config.dict()  # 获取控制器配置
            if "connector_name" in config_dict:
                if self.is_perpetual(
                    config_dict["connector_name"]
                ):  # 检查是否为永续合约
                    if "position_mode" in config_dict:
                        connectors_position_mode[config_dict["connector_name"]] = (
                            config_dict["position_mode"]
                        )  # 设置仓位模式
                    if "leverage" in config_dict:
                        self.connectors[config_dict["connector_name"]].set_leverage(
                            leverage=config_dict["leverage"],
                            trading_pair=config_dict["trading_pair"],
                        )  # 设置杠杆
        for connector_name, position_mode in connectors_position_mode.items():
            self.connectors[connector_name].set_position_mode(
                position_mode
            )  # 应用仓位模式
