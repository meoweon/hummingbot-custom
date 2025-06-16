以下是基于提供的 Hummingbot-backend-api OpenAPI 文档中 `"Docker Management"` 和 `"Manage Broker Messages"` 标签下的 API 设计，编写的容器和机器人管理 API 文档。文档将遵循与 `"Manage Credentials"` API 文档相似的格式，逐一介绍调用方法、参数、使用实例、返回示例、使用场景和注意事项。我会确保内容准确、详尽，并与 OpenAPI 规范一致，同时补充必要的细节。

---

## 容器和机器人管理 API 文档

以下是针对 `"Docker Management"` 和 `"Manage Broker Messages"` 标签下的 API 的详细描述。这些 API 用于管理 Docker 容器和 Hummingbot 机器人实例，包括创建、启动、停止、移除容器，以及管理机器人状态和策略。

---

### 1. GET /is-docker-running
#### 功能
检查 Docker 服务是否正在运行。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/is-docker-running`
- **认证**: HTTP Basic（需要用户名和密码）
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/is-docker-running" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "status": true
  }
  ```
- **文档定义**: 返回类型为 `object`，具体字段未定义，需参考后端实现。示例中假设返回一个包含 `status` 字段的对象。

#### 使用场景
- 在创建或管理容器前，确认 Docker 服务是否可用。
- 系统初始化时检查环境状态。

#### 注意事项
- 如果返回 `false`，需检查 Docker 服务是否已启动。
- 建议在所有容器操作前调用此 API，确保环境就绪。
- **文档补充**: 文档未明确返回字段，实际字段需通过后端实现确认。

---

### 2. GET /available-images/{image_name}
#### 功能
检查指定 Docker 镜像是否可用。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/available-images/{image_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `image_name`（string，必填），镜像名称，例如 `"hummingbot/hummingbot:latest"`

#### 使用实例
```bash
curl -X GET "http://localhost:8000/available-images/hummingbot%2Fhummingbot:latest" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "available": true,
    "image_name": "hummingbot/hummingbot:latest"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "image_name"],
        "msg": "Invalid image name",
        "type": "value_error"
      }
    ]
  }
  ```
- **文档定义**: 返回类型为 `object`，具体字段未定义，需参考实现。

#### 使用场景
- 在创建 Hummingbot 实例前，检查所需镜像是否存在。
- 确认是否需要拉取新镜像。

#### 注意事项
- 镜像名称需正确编码（例如 `/` 需编码为 `%2F`）。
- 如果镜像不可用，可调用 `POST /pull-image/` 拉取镜像。

---

### 3. GET /active-containers
#### 功能
列出所有正在运行的 Docker 容器。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/active-containers`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/active-containers" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  [
    {
      "container_name": "grid_bot_1",
      "image": "hummingbot/hummingbot:latest",
      "status": "running"
    },
    {
      "container_name": "grid_bot_2",
      "image": "hummingbot/hummingbot:latest",
      "status": "running"
    }
  ]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `object`，具体字段未定义。

#### 使用场景
- 查看当前运行的 Hummingbot 实例。
- 监控容器状态。

#### 注意事项
- 返回数据可能为空，表示无运行中的容器。
- 建议定期调用以监控容器状态。

---

### 4. GET /exited-containers
#### 功能
列出所有已退出的 Docker 容器。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/exited-containers`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/exited-containers" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  [
    {
      "container_name": "grid_bot_3",
      "image": "hummingbot/hummingbot:latest",
      "status": "exited",
      "exit_code": 0
    }
  ]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `object`，具体字段未定义。

#### 使用场景
- 检查已停止的容器，决定是否清理。
- 排查容器异常退出原因。

#### 注意事项
- 可结合 `POST /clean-exited-containers` 清理已退出容器。
- 检查 `exit_code` 以了解容器退出原因。

---

