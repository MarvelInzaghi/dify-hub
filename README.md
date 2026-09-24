# dify-hub

统一「提示词（Prompt）+ 技能（Skill）」管理平台，以**外挂**方式搭建在 Dify 之上，**不改 Dify 源码**（不影响 Dify 升级）。

- **Dify = 无头引擎**：技能内容存储/版本/发布、应用配置、LLM 执行，全部复用 Dify 既有能力。
- **本平台 = 控制面 + 公开 API**：统一管理界面、提示词库、分享/权限/配额、对外「仅运行」API。
- **单一 Adapter 层**：所有对 Dify 的调用收敛在 `server/app/dify_adapter/`，Dify 升级只改这里。

技术栈：Python FastAPI（后端）+ Vite/React/TypeScript（前端）+ 独立 Postgres。

## 当前状态

**Phase 0 ✅**：Dify Console API Adapter（双鉴权 + 技能 CRUD + 应用/model-config）+ PoC 脚本。

**Phase 1 后端 ✅**：提示词库后端（FastAPI + SQLAlchemy）——数据模型（`prompts`/`prompt_versions`）、`{{变量}}` 解析/渲染、CRUD、版本发布（快照 + 渲染进 Dify 应用）、变量校验、单元测试。

**Phase 2 后端 ✅**：技能库后端——`skills` 注册表（映射 `dify_skill_id` + 锁定已发布版本 + 分类/标签元数据），服务层复用 Phase 0 的 Dify 技能 Adapter（CRUD/文件/发布/版本/绑定 Agent）。

**Phase 3 后端 ✅**：执行网关 + 公开「仅运行」API——`publications`（执行契约，含 Dify app id + Service API token）、`api_keys`（哈希存储 + scope + 配额）、`usage`（审计）、Service API 客户端（chat/completion + 流式）、`POST /v1/run/{slug}`（鉴权/scope/配额/填变量/执行）。

**前端 ✅**：统一管理界面（Vite + React + TS + React Router）——提示词库（列表 + 搜索/tags 筛选 + 分页 + 删除 + 编辑器 + `{{变量}}` 类型/标签/描述/必填/默认值 + 版本历史/回滚 + 发布）、技能库（搜索/分类/分页 + 多文件编辑器（新建/改名/删除/编辑文本）+ 发布 + 版本历史）、发布、API Keys（创建/吊销 + 明文仅显一次）、用量看板；全站加载/空/错误态。

**Phase 4 加固 ✅**：`service_api_token` 加密落库（Fernet，非确定性 + 兼容旧明文）、公开 run API 按分钟限流、Dify 升级冒烟脚本（`scripts/smoke.py`）、Alembic 迁移（替换 `create_all`）。

后续：
- 管理端鉴权（`/api/*` 目前无登录）
- 用量图表（时间序列/分组）

## 运行 API（Phase 1）

```bash
cd server
py -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example .env                          # 可选；不配 Dify 也能用提示词库
uvicorn app.main:app --reload                    # 或 py -m uvicorn app.main:app --reload
```

端点（前缀 `/api`）：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/prompts` | 创建提示词 |
| GET | `/prompts` | 列表（`page`/`limit`/`keyword`） |
| GET | `/prompts/{id}` | 详情 |
| PATCH | `/prompts/{id}` | 更新 |
| DELETE | `/prompts/{id}` | 删除（连带版本） |
| POST | `/prompts/{id}/publish` | 发布版本（快照 + 渲染进 Dify 应用） |
| GET | `/prompts/{id}/versions` | 版本历史 |
| GET | `/prompts/{id}/versions/{vid}` | 版本详情 |
| GET | `/prompts/{id}/variables` | 从内容提取的变量名 |
| POST | `/prompts/{id}/preview` | 用给定值渲染模板 |

技能端点（前缀 `/api`，需配置 Dify）：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/skills` | 创建技能（→ Dify + 注册表） |
| GET | `/skills` | 列表（`page`/`limit`/`keyword`/`category`） |
| GET | `/skills/{id}` | 详情（注册表 + Dify 草稿文件） |
| PATCH | `/skills/{id}` | 更新元数据 |
| DELETE | `/skills/{id}` | 删除（→ Dify + 注册表） |
| PUT | `/skills/{id}/files` | 写草稿文件（`{path, content}`） |
| POST | `/skills/{id}/publish` | 发布版本（→ Dify，锁定版本） |
| GET | `/skills/{id}/versions` | 版本历史 |
| PUT | `/skills/agent/{agent_id}/bind` | 绑定技能到 Agent（`{skill_ids}`） |

公开「仅运行」API（前缀 `/v1`，Bearer 鉴权用 `/api/api-keys` 发的 key）：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/run/{slug}` | 运行一个已发布的提示词/Agent（`{inputs, query, response_mode, user}`） |

API Key 管理（内部，前缀 `/api`）：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/api-keys` | 创建 key（明文仅此一次返回） |
| GET | `/api/api-keys` | 列出 key |
| POST | `/api/api-keys/{id}/revoke` | 吊销 key |


