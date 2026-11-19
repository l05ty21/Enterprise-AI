#!/usr/bin/env bash
# 自动部署脚本：检测远端分支 → 构建变动服务 → 重启 → 健康检查 → 失败回滚
#
# 手动执行：  /opt/enterprise-ai/deploy/deploy.sh
# 自动执行：  ea-deploy.timer（每 2 分钟一次）
# 日志：      /var/log/ea-deploy.log
#
# 设计要点：
#   1. flock 防并发——定时器可能在上一次部署还没结束时再次触发
#   2. 只重建路径有变动的服务，纯文档改动不会触发构建
#   3. 部署前把当前镜像打 :prev 标签，健康检查失败时秒级回滚
#   4. 构建在旧容器仍在运行时进行，构建失败不影响线上

set -uo pipefail

APP_DIR=/opt/enterprise-ai
DEPLOY_DIR="$APP_DIR/deploy"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.app.yml"
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
NEED_FRONTEND=0
echo "$CHANGED" | grep -q '^backend/' && NEED_BACKEND=1
echo "$CHANGED" | grep -q '^frontend/' && NEED_FRONTEND=1
if echo "$CHANGED" | grep -qE '^(deploy/|backend/Dockerfile|frontend/Dockerfile)'; then
  NEED_BACKEND=1
  NEED_FRONTEND=1
fi

log "变动文件数: $(echo "$CHANGED" | wc -l)，backend=$NEED_BACKEND frontend=$NEED_FRONTEND"

# 备份当前镜像，供失败回滚使用
docker tag enterprise-ai-backend:latest  enterprise-ai-backend:prev  2>/dev/null || true
docker tag enterprise-ai-frontend:latest enterprise-ai-frontend:prev 2>/dev/null || true

if ! git reset --hard "$NEW" -q; then
  log "git reset 失败，终止"
  exit 1
fi

TARGETS=""
[ "$NEED_BACKEND" = 1 ] && TARGETS="$TARGETS backend"
[ "$NEED_FRONTEND" = 1 ] && TARGETS="$TARGETS frontend"

if [ -n "$TARGETS" ]; then
  log "开始构建:$TARGETS"
  if ! compose build $TARGETS >>"$LOG" 2>&1; then
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
    if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
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
log "已回滚，线上恢复为 ${OLD:0:7}"
exit 1
