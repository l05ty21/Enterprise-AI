# 接口文档

- **Base URL**：`http://127.0.0.1:8000/api/v1`
- **交互式文档**：`/docs`（Swagger UI）、`/redoc`
- **认证方式**：`Authorization: Bearer <access_token>`
- **内容类型**：`application/json; charset=utf-8`

## 1. 通用约定

### 分页

请求：`?page=1&page_size=20`（`page ≥ 1`，`1 ≤ page_size ≤ 200`）

响应：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "pages": 0
}
```

### 错误

```json
{
  "code": "forbidden",
  "message": "缺少权限: user:create",
  "detail": null,
  "path": "/api/v1/users"
}
```

| 状态码 | code | 含义 |
| --- | --- | --- |
| 400 | `bad_request` | 业务参数不合法 |
| 401 | `unauthorized` | 未登录 / 令牌无效 / 密码错误 |
| 403 | `forbidden` | 权限不足 |
| 404 | `not_found` | 资源不存在或不属于当前企业 |
| 409 | `conflict` | 唯一约束冲突 |
| 422 | `validation_error` | 参数校验失败（`detail` 为字段错误数组） |

## 2. 认证

### POST /auth/login

无需认证。

```json
{
  "username": "admin",
  "password": "Admin@123456",
  "organization_code": "demo"
}
```

`organization_code` 在系统只有一个企业时可省略；多个企业时必须提供。

响应 `200`：

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /auth/refresh

```json
{ "refresh_token": "eyJhbGciOi..." }
```

旧 refresh 立即失效（轮换）。重复使用返回 `401`。

### POST /auth/logout

需要认证。body 可选 `{"refresh_token": "..."}`，同时吊销两者。

响应：`{"message": "已退出登录"}`

### GET /auth/me

返回当前用户、企业、部门、角色与权限点：

```json
{
  "id": 1,
  "username": "admin",
  "real_name": "系统管理员",
  "organization_id": 1,
  "organization_name": "示例科技有限公司",
  "department_id": null,
  "department_name": null,
  "is_superuser": true,
  "roles": [{ "id": 1, "name": "超级管理员", "code": "super_admin" }],
  "permissions": ["user:read", "user:create", "..."]
}
```

### PUT /auth/me

可改 `real_name`、`email`、`phone`、`avatar`。

### PUT /auth/me/password

```json
{ "old_password": "Admin@123456", "new_password": "NewPassw0rd" }
```

新密码要求：至少 8 位，且同时包含字母和数字。

## 3. 用户管理

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/users` | `user:read` | 列表，支持 `keyword`/`department_id`/`status`/`role_id` |
| POST | `/users` | `user:create` | 创建 |
| GET | `/users/{id}` | `user:read` | 详情 |
| PUT | `/users/{id}` | `user:update` | 修改（可重置密码、换角色） |
| DELETE | `/users/{id}` | `user:delete` | 禁用（软删除） |

创建示例：

```json
{
  "username": "zhangsan",
  "password": "Zhang@123456",
  "real_name": "张三",
  "email": "zhangsan@example.com",
  "department_id": 3,
  "role_ids": [4],
  "status": 1
}
```

约束：

- 用户名：字母开头，3-64 位，可含数字、`_`、`.`、`-`。
- 不能禁用当前登录账号。
- `role_ids` 必须是本企业的角色，否则 `400`。

## 4. 角色与权限

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/roles` | `role:read` | 角色列表（含 `permission_ids`、`user_count`） |
| POST | `/roles` | `role:create` | 创建 |
| GET | `/roles/{id}` | `role:read` | 详情 |
| PUT | `/roles/{id}` | `role:update` | 改名 / 改描述 / 重设权限 |
| DELETE | `/roles/{id}` | `role:delete` | 有用户或内置角色时拒绝 |
| GET | `/permissions` | `role:read` | 全部权限点 |

创建示例：

```json
{
  "name": "审计员",
  "code": "auditor",
  "description": "只读角色",
  "permission_ids": [11, 12, 15]
}
```

## 5. 部门

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/departments` | `department:read` | 返回树形结构 |
| POST | `/departments` | `department:create` | 创建 |
| PUT | `/departments/{id}` | `department:update` | 改名 / 移动 / 设负责人 |
| DELETE | `/departments/{id}` | `department:delete` | 有子部门或成员时拒绝 |

树形响应示例：

```json
[
  {
    "id": 1,
    "name": "总公司",
    "parent_id": null,
    "leader_name": null,
    "member_count": 0,
    "children": [
      { "id": 2, "name": "技术部", "parent_id": 1, "member_count": 2, "children": [] }
    ]
  }
]
```

移动部门时若目标是自己或自己的子部门，返回 `400`（防环）。

## 6. 系统

### GET /health

```json
{
  "status": "ok",
  "app": "智企协同 Enterprise AI",
  "env": "dev",
  "version": "0.1.0",
  "database": "up"
}
```

## 7. curl 示例

```bash
# 登录
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123456","organization_code":"demo"}'

# 查询用户
curl "http://127.0.0.1:8000/api/v1/users?page=1&page_size=10" \
  -H "Authorization: Bearer <access_token>"

# 创建部门
curl -X POST http://127.0.0.1:8000/api/v1/departments \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"前端组","parent_id":2}'
```
