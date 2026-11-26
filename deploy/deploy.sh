#!/usr/bin/env bash
# 自动部署脚本：检测远端分支 → 构建变动服务 → 重启 → 健康检查 → 失败回滚
#
# 手动执行：  /opt/enterprise-ai/deploy/deploy.sh
# 自动执行：  ea-deploy.timer（每 2 分钟一次）
# 日志：      /var/log/ea-deploy.log
#
# 设计要点：
#   1. flock 防并发——定时器可能在上一次部署还没结束时再次触发
#   2. 前端不再在服务器构建：静态产物由本地 deploy/deploy_frontend.py 上传到
#      deploy/html，通过 bind mount 直接给 nginx 使用（1 GiB 内存扛不住 vite build）
#   3. 只重建后端；纯前端提交只做 git 同步，等本地推送产物
#   4. 部署前把当前镜像打 :prev 标签，健康检查失败时秒级回滚

set -uo pipefail

APP_DIR=/opt/enterprise-ai
DEPLOY_DIR="$APP_DIR/deploy"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.app.yml"
HTML_DIR="$DEPLOY_DIR/html"
BRANCH=main
LOG=/var/log/ea-deploy.log
LOCK=/var/lock/ea-deploy.lock
HEALTH_URL=http://127.0.0.1/api/v1/health

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

log() { printf '%s  %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

mkdir -p "$(dirname "$LOG")" && touch "$LOG"

exec 9>"$LOCK"
if ! flock -n 9; then
  log "上一次部署还在进行，跳过本轮"
  exit 0
fi

cd "$APP_DIR" || { log "目录不存在: $APP_DIR"; exit 1; }

if ! git fetch origin "$BRANCH" -q 2>>"$LOG"; then
  log "git fetch 失败（网络或凭据问题），跳过"
  exit 1
fi

OLD=$(git rev-parse HEAD)
NEW=$(git rev-parse "origin/$BRANCH")

if [ "$OLD" = "$NEW" ]; then
  exit 0
fi

log "=== 检测到新提交: ${OLD:0:7} -> ${NEW:0:7} ==="
git log --oneline "$OLD..$NEW" | head -20 >>"$LOG"

CHANGED=$(git diff --name-only "$OLD" "$NEW")
NEED_BACKEND=0
FRONTEND_CHANGED=0
DEPLOY_CHANGED=0
echo "$CHANGED" | grep -q '^backend/' && NEED_BACKEND=1
echo "$CHANGED" | grep -q '^backend/Dockerfile' && NEED_BACKEND=1
echo "$CHANGED" | grep -q '^frontend/' && FRONTEND_CHANGED=1
echo "$CHANGED" | grep -q '^deploy/' && DEPLOY_CHANGED=1

log "变动文件数: $(echo "$CHANGED" | wc -l)，backend=$NEED_BACKEND frontend=$FRONTEND_CHANGED deploy=$DEPLOY_CHANGED"

# deploy/html 是 nginx 的根目录（bind mount）。为空时先从现有镜像兜底导出，
# 避免刚切到挂载目录时站点 404。
ensure_html() {
  mkdir -p "$HTML_DIR"
  if [ ! -f "$HTML_DIR/index.html" ]; then
    log "deploy/html 为空，从现有前端镜像兜底导出一次"
    local cid
    cid=$(docker create enterprise-ai-frontend:latest 2>/dev/null) || return 0
    docker cp "$cid:/usr/share/nginx/html/." "$HTML_DIR/" >>"$LOG" 2>&1 || true
    docker rm -f "$cid" >/dev/null 2>&1 || true
  fi
}

ensure_html

if [ "$NEED_BACKEND" = 0 ] && [ "$DEPLOY_CHANGED" = 0 ]; then
  git reset --hard "$NEW" -q
  if [ "$FRONTEND_CHANGED" = 1 ]; then
    log "只有前端改动：请在本地执行 deploy/deploy_frontend.py 构建并上传，服务器跳过重建"
  fi
  log "无需重建，代码同步到 ${NEW:0:7}"
  exit 0
fi

# 备份当前镜像，供失败回滚使用
docker tag enterprise-ai-backend:latest  enterprise-ai-backend:prev  2>/dev/null || true
docker tag enterprise-ai-frontend:latest enterprise-ai-frontend:prev 2>/dev/null || true

if ! git reset --hard "$NEW" -q; then
  log "git reset 失败，终止"
  exit 1
fi

if [ "$NEED_BACKEND" = 1 ]; then
  log "开始构建后端"
  if ! compose build backend >>"$LOG" 2>&1; then
    log "!!! 构建失败，代码回退到 ${OLD:0:7}，线上保持旧版本"
    git reset --hard "$OLD" -q
    exit 1
  fi
  log "构建完成"
fi

log "启动容器"
if compose up -d >>"$LOG" 2>&1; then
  for _ in $(seq 1 20); do
    sleep 3
    if curl -fsS -m 5 "$HEALTH_URL" >/dev/null 2>&1; then
      log "部署成功，当前版本 ${NEW:0:7}"
      exit 0
    fi
  done
fi

log "!!! 健康检查失败，开始回滚到 ${OLD:0:7}"
git reset --hard "$OLD" -q
docker tag enterprise-ai-backend:prev  enterprise-ai-backend:latest  2>/dev/null || true
docker tag enterprise-ai-frontend:prev enterprise-ai-frontend:latest 2>/dev/null || true
compose up -d >>"$LOG" 2>&1
log "已回滚，线上恢复为 ${OLD:0:7}（前端产物需本地重新上传）"
exit 1
