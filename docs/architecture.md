# 架构设计

## 1. 总体分层

```
浏览器 (Vue 3 SPA)
      │  HTTPS / JSON
      ▼
┌─────────────────────────────────────────────┐
│ API 层  app/api/v1/endpoints                │  路由、参数解析、权限声明
├─────────────────────────────────────────────┤
│ 依赖层  app/api/deps.py                     │ JWT 解析、CurrentUser、require_permissions
├─────────────────────────────────────────────┤
│ 服务层  app/services                        │ 业务规则、事务边界、跨表校验
├─────────────────────────────────────────────┤
│ 仓储层  app/repositories                    │ 单表/联表查询，返回 ORM 对象
├─────────────────────────────────────────────┤
│ 模型层  app/models (SQLAlchemy 2.0 async)   │ 26 张表，MySQL 8.0
└─────────────────────────────────────────────┘
      │                    │
      ▼                    ▼
   MySQL 8.0          Redis（令牌黑名单 / 后续缓存与队列）
```

设计原则：

1. **路由层不写业务**：只做参数绑定、调用 service、返回 schema。
2. **服务层管事务**：一个业务动作一个事务，`commit` 显式调用。
3. **仓储层只管数据**：不出现业务判断，便于后续替换或加缓存。
4. **Schema 与模型分离**：对外结构不随表结构漂移。

## 2. 请求生命周期

以 `GET /api/v1/users` 为例：

```
Request
  → CORSMiddleware
  → HTTPBearer 取出 access_token
  → decode_token() 校验签名/过期/类型(access)
  → TokenStore 检查 jti 是否已吊销
  → 加载 User，校验 status=1 且 organization_id 与令牌一致
  → 查询角色 → 计算 permissions（super_admin 直通全量）
  → require_permissions("user:read")
  → UserService.list_users(org_id, query, page)
  → UserRepository.search() → SQL
  → 组装 UserRead（含部门名、角色）
  → 200 {items, total, page, page_size, pages}
```

## 3. 认证与令牌

| 令牌 | 有效期 | 载荷 | 用途 |
| --- | --- | --- | --- |
| access | 60 分钟（可配） | `sub, org, typ=access, jti, exp` | 访问接口 |
| refresh | 7 天（可配） | `sub, org, typ=refresh, jti, exp` | 换取新令牌 |

- 密码使用 **Argon2id**（`pwdlib`），不保存明文，也不做可逆加密。
- 刷新时执行**令牌轮换**：旧 refresh 立即写入吊销名单，降低泄露风险。
- 退出登录同时吊销 access 与 refresh 的 `jti`。
- 吊销名单优先用 Redis（`token:revoked:{jti}`，TTL 与令牌一致）；未配置 `REDIS_URL` 时退化为进程内字典，**仅适合单实例开发**。
- 关键点：`organization_id` 写进令牌，服务端不信任前端传入的租户 ID。

## 4. 权限模型（RBAC）

```
User ──< user_roles >── Role ──< role_permissions >── Permission
```

- `permissions.code` 是全局唯一的字符串，例如 `user:create`、`menu:knowledge`。
- 权限分三类：`menu`（前端菜单/路由）、`button`（页面操作）、`api`（接口）。
- 路由通过 `require_permissions("role:update")` 声明；`super_admin` 角色直通。
- 前端 `auth.has(code)` 控制菜单与按钮显示，**但后端仍然逐接口校验**——前端隐藏不是安全边界。

内置角色（种子脚本创建）：

| code | 名称 | 权限 |
| --- | --- | --- |
| `super_admin` | 超级管理员 | 全部 |
| `org_admin` | 企业管理员 | 全部（本企业范围） |
| `dept_manager` | 部门经理 | 用户/部门只读、工单、审批、项目 |
| `employee` | 普通员工 | 工单、审批、项目只读、AI 对话 |

## 5. 多租户隔离

三层保障：

1. **数据层**：所有业务表带 `organization_id` 外键。
2. **服务层**：查询条件强制拼 `organization_id = current_user.organization_id`。
3. **测试层**：`tests/test_tenant_isolation.py` 验证 A 企业无法读写 B 企业数据（返回 404 而非 403，避免探测资源是否存在）。

跨企业数据在接口层表现为「不存在」，这是有意的设计。

## 6. 错误处理

统一异常 `AppError` → JSON：

```json
{
  "code": "forbidden",
  "message": "缺少权限: user:create",
  "detail": null,
  "path": "/api/v1/users"
}
```

| 状态码 | code | 场景 |
| --- | --- | --- |
| 400 | `bad_request` | 业务参数不合法（如部门成环） |
| 401 | `unauthorized` | 未登录、令牌过期、密码错误 |
| 403 | `forbidden` | 权限不足 |
| 404 | `not_found` | 资源不存在或不属于本企业 |
| 409 | `conflict` | 唯一约束冲突（用户名、角色编码） |
| 422 | `validation_error` | Pydantic 校验失败，`detail` 为字段级错误数组 |

## 7. AI 模型网关（第二阶段设计）

业务代码不直接依赖厂商 SDK，统一抽象：

```python
class LLMProvider(Protocol):
    async def chat(self, messages, **kwargs) -> ChatResult: ...
    async def chat_stream(self, messages, **kwargs) -> AsyncIterator[str]: ...

class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

- `ModelGateway` 根据 `ai_model_configs` 选择 provider，负责参数映射、超时、重试、用量记录（`ai_usage_logs`）。
- 云端与 Ollama 都走 OpenAI 兼容协议，因此只需要一个 HTTP 实现 + 不同 `base_url`。
- **向量维度一致性**：更换 embedding 模型必须重建 collection，`document_chunks.embedding_model` 记录每批切片所用模型，便于灰度与回滚。

## 8. 已知取舍

| 取舍 | 原因 |
| --- | --- |
| 令牌吊销用 Redis 但允许内存退化 | 开发环境不强制装 Redis；多实例部署必须配 Redis |
| 用户删除=禁用 | 工单、审批、日志依赖用户外键，物理删除会破坏历史 |
| `departments.leader_id` 不建外键 | 与 `users.department_id` 互相引用会形成建表环 |
| 测试用 SQLite | 无需外部服务即可跑 CI；生产仍用 MySQL，DDL 由 Alembic 生成 |
