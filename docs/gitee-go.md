# Gitee Go 流水线接入说明

> 目标：`git push` 之后，前端在 Gitee 的云构建机上打包、自动下发到阿里云服务器，后端由服务器本地重建 —— 本地不再需要跑 `deploy/deploy_frontend.py`。

## 1. 流水线做了什么

```
git push main
   │
   ▼
Gitee Go 构建机（Node 22）
   ├─ npm ci
   ├─ npm run build（VITE_SHOW_DEMO_ACCOUNT=false）
   └─ 产物 frontend/dist → BUILD_ARTIFACT
   │
   ▼
主机部署（deploy@agent，服务器上常驻的 Agent 拉取制品）
   ├─ 解包 output.tar.gz → 覆盖 /opt/enterprise-ai/deploy/html
   ├─ 调 deploy/deploy.sh：git 同步 + 需要时重建后端 + 健康检查/回滚
   └─ curl /api/v1/health 与首页状态码
```

- 为什么前端放云端：服务器只有 1 GiB，`vite build` 峰值约 700 MB。
- 为什么后端仍在本机建：镜像层有缓存，重建约 40 秒；放到云端还得配镜像仓库，收益不大。
- 流水线文件：`.workflow/main-deploy.yml`（仓库即配置，改流水线改这个文件）。

## 2. 一次性配置（约 10 分钟）

### 2.1 开通 Gitee Go

仓库页顶部 `代码 / Issues / Pull Requests / Wiki / 统计 / 流水线 / 管理` 里点 **「流水线」** → 按提示开通。
需要账号绑定手机号（Gitee 的硬性要求）。

免费额度：单个仓库 **200 分钟**永久 + 个人/组织每月 **500 分钟**；一次构建约 1–2 分钟，够用。

### 2.2 建主机组并装 Agent

入口在 **仓库 →「管理」→「主机管理」**（部分版本在「流水线 → 主机组」）。

1. 新建主机组，**ID 填 `ea-aliyun`**（必须和 `.workflow/main-deploy.yml` 里的 `hostGroupID` 一字不差）。
2. 组内「添加主机」→ 页面会给出**一段安装命令**，复制到服务器上以 root 执行：

   ```bash
   # 形如（以页面给的为准，带一次性 token）：
   curl -fsSL https://.../install.sh | bash -s -- --token xxxxx
   ```

3. 等终端出现 `Agent started success`，回到页面把该主机勾选为「在线」，并把主机组**关联到本仓库**（在「功能设置 / 主机管理」里授权）。

> Agent 是常驻小进程，占十几到几十 MB 内存，对 1 GiB 机器可以接受；它是**主动外连** Gitee，不需要在阿里云防火墙开新端口。

### 2.3 让流水线生效

仓库里已经有 `.workflow/main-deploy.yml`，push 之后流水线列表会出现「主干发布（前端云端构建 → 阿里云部署）」。

如果没有自动出现：**流水线 → 新建 → 代码视图 / YAML**，把该文件内容整段粘进去保存（Gitee 会自己提交一份 yml 到仓库）。

### 2.4 先手动跑一次

在流水线页点「执行」，看两个阶段：

| 阶段 | 预期 | 耗时 |
| --- | --- | --- |
| 构建 | 前端构建成功，制品 `BUILD_ARTIFACT` | 1–2 分钟 |
| 部署 | 主机部署成功，日志末尾 `SITE_HTTP=200`、健康接口 JSON | 10 秒–1 分钟 |

如果构建阶段报 **Node 版本不存在**：打开流水线编辑页，把「前端构建」步骤里的 Node 版本下拉改成 22.x（或 20.x），保存后再跑。
注意：Gitee 会把改动写回 `.workflow/*.yml`，**记得 `git pull` 把这行拉回本地**，否则下次 push 又覆盖回去。

## 3. 之后怎么用

```bash
git add -A && git commit -m "feat: xxx" && git push
```

- 流水线：仓库「流水线」页看构建/部署日志。
- 服务器：`tail -f /var/log/ea-deploy.log` 看后端重建与回滚记录。
- 本地 `deploy/deploy_frontend.py` 保留作应急（比如 Gitee Go 额度用完、或流水线挂了）。

## 4. 和现有 systemd 定时器的关系

服务器上的 `ea-deploy.timer` 每 2 分钟也会拉一次代码。两者并存不会打架：`deploy.sh` 用 `flock` 串行化，且代码已同步时直接退出。

稳定运行一周后可以关掉定时器，让发布只有一个入口：

```bash
systemctl disable --now ea-deploy.timer
```

想留作兜底也可以：流水线失败时，定时器仍能把**后端**带上线（前端产物不会更新）。

## 5. 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| 保存 yml 报 `nodeVersion` 不合法 | 版本号不在可选列表，用编辑页下拉选一个 22.x，再 `git pull` |
| 部署阶段报主机离线 | Agent 掉了：服务器上 `ps -ef \| grep -i agent` 看进程，或回主机管理页重装 |
| `tar: output.tar.gz: No such file` | 制品名被 shell 截断。**制品名只用字母/数字/下划线**，不要带 `-` 或 `.` |
| 制品里找不到 `index.html` | `artifacts.path` 填错。当前是 `./frontend/dist`，从仓库根目录算 |
| `Permission denied` 写 `/opt/...` | Agent 不是 root 装的。卸载后以 root 重装 |
| `deploy/deploy.sh: No such file` | 服务器 `/opt/enterprise-ai` 还没部署好，先按 `docs/deploy.md` 起一遍 |
| 部署成功但页面没变 | 看日志里的「线上入口」是否为新 hash；浏览器 `Ctrl+F5`；再查 nginx 缓存头 |
| GUI 改了流水线，push 后又变回去 | 流水线配置以仓库 `.workflow/*.yml` 为准，改完记得把 Gitee 自动提交的那份拉回本地 |
| 构建排队很久 | 免费额度共享池，高峰期排队；可错峰或升级套餐 |

## 6. 兜底方案

Gitee Go 开通不了、或不想在服务器上跑 Agent 时：

1. 继续用现在的「本地构建 + SFTP 上传」：`python deploy/deploy_frontend.py`；
2. 后端仍由 `ea-deploy.timer` 每 2 分钟自动上线。

两条链路互不依赖，随时可以只启用其中一条。
