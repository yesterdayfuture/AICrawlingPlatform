# 智能爬取系统 (Intelligent Crawler System)

一个支持内容解析的全栈智能爬取系统。前端基于 Vue 3，后端基于 FastAPI，数据库支持 SQLite / PostgreSQL。集成大模型（OpenAI 协议）对抓取结果进行结构化解析。

## 功能概览

| 模块 | 核心能力 |
| --- | --- |
| 总览 | 统计卡片（点击跳转对应页）+ 按天聚合的 ECharts 折线图，支持时间过滤与天数选择 |
| 爬虫地址 | CRUD、名称/描述模糊+精准查询、分页+页大小、状态过滤、GET/POST 配置（headers/params/body）、表单内提示样例 |
| 大模型管理 | CRUD、查询、分页、状态过滤；后端用 `openai` 库调用（兼容 OpenAI 协议服务商：OpenAI / DeepSeek / Moonshot 等） |
| 提示词管理 | CRUD、查询、分页、状态过滤，支持 `{content}` 占位符引用待解析内容 |
| 任务中心 | CRUD、查询、分页、状态过滤、多选爬虫、定时调度（分/时/日/月，基于 APScheduler）+ 立即执行 + 启动/暂停/停止定时 |
| 任务结果 | CRUD、查询、分页、状态过滤、详情查看每个地址结果与异常信息、点击解析选择模型+提示词 |
| 解析结果 | CRUD、查询、分页、状态过滤、详情含原始输入/输出、输入/输出/总 tokens、速度、耗时、异常信息 |
| 用户管理 | 管理员可见：新增/编辑/删除/禁用启用普通用户、角色分配 |
| 操作日志 | 管理员可见：记录用户写操作（POST/PUT/DELETE），含完整请求参数（query + body，敏感字段已脱敏）、IP、耗时、状态码，支持关键词/用户名/模块/动作/状态/时间范围筛选，详情抽屉查看完整参数 |
| 个人中心 | 修改昵称、邮箱、密码 |
| 认证 | JWT 登录、token 失效自动跳转登录页、基于角色的访问控制 + 数据权限过滤 |

> 所有列表界面均支持时间范围过滤。

## 技术栈

**后端**
- Python 3.10+ / FastAPI 0.115
- SQLAlchemy 2.0 ORM
- Pydantic v2 数据校验
- httpx 爬虫请求客户端
- openai 官方库调用 LLM
- APScheduler 3.10 定时任务调度（BackgroundScheduler 后台线程）
- JWT 认证 + bcrypt 密码哈希
- SQLite（默认）或 PostgreSQL

**前端**
- Vue 3.5 + Vite 5
- Vue Router 4（带登录守卫）
- Element Plus 2.8（UI 组件库，中文本地化）
- ECharts 5（折线图）
- Axios（HTTP 客户端，统一 `{code,msg,data}` 响应拦截，自动携带 token）
- dayjs（时间格式化）
- marked + dompurify（Markdown 安全渲染）

## 目录结构

