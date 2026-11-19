# 数据库设计

## 1. 基本约定

| 项目 | 约定 |
| --- | --- |
| 字符集 | `utf8mb4` / `utf8mb4_unicode_ci` |
| 主键 | `BIGINT UNSIGNED AUTO_INCREMENT` |
| 时间 | `DATETIME`，`created_at` / `updated_at` 由数据库默认值维护 |
| 状态 | `TINYINT/SMALLINT`，`1` 启用，`0` 停用 |
| 逻辑删除 | 用户用 `status=0` 表示禁用，不做物理删除 |
| 命名 | 表名复数下划线；索引 `idx_*`、唯一键 `uk_*`、外键 `fk_*` |

建表脚本：`backend/sql/init.sql`（由 `backend/scripts/generate_init_sql.py` 依据模型生成）。
迁移脚本：`backend/alembic/versions/`。

## 2. 表清单（26 张）

### 组织与权限（7）

| 表 | 说明 | 关键约束 |
| --- | --- | --- |
| `organizations` | 企业租户 | `code` 唯一 |
| `departments` | 部门树 | `parent_id` 自引用；`idx_department_org` |
| `users` | 用户 | `(organization_id, username)` 唯一、`(organization_id, email)` 唯一 |
| `roles` | 角色 | `(organization_id, code)` 唯一 |
| `permissions` | 权限点 | `code` 全局唯一 |
| `user_roles` | 用户-角色 | 复合主键 |
| `role_permissions` | 角色-权限 | 复合主键 |

### AI 知识库（3）

| 表 | 说明 |
| --- | --- |
| `knowledge_bases` | 知识库，含可见范围 `private/department/org` |
| `documents` | 文档元数据、解析状态 `pending/parsing/ready/failed` |
| `document_chunks` | 切片元数据 + `vector_id` / `collection_name` / `embedding_model` |

> 向量本体存 Milvus，MySQL 只存定位信息。`uk_vector_id(collection_name, vector_id)` 防止重复写入。

### AI 对话（4）

| 表 | 说明 |
| --- | --- |
| `conversations` | 会话 |
| `chat_messages` | 消息，`references_json` 存 RAG 引用，`tool_calls` 存 Agent 调用 |
| `ai_model_configs` | 模型配置，`api_key_encrypted` 只存密文 |
| `ai_usage_logs` | 用量与延迟，按 `(organization_id, created_at)` 建索引 |

### 工单（3）

`tickets`（`(organization_id, ticket_no)` 唯一）、`ticket_comments`、`ticket_histories`（状态流转审计）。

### 审批（3）

`approval_templates`（`flow_config` JSON）、`approval_instances`、`approval_tasks`。

> 状态变更与历史/任务写入必须在**同一事务**内完成。

### 项目任务（3）

`projects`、`tasks`、`task_comments`。

### 系统管理（3）

`notifications`、`operation_logs`、`login_logs`。

## 3. 租户隔离规则

1. 除 `organizations`、`permissions` 外，所有业务表必须有 `organization_id`。
2. 任何查询都要带 `organization_id = 当前登录用户的企业`，**不接受前端传入的租户 ID**。
3. 唯一约束尽量带上 `organization_id`（例如用户名只在本企业内唯一）。
4. 越权访问统一返回 404，避免通过状态码探测其他企业的资源是否存在。

## 4. 索引设计说明

| 索引 | 解决的问题 |
| --- | --- |
| `idx_user_department` | 按部门筛选成员 |
| `idx_role_org_code` | 企业内角色编码唯一 + 登录后加载角色 |
| `idx_kb_org` | 知识库列表按企业过滤 |
| `idx_document_kb` / `idx_document_status` | 知识库内文档分页、解析状态轮询 |
| `idx_chat_conversation` | 会话消息按时间加载 |
| `idx_ticket_assignee(assignee_id, status)` | 「我的待办工单」 |
| `idx_approval_task(approver_id, status)` | 「待我审批」 |
| `idx_operation_time(organization_id, created_at)` | 审计日志按时间范围查询 |

## 5. 迁移工作流

```bash
cd backend

# 修改模型后生成迁移（需要能连上数据库）
alembic revision --autogenerate -m "add xxx"

# 检查生成的迁移文件！autogenerate 不会识别所有变更（重命名、部分默认值）
# 然后升级
alembic upgrade head

# 回滚一步
alembic downgrade -1

# 只生成 SQL 不执行（用于 DBA 审核 / 无法连库时校验 MySQL DDL）
alembic upgrade head --sql
```

注意事项：

- `alembic.ini` 保持 **纯 ASCII**，否则中文 Windows 下 `configparser` 会按 GBK 读取并报 `UnicodeDecodeError`。
- 首次 autogenerate 在 SQLite 上会生成 `DEFAULT (CURRENT_TIMESTAMP)`，MySQL 不认，用 `scripts/fix_migration_defaults.py` 修正为 `DEFAULT CURRENT_TIMESTAMP`。
- 生产环境不要开 `AUTO_CREATE_TABLES`，表结构统一走 Alembic。

## 6. Milvus Collection 设计（第三阶段）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | VARCHAR(64) | 主键，等于 `document_chunks.vector_id` |
| `organization_id` | INT64 | 租户过滤（必填） |
| `kb_id` | INT64 | 知识库过滤 |
| `document_id` | INT64 | 文档过滤 |
| `chunk_index` | INT64 | 切片序号 |
| `embedding` | FLOAT_VECTOR | 维度由 embedding 模型决定 |

检索时 **必须** 带 `organization_id` 和可见范围过滤，不能只按相似度返回。
