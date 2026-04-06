# pivkeyu_emby

pivkeyu_emby 是一个基于 Telegram、Emby、FastAPI 和 MySQL 的管理机器人，提供用户面板、管理面板、Mini App、Webhook、排行榜、定时任务和插件系统。

## 功能概览

- Telegram 用户侧功能：注册、签到、积分、续期、红包、邀请码、资源查询
- 管理侧功能：用户管理、续期、审计、同步、批量操作、配置面板
- Web 能力：`/admin` 管理后台、`/miniapp` Telegram Mini App、Emby Webhook
- 插件系统：支持内置插件和运行时插件，支持插件依赖安装与迁移
- 部署方式：Docker Compose 本地构建优先，默认附带 MySQL 与 Caddy 反代

## 目录说明

```text
.
├── bot/                  # Telegram Bot、Web、数据库、插件主代码
├── caddy/                # Caddy 反代配置
├── data/                 # 运行时数据、config.json、运行时插件
├── log/                  # 日志与运行时产物
├── mysql/                # MySQL 附加调优配置
├── scripts/              # 冒烟检查与辅助脚本
├── config_example.json   # 示例配置
├── docker-compose.yml    # 默认部署编排
├── Dockerfile            # 应用镜像构建文件
└── main.py               # 启动入口
```

## 快速开始

### 1. 准备条件

- 一台适合 `host` 网络模式的 Linux 服务器
- Docker 和 Docker Compose
- Telegram `bot_token`
- Telegram `api_id` / `api_hash`
- Emby 管理员 API Key 和 Emby 服务地址

### 2. 构建并启动

```bash
docker compose build --no-cache
docker compose up -d
```

### 3. 修改配置

Docker 部署时，程序优先读取：

```text
./data/config.json
```

如果该文件不存在，首次启动会由 `config_example.json` 自动生成。

### 4. 至少替换这些字段

- `bot_name`
- `bot_token`
- `owner_api`
- `owner_hash`
- `owner`
- `group`
- `main_group`
- `chanel`
- `emby_api`
- `emby_url`
- `emby_line`

如果你要启用 Web 后台和 Mini App，还需要配置：

- `api.status`
- `api.public_url`
- `api.admin_token`

### 5. 运行本地冒烟检查

```bash
python3 scripts/smoke_checks.py
```

## 配置规则

程序读取配置文件的优先级如下：

1. `data/config.json`
2. `config.json`
3. 如果都不存在，则从 `config_example.json` 复制到 `data/config.json`

`config_example.json` 中的 `_comment_*` 字段只是说明文字，程序会自动忽略。

## 关键配置项

### Telegram 与权限

- `bot_name`：机器人用户名，不带 `@`
- `bot_token`：BotFather 提供的 token
- `owner_api`：Telegram `api_id`
- `owner_hash`：Telegram `api_hash`
- `owner`：最高管理员 TG ID
- `admins`：附加管理员列表
- `group`：允许使用功能的群组 ID 列表
- `main_group`：主群公开用户名
- `chanel`：频道公开用户名

### Emby

- `emby_api`：Emby 管理 API Key
- `emby_url`：Emby 服务地址
- `emby_line`：展示给用户的 Emby 线路
- `emby_whitelist_line`：白名单专属线路
- `emby_block`：默认隐藏的媒体库
- `extra_emby_libs`：额外媒体库列表
- `partition_libs`：分区礼包和媒体库映射

### 数据库

- `db_host`
- `db_user`
- `db_pwd`
- `db_name`
- `db_port`
- `db_is_docker`
- `db_docker_name`
- `db_backup_dir`
- `db_backup_maxcount`

当前默认 `docker-compose.yml` 使用：

```text
db_host = 127.0.0.1
db_user = pivkeyu
db_pwd = pivkeyu
db_name = pivkeyu
```

底层调优默认值还包括：

