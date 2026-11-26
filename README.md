# 智企协同 Enterprise AI

企业级 AI SaaS 平台。**第一阶段已完成：基础框架 + 登录权限系统。**

> 技术栈：Vue 3 + TypeScript + Element Plus ｜ FastAPI + SQLAlchemy 2.0（异步）｜ MySQL 8.0 + Redis + MinIO + Milvus ｜ 云端 API + Ollama

---

## 当前进度

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| 一 | 工程初始化、MySQL 异步连接、Alembic、JWT 认证、RBAC、部门树、后台页面 | ✅ 已完成 |
| 二 | AI 模型网关（云端 + Ollama 统一接入） | ✅ 已完成（云端可用，Ollama 待接入） |
| 三 | 企业知识库 RAG（MySQL 向量 + 混合检索，替代 Milvus） | ✅ 已完成 |
| 四 | AI Agent（调用工单 / 任务工具） | 待开始 |
| 五 | 工单与审批流程 | ✅ 已完成（含附件、多级串签） |
| 六 | 数据分析与生产部署 | 部分完成（已上线自动部署，数据看板待做） |
| 七 | 产品体验补齐 | ✅ 已完成：待办工作台、站内通知、首次强制改密、演示账号开关 |

已实现模块：身份权限（38 权限点 / 4 角色）、组织架构、AI 模型网关（6 家厂商）、知识库 RAG、AI 助手、工单（提交 / 指派 / 流转 / 评论 / 附件）、审批（多级串签 / 附件）、站内通知、待办工作台、首次强制改密。测试覆盖见 `backend/tests`。

第一阶段验收项：登录/刷新/退出、用户增删改查、角色多对多、接口级权限校验、部门树、Alembic 迁移、前端路由权限、跨企业数据隔离。**已有 42 个自动化测试覆盖。**

---

## 目录结构

```
.
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/          # 路由层（endpoints + deps）
│   │   ├── core/            # 配置、安全、异常、常量、日志
│   │   ├── db/              # Base、会话、类型、种子脚本
│   │   ├── models/          # SQLAlchemy 2.0 模型（26 张表）
│   │   ├── schemas/         # Pydantic v2 模型
│   │   ├── repositories/    # 数据访问层
│   │   ├── services/        # 业务逻辑层
│   │   └── tasks/           # Celery
│   ├── alembic/             # 数据库迁移
│   ├── sql/init.sql         # MySQL 建表脚本（由模型生成）
│   ├── scripts/             # 生成 SQL / 修正迁移 / 自检脚本
│   └── tests/               # pytest（SQLite 内存库）
├── frontend/                # Vue 3 前端
├── deploy/                  # Docker Compose、Nginx、MySQL 配置
└── docs/                    # 架构、数据库、接口文档
```

---

## 快速开始

### 1. 准备数据库

任选其一：

**A. 已有本地 MySQL**（本次开发环境使用 phpstudy 自带的 MySQL 8.0.12）

```sql
CREATE DATABASE enterprise_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**B. 用 Docker 起基础设施**（MySQL / Redis / MinIO / Milvus）

```bash
cd deploy
docker compose -f docker-compose.infra.yml up -d
```

### 2. 启动后端

```bash
cd backend

python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS / Linux

pip install -r requirements.txt
copy .env.example .env           # 修改 DATABASE_URL 里的账号密码

alembic upgrade head             # 建表
python -m app.db.seed            # 初始化企业、权限、角色、管理员

uvicorn app.main:app --reload --port 8000
```

访问接口文档：<http://127.0.0.1:8000/docs>

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>，默认账号：

| 企业编码 | 用户名 | 密码 |
| --- | --- | --- |
| `demo` | `admin` | `Admin@123456` |

> 首次登录后请立即修改密码。

### 4. 跑测试

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q
```

测试使用 SQLite 内存库，不需要 MySQL / Redis。

---

## 文档

- [架构设计](docs/architecture.md)
- [数据库设计](docs/database.md)
- [接口文档](docs/api.md)
- [部署手册](docs/deploy.md) —— 阿里云 ECS 单机部署全流程
- [GitHub Actions 自动部署与排错](docs/github-actions-deploy-guide.md) —— 日常发版流程、双远程推送、常见错误解决
- [后端说明](backend/README.md)
- [前端说明](frontend/README.md)

---

## 开发约定

- **分层**：`api → service → repository → model`，路由层不写业务逻辑，服务层不拼 SQL。
- **事务边界**：service 层显式 `commit`，`get_db` 只负责异常回滚。
- **租户隔离**：所有查询必须带 `organization_id`，且从登录态取，绝不信前端传参。
- **权限**：接口用 `require_permissions("user:create")` 声明式校验，超级管理员直通。
- **软删除**：用户禁用而非物理删除，保留工单/审批/日志的历史关联。

## 已知限制

- `deploy/docker-compose.infra.yml` 已通过 `docker compose config` 语法校验，其 `redis` 服务已在 Docker Desktop 4.99（WSL2 后端）上实际跑通；MySQL / MinIO / etcd / Milvus 未实际拉取验证（本地开发用 phpstudy 的 MySQL）。
- Milvus / MinIO / Celery 属于第二、三阶段依赖，第一阶段代码只保留接入位。
- 前端 `npm run build` 需要 Node 20+；本仓库在 Node 24 下验证。

## 本机环境备忘（Windows / phpstudy）

以下三个坑是在本机实际跑通第一阶段时踩到的，换机器复现时先检查：

- **MySQL 默认存储引擎必须是 InnoDB。** phpstudy 自带的 `my.ini` 里是 `default-storage-engine=MyIsam`，会导致 26 张表全部建成 MyISAM：51 个外键被静默忽略、service 层的 `commit`/回滚形同虚设、联合唯一索引超过 1000 字节直接建表失败（`document_chunks` 的 `uk_vector_id` 就会挂）。已改为 `InnoDB`。
- **中文 Windows 下 `pip install -r requirements.txt` 会抛 `UnicodeDecodeError`。** requirements.txt 里有中文注释，pip 按 GBK 读取。先设 `PYTHONUTF8=1`（PowerShell：`$env:PYTHONUTF8='1'`）再装。
- **`.venv` 不能用 `--system-site-packages` 建。** 否则 `import alembic` 之类会优先命中 Anaconda 的全局包，版本和 `requirements.txt` 对不上。务必让 `pip install` 把锁定版本装进 venv 自己的 `site-packages`。
