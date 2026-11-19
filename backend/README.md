# 后端说明（FastAPI）

## 目录结构

```
backend/
├── app/
│   ├── main.py                 # create_app、异常处理、CORS
│   ├── api/
│   │   ├── deps.py             # get_current_user / require_permissions
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/      # auth, users, roles, permissions, departments, health
│   ├── core/                   # config, security, exceptions, constants, logging, token_store
│   ├── db/                     # base, session, types, seed
│   ├── models/                 # 26 张表
│   ├── schemas/                # Pydantic v2
│   ├── repositories/           # 数据访问
│   ├── services/               # 业务逻辑
│   └── tasks/                  # Celery（第二、三阶段启用）
├── alembic/                    # 迁移
├── sql/init.sql                # MySQL 建表脚本
├── scripts/                    # 生成 / 修正 / 自检
└── tests/                      # pytest
```

## 环境准备

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # 修改 DATABASE_URL、SECRET_KEY
```

要求 Python 3.12+、MySQL 8.0+。

## 初始化数据库

```bash
# 1. 建库（MySQL 客户端执行）
CREATE DATABASE enterprise_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 2. 建表
alembic upgrade head

# 3. 初始化企业 / 权限 / 内置角色 / 管理员 / 示例部门
python -m app.db.seed
```

种子脚本是幂等的，可以重复执行；管理员初始密码来自 `.env` 的 `FIRST_SUPERUSER_PASSWORD`。

如果还没配好 Alembic，也可以临时：

```bash
python -m app.db.seed --create-tables
```

## 启动

```bash
uvicorn app.main:app --reload --port 8000
```

- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

## 测试

```bash
.venv\Scripts\python.exe -m pytest -q
```

- 使用 SQLite 内存库（`aiosqlite`），不依赖 MySQL / Redis。
- 每个测试独立建库、独立种子数据，互不影响。
- 覆盖：登录/刷新/退出、用户 CRUD、RBAC 拒绝、部门树与防环、跨企业隔离。

当前：**42 passed**。

## 代码约定

```python
# 路由层：只做声明与转发
@router.post("", response_model=UserRead, status_code=201)
async def create_user(payload: UserCreate, current: CreateUser, db: DBDep) -> UserRead:
    return await UserService(db).create_user(current.organization_id, payload)
```

- 新接口记得：`response_model` + `require_permissions` + 从 `current.organization_id` 取租户。
- service 里 `await self.session.commit()` 才落库，异常由 `get_db` 回滚。
- 不要在异步接口里混用同步 `Session`。

## 常用脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/generate_init_sql.py` | 由模型生成 `sql/init.sql` |
| `scripts/fix_migration_defaults.py` | 修正 autogenerate 出的 `DEFAULT (CURRENT_TIMESTAMP)` |
| `scripts/show_tables.py` | 打印 SQLite 库表与行数，用于自检 |

## 常见问题

**`UnicodeDecodeError: 'gbk' codec`（Alembic）**
`alembic.ini` 必须是纯 ASCII。本仓库已处理，勿在其中写中文注释。

**`RuntimeError: no such table`**
没跑 `alembic upgrade head`，或 `.env` 指向了另一个库。

**登录返回 400「存在多个企业」**
库里有多条 `organizations` 记录，登录时需带 `organization_code`。

**改了密码后旧令牌还能用**
access token 默认 60 分钟有效，属于预期行为；退出登录会立刻吊销当前令牌。
