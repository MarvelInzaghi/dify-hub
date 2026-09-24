# dify-hub 离线部署指南

本文档说明如何把 dify-hub 打包并部署到**无外网**的生产机器（Docker 方式）。

## 1. 打包内容

`deploy/` 目录（连同本文档）即为一个完整离线部署包：

| 文件 | 说明 |
|---|---|
| `dify-hub-api.tar` | 后端镜像（FastAPI + 全部依赖 + 代码） |
| `dify-hub-web.tar` | 前端镜像（nginx + 已构建 SPA） |
| `docker-compose.yml` | api + web 两个服务编排 |
| `.env` | 运行配置（Dify 地址/鉴权、密钥等） |
| `README.md` | 本文档 |

## 2. 前置条件

- **离线机**：Docker 20.10+、Docker Compose v2（`docker compose` 命令）。
- 一个可访问的 **Dify 1.17 实例**（dify-hub 依赖它作为无头引擎）。
- 一台**有外网的机器**（仅构建镜像时需要，一次性）。

## 3. 构建镜像（有网机器上，一次性）

```bash
# 在有 Docker + 外网的机器上，进入项目根目录
bash deploy/build-offline.sh
```

脚本会构建两个镜像并导出为 `deploy/dify-hub-api.tar`、`deploy/dify-hub-web.tar`。

## 4. 部署（离线机器上）

```bash
# 1) 把整个 deploy/ 目录拷贝到离线机（含两个 .tar）
scp -r deploy/ <user>@<offline-host>:~/dify-hub/

# 2) 加载镜像
docker load -i ~/dify-hub/deploy/dify-hub-api.tar
docker load -i ~/dify-hub/deploy/dify-hub-web.tar

# 3) 编辑配置（见第 5 节）
vim ~/dify-hub/deploy/.env

# 4) 启动
cd ~/dify-hub/deploy && docker compose up -d
```

## 5. 配置说明（`.env`）

| 变量 | 说明 |
|---|---|
| `DIFY_BASE_URL` | Dify 入口地址。**Dify 与 dify-hub 同主机**填 `http://host.docker.internal`；**在别的机器**填 `http://<dify-ip>:80` |
| `DIFY_ADMIN_API_KEY` | Dify 管理员 Key（Dify 需开启 `ADMIN_API_KEY_ENABLE=true` + `ADMIN_API_KEY=<该值>`） |
| `DIFY_WORKSPACE_ID` | Dify 工作区（tenant）id，从 Dify 数据库 `tenants.id` 获取 |
| `DIFY_DEFAULT_MODEL_CONFIG_JSON` | 发布提示词时渲染进 Dify 应用的模型配置（provider/name/params） |
| `DATABASE_URL` | 后端数据库，默认 `sqlite:////data/dify_hub.db`（落在命名卷 `api_data`，**无需改**） |
| `SECRET_KEY` | 敏感 token 落库加密密钥，**生产必须改成强随机值** |
| `RATE_LIMIT_PER_MINUTE` | 公开运行接口每 Key 每分钟限流，`<=0` 关闭 |
| `WEB_PORT` | 前端对外端口，默认 `8100` |

## 6. 验证

```bash
cd ~/dify-hub/deploy

# 前端首页
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8100/

# 后端（技能列表，需 Dify 可达且鉴权正确）
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8100/api/skills

# 容器状态 / 日志
docker compose ps
docker compose logs -f api
```

前端访问地址：`http://<离线机-ip>:8100`。

## 7. 常用运维

```bash
cd ~/dify-hub/deploy

docker compose restart api      # 重启后端
docker compose logs -f api      # 看后端日志
docker compose down             # 停止（数据卷保留）
docker compose down -v          # 停止并删除数据卷（会清空 SQLite 数据！）
```

**数据备份**：SQLite 数据存在命名卷 `api_data` 里，备份方式：

```bash
docker run --rm -v dify-hub-deploy_api_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/dify_hub_backup.tar.gz -C /data .
```

> 卷名实际是 `deploy_api_data`（compose 项目名 + `_` + 卷名），可用 `docker volume ls` 确认。

## 8. 升级

代码更新后，在有网机器上重新构建 + 导出，再替换到离线机：

```bash
# 有网机器
bash deploy/build-offline.sh

# 离线机
docker load -i deploy/dify-hub-api.tar
docker load -i deploy/dify-hub-web.tar
cd deploy && docker compose up -d --force-recreate
```

> `--force-recreate` 会用新镜像重建容器；SQLite 数据在命名卷里，重建不丢数据。