```
CrawlerManagementSystem/
├── backend/
│   ├── main.py                 直接启动入口（python main.py）
│   ├── app/
│   │   ├── main.py              FastAPI 入口（CORS + 路由注册 + lifespan 建表 + 默认管理员）
│   │   ├── config.py            配置（DB URL / CORS / 超时 / JWT 密钥 / 默认管理员）
│   │   ├── database.py          SQLAlchemy 引擎与会话
│   │   ├── models.py            ORM 模型（业务表 + User）
│   │   ├── schemas.py           Pydantic 校验模型
│   │   ├── security.py          密码哈希 + JWT 签发/校验 + 依赖注入
│   │   ├── common.py            统一响应 / 分页 / 时间范围解析
│   │   ├── tz.py                时区工具（北京时间 UTC+8）
│   │   ├── routers/             路由模块 + 通用过滤器
│   │   │   ├── _filters.py      名称/描述/状态/时间 统一过滤
│   │   │   ├── _owner.py        数据权限过滤（管理员/普通用户可见性）
│   │   │   ├── auth.py          登录 / 获取当前用户 / 修改密码 / 修改资料
│   │   │   ├── users.py         管理员用户管理 CRUD
│   │   │   ├── dashboard.py     总览统计与趋势
│   │   │   ├── crawlers.py      爬虫地址 CRUD（带权限）
│   │   │   ├── models.py        大模型 CRUD（带权限）
│   │   │   ├── prompts.py       提示词 CRUD（带权限）
│   │   │   ├── tasks.py         任务 CRUD + 立即执行 + 定时启停（带权限）
│   │   │   ├── task_results.py  任务结果 CRUD + 解析触发（带权限）
│   │   │   ├── parse_results.py 解析结果 CRUD（带权限）
│   │   │   └── operation_logs.py 操作日志查询 + 清理（管理员）
│   │   └── services/
│   │       ├── crawler_service.py       GET/POST 抓取 + 任务执行
│   │       ├── scheduler_service.py     APScheduler 定时调度管理
│   │       ├── operation_log_service.py 操作日志：路径推断 + 写日志 + 脱敏
│   │       ├── llm_service.py           OpenAI 协议解析
│   │       └── export_service.py        通用数据导出（JSON/CSV/Excel）
│   ├── requirements.txt
│   └── run.sh                   启动脚本
└── frontend/
    ├── src/
    │   ├── main.js              应用入口（Element Plus 中文化）
    │   ├── App.vue              主框架布局（公开路由独立渲染）
    │   ├── router/index.js      路由 + 登录守卫 + 管理员守卫
    │   ├── store/user.js        用户 store（token、用户信息、登录/登出）
    │   ├── api/
    │   │   ├── http.js          axios 实例 + token 拦截 + 401 跳登录
    │   │   └── index.js         各实体 API 封装 + 通用导出
    │   ├── components/
    │   │   ├── SearchToolbar.vue 复用搜索栏
    │   │   ├── ExportDialog.vue  通用导出弹窗
    │   │   └── MarkdownPreview.vue Markdown 预览（渲染/源码/HTML）
    │   ├── styles/global.css    全局样式
    │   └── views/
    │       ├── Login.vue        登录页（独立全屏）
    │       ├── Dashboard.vue
    │       ├── Crawlers.vue
    │       ├── Models.vue
    │       ├── Prompts.vue
    │       ├── Tasks.vue
    │       ├── TaskResults.vue
    │       ├── ParseResults.vue
    │       ├── Users.vue        用户管理（管理员）
    │       └── Profile.vue      个人中心
    ├── index.html
    ├── eslint.config.js         ESLint flat config（Vue 3 规则）
    ├── package.json
    └── vite.config.js           含 /api 代理到 8000
```

## 数据库表结构

| 表 | 说明 |
| --- | --- |
| `users` | 用户（username, password_hash, nickname, email, role[admin/user], is_active, last_login_at） |
| `crawlers` | 爬虫地址（name, url, method, headers, params, body, status, owner_id, is_public） |
| `llm_models` | 大模型（provider, base_url, api_key, model_name, temperature, max_tokens, owner_id, is_public） |
| `prompts` | 提示词（system_prompt, user_prompt 支持 `{content}` 占位符, owner_id, is_public） |
| `tasks` | 任务（is_scheduled, interval_value, interval_unit, last_run_at, owner_id, is_public）—— `is_scheduled` + `status='enabled'` 决定是否被 APScheduler 调度 |
| `task_crawlers` | 任务-爬虫多对多关联表 |
| `task_results` | 任务执行结果（status, duration, success_count, failed_count, error_message） |
| `task_result_items` | 单个爬虫的抓取结果（status_code, content, error_message, duration） |
| `parse_results` | 解析结果（raw_input, raw_output, parsed_content, input/output/total_tokens, speed, duration） |
| `operation_logs` | 操作日志（user_id, username, module, action, method, path, params, status, status_code, ip, user_agent, error_msg, duration_ms） |

## 快速开始

### 1. 后端

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# 默认使用 SQLite，启动时自动建表 + 恢复已存在的定时任务
python main.py                 # 直接启动（默认开启热重载）
# 或自定义参数
python main.py --host 0.0.0.0 --port 8000 --no-reload
# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> 应用启动时会自动启动 APScheduler 后台调度器，并从数据库恢复所有 `is_scheduled=True 且 status='enabled'` 的任务到调度器中。

切换 PostgreSQL：编辑 `backend/.env` 设置 `DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/dbname`，然后重新启动。

API 文档自动生成：http://localhost:8000/docs

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 即可使用。前端已配置 `/api` 代理到后端 8000 端口。

