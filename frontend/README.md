# 前端说明（Vue 3 + TypeScript）

## 技术栈

Vue 3.5 · TypeScript 5.7 · Vite 6 · Element Plus 2.9 · Pinia · Vue Router 4 · Axios · ECharts

## 启动

```bash
npm install
npm run dev
```

默认 <http://localhost:5173>，通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`。

其他命令：

```bash
npm run type-check   # vue-tsc 类型检查
npm run build        # 类型检查 + 生产构建
npm run preview      # 预览构建产物
```

## 目录

```
src/
├── api/            # client.ts（拦截器/自动刷新）+ 各业务接口
├── layouts/        # DefaultLayout：侧边栏 + 顶栏
├── router/         # 路由表 + 全局守卫
├── stores/         # auth（用户/权限）、app（侧边栏）
├── types/          # 与后端 schema 对应的类型
├── utils/          # token 存取
└── views/          # 登录、工作台、用户、角色、部门、个人中心、403/404
```

## 权限如何生效

1. 登录后 `auth.fetchMe()` 拿到 `permissions: string[]` 与 `is_superuser`。
2. 路由 `meta.permission` 在守卫里校验，不通过跳 `/403`。
3. 菜单与按钮用 `auth.has('user:create')` 控制显示。
4. **前端隐藏不等于安全**：后端每个接口仍会独立校验。

```ts
// router/index.ts
{ path: 'users', meta: { permission: 'user:read' } }
```

```vue
<el-button v-if="auth.has('user:create')">新建用户</el-button>
```

## Token 与自动刷新

- access / refresh 存在 `localStorage`。
- 请求拦截器自动附加 `Authorization: Bearer`。
- 响应遇到 `401` 时：用 refresh 换新令牌并重放原请求；刷新失败则清空登录态跳登录页。
- 并发请求只触发一次刷新（队列合并）。
- 退出登录会调用后端 `/auth/logout` 吊销令牌。

## 环境变量

| 文件 | 变量 | 说明 |
| --- | --- | --- |
| `.env.development` | `VITE_API_BASE_URL=/api/v1` | 走 Vite 代理 |
| `.env.development` | `VITE_PROXY_TARGET` | 后端地址 |
| `.env.production` | `VITE_API_BASE_URL=/api/v1` | 由 Nginx 代理 |

## 生产构建

```bash
npm run build      # 产物在 dist/
```

用 Nginx 托管 `dist/` 并把 `/api` 反代到 FastAPI，配置见 `frontend/nginx.conf`。

## 页面清单

| 路由 | 说明 | 需要的权限 |
| --- | --- | --- |
| `/login` | 登录（可填企业编码） | 公开 |
| `/dashboard` | 工作台、统计卡片、进度图 | `menu:dashboard` |
| `/users` | 用户列表、筛选、增改、禁用 | `user:read`（操作另需 create/update/delete） |
| `/roles` | 角色列表、权限勾选分配 | `role:read` |
| `/departments` | 部门树、增改删 | `department:read` |
| `/profile` | 个人资料、修改密码 | 登录即可 |

## 注意

- 角色 / 部门下拉数据需要 `role:read` / `department:read`；没有权限时组件自动隐藏，页面仍可用。
- Element Plus 为全量引入（打包体积较大但配置简单）；后续可切换 `unplugin-vue-components` 按需引入。
- ECharts 只注册了用到的 `BarChart` + 基础组件，新增图表类型需在 `DashboardView.vue` 里扩展 `use([...])`。