- 应用容器与 MySQL 容器 `nofile=131072`
- MySQL 额外挂载 `mysql/conf.d/zz-pivkeyu-tuning.cnf`
- 数据库连接池默认 `pool_size=64`、`max_overflow=64`
- Pyrogram 默认 `workers=256`
- Emby `aiohttp` 连接池默认 `limit=192`、`limit_per_host=64`
- 当前这组默认值偏激进，更适合 `4C/8G+` 的 Linux 服务器；如果机器更小，建议先下调 MySQL Buffer Pool 和并发参数

### Web 与 Mini App

- `api.status`：是否启动 FastAPI
- `api.http_url` / `api.http_port`：监听地址和端口
- `api.public_url`：外网 HTTPS 地址
- `api.miniapp_title`：Telegram 菜单按钮标题
- `api.admin_token`：后台鉴权令牌
- `api.allow_origins`：CORS 白名单

## 默认访问入口

- `GET /health`：健康检查
- `GET /admin`：管理后台
- `GET /miniapp`：Mini App 页面
- `POST /emby/webhook/*`：Emby Webhook

启用 API 后，本地默认监听：

```text
http://127.0.0.1:8838
```

## 插件系统

### 插件位置

```text
内置插件：
bot/plugins/<plugin_name>/

运行时插件：
data/runtime_plugins/<plugin_name>/
```

### 当前内置探针插件

仓库内置了样例插件 `pivkeyu_template`，可用来确认插件系统正常工作：

- Bot 侧：`/plugin_ping`
- Web 侧：`GET /plugins/template/ping`

### 运行时插件行为

- 后台上传安装的运行时插件保存在 `data/runtime_plugins`
- Docker 重建镜像后，这些插件仍会跟随 `data/` 保留
- Docker 重建时会自动安装 `plugin.json` 中声明的 `dependencies.python`
- 插件自带的 `migrations/*.py` 会在加载前自动执行并记录历史

推荐的 Docker 插件升级流程：

1. 在 `/admin` 后台上传新的插件 ZIP
2. 如果后台提示需要重建容器，执行：

```bash
docker compose build pivkeyu_emby
docker compose up -d pivkeyu_emby
```

3. 容器启动后会自动安装依赖、执行迁移并重新加载插件

更详细的插件开发说明见：

- [bot/plugins/README.md](bot/plugins/README.md)
- [bot/plugins/xiuxian_game/README.md](bot/plugins/xiuxian_game/README.md)

## 反代与 HTTPS

仓库内置了 `Caddy` 反代服务，相关说明见：

- [REVERSE_PROXY.md](REVERSE_PROXY.md)

如果你不需要自动 HTTPS，可以自行裁剪 `docker-compose.yml` 中的 `pivkeyu-caddy` 服务。

## 开发与检查

### 语法和离线烟测

```bash
python3 -m compileall main.py bot scripts
python3 scripts/smoke_checks.py
```

### Docker 烟测

```bash
docker compose config
docker compose build
```

## 注意事项

- 当前 `docker-compose.yml` 使用 `network_mode: host`，更适合 Linux 服务器
- 项目启动时会自动执行数据库迁移
- MySQL 已配置健康检查，应用会等待数据库健康后再启动
- 数据库在刚启动还未就绪时，应用会按重试参数等待后再执行迁移
- 默认运行配置建议都放在 `data/` 下，避免重建镜像后丢失
- 如需按机器规格调优，可直接调整 `docker-compose.yml` 里的 `PIVKEYU_DB_*`、`PIVKEYU_PYROGRAM_*`、`PIVKEYU_EMBY_HTTP_*` 环境变量
- 非 Docker 部署可直接使用 [pivkeyu_emby.service](/Users/pivkeyu/Documents/pivkeyu_emby/pivkeyu_emby.service) 中的 `LimitNOFILE` 和 `Environment=` 模板

## 补充文档

- [REVERSE_PROXY.md](REVERSE_PROXY.md)
- [bot/plugins/README.md](bot/plugins/README.md)