生产构建：

```bash
npm run build     # 产物输出到 dist/
npm run preview   # 本地预览构建产物
```

## 配置项（.env 文件）

配置通过 `backend/.env` 文件读取（由 pydantic-settings 自动加载）。优先级：环境变量 > `.env` 文件 > 代码默认值。

复制示例文件并按需修改：

```bash
cp backend/.env.example backend/.env
```

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./crawler.db` | 数据库连接串 |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | 允许的前端跨域来源（逗号分隔） |
| `LLM_TIMEOUT` | `120` | 大模型调用超时（秒） |
| `CRAWLER_TIMEOUT` | `30` | 爬虫请求超时（秒） |
| `JWT_SECRET` | 随机字符串 | JWT 签名密钥（生产环境务必修改） |
| `JWT_ALGORITHM` | `HS256` | JWT 签名算法 |
| `JWT_EXPIRE_HOURS` | `24` | Token 有效期（小时） |
| `DEFAULT_ADMIN_USERNAME` | `admin` | 默认管理员用户名（首次启动自动创建） |
| `DEFAULT_ADMIN_PASSWORD` | `admin123` | 默认管理员密码（首次启动自动创建，建议登录后立即修改） |

> `.env` 已加入 `.gitignore`，不会提交到版本控制；`.env.example` 作为模板提交。
> 默认管理员账户会在首次启动时自动创建，**生产环境务必修改默认密码**。

## 典型使用流程

1. **登录系统**：使用默认管理员 `admin / admin123` 登录（首次登录后请前往「个人中心」修改密码）
2. **配置爬虫地址**：在「爬虫地址」页新增目标 URL，选择 GET/POST，填写 headers/params/body
3. **配置大模型**：在「大模型管理」页填写 base_url、api_key、model_name（兼容 OpenAI 协议的服务商均可）
4. **配置提示词**：在「提示词管理」页编写 system/user prompt，可用 `{content}` 占位符
5. **创建任务**：在「任务中心」多选爬虫，按需开启定时（分/时/日/月），点击「执行」立即运行；或配置好间隔后通过操作列「启动定时」让任务按周期自动执行，支持随时「暂停」/「停止定时」
6. **查看结果**：在「任务结果」点击「详情」查看每个地址的抓取内容与异常；点击「解析」选择模型+提示词
7. **查看解析**：在「解析结果」点击「详情」查看原始输入/输出、tokens 用量、速度、耗时
8. **用户管理**（管理员）：在「用户管理」新增普通用户、分配角色、禁用/启用/删除
9. **个人中心**：所有用户可在此修改昵称、邮箱、密码

## API 概览

所有响应统一为 `{code, msg, data}`，`code=0` 表示成功。

| 实体 | 路径前缀 | 方法 |
| --- | --- | --- |
| 认证 | `/api/auth` | `POST /login`、`GET /me`、`PUT /me`、`PUT /password` |
| 用户管理 | `/api/users` | `GET / /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`、`PUT /{id}/toggle-status` |
| 总览 | `/api/dashboard` | `GET /stats`、`GET /trend`、`GET /export` |
| 爬虫 | `/api/crawlers` | `GET / /all /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`、`GET /export` |
| 大模型 | `/api/models` | 同上 |
| 提示词 | `/api/prompts` | 同上 |
| 任务 | `/api/tasks` | CRUD + `POST /{id}/run`（立即执行） + `POST /{id}/schedule/start`（启动定时） + `POST /{id}/schedule/pause`（暂停定时） + `POST /{id}/schedule/stop`（停止定时） + `GET /export` |
| 任务结果 | `/api/task-results` | CRUD + `POST /{id}/parse` + `GET /export` |
| 解析结果 | `/api/parse-results` | CRUD + `GET /export` |

> 所有列表接口均需登录（携带 `Authorization: Bearer <token>`）。
> 普通用户仅能查看/操作自己创建的数据 + 管理员设为公开的数据；管理员可见全部。

列表接口通用查询参数：`page`、`page_size`、`name`、`description`、`search_mode`(fuzzy/exact)、`status`、`start_time`、`end_time`。
导出接口通用参数：`format`(json/csv/xlsx)、`ids`（逗号分隔，可选）、`name`/`status`/`start_time`/`end_time`（筛选）。

## 开发说明

- 后端采用分层架构：`routers`（路由）→ `services`（业务）→ `models`（ORM）→ `schemas`（校验）
- 前端 `api/http.js` 拦截统一响应，业务代码直接 `await api.xxx()` 拿到 `data`
- `SearchToolbar.vue` 是所有列表页复用的搜索组件，统一定义查询条件
- Element Plus 已配置中文本地化（`zhCn`）
- 前端 IDE 中若提示 `v-model:current-page` 报错，是 Vue 2 风格的 lint 规则误报，Vue 3 + Element Plus 必须使用该参数式语法，不影响构建

## 时区约定

项目统一使用**北京时间（UTC+8）**存储和展示时间。

- `app/tz.py` 提供 `now_cst()` 函数，返回 naive datetime（无时区信息）
- 所有业务表时间字段（`created_at` / `updated_at` / `started_at` / `finished_at` / `last_login_at` / `last_run_at`）统一使用 `now_cst()`
- 前端 dayjs 解析无时区字符串时按本地时区处理，正好显示北京时间
- 调度器时区固定 `Asia/Shanghai`，与业务时间保持一致
- **唯一例外**：JWT `exp` 仍用 `datetime.utcnow()`，符合 JWT 标准

## 操作日志

系统自动记录用户的写操作（POST/PUT/DELETE），管理员可在「操作日志」页面查看。

### 记录范围

通过 `services/operation_log_service.py` 中的 `_PATH_RULES` 映射表定义哪些路径需要记录。仅记录映射表中存在的路径，未匹配的路径不记录。

### 请求参数记录

中间件（`main.py` 的 `operation_log_middleware`）会提前读取请求 body（仅 `Content-Type: application/json`），存入 `request.state.body_data`，日志服务合并 query 参数和 body 参数后存入 `params` 字段。

- 敏感字段自动脱敏为 `***`（`password`、`api_key`、`token`、`secret` 等）
- 前端详情抽屉可查看完整 JSON 格式的请求参数

### 日志清理

管理员可通过 `DELETE /api/operation-logs?before_days=N` 清理 N 天前的日志，`before_days=0` 清空全部。

## 定时任务调度

任务支持定时执行，基于 `APScheduler` 的 `BackgroundScheduler` 实现，调度器在应用 `lifespan` 中随服务启动/关闭。

### 调度模型

一个任务是否被调度，由两个字段共同决定：
- `is_scheduled = True` 且 `status = 'enabled'`：调度器中存在对应 job，按周期执行
- `is_scheduled = True` 且 `status = 'disabled'`：暂停态，配置保留但不会被触发
- `is_scheduled = False`：手动模式，无论 `status` 如何都不会被调度

### 间隔单位

| 单位 | 含义 | 触发器 |
| --- | --- | --- |
| `min` | 每 N 分钟 | `IntervalTrigger(minutes=N)` |
| `hour` | 每 N 小时 | `IntervalTrigger(hours=N)` |
| `day` | 每 N 天 | `IntervalTrigger(days=N)` |
| `month` | 每 N 个月 | `CronTrigger(day=1, month='*/N', hour=0, minute=0)` |

### 控制接口

| 接口 | 行为 | 字段变化 |
| --- | --- | --- |
| `POST /api/tasks/{id}/schedule/start` | 启动定时 | `is_scheduled=True, status=enabled` → 注册 job |
| `POST /api/tasks/{id}/schedule/pause` | 暂停定时 | `status=disabled` → 移除 job（配置保留） |
| `POST /api/tasks/{id}/schedule/stop` | 停止定时 | `is_scheduled=False` → 移除 job，回手动 |

创建/更新/删除任务时，路由层会自动同步调度器状态（`schedule_task` / `unschedule_task`）。

### 实现要点

- 调度器单例：`services/scheduler_service.py` 中的 `_scheduler`，`MemoryJobStore` 存储
- job_id 约定：`task_{id}`，`max_instances=1, coalesce=True` 防止重叠与积压
- 执行入口：`_run_scheduled_task(task_id)` 在调度器线程中运行，使用独立 `SessionLocal()`，避免与请求级 Session 冲突
- 启动恢复：`start_scheduler()` 会扫描 DB 中 `is_scheduled=True 且 status='enabled'` 的任务重新注册
- 时区：调度器统一使用 `Asia/Shanghai`