## Dify Console API 鉴权（重要）

Dify 的 Console API（`/console/api/*`，web 界面内部接口）鉴权有两条路，Adapter 都支持，按配置二选一：

### 策略 A：Admin API Key（推荐，服务端到服务端）

Dify 1.17.0 内置 `ADMIN_API_KEY` 机制（见 `api/extensions/ext_login.py:74-89`）。开启后：

- 请求带 `Authorization: Bearer <ADMIN_API_KEY>` + `X-WORKSPACE-ID: <tenant_id>`。
- 自动解析为该工作区的 **owner** 账号，**免登录、免 CSRF、免会话续期**。

需要在 Dify 的 **环境变量**（不是源码）里开启：

```
ADMIN_API_KEY_ENABLE=true
ADMIN_API_KEY=<一个强随机串>
```

`DIFY_WORKSPACE_ID` 取工作区（tenant）id，可从 Dify 数据库 `tenants.id` 或登录态下的工作区列表获取。

### 策略 B：邮箱密码 Cookie 会话（备用）

`POST /console/api/login` 返回 `access_token / refresh_token / csrf_token` 三个 **HttpOnly Cookie**，之后每次请求要带 cookie + `X-CSRF-Token` 请求头（值来自 csrf_token cookie），过期走 `POST /refresh-token`。

注意：登录的 `password` 字段是 **base64 编码**（`FieldEncryption.decrypt_field` 即 base64 解码），不是明文、也不是 RSA。

## 运行 PoC

前置：一个已初始化、可访问的 Dify 实例；按策略 A 或 B 配置好鉴权。

```bash
cd server
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example .env    # 填入 DIFY_BASE_URL + 一种鉴权策略
python scripts/poc.py
```

PoC 会：列出技能 → 创建技能 → 写入 `SKILL.md` 草稿 → 发布版本 → 创建应用 → 读取应用详情。

## 目录结构

```
dify-hub/
├── server/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── config.py                 # 配置（所有 Dify 耦合都在这声明）
│   │   └── dify_adapter/             # 唯一接触 Dify 的模块
│   │       ├── client.py             # DifyConsoleClient（前缀 + 请求 + 401 刷新）
│   │       ├── auth.py               # 双鉴权策略（admin key / cookie）
│   │       ├── skills.py             # 技能 CRUD / 版本 / 发布 / 绑定
│   │       ├── apps.py               # 应用创建 / model-config
│   │       ├── errors.py             # 错误类型
│   │       └── __init__.py           # DifyClient 门面
│   └── scripts/poc.py                # Phase 0 打通验证脚本
└── .env.example
```

## 运行前端

```bash
cd web
npm install
npm run dev        # 开发（/api 代理到 http://localhost:8000）
npm run build      # 类型检查 + 生产构建
```

技术栈说明：前端用 **Vite + React + TypeScript**（而非 Next.js）——本平台是纯管理 SPA，通过独立 FastAPI 后端通信，无需 Next.js 的 SSR/API 路由，Vite 更轻且可直接 `tsc` 校验。

## 数据库迁移（Alembic）

应用启动时 `init_db()` 会执行 `alembic upgrade head`。改了 `app/models.py` 后生成迁移：

```bash
cd server
alembic revision --autogenerate -m "描述"   # 生成迁移，务必 review 生成结果
alembic upgrade head                          # 应用迁移
alembic downgrade -1                          # 回退一版（验证用）
```

连接串从 `Settings.database_url` 读取；standalone 运行时用 `DATABASE_URL=...` 覆盖。多副本生产建议把 `alembic upgrade head` 放到部署步骤单独执行，而非启动时。

## Dify 升级回归

每次升级 Dify 后，跑冒烟脚本验证 Adapter 契约（失败只改 Adapter，不动 Dify）：

```bash
cd server && py scripts/smoke.py
```

脚本按 `DIFY_TARGET_VERSION` 锁定目标版本，依次验证 skills 的 list/create/publish/delete 与 apps 的 create/get。上线前把 `SECRET_KEY` 换成强随机值（用于 token 加密）。

## Dify 集成契约参考（1.17.0）

| 能力 | 端点（前缀 `/console/api`） | 源码 |
|---|---|---|
| 技能列表/创建 | `GET/POST /workspaces/current/skills` | `api/controllers/console/workspace/skills.py` |
| 技能草稿文件 | `PATCH/PUT .../skills/{id}/files` | 同上 |
| 技能发布/版本/回滚 | `POST .../publish`、`GET .../versions`、`POST .../restore` | 同上 |
| 技能绑定 Agent | `PUT /workspaces/current/agents/{id}/skills` | 同上 |
| 应用创建 | `POST /apps` | `api/controllers/console/app/app.py` |
| 应用 model-config | `POST /apps/{id}/model-config` | `api/controllers/console/app/model_config.py` |
| 执行（官方稳定） | `/v1/chat-messages`、`/v1/completion-messages` | `api/controllers/service_api/` |
