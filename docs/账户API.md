感谢你提供了完整的 OpenAPI 文档，我将重新检查之前对 `"Manage Credentials"` 标签下 API 的描述，确保内容准确无误，并根据完整文档补充或修正可能遗漏的细节。以下是对这些 API 的重新整理和验证，逐一介绍调用方法、参数、使用实例、返回示例、使用场景和注意事项。

---

### 1. GET /accounts-state
#### 功能
获取所有账户的当前状态，通常包括每个账户关联的交易所（连接器）及其状态数据（如余额）。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/accounts-state`
- **认证**: HTTP Basic（需要用户名和密码）
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/accounts-state" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "my_trading_account": {
      "binance": [
        {"balance": "100.5", "currency": "USDT"},
        {"balance": "0.002", "currency": "BTC"}
      ],
      "okx": [
        {"balance": "50.0", "currency": "USDT"}
      ]
    }
  }
  ```
- **文档定义**: 返回类型为 `object`，键为账户名，值是一个嵌套对象（键为连接器名，值为对象数组）。实际返回内容可能因实现而异。

#### 使用场景
- 检查所有账户在不同交易所的余额或状态。
- 在添加或更新密钥后，验证密钥是否有效。
- 监控账户资金分配情况。

#### 注意事项
- 如果返回数据为空，可能是密钥无效、权限不足或网络问题。
- 可能包含已删除账户（需检查配置文件或后端逻辑）。
- 建议定期调用以确保状态最新。
- **文档补充**: 文档未明确定义返回对象的具体字段（如 `balance`, `currency`），实际字段需参考后端实现或日志。

---

### 2. GET /account-state-history
#### 功能
获取所有账户的历史状态数据，可能包括余额变化、交易记录等时间序列数据。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/account-state-history`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/account-state-history" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  [
    {
      "timestamp": "2025-04-04T10:00:00Z",
      "account_name": "my_trading_account",
      "binance": [
        {"balance": "100.5", "currency": "USDT"}
      ]
    },
    {
      "timestamp": "2025-04-04T11:00:00Z",
      "account_name": "my_trading_account",
      "binance": [
        {"balance": "95.0", "currency": "USDT"}
      ]
    }
  ]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `object`，具体字段未定义，需参考实现。

#### 使用场景
- 分析账户余额随时间的变化。
- 生成账户的历史绩效报告。
- 排查问题（如余额异常）。

#### 注意事项
- 数据量可能较大，建议后端支持分页或时间范围过滤（文档未提供）。
- 确保时间戳格式一致，便于分析。
- 可能需要结合日志进一步排查历史数据异常。

---

### 3. GET /available-connectors
#### 功能
返回系统支持的所有连接器（交易所）名称列表。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/available-connectors`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/available-connectors" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  ["binance", "okx", "kucoin", "gate_io"]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `string`。

#### 使用场景
- 在添加新凭证前，查看支持的交易所。
- 用于前端界面展示可选交易所列表。
- 确认目标交易所是否可用。

#### 注意事项
- 确保连接器名称拼写正确，后续操作依赖此列表。
- 如果目标交易所不在列表中，需联系后端确认支持情况。

---

### 4. GET /connector-config-map/{connector_name}
#### 功能
获取指定连接器（交易所）的配置项列表，例如所需密钥字段。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/connector-config-map/{connector_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `connector_name`（string，必填），连接器名称，例如 `"binance"`

#### 使用实例
```bash
curl -X GET "http://localhost:8000/connector-config-map/binance" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  ["binance_api_key", "binance_api_secret"]
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "connector_name"],
        "msg": "Connector not found",
        "type": "value_error"
      }
    ]
  }
  ```
- **文档定义**: 返回类型为 `array`，元素为 `string`。

#### 使用场景
- 在添加凭证前，获取交易所需要的密钥字段。
- 用于动态生成表单或验证用户输入。

#### 注意事项
- 不同交易所字段不同，例如：
  - Binance: `["binance_api_key", "binance_api_secret"]`
  - OKX: `["okx_api_key", "okx_secret_key", "okx_passphrase"]`
- 确保提供所有字段，否则添加密钥可能失败。

---

### 5. GET /all-connectors-config-map
#### 功能
获取所有连接器的配置映射。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/all-connectors-config-map`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/all-connectors-config-map" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {
    "binance": ["binance_api_key", "binance_api_secret"],
    "okx": ["okx_api_key", "okx_secret_key", "okx_passphrase"],
    "kucoin": ["api_key", "secret_key", "passphrase"]
  }
  ```
- **文档定义**: 返回类型为 `object`，键为连接器名，值为 `array`（元素为 `string`）。

#### 使用场景
- 初始化系统时，获取所有交易所的配置要求。
- 批量管理多个连接器的凭证。

#### 注意事项
- 返回数据可能较大，建议缓存以提高效率。
- 确保后端支持所有列出的连接器。

---

### 6. GET /list-accounts
#### 功能
列出系统中所有账户的名称。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/list-accounts`
- **认证**: HTTP Basic
- **参数**: 无

#### 使用实例
```bash
curl -X GET "http://localhost:8000/list-accounts" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  ["my_trading_account", "team_account"]
  ```
- **文档定义**: 返回类型为 `array`，元素为 `string`。

#### 使用场景
- 查看当前系统中已注册的账户。
- 用于选择账户进行后续操作。

#### 注意事项
- 如果已删除账户仍出现在列表中，可能是删除未生效（检查配置文件）。
- 定期调用以保持账户列表最新。

---

### 7. GET /list-credentials/{account_name}
#### 功能
列出指定账户关联的所有连接器（凭证）名称。

#### 调用方法
- **HTTP 方法**: GET
- **URL**: `http://localhost:8000/list-credentials/{account_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**: `account_name`（string，必填），账户名称

#### 使用实例
```bash
curl -X GET "http://localhost:8000/list-credentials/my_trading_account" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  ["binance", "okx"]
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "account_name"],
        "msg": "Account not found",
        "type": "value_error"
      }
    ]
  }
  ```
- **文档定义**: 返回类型为 `array`，元素为 `string`。

#### 使用场景
- 检查某个账户绑定了哪些交易所。
- 在删除或更新凭证前确认现有配置。

#### 注意事项
- 确保账户名正确，否则会返回 422 错误。
- 可结合 `GET /list-accounts` 使用，获取账户列表后再查询凭证。

---

### 8. POST /add-account
#### 功能
添加一个新账户，作为凭证管理的逻辑容器。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/add-account?account_name={account_name}`
- **认证**: HTTP Basic
- **参数**:
  - **查询参数**: `account_name`（string，必填），账户名称
  - **请求体**: 无（不传递密钥）

#### 使用实例
```bash
curl -X POST "http://localhost:8000/add-account?account_name=new_account" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 201):
  ```json
  {}
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["query", "account_name"],
        "msg": "Account already exists",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 初始化一个新账户，后续为其绑定凭证。
- 用于多账户管理系统中的账户创建。

#### 注意事项
- 仅创建账户，不涉及密钥添加。
- 账户名应唯一且具描述性。
- 创建后账户为空，需后续绑定凭证。

---

### 9. POST /delete-account
#### 功能
删除指定账户及其所有关联凭证。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/delete-account?account_name={account_name}`
- **认证**: HTTP Basic
- **参数**:
  - **查询参数**: `account_name`（string，必填），账户名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/delete-account?account_name=new_account" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {}
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["query", "account_name"],
        "msg": "Account not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 清理不再使用的账户。
- 在账户管理界面中实现删除功能。

#### 注意事项
- 操作不可逆，删除前确认无重要数据。
- 可能未完全删除配置文件（需手动检查 `conf/` 目录）。
- 删除后调用 `GET /list-accounts` 确认。

---

### 10. POST /delete-credential/{account_name}/{connector_name}
#### 功能
删除指定账户中某个连接器的凭证。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/delete-credential/{account_name}/{connector_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**:
    - `account_name`（string，必填），账户名称
    - `connector_name`（string，必填），连接器名称

#### 使用实例
```bash
curl -X POST "http://localhost:8000/delete-credential/my_trading_account/binance" \
-u "username:password"
```

#### 返回示例
- **成功** (状态码: 200):
  ```json
  {}
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["path", "connector_name"],
        "msg": "Credential not found",
        "type": "value_error"
      }
    ]
  }
  ```

#### 使用场景
- 删除失效或不再使用的交易所凭证。
- 调整账户配置，保持其他凭证不变。

#### 注意事项
- 删除前确认凭证不再使用，避免影响运行中的机器人。
- 删除后调用 `GET /list-credentials/{account_name}` 确认。

---

### 11. POST /add-connector-keys/{account_name}/{connector_name}
#### 功能
为指定账户添加某个连接器的密钥。

#### 调用方法
- **HTTP 方法**: POST
- **URL**: `http://localhost:8000/add-connector-keys/{account_name}/{connector_name}`
- **认证**: HTTP Basic
- **参数**:
  - **路径参数**:
    - `account_name`（string，必填），账户名称
    - `connector_name`（string，必填），连接器名称
  - **请求体**: JSON 对象，包含密钥字段（因连接器而异）。
    - **Binance 示例**:
      ```json
      {
        "binance_api_key": "your_api_key",
        "binance_api_secret": "your_secret_key"
      }
      ```
    - **OKX 示例**:
      ```json
      {
        "okx_api_key": "your_api_key",
        "okx_secret_key": "your_secret_key",
        "okx_passphrase": "your_passphrase"
      }
      ```

#### 使用实例
```bash
curl -X POST "http://localhost:8000/add-connector-keys/my_trading_account/okx" \
-u "username:password" \
-H "Content-Type: application/json" \
-d '{"okx_api_key": "xxx", "okx_secret_key": "yyy", "okx_passphrase": "zzz"}'
```

#### 返回示例
- **成功** (状态码: 201):
  ```json
  {}
  ```
- **错误** (状态码: 422):
  ```json
  {
    "detail": [
      {
        "loc": ["body", "okx_passphrase"],
        "msg": "Field required",
        "type": "value_error.missing"
      }
    ]
  }
  ```

#### 使用场景
- 为新账户绑定交易所凭证。
- 更新现有账户的密钥（覆盖旧密钥）。

#### 注意事项
- 确保提供 `GET /connector-config-map/{connector_name}` 返回的所有字段。
- 使用 HTTPS 传输密钥，避免泄露。
- 添加后立即调用 `GET /accounts-state` 验证密钥有效性。
- **文档补充**: 请求体的 `Keys` 字段定义为 `object`，具体字段需根据连接器动态确定。

---

### 重新检查后的修正和补充
1. **返回示例一致性**:
   - 之前的返回示例与文档定义一致，但部分字段（如 `balance`, `currency`）是推测的，实际字段需参考后端实现。
   - 文档中未明确定义返回字段，建议通过实际调用或查看后端代码确认。

2. **参数和请求体**:
   - `POST /add-connector-keys/{account_name}/{connector_name}` 的请求体定义为 `object`，未指定具体字段，需结合 `GET /connector-config-map/{connector_name}` 的返回动态构造。

3. **注意事项补充**:
   - 文档未提供分页或过滤参数，历史数据（如 `GET /account-state-history`）可能需要后端支持分页。
   - 删除操作（`POST /delete-account` 和 `POST /delete-credential`）可能未完全清理文件，需手动检查 `conf/` 目录。

4. **完整性**:
   - 之前的描述已覆盖所有 `"Manage Credentials"` 标签下的 API，未遗漏。
   - 文档中未提供额外的参数或响应细节，之前的描述已尽可能准确。

---

### 总结
重新检查后，之前的描述与 OpenAPI 文档一致，未发现重大错误。补充了部分注意事项（如返回字段需确认、删除操作可能不彻底），并确保了示例和文档定义的一致性。如果你在实际调用中遇到具体问题（例如返回数据异常），可以提供更多细节，我会进一步帮你分析！