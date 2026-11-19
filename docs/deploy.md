# 部署手册（阿里云 ECS 单机 · Docker Compose）

本文记录第一阶段 + 第二阶段在**一台 2 vCPU / 1 GiB 内存**的 ECS 上从零部署的完整流程，
包含踩过的坑与对应处理。换机器或重装时可照着走一遍。

> 当前线上实例：Alibaba Cloud Linux 3（OpenAnolis）· 2 vCPU / 896 MiB / 30 GiB ESSD ·
> 预装 Docker 26.1.3 + Compose v2.27 · 代码目录 `/opt/enterprise-ai`

---

## 0. 为什么不用 `docker-compose.prod.yml`

仓库里的 `docker-compose.prod.yml` 是**完整形态**：Nginx + FastAPI + Celery + MySQL + Redis +
MinIO + etcd + Milvus。其中 Milvus standalone 光常驻内存就要 4 GB 以上，
1 GiB 的实例根本起不来。

第一、二阶段实际只需要 4 个服务，因此另写了 **`docker-compose.app.yml`**：

| 服务 | 作用 | 1 GiB 下的内存占用 |
| --- | --- | --- |
| mysql | 业务库 | ~156 MB |
| redis | 令牌黑名单 | ~5 MB |
| backend | FastAPI | ~89 MB |
| frontend | nginx 托管静态资源 + 反代 `/api` | ~5 MB |

合计约 255 MB，给系统和构建留出余量。**Milvus / etcd / MinIO / Celery 等到第三阶段再开**，
届时建议把实例升到 8 GB 以上。

---

## 1. 服务器初始化

### 1.1 加 swap（1 GiB 机器的救命稻草）

没有 swap 时，`vite build` 这种瞬时内存峰值会直接把 Node 打成 `Aborted (core dumped)`。

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab   # 重启后仍然生效
sysctl -w vm.swappiness=20
```

### 1.2 确认 Docker

```bash
docker version --format '{{.Server.Version}}'
docker compose version
systemctl is-enabled docker     # 应该是 enabled，保证重启后自动起容器
```

---

## 2. 拉取代码

```bash
mkdir -p /opt && cd /opt
git clone https://gitee.com/litianyu112233/Enterprise-AI.git enterprise-ai
cd enterprise-ai
```

> 仓库是公开的，不需要配置凭据。私有仓库需先配置 deploy key 或使用 HTTPS token。

---

## 3. 生成 `deploy/.env`（不入库）

`deploy/.env` 已在 `.gitignore` 中，**绝对不要提交**。内容参考 `deploy/.env.example`，
其中三个值必须现场随机生成：

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # AI_KEY_ENCRYPTION_KEY（用于加密企业 API Key）
openssl rand -hex 12   # MYSQL_ROOT_PASSWORD
```

关键项说明：

| 变量 | 说明 |
| --- | --- |
| `SECRET_KEY` | JWT 签名密钥，泄露 = 所有已签发令牌需作废 |
| `AI_KEY_ENCRYPTION_KEY` | 加密 `ai_model_configs.api_key_encrypted`；**与 SECRET_KEY 分开更安全** |
| `MYSQL_ROOT_PASSWORD` | 数据库密码，容器初始化时写入数据卷 |
| `CORS_ORIGINS` | 允许的前端来源，多个用逗号分隔（后端已支持逗号写法） |
| `AI_*` | 平台级兜底模型配置；企业可在后台另行配置自己的 Key |
| `APT_MIRROR` / `PIP_INDEX_URL` / `NPM_REGISTRY` | 构建期镜像源，见第 4 节 |

---

## 4. 构建镜像

```bash
cd /opt/enterprise-ai/deploy
docker compose -f docker-compose.app.yml build
```

### 4.1 国内构建必须换源

默认的 `deb.debian.org` 在国内会**卡在下载索引**（实测 3 分钟零增长）。
两个 Dockerfile 已参数化，通过 `.env` 传入即可：

```ini
APT_MIRROR=mirrors.aliyun.com
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
NPM_REGISTRY=https://registry.npmmirror.com
```

### 4.2 长时间构建用 systemd 托管

通过 SSH 直接跑几十分钟的构建，连接一断进程就没了。用 `systemd-run` 托管：

```bash
systemd-run --unit=ea-build --collect \
  sh -c 'cd /opt/enterprise-ai/deploy && docker compose -f docker-compose.app.yml build > /tmp/build.log 2>&1'

systemctl is-active ea-build   # 查状态
tail -f /tmp/build.log         # 看进度
```

---

## 5. 启动

```bash
cd /opt/enterprise-ai/deploy
docker compose -f docker-compose.app.yml up -d
```

启动顺序由 `depends_on` + healthcheck 保证：
`mysql(healthy) → backend → frontend`。

**backend 容器启动时会自动执行**：

```bash
alembic upgrade head      # 建表 / 增量迁移
python -m app.db.seed     # 幂等种子：企业、38 个权限点、4 个角色、admin 账号
uvicorn ... --workers 1   # 1 GiB 机器用单 worker，避免多进程抢内存
```

> ⚠️ **不要把 `backend/sql/init.sql` 挂到 `docker-entrypoint-initdb.d`**。
> 它不含 `alembic_version`，会在首次启动时先建表，随后 `alembic upgrade head`
> 因“表已存在”失败。建表统一交给 alembic 即可。

---

## 6. 验证清单

```bash
# 容器状态
docker compose -f docker-compose.app.yml ps

# 容器内侧
curl -s http://127.0.0.1/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1/

# 数据库
docker exec ea-mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N enterprise_ai \
  -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=\"enterprise_ai\";"'
```

从外网再验一遍：

```bash
curl -s http://<公网IP>/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' http://<公网IP>/login
curl -s -o /dev/null -w '%{http_code}\n' http://<公网IP>/register
```

浏览器全流程（登录 → 跳转 → 对话 → 模型配置）可用 Playwright 自动跑一遍。

### 安全组

阿里云默认只开 22。需要在控制台「安全组 → 入方向」放行 **80/80**（或后续的 443）。
数据库 3306、Redis 6379、后端 8000 **不要**对公网开放 —— 编排里用的都是 `expose`，
只有 frontend 映射了宿主机 80，这一点已确认。

---

## 7. 日常更新

```bash
# 本地
git add -A && git commit -m "..." && git push

# 服务器
cd /opt/enterprise-ai
git fetch origin && git reset --hard origin/main     # 服务器不做本地修改，直接对齐远端
cd deploy
docker compose -f docker-compose.app.yml up -d --build
```

`--build` 只会重建有变化的镜像，**MySQL 数据卷不受影响**。

只想重建某一端时：

```bash
docker compose -f docker-compose.app.yml build backend
docker compose -f docker-compose.app.yml up -d backend
```

容器重启策略是 `unless-stopped`，服务器重启后会自动拉起。

---

## 7.5 自动部署（Push 即上线）

服务器上启用 systemd 定时器后，**只要把代码推到 `main` 分支，2 分钟内自动上线**。

工作方式：

1. 每 2 分钟 `git fetch origin main`，比对本地与远端 SHA
2. 有差异 → 按变更路径决定只重建 `backend` 还是 `frontend`（纯文档改动不构建）
3. 部署前把当前镜像打 `:prev` 标签
4. `up -d` 后轮询 `/api/v1/health`，**60 秒内不健康就自动回滚代码和镜像**
5. `flock` 防止定时器在上一次未结束时重复触发
6. 全部过程写入 `/var/log/ea-deploy.log`

安装（服务器上执行一次）：

```bash
cd /opt/enterprise-ai
chmod +x deploy/deploy.sh
cp deploy/systemd/ea-deploy.service deploy/systemd/ea-deploy.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ea-deploy.timer
systemctl list-timers ea-deploy.timer
```

常用命令：

```bash
systemctl start ea-deploy.service        # 立刻手动跑一次，不等 2 分钟
systemctl status ea-deploy.timer         # 定时器状态
journalctl -u ea-deploy.service -n 50    # 服务侧日志
tail -f /var/log/ea-deploy.log           # 部署明细
systemctl disable --now ea-deploy.timer  # 关掉自动部署
```

> 开启后 `main` 的每次推送都会直接上线。开发中可以先把改动推到别的分支，
> 验证没问题再合并到 `main`。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 构建卡在 `Get:4 ... Packages` 不动 | 国内访问 `deb.debian.org` 挂起 | 设置 `APT_MIRROR=mirrors.aliyun.com` 重新构建 |
| `Code is nested too deeply`（element-plus 图标） | Alpine/musl 默认线程栈仅 128 KB，Rollup 原生解析器递归爆栈 | 前端构建阶段改用 `node:22-slim`（glibc 栈 8 MB） |
| `vite build` 报 `Aborted (core dumped)` | 1 GiB 内存下 V8 堆峰值 OOM | 构建阶段设 `NODE_OPTIONS=--max-old-space-size=768` |
| `alembic upgrade head` 报 table already exists | 同时挂载了 `init.sql` | 不要挂载 init.sql，建表只走 alembic |
| 登录成功但不跳转（历史问题） | 前端 `isLoggedIn` 由 computed 直接读 localStorage，无响应式依赖导致永久缓存 | 已改为 ref 持有 token，见 `stores/auth.ts` |
| MySQL 外键/事务不生效（本地 phpstudy） | 默认存储引擎是 MyISAM | `my.ini` 改 `default-storage-engine=InnoDB`，或 `SET GLOBAL` 立即生效 |

---

## 9. 待办的安全加固

- [ ] 更换 SSH 弱密码 / 改用密钥登录并关闭密码认证
- [ ] 修改 `admin` 的默认密码（`Admin@123456`）
- [ ] 演示结束后设置 `ALLOW_SELF_REGISTRATION=false`，或给注册接口加 IP 限流
- [ ] 有域名后接入 HTTPS（阿里云免费证书 + nginx 443）
