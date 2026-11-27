# 智企协同：GitHub Actions 自动部署教学手册（含填写说明与排错）

面向：**教别人从零搭一套「推代码 → 部署到阿里云」**。  
文中用「**【填】**」标出每个界面/命令里该填什么；用「**【本项目示例】**」给出当前仓库的真实值，别人照抄时请改成自己的。

**先看第 2 节：** [手动部署与自动部署流程对照](#2-手动部署与自动部署流程完整对照)。

---

## 0. 开始前准备一张「信息表」

先让对方填好这张表，后面所有地方都从这里抄，避免写错用户名。

| 项目 | 你要准备的内容 | 【本项目示例】 |
| --- | --- | --- |
| 本机项目路径 | 本地仓库绝对路径 | `D:\专高五前两个月\项目\专高六第一周个人项目` |
| GitHub 用户名 | github.com 登录名 | `l05ty21` |
| GitHub 仓库名 | 新建仓库时的名字 | `Enterprise-AI` |
| Gitee 用户名 | gitee.com 登录名 | `litianyu112233` |
| Gitee 仓库名 | 已有仓库名 | `Enterprise-AI` |
| 服务器公网 IP | 阿里云控制台「公」后面的 IP | `59.110.239.98` |
| SSH 登录用户 | 能操作 Docker / `/opt` 的用户 | `root`（推荐；也可用 `admin`+sudo） |
| 服务器项目目录 | 线上代码目录 | `/opt/enterprise-ai` |
| 服务器登录密码 | root 或 admin 密码 | （自己保管，不要写进仓库） |

拼出来的地址（后面会反复用到）：

| 名称 | 怎么拼 | 【本项目示例】 |
| --- | --- | --- |
| GitHub HTTPS | `https://github.com/{GitHub用户名}/{仓库名}.git` | `https://github.com/l05ty21/Enterprise-AI.git` |
| GitHub SSH | `git@github.com:{GitHub用户名}/{仓库名}.git` | `git@github.com:l05ty21/Enterprise-AI.git` |
| Gitee HTTPS | `https://gitee.com/{Gitee用户名}/{仓库名}.git` | `https://gitee.com/litianyu112233/Enterprise-AI.git` |
| Actions 页面 | `https://github.com/{GitHub用户名}/{仓库名}/actions` | `https://github.com/l05ty21/Enterprise-AI/actions` |
| Secrets 页面 | `https://github.com/{GitHub用户名}/{仓库名}/settings/secrets/actions` | （同上路径） |

> 注意用户名里的数字：本项目是 **`l05ty21`（数字 5）**，不要写成 `l0sty21`（数字 0）。

---

## 1. 先讲清楚整体在干什么

```
本机改代码
   ├─ git push github main  →  GitHub Actions 自动跑
   │                              ├─ 云端 npm build 前端（不占服务器内存）
   │                              ├─ 上传到服务器 /opt/enterprise-ai/deploy/html
   │                              └─ SSH 执行 deploy.sh（拉代码 + 重建后端）
   │
   └─ git push origin main  →  同步到 Gitee
                                  └─ 服务器从 Gitee 拉代码（国内快、稳）
```

**为什么要两个远程？**

| 远程名 | 指向哪里 | 干什么 |
| --- | --- | --- |
| `github` | GitHub | 触发自动部署流水线 |
| `origin` | Gitee | 给服务器 `deploy.sh` 拉后端代码 |

**为什么前端不在服务器上 build？**  
服务器只有约 1 GiB 内存，`vite build` 容易把机器打挂。改成 GitHub 云端构建再上传。

**为什么服务器不直接拉 GitHub？**  
阿里云访问 GitHub 经常超时。服务器只跟 Gitee。

---

## 2. 手动部署与自动部署流程（完整对照）

本项目有两套上线方式，**推荐日常用自动部署**；GitHub 网络不通或演示「手工发版」时用手动部署。

### 2.1 怎么选

| 方式 | 什么时候用 | 你要做什么 |
| --- | --- | --- |
| **自动部署** | 日常发版（推荐） | 本机 `git push` 两次 → 看 Actions 绿勾 |
| **手动部署** | GitHub 推不上、或给老师演示手工流程 | 本机推 Gitee + 传前端 + 服务器跑脚本 |
| **定时器轮询**（旧） | 仅对比演示 | `ea-deploy.timer` 每 2 分钟拉 Gitee；**平时应关闭**，避免和 Actions 冲突 |

---

### 2.2 自动部署流程（GitHub Actions）

```
本机改代码
   → git push github main          【触发 Actions】
   → git push origin main          【同步 Gitee，供服务器拉代码】
        ↓
GitHub Actions（云端自动）
   ① 拉取仓库代码
   ② npm ci + npm run build（构建前端）
   ③ 用 Secrets 里的 SSH 密钥登录服务器
   ④ scp 上传前端到 /opt/enterprise-ai/deploy/html
   ⑤ ssh 执行 /opt/enterprise-ai/deploy/deploy.sh
        ├─ git fetch Gitee
        ├─ 有后端变更 → docker compose build backend + up
        └─ 健康检查 /api/v1/health（失败则回滚）
        ↓
浏览器打开 http://你的服务器IP ，Ctrl+F5 强刷验证
```

**本机要敲的命令：**

```powershell
cd "D:\专高五前两个月\项目\专高六第一周个人项目"

git add .
git commit -m "说明改了什么"
git push github main    # 触发自动部署
git push origin main    # 同步 Gitee
```

**然后：** 打开 https://github.com/l05ty21/Enterprise-AI/actions  
看 **「部署至阿里云」** 是否绿勾。一般**不用**再点「运行」按钮。

**流水线文件：** `.github/workflows/deploy.yml`  
**服务器脚本（被 Actions 调用）：** `deploy/deploy.sh`

---

### 2.3 手动部署流程（不依赖 Actions）

一句话：**推 Gitee → 本机传前端 → 服务器跑 deploy.sh**。

```
① 本机：git push origin main（推到 Gitee）
② 本机：python deploy/deploy_frontend.py（构建并上传前端）
③ 服务器：sudo /opt/enterprise-ai/deploy/deploy.sh（拉代码 + 重启后端）
④ 浏览器强刷验证
```

#### 步骤 ① 本机提交并推到 Gitee

```powershell
cd "D:\专高五前两个月\项目\专高六第一周个人项目"

git add .
git commit -m "说明改了什么"
git push origin main
```

#### 步骤 ② 本机构建前端并上传到服务器

> 不要在 1G 服务器上执行 `npm run build`。

```powershell
$env:ECS_PASS='你的服务器密码'
# 可选：$env:ECS_HOST='59.110.239.98'

python deploy/deploy_frontend.py
```

脚本会：本机 `npm run build` → 打包上传 → 解压到服务器 `/opt/enterprise-ai/deploy/html`。

若本地已经 build 过、只想再传一次：

```powershell
python deploy/deploy_frontend.py --skip-build
```

#### 步骤 ③ 服务器拉代码并部署后端

SSH 登录阿里云后：

```bash
sudo /opt/enterprise-ai/deploy/deploy.sh
```

等价于：从 Gitee 拉最新代码 → 按需重建后端容器 → 健康检查。

若需要逐步手动（排错时）：

```bash
cd /opt/enterprise-ai
sudo git fetch origin main
sudo git reset --hard origin/main
cd deploy
sudo docker compose -f docker-compose.app.yml build backend
sudo docker compose -f docker-compose.app.yml up -d
curl -s http://127.0.0.1/api/v1/health
```

有数据库迁移时再执行（按线上习惯）：

```bash
sudo docker compose -f docker-compose.app.yml exec backend alembic upgrade head
```

#### 步骤 ④ 验证

1. 浏览器打开 `http://59.110.239.98`，Ctrl+F5  
2. 服务器：`curl -s http://127.0.0.1/api/v1/health`  
3. 可选：`sudo tail -n 40 /var/log/ea-deploy.log`

---

### 2.4 两种方式对照表

| 步骤 | 自动部署 | 手动部署 |
| --- | --- | --- |
| 推代码 | `push github` + `push origin` | 至少 `push origin` |
| 构建前端 | Actions 云端构建 | 本机 `deploy_frontend.py` |
| 上传前端 | Actions `scp` 自动上传 | 同上脚本自动上传 |
| 更新后端 | Actions SSH 调 `deploy.sh` | 你自己在服务器执行 `deploy.sh` |
| 看结果 | GitHub Actions 绿勾 | 浏览器 + `curl` 健康检查 |
| 适用 | 日常、演示 CI/CD | 网络不稳、教学「手工发版」 |

---

### 2.5 改动范围速查

| 你改了什么 | 自动部署怎么做 | 手动部署怎么做 |
| --- | --- | --- |
| 只改前端 | 双 push，等 Actions | `push origin` + `deploy_frontend.py` |
| 只改后端 | 双 push，等 Actions | `push origin` + 服务器 `deploy.sh` |
| 前后端都改 | 双 push，等 Actions | `push origin` + `deploy_frontend.py` + `deploy.sh` |

---

## 3. 第一步：在 GitHub 新建空仓库（网页上填什么）

打开：https://github.com/new

| 网页字段（中文界面） | 【填】什么 | 【本项目示例】 | 注意 |
| --- | --- | --- | --- |
| Owner（所有者） | 你的 GitHub 账号 | `l05ty21` | 默认即可 |
| Repository name（存储库名称） | 英文仓库名 | `Enterprise-AI` | 不要空格 |
| Description（描述） | 可空，或写项目简介 | `企业级 AI SaaS` | 可选 |
| Public / Private | 选 **Public** 更省事（Actions 额度） | Public | 私有仓也行但有分钟限制 |
| Add a README | **关掉** | Off | 本地已有代码，空仓最好推 |
| Add .gitignore | **None** | None | 同上 |
| Add a license | **None** | None | 同上 |

点绿色按钮：**Create repository（创建存储库）**。

---

## 4. 第二步：本机关联 GitHub 并推送（终端填什么）

在**本机**打开 PowerShell（不是阿里云网页终端）：

```powershell
# 【填】改成你的本机项目路径
cd "D:\专高五前两个月\项目\专高六第一周个人项目"

# 看现有远程：通常已有 origin → Gitee
git remote -v
```

添加名为 `github` 的远程（名字建议就叫 `github`，后面命令都按这个写）：

```powershell
# 【填】把 URL 换成你的 GitHub 地址
git remote add github https://github.com/l05ty21/Enterprise-AI.git

git push -u github main
```

| 命令里的词 | 含义 | 你能不能改 |
| --- | --- | --- |
| `github` | 远程的**别名** | 能改，但本文后面都按 `github` 写 |
| `https://github.com/...` | 真实仓库地址 | **必须改成你的** |
| `main` | 分支名 | 若你主分支叫 `master` 就改成 `master` |

成功标志：终端出现 `main -> main`，浏览器打开 GitHub 仓库能看到代码。

---

## 5. 第三步：生成部署用 SSH 密钥（本机）

### 5.1 生成命令（一般不用改）

```powershell
ssh-keygen -t ed25519 -C "github-actions" -f $env:USERPROFILE\.ssh\gha_deploy -N '""'
```

| 参数 | 【填】什么 | 说明 |
| --- | --- | --- |
| `-C "github-actions"` | 备注名，可随便写 | 只是标签 |
| `-f ...\gha_deploy` | 私钥文件名 | 会生成 `gha_deploy` 和 `gha_deploy.pub` |
| `-N '""'` | 空密码 | Actions 不能交互输密码，必须空 |

生成后本机有两个文件：

| 文件 | 用途 | 给谁 |
| --- | --- | --- |
| `C:\Users\你的用户名\.ssh\gha_deploy` | **私钥** | 只给 GitHub Secret（先转 Base64） |
| `C:\Users\你的用户名\.ssh\gha_deploy.pub` | **公钥** | 放到服务器 `authorized_keys` |

### 5.2 把公钥装到服务器

```powershell
# 【填】root → 你的 SSH 用户；IP → 你的公网 IP
type $env:USERPROFILE\.ssh\gha_deploy.pub | ssh root@59.110.239.98 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

出现 `password:` 时：**盲打**服务器密码后回车（屏幕不会显示 `*`，这是正常的）。

### 5.3 测试免密是否成功

```powershell
# 【填】用户和 IP
ssh -i $env:USERPROFILE\.ssh\gha_deploy root@59.110.239.98
```

成功：直接进入 `root@...#` 提示符，不再要密码。  
然后输入 `exit` 回到本机。

---

## 6. 第四步：GitHub Secrets（网页上「这里填什么」）

### 6.1 打开哪里

浏览器打开（【填】用户名和仓库名）：

`https://github.com/l05ty21/Enterprise-AI/settings/secrets/actions`

路径点击版：仓库页 → **Settings（设置）** → 左侧 **Secrets and variables（秘密与变量）** → **Actions（行动）** → **New repository secret（新存储库密钥）**。

要建 **3 个** Secret（建三次，每次一个）。

---

### 6.2 第 1 个 Secret：`SSH_HOST`

| 框 | 【填】什么 | 【本项目示例】 | 错例 |
| --- | --- | --- | --- |
| **Name** | 必须一字不差：`SSH_HOST` | `SSH_HOST` | `ssh_host`、`HOST`（名字错了流水线读不到） |
| **Secret** | 服务器公网 IP，不要加 `http://` | `59.110.239.98` | `http://59.110.239.98`、带空格 |

点 **Add secret（添加密钥）**。

---

### 6.3 第 2 个 Secret：`SSH_USER`

| 框 | 【填】什么 | 【本项目示例】 | 说明 |
| --- | --- | --- | --- |
| **Name** | `SSH_USER` | `SSH_USER` | 必须这个拼写 |
| **Secret** | SSH 登录用户名 | `root` | 若用 admin，填 `admin`，且要保证能跑 `deploy.sh` / docker |

---

### 6.4 第 3 个 Secret：`SSH_PRIVATE_KEY`（最容易填错）

**不要**直接粘贴私钥原文（Windows 容易丢换行，Actions 会报「未找到密钥」）。  
**要**粘贴私钥文件的 **Base64 一整行**。

本机先执行（把内容拷进剪贴板）：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$env:USERPROFILE\.ssh\gha_deploy")) | Set-Clipboard
```

然后在 GitHub：

| 框 | 【填】什么 | 对不对怎么看 |
| --- | --- | --- |
| **Name** | `SSH_PRIVATE_KEY` | 必须这个名字（流水线按这个读） |
| **Secret** | 剪贴板里那一长串 Base64 | 一般以 `LS0t` 开头；**不是** `BEGIN PRIVATE KEY`；**不是** `.pub` 公钥；**不是** `Get-Content ...` 命令 |

点 **添加密钥**。

三个建完后，Secrets 列表应能看到：

```text
SSH_HOST
SSH_PRIVATE_KEY
SSH_USER
```

（顺序不重要。）

可选第 4 个：

| Name | Secret | 何时需要 |
| --- | --- | --- |
| `SSH_PORT` | `22` | 只有改过 SSH 端口才需要；不填默认 22 |

---

## 7. 第五步：流水线文件里有什么（一般不用改填写项）

文件位置：项目里的 `.github/workflows/deploy.yml`

教别人时强调：

| 内容 | 要不要手改 |
| --- | --- |
| `on.push.branches: [main]` | 主分支若叫 `master` 才改 |
| `secrets.SSH_HOST` 等 | **不要**把真实 IP/密钥写进 yml，必须走 Secrets |
| `VITE_SHOW_DEMO_ACCOUNT: "true"` | 演示要显示账号就 `true`；正式上线可改 `false` |
| 服务器路径 `/opt/enterprise-ai` | 若别人目录不同，要改 yml 里对应路径 |

把文件提交并推到 GitHub 后，Actions 才会出现「Deploy to Aliyun / 部署至阿里云」。

---

## 8. 第六步：服务器上要执行的命令（【填】哪里）

用阿里云「远程连接」或本机 SSH 登录服务器。若是 `admin` 用户，记得加 `sudo`。

### 8.1 关掉旧的定时自动部署（避免和 Actions 抢）

```bash
sudo systemctl disable --now ea-deploy.timer
systemctl is-enabled ea-deploy.timer
systemctl is-active ea-deploy.timer
```

期望大致：`disabled` + `inactive`。

### 8.2 确认服务器从 Gitee 拉代码

```bash
cd /opt/enterprise-ai

# 【填】换成你的 Gitee 地址
sudo git remote set-url origin https://gitee.com/litianyu112233/Enterprise-AI.git

sudo git remote -v
sudo git fetch origin main
```

`git remote -v` 应显示 **gitee.com**，不要显示 github.com。

---

## 9. 日常发版（教别人反复练的四步）

**在本机终端执行**（路径【填】成学员自己的）：

```powershell
cd "D:\专高五前两个月\项目\专高六第一周个人项目"

git add .
git commit -m "这里写清楚改了什么"   # 【填】提交说明，随便但要有意义
git push github main                 # 触发 Actions
git push origin main                 # 同步 Gitee
```

然后打开 Actions 页面（【填】用户名仓库名）：

https://github.com/l05ty21/Enterprise-AI/actions

| 看到什么 | 含义 |
| --- | --- |
| 黄圈转圈 | 正在跑 |
| 绿勾 | 部署成功 |
| 红叉 | 失败 → 点进去看是哪一步红了 |

**一般不用点「运行 / Run workflow」**；push 就会自动跑。  
「手动运行」只在自动没触发时用。

成功后浏览器打开站点，**Ctrl+F5** 强刷。

---

## 10. 登录页演示账号（演示时填什么）

登录页展示（`frontend/src/views/LoginView.vue`）：

| 输入框 | 【填】什么 |
| --- | --- |
| 企业编码 | `demo` |
| 用户名 | `admin` |
| 密码 | `Admin@123456` |

也可点页面上的 **「一键填充」**。

要隐藏演示账号：把 `SHOW_DEMO_ACCOUNT` 改为 `false`，重新构建部署前端。

---

## 11. 常见错误：现象 → 原因 → 怎么填/怎么敲

### 11.1 推 GitHub：`Connection was reset`

**原因：** 网络到 GitHub 不稳。

**改成 SSH 再推（推荐）：**

1. 本机生成/查看**另一把**登录用公钥（可与部署钥分开）：

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
# 没有就：ssh-keygen -t ed25519 -C "github" -f $env:USERPROFILE\.ssh\id_ed25519 -N '""'
```

2. 打开 https://github.com/settings/keys → **New SSH key**  

| 框 | 【填】 |
| --- | --- |
| Title | 例如 `我的电脑` |
| Key | 整行 `ssh-ed25519 AAAA...` 公钥内容 |

3. 本机改远程并推：

```powershell
# 【填】你的 GitHub SSH 地址
git remote set-url github git@github.com:l05ty21/Enterprise-AI.git
ssh -T git@github.com
git push github main
```

---

### 11.2 `non-fast-forward` / rejected

**原因：** 远程比你新，或历史分叉。

```powershell
# 若推 Gitee 被拒：
git pull origin main --rebase
git push origin main

# 若推 GitHub 被拒：
git pull github main --rebase
git push github main
```

`pull --rebase`：**先把远程新提交拉下来叠在下面，再让你的提交接在后面**，然后才能 push。  
不要随手 `--force`。

---

### 11.3 Actions 红叉：`ssh: 未找到密钥` / 无法认证

**原因：** `SSH_PRIVATE_KEY` 填错了。

| 错填成了什么 | 正确应该是 |
| --- | --- |
| `Get-Content $env:USERPROFILE\...` 这行命令 | Base64 字符串 |
| `gha_deploy.pub` 公钥内容 | 私钥的 Base64 |
| 带换行的 `BEGIN OPENSSH PRIVATE KEY` 原文 | Base64（本流水线按 Base64 解码） |

按 **第 6.4 节** 重新生成 Base64 → 编辑 Secret → Actions 里 **Re-run all jobs**。

---

### 11.4 VS Code 左上角一直「同步更改」，一点就弹 Connection was reset

**原因：** 同步按钮默认对的是 GitHub；GitHub 推失败，数字消不掉。

**教别人：** 先别点同步按钮，用终端把 `git push github main` 推成功；成功后同步提示会消失。

---

### 11.5 服务器 `Permission denied`

**原因：** `admin` 改不了 root 的目录。

```bash
sudo git remote set-url origin https://gitee.com/你的Gitee用户/你的仓库.git
sudo git fetch origin main
```

---

### 11.6 服务器拉 GitHub 卡住 / `curl 52` / timed out

**原因：** 服务器到不了 GitHub。

**处理：** origin 改回 Gitee，不要坚持服务器拉 GitHub。

---

### 11.7 Linux 提示 Password 却「输入不进去」

**不是键盘坏了。** 密码输入默认不回显。盲打完回车。  
权限不够时用：`sudo 命令`。

---

### 11.8 只推了 GitHub、没推 Gitee

前端可能已更新，后端代码服务器拉不到最新。  
**口诀：两个都推。**

```powershell
git push github main
git push origin main
```

---

### 11.9 Actions 黄色提示 Node.js 20 deprecated

**可忽略。** 真正失败看红叉步骤日志。

---

## 12. 备用方案：GitHub 推不上去时怎么上线

本机：

```powershell
git push origin main

# 【填】服务器密码
$env:ECS_PASS='你的服务器密码'
# 可选：$env:ECS_HOST='59.110.239.98'

python deploy/deploy_frontend.py
```

这会本机构建前端并上传；后端仍靠服务器从 Gitee 拉取（若开了 timer）或你手动 `sudo /opt/enterprise-ai/deploy/deploy.sh`。

---

## 13. 验收清单（教完让对方自己勾）

- [ ] GitHub 空仓已建，且未勾选 README  
- [ ] `git remote -v` 能看到 `github` → GitHub，`origin` → Gitee  
- [ ] `gha_deploy` 密钥能免密 SSH 进服务器  
- [ ] Secrets 三个名字完全正确：`SSH_HOST` / `SSH_USER` / `SSH_PRIVATE_KEY`  
- [ ] `SSH_PRIVATE_KEY` 是 Base64，不是命令、不是公钥  
- [ ] 服务器 `ea-deploy.timer` 已 disable  
- [ ] 服务器 `origin` 指向 Gitee，且 `git fetch` 成功  
- [ ] `git push github main` 后 Actions 出现绿勾  
- [ ] 浏览器强刷站点看到新前端  
- [ ] 登录页演示账号可用：`demo` / `admin` / `Admin@123456`  

---

## 14. 给别人讲的 30 秒版

「改完代码在本机 push 到 GitHub，Actions 自动构建前端并 SSH 部署到阿里云；同时 push 到 Gitee，服务器从 Gitee 拉后端。Secrets 里要填服务器 IP、SSH 用户、私钥的 Base64。服务器不要直连 GitHub，会超时。」

---

## 15. 相关文件

| 文件 | 作用 |
| --- | --- |
| `.github/workflows/deploy.yml` | Actions 流水线（读 Secrets） |
| `deploy/deploy.sh` | 服务器部署脚本 |
| `deploy/deploy_frontend.py` | 本机上传前端（备用） |
| `deploy/systemd/ea-deploy.timer` | 旧轮询方案（应关闭） |
| `docs/deploy.md` | 阿里云 Docker 部署总手册 |
| `frontend/src/views/LoginView.vue` | 登录页与演示账号 |