### 5. POST /clean-exited-containers
#### 功能
清理所有已退出的 Docker 容器。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/clean-exited-containers`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X POST "http://localhost:8000/clean-exited-containers" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Exited containers cleaned successfully",
    "removed": ["grid_bot_3"]
  }
  ```
- **文档定义**: 返回类型为 `object`，具体字段未定义。

#### 使用场景
- 定期清理已退出容器，释放资源。
- 在系统维护时使用。

#### 注意事项
- 操作不可逆，清理前确认无重要数据。
- 可先调用 `GET /exited-containers` 查看待清理容器。

---

### 6. POST /remove-container/{container_name}
#### 功能
移除指定 Docker 容器。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/remove-container/{container_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `container_name`（string，必填），容器名称
  - **查询参数**:
    - `archive_locally`（boolean，可选，默认为 `true`），是否本地归档
    - `s3_bucket`（string，可选），S3 存储桶名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/remove-container/grid_bot_1?archive_locally=true&s3_bucket=my-bucket" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Container removed successfully",
    "container_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "container_name"],
        "msg": "Container not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 删除不再使用的 Hummingbot 实例。
- 清理异常容器。

#### 注意事项
- 容器需先停止（调用 `POST /stop-container/{container_name}`）。
- 如果 `archive_locally` 为 `true`，确保本地存储空间足够。
- 如果指定 `s3_bucket`，确保 S3 配置正确。

---

### 7. POST /stop-container/{container_name}
#### 功能
停止指定 Docker 容器。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/stop-container/{container_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `container_name`（string，必填），容器名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/stop-container/grid_bot_1" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Container stopped successfully",
    "container_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "container_name"],
        "msg": "Container not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 暂停运行中的 Hummingbot 实例。
- 在移除容器前停止容器。

#### 注意事项
- 停止容器可能导致策略中断，需确认无未完成交易。
- 可结合 `GET /active-containers` 确认容器状态。

---

### 8. POST /start-container/{container_name}
#### 功能
启动指定 Docker 容器。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/start-container/{container_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `container_name`（string，必填），容器名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/start-container/grid_bot_1" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Container started successfully",
    "container_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "container_name"],
        "msg": "Container not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 启动已创建但未运行的 Hummingbot 实例。
- 恢复暂停的容器。

#### 注意事项
- 确保容器配置（如脚本和凭证）正确，否则启动可能失败。
- 启动后可调用 `GET /get-bot-status/{bot_name}` 检查状态。

---

### 9. POST /create-hummingbot-instance
#### 功能
创建新的 Hummingbot 实例（Docker 容器）。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/create-hummingbot-instance`
- **认证**: HTTP Basic
- **参数**:
  - **请求体**: JSON 对象，包含实例配置。
    ```json
    {
      "instance_name": "grid_bot_1",
      "credentials_profile": "my_account/binance",
      "image": "hummingbot/hummingbot:latest",
      "script": "grid_strategy.py",
      "script_config": "grid_config_1.yml"
    }
    ```
    - `instance_name`（string，必填），实例名称
    - `credentials_profile`（string，必填），凭证配置文件
    - `image`（string，可选，默认为 `"hummingbot/hummingbot:latest"`），Docker 镜像
    - `script`（string，可选），策略脚本
    - `script_config`（string，可选），脚本配置文件

#### 使用实例
```bash
curl -X POST "http://localhost:8000/create-hummingbot-instance" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"instance_name": "grid_bot_1", "credentials_profile": "my_account/binance", "image": "hummingbot/hummingbot:latest", "script": "grid_strategy.py", "script_config": "grid_config_1.yml"}'
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Hummingbot instance created successfully",
    "instance_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "instance_name"],
        "msg": "Instance name already exists",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 创建新的 Hummingbot 实例以运行交易策略。
- 初始化自动化交易机器人。

#### 注意事项
- 确保 `credentials_profile` 已正确配置（通过 `POST /add-connector-keys`）。
- 确保 `script` 和 `script_config` 文件存在（通过 `POST /add-script` 和 `POST /add-script-config`）。
- 创建后需调用 `POST /start-container/{container_name}` 启动实例。

---

### 10. POST /pull-image/
#### 功能
拉取指定 Docker 镜像。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/pull-image/`
- **认证**: HTTP Basic
- **参数**:
  - **请求体**: JSON 对象，包含镜像名称。
    ```json
    {
      "image_name": "hummingbot/hummingbot:latest"
    }
    ```
    - `image_name`（string，必填），镜像名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/pull-image/" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"image_name": "hummingbot/hummingbot:latest"}'
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Image pulled successfully",
    "image_name": "hummingbot/hummingbot:latest"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "image_name"],
        "msg": "Invalid image name",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 在创建 Hummingbot 实例前拉取所需镜像。
- 更新本地镜像版本。

#### 注意事项
- 确保网络连接正常，拉取镜像可能需要时间。
- 可先调用 `GET /available-images/{image_name}` 检查镜像是否已存在。

---

### 11. GET /get-active-bots-status
#### 功能
获取所有活跃机器人的缓存状态。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/get-active-bots-status`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/get-active-bots-status" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  [
    {
      "bot_name": "grid_bot_1",
      "status": "running",
      "uptime": 3600,
      "profit": 150.5
    },
    {
      "bot_name": "grid_bot_2",
      "status": "running",
      "uptime": 1800,
      "profit": 75.0
    }
  ]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `object`，具体字段未定义。

#### 使用场景
- 监控所有运行中机器人的状态。
- 在策略列表页面展示机器人概览。

#### 注意事项
- 返回数据为缓存状态，可能不是实时的。
- 建议定期调用以更新状态。

---

### 12. GET /get-bot-status/{bot_name}
#### 功能
获取指定机器人的当前状态。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/get-bot-status/{bot_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `bot_name`（string，必填），机器人名称

#### 使用实例
```bash
curl -X GET "http://localhost:8000/get-bot-status/grid_bot_1" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "bot_name": "grid_bot_1",
    "status": "running",
    "uptime": 3600,
    "profit": 150.5,
    "trades": 10
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "bot_name"],
        "msg": "Bot not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 查看特定机器人的详细状态。
- 排查机器人运行问题。

#### 注意事项
- 确保机器人名称正确，否则返回 422 错误。
- 可结合 `GET /active-containers` 确认机器人是否运行。

---

### 13. GET /get-bot-history/{bot_name}
#### 功能
获取指定机器人的历史状态数据。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/get-bot-history/{bot_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `bot_name`（string，必填），机器人名称

#### 使用实例
```bash
curl -X GET "http://localhost:8000/get-bot-history/grid_bot_1" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  [
    {
      "timestamp": "2025-04-08T10:00:00Z",
      "status": "running",
      "profit": 100.0,
      "trades": 5
    },
    {
      "timestamp": "2025-04-08T11:00:00Z",
      "status": "running",
      "profit": 150.5,
      "trades": 10
    }
  ]
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "bot_name"],
        "msg": "Bot not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 分析机器人历史表现。
- 生成绩效报告。

#### 注意事项
- 数据量可能较大，建议后端支持分页或时间范围过滤（文档未提供）。
- 确保时间戳格式一致，便于分析。

---

### 14. POST /start-bot
#### 功能
启动指定机器人。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/start-bot`
- **认证**: HTTP Basic
- **参数**:
  - **请求体**: JSON 对象，包含启动参数。
    ```json
    {
      "bot_name": "grid_bot_1",
      "log_level": "INFO",
      "script": "grid_strategy.py",
      "conf": "grid_config_1.yml",
      "async_backend": false
    }
    ```
    - `bot_name`（string，必填），机器人名称
    - `log_level`（string，可选），日志级别
    - `script`（string，可选），策略脚本
    - `conf`（string，可选），配置文件
    - `async_backend`（boolean，可选，默认为 `false`），是否异步启动

#### 使用实例
```bash
curl -X POST "http://localhost:8000/start-bot" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"bot_name": "grid_bot_1", "log_level": "INFO", "script": "grid_strategy.py", "conf": "grid_config_1.yml", "async_backend": false}'
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Bot started successfully",
    "bot_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "bot_name"],
        "msg": "Bot not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 启动已创建的 Hummingbot 机器人。
