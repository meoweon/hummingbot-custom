### 描述

此页面帮助您部署和管理Hummingbot实例：

- 启动和停止Hummingbot经纪人
- 创建、启动和停止机器人实例
- 管理实例运行的策略和脚本文件
- 获取正在运行实例的状态

### 部署V2

使用部署V2页面，您可以：

1. **选择控制器配置**：从已创建的配置中选择一个或多个控制器配置。
2. **设置实例参数**：
   - 实例名称：为您的机器人实例命名
   - Hummingbot镜像：选择要使用的Docker镜像
   - 凭证：选择用于交易的账户凭证
3. **风险管理设置**：
   - 最大全局回撤(%)：设置机器人允许的最大总体回撤比例
   - 最大控制器回撤(%)：设置单个控制器允许的最大回撤比例
4. **再平衡配置**：
   - 再平衡间隔(分钟)：设置自动再平衡资产的时间间隔
   - 再平衡资产：选择用于再平衡的基础资产(通常为USDT等稳定币)

### 维护者

此页面由Hummingbot基金会维护作为其他页面的模板：

* [cardosfede](https://github.com/cardosfede)
* [fengtality](https://github.com/fengtality)

### 维基

查看[维基](https://github.com/hummingbot/dashboard/wiki/%F0%9F%90%99-Bot-Orchestration)获取更多信息。 