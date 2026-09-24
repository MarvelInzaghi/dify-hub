# dify-hub API 文档

本文档梳理 dify-hub 后端已支持的**全部接口**，供其他应用对接与二次开发使用。

## 1. 概述

- **基础地址**：`http://<服务器>:8100`（经 nginx 反向代理，`/api`、`/v1` 转发到后端 8101）。
- **数据格式**：请求/响应均为 JSON（文件上传接口为 `multipart/form-data`）。
- **路由前缀**：
  - `/api/*` —— 管理面（提示词库、技能库、发布、API Keys、用量）
  - `/v1/*` —— 公开「仅运行」面（外部调用）

## 2. 鉴权

| 前缀 | 鉴权方式 | 说明 |
|---|---|---|
| `/api/*` | **无登录鉴权** | 当前为内网管理接口，未启用登录；对外暴露前需自行加鉴权 |
| `/v1/*` | `Authorization: Bearer <API_Key>` | Key 通过 `POST /api/api-keys` 创建（明文仅创建时返回一次） |

公开运行接口的鉴权流程：`/v1/run/{slug}` 会校验 Bearer Key 的哈希、有效性（active）、scope（是否授权该 slug）与配额/限流。

---

## 3. 提示词库 `/api/prompts`

### 创建提示词
`POST /api/prompts`

请求体（`PromptCreate`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | 唯一标识（slug），`^[a-z0-9][a-z0-9_-]{0,63}$`，长度 ≤64 |
| display_name | string | 是 | 显示名，长度 ≤128 |
| description | string | 否 | 描述 |
| mode | string | 否 | `completion` 或 `chat`，默认 `completion` |
| content | string | 否 | 模板正文，含 `{{变量}}` 占位符 |
| variables | VariableSchema[] | 否 | 变量定义列表 |
| tags | string[] | 否 | 标签 |

响应：`201` → `PromptOut`。

### 提示词列表
`GET /api/prompts`

查询参数：`page`(int,1)、`limit`(int,20)、`keyword`(string)、`tags`(string[],可多个)

响应：`PromptListOut` = `{ data: PromptOut[], page, limit, total }`。

### 提示词详情
`GET /api/prompts/{prompt_id}` → `PromptOut`

### 更新提示词
`PATCH /api/prompts/{prompt_id}`

请求体（`PromptUpdate`，全可选）：`display_name`、`description`、`mode`、`content`、`variables`、`tags`

响应：`PromptOut`。

### 删除提示词
`DELETE /api/prompts/{prompt_id}` → `204`（连带删除版本）

### 发布版本
`POST /api/prompts/{prompt_id}/publish`

请求体（`PromptPublish`）：`{ changelog?: string }`

响应：`PromptVersionOut`（渲染进 Dify 应用）。

### 版本历史
`GET /api/prompts/{prompt_id}/versions` → `PromptVersionOut[]`

### 版本详情
`GET /api/prompts/{prompt_id}/versions/{version_id}` → `PromptVersionOut`

### 回滚版本
`POST /api/prompts/{prompt_id}/restore`

请求体（`PromptRestore`）：`{ version_id: string }`

响应：`PromptOut`。

### 提取变量名
`GET /api/prompts/{prompt_id}/variables` → `{ data: string[] }`

### 渲染预览
`POST /api/prompts/{prompt_id}/preview`

请求体（`PromptPreview`）：`{ values: { 变量名: 值 } }`

响应：`{ rendered: string }`。

---

## 4. 技能库 `/api/skills`

> 技能列表会**自动与 Dify 1.17 同步**（每次列表对账：补齐 Dify 侧新增、移除已删除）。

### 创建技能
`POST /api/skills`

请求体（`SkillCreate`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 否 | 唯一标识（slug），可选，空则由 Dify 生成 |
| display_name | string | 是 | 显示名 |
| description | string | 否 | 描述 |
| icon | string | 否 | 图标，默认 `📄` |
| category | string | 否 | 分类（dify-hub 自定义） |
| tags | string[] | 否 | 标签 |

响应：`201` → `SkillOut`。

### 技能列表
`GET /api/skills`

查询参数：`page`(int,1)、`limit`(int,20)、`keyword`(string)、`category`(string)

响应：`SkillListOut` = `{ data: SkillOut[], page, limit, total }`。

### 导入技能包（zip）
`POST /api/skills/import`

`multipart/form-data`，字段 `file`：上传 `.zip`（必须含 `SKILL.md`，frontmatter 提供 name/description）。

响应：`201` → `SkillOut`。

### 技能详情
`GET /api/skills/{skill_id}` → `SkillDetailOut`（含草稿文件列表、最新发布版本号）

### 更新元数据
`PATCH /api/skills/{skill_id}`

请求体（`SkillUpdate`，全可选）：`display_name`、`description`、`icon`、`category`、`tags`

响应：`SkillOut`。

### 删除技能
`DELETE /api/skills/{skill_id}` → `204`

### 写草稿文件
`PUT /api/skills/{skill_id}/files`

请求体（`SkillFileUpsert`）：`{ path: string, content: string }`

响应：`dict`（Dify 返回的文件详情）。

### 文件操作
`POST /api/skills/{skill_id}/file-op`

请求体（`SkillFileOp`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| operation | string | `upsert_text` / `mkdir` / `rename` / `delete` |
| path | string | 目标路径 |
| target_path | string | 仅 `rename` 时用 |
| content | string | 仅 `upsert_text` 时用 |

响应：`dict`。

### 发布版本
`POST /api/skills/{skill_id}/publish`

请求体（`SkillPublish`）：`{ changelog?: string, version_name?: string }`

响应：`dict`（版本信息）。

### 版本历史
`GET /api/skills/{skill_id}/versions` → `{ data: SkillVersion[] }`

### 下载技能包（zip）
`GET /api/skills/{skill_id}/export`

响应：`application/zip`（已发布技能包，含 `SKILL.md` 与全部文件），带 `Content-Disposition: attachment`。

### 技能清单（供外部智能体注入）
`GET /api/skills/{skill_id}/manifest`

响应：`{ name, display_name, description, skill_md, version }`（`skill_md` 为 `SKILL.md` 正文）。

### 绑定技能到 Agent
`PUT /api/skills/agent/{agent_id}/bind`

请求体（`SkillBind`）：`{ skill_ids: string[] }`（dify-hub 侧技能 id）

响应：`dict`。

---

## 5. 发布 `/api/publications`

### 发布提示词（生成执行契约）
`POST /api/publications`

请求体（`PublicationPublishRequest`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| prompt_id | string | 是 | 提示词 id |
| slug | string | 是 | 发布 slug，`^[a-z0-9][a-z0-9-]{0,63}$` |
| changelog | string | 否 | 变更说明 |

响应：`201` → `PublicationOut`（含 `dify_app_id`、`service_api_token` 已加密、`variable_schema`）。

### 发布列表
`GET /api/publications` → `PublicationOut[]`

---

## 6. API Keys `/api/api-keys`

### 创建 API Key
`POST /api/api-keys`

请求体（`ApiKeyCreate`）：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| name | string | 是 | 名称，≤128 |
| scopes | string[] | 否 | 授权范围（发布 slug 列表），默认 `["*"]` 全部 |
| quota | int | 否 | 总调用次数配额，`-1` 不限，默认 -1 |

响应：`201` → `ApiKeyCreated`（含 `api_key` 明文，**仅此一次返回**）。

### API Key 列表
`GET /api/api-keys` → `ApiKeyOut[]`（只含未吊销的 key）

### 吊销 API Key（彻底删除）
`POST /api/api-keys/{key_id}/revoke` → `204`

---

## 7. 用量 `/api/usage`

### 用量列表
`GET /api/usage`

查询参数：`limit`(int, 默认 200)

响应：`UsageOut[]`（按时间倒序）。

---

## 8. 公开运行 `/v1`

### 运行一个发布
`POST /v1/run/{slug}`

请求头：`Authorization: Bearer <API_Key>`

请求体（`RunRequest`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| inputs | object | 变量名 → 值（对应发布的 `variable_schema`） |
| query | string | chat 模式的用户问题 |
| user | string | 调用方标识，默认 `anonymous` |
| response_mode | string | `blocking`（返回 JSON）或 `streaming`（SSE 流式） |
| conversation_id | string | 会话 id（chat 模式多轮） |

- `blocking` 响应：Dify Service API 的 `message` JSON（含 `answer`、`metadata.usage` 等）。
- `streaming` 响应：`text/event-stream`。

错误：`401`（Key 无效）、`403`（未授权该 slug）、`404`（slug 不存在）、`429`（配额/限流）、`502`（Dify 执行失败）。

---

## 9. 数据模型参考

### VariableSchema（变量定义）
`name`(string, `^[a-zA-Z_][a-zA-Z0-9_]{0,29}$`)、`label`、`type`(`string|number|boolean`)、`description`、`required`(bool)、`default`

### PromptOut（提示词）
`id`、`name`、`display_name`、`description`、`mode`、`content`、`variables`、`tags`、`latest_published_version_id`、`dify_app_id`、`created_at`、`updated_at`

### PromptVersionOut（提示词版本）
`id`、`prompt_id`、`version_number`、`content`、`variables`、`changelog`、`dify_app_id`、`created_at`

### SkillOut（技能）
`id`、`dify_skill_id`、`name`、`display_name`、`description`、`category`、`tags`、`latest_dify_skill_version_id`、`created_at`、`updated_at`

### SkillDetailOut（技能详情）
继承 SkillOut，另加 `files`(数组)、`latest_published_version_number`、`latest_published_at`

### PublicationOut（发布）
`id`、`slug`、`name`、`item_type`、`item_id`、`pinned_version_id`、`mode`、`dify_app_id`、`variable_schema`、`status`、`created_at`、`updated_at`

### ApiKeyOut / ApiKeyCreated（API Key）
`id`、`name`、`key_prefix`、`scopes`、`quota`、`status`、`created_at`、`last_used_at`；`ApiKeyCreated` 另加 `api_key`（明文仅一次）

### UsageOut（用量记录）
`id`、`api_key_id`、`publication_id`、`mode`、`latency_ms`、`prompt_tokens`、`completion_tokens`、`total_tokens`、`status`、`error`、`created_at`

---

## 10. 调用示例（curl）

### 创建一个 API Key（拿到 Bearer Token）
```bash
curl -X POST 'http://<服务器>:8100/api/api-keys' \
  -H 'Content-Type: application/json' \
  -d '{"name": "my-app", "scopes": ["*"], "quota": -1}'
# 响应里的 api_key 即后续 Bearer Token（仅返回一次）
```

### 阻塞调用（blocking）
```bash
curl -X POST 'http://<服务器>:8100/v1/run/<slug>' \
  -H 'Authorization: Bearer <API_Key>' \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {"topic": "人工智能"}, "response_mode": "blocking"}'
```

### 流式调用（streaming）
```bash
curl -X POST 'http://<服务器>:8100/v1/run/<slug>' \
  -H 'Authorization: Bearer <API_Key>' \
  -H 'Content-Type: application/json' \
  -d '{"inputs": {}, "response_mode": "streaming"}'
```

### 导入技能包
```bash
curl -X POST 'http://<服务器>:8100/api/skills/import' \
  -F 'file=@/path/to/skill.zip'
```