- 恢复暂停的机器人。

#### 注意事项
- 确保 `script` 和 `conf` 文件存在。
- 如果 `async_backend` 为 `true`，启动可能是异步的，需稍后检查状态。

---

### 15. POST /stop-bot
#### 功能
停止指定机器人。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/stop-bot`
- **认证**: HTTP Basic
- **参数**:
  - **请求体**: JSON 对象，包含停止参数。
    ```json
    {
      "bot_name": "grid_bot_1",
      "skip_order_cancellation": false,
      "async_backend": false
    }
    ```
    - `bot_name`（string，必填），机器人名称
    - `skip_order_cancellation`（boolean，可选，默认为 `false`），是否跳过取消订单
    - `async_backend`（boolean，可选，默认为 `false`），是否异步停止

#### 使用实例
```bash
curl -X POST "http://localhost:8000/stop-bot" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"bot_name": "grid_bot_1", "skip_order_cancellation": false, "async_backend": false}'
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Bot stopped successfully",
    "bot_name": "grid_bot_1"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "bot_name"],
        "msg": "Bot not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 暂停运行中的 Hummingbot 机器人。
- 在调整策略或维护时使用。

#### 注意事项
- 如果 `skip_order_cancellation` 为 `false`，确保所有订单已处理完成。
- 停止后可调用 `GET /get-bot-status/{bot_name}` 确认状态。

---

### 16. POST /import-strategy
#### 功能
为指定机器人导入策略。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/import-strategy`
- **认证**: HTTP Basic
- **参数**:
  - **请求体**: JSON 对象，包含策略信息。
    ```json
    {
      "bot_name": "grid_bot_1",
      "strategy": "grid_strategy"
    }
    ```
    - `bot_name`（string，必填），机器人名称
    - `strategy`（string，必填），策略名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/import-strategy" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"bot_name": "grid_bot_1", "strategy": "grid_strategy"}'
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "message": "Strategy imported successfully",
    "bot_name": "grid_bot_1",
    "strategy": "grid_strategy"
  }
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "strategy"],
        "msg": "Strategy not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 为机器人导入新的交易策略。
- 在策略调整时使用。

#### 注意事项
- 确保策略名称有效（可通过 `GET /list-scripts` 检查）。
- 导入后需重新启动机器人以应用策略。

---

## 重新检查后的修正和补充

1. **返回示例一致性**:
   - 返回示例基于 OpenAPI 文档的定义，部分字段（如 `status`, `profit`）是推测的，实际字段需参考后端实现。
   - 文档中未明确定义返回字段，建议通过实际调用或查看后端代码确认。

2. **参数和请求体**:
   - `POST /create-hummingbot-instance` 和 `POST /start-bot` 的请求体字段基于 OpenAPI 文档中的 `HummingbotInstanceConfig` 和 `StartBotAction` 模式，确保参数准确。

3. **注意事项补充**:
   - 文档未提供分页或过滤参数，历史数据（如 `GET /get-bot-history/{bot_name}`）可能需要后端支持分页。
   - 容器操作（如 `POST /remove-container`）可能涉及归档，需确保存储配置正确。

4. **完整性**:
   - 已覆盖 `"Docker Management"` 和 `"Manage Broker Messages"` 标签下的所有 API，未遗漏。
   - 补充了使用场景和注意事项，确保文档实用性。

---

## 总结

以上文档详细描述了容器和机器人管理相关的 API，与 `"Manage Credentials"` API 文档风格一致。每个 API 均包含调用方法、参数、使用实例、返回示例、使用场景和注意事项，确保用户能够快速上手。如果你在实际使用中遇到问题（例如返回数据异常或参数不明确），可以提供更多细节，我会进一步协助分析！