#!/usr/bin/env python3
"""本地构建前端并增量发布到服务器。

用法（Windows PowerShell）：
    $env:ECS_PASS='服务器密码'
    python deploy/deploy_frontend.py

常用参数：
    --skip-build     直接上传 frontend/dist（不重新构建）
    --site URL       发布后校验的站点地址，默认 http://59.110.239.98

为什么要在本地构建：
    线上是 1 vCPU / 1 GiB 的轻量服务器，`vite build` 峰值要 700 MB 左右，
    在服务器上构建会把内存吃满、靠 2 GB swap 硬扛（负载飙到 8）。
    现在前端镜像不参与发布，nginx 通过 bind mount 直接读 deploy/html，
    所以发布只是「本地产物 → 上传 → 覆盖文件」，几秒钟完成，且不动后端。

流程：
    1. frontend/ 下 npm ci（缺 node_modules 时）+ npm run build
    2. 打包 dist 上传到服务器 /tmp
    3. 解包到 deploy/html：先落 hash 资源，再原子替换 index.html
    4. 清理 7 天前的旧 hash 资源，curl 校验首页
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import paramiko  # noqa: E402

HOST = os.environ.get("ECS_HOST", "59.110.239.98")
USER = os.environ.get("ECS_USER", "root")
PASS = os.environ.get("ECS_PASS", "")
HTML_DIR = "/opt/enterprise-ai/deploy/html"
REMOTE_TAR = "/tmp/fe-dist.tar.gz"

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"
DIST = FRONTEND / "dist"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass


def step(message: str) -> None:
    print(f"\n=== {message} ===", flush=True)


def run_local(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(args)}  (cwd={cwd})", flush=True)
    completed = subprocess.run(args, cwd=str(cwd), shell=(os.name == "nt"), env=env)
    if completed.returncode != 0:
        raise SystemExit(f"命令失败（exit {completed.returncode}）: {' '.join(args)}")


def build_env() -> dict[str, str]:
    """esbuild 会往 %TEMP% 写临时文件，在 Windows 上常被杀软/索引占用导致
    `remove ...: Access is denied`。固定到工程内的 .tmp 目录可绕开。"""
    env = os.environ.copy()
    tmp_dir = REPO_ROOT / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    env["TMP"] = str(tmp_dir)
    env["TEMP"] = str(tmp_dir)
    # 生产构建默认隐藏登录页演示账号；本地开发仍可读 frontend/.env
    env.setdefault("VITE_SHOW_DEMO_ACCOUNT", "false")
    return env


def build_frontend(skip_build: bool) -> str:
    if skip_build:
        if not (DIST / "index.html").is_file():
            raise SystemExit("--skip-build 需要 frontend/dist/index.html 已存在")
        return "跳过构建，直接使用现有 frontend/dist"

    if not (FRONTEND / "node_modules").is_dir():
        step("安装依赖（首次，约 1-2 分钟）")
        run_local(["npm", "ci", "--no-audit", "--no-fund"], FRONTEND, build_env())

    step("构建前端")
    started = time.time()
    run_local(["npm", "run", "build"], FRONTEND, build_env())
    return f"构建完成，用时 {time.time() - started:.1f}s"


def make_tarball() -> Path:
    if not (DIST / "index.html").is_file():
        raise SystemExit("frontend/dist 不存在或为空")
    archive = REPO_ROOT / ".tmp" / "fe-dist.tar.gz"
    archive.parent.mkdir(exist_ok=True)
    if archive.exists():
        archive.unlink()
    with tarfile.open(archive, "w:gz") as tar:
        for item in sorted(DIST.iterdir()):
            tar.add(item, arcname=item.name)
    size = archive.stat().st_size / 1024
    print(f"打包完成: {archive} ({size:.0f} KB)")
    return archive


def connect() -> paramiko.SSHClient:
    # 优先用免密钥（~/.ssh/ea_deploy），没有文件时退回密码
    key_path = os.environ.get("ECS_KEY") or Path.home() / ".ssh" / "ea_deploy"
    use_key = Path(key_path).is_file()
    if not use_key and not PASS:
        raise SystemExit("没有找到 ~/.ssh/ea_deploy，也没有设置 ECS_PASS")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        22,
        USER,
        password=PASS or None,
        key_filename=str(key_path) if use_key else None,
        timeout=25,
        banner_timeout=25,
        auth_timeout=25,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def run_remote(client: paramiko.SSHClient, script: str) -> str:
    _, stdout, stderr = client.exec_command(script, timeout=600)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if out.strip():
        print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    if code != 0:
        raise SystemExit(f"远端命令失败（exit {code}）")
    return out


DEPLOY_SCRIPT = """set -euo pipefail
TMP=$(mktemp -d /tmp/fe-dist.XXXXXX)
trap 'rm -rf "$TMP"' EXIT
tar -xzf {tar} -C "$TMP"

HTML={html}
mkdir -p "$HTML/assets"

# 带 hash 的资源互不覆盖，可以先铺；index.html 最后用 mv 原子替换
cp -a "$TMP/assets/." "$HTML/assets/"
for extra in favicon.svg 50x.html; do
  [ -f "$TMP/$extra" ] && cp -a "$TMP/$extra" "$HTML/"
done
cp -f "$TMP/index.html" "$HTML/index.html.new"
mv -f "$HTML/index.html.new" "$HTML/index.html"

# 清掉一周前的旧资源，避免每次发版堆积
find "$HTML/assets" -type f -mtime +7 -delete

echo "HTML_SIZE=$(du -sh "$HTML" | cut -f1)"
echo "INDEX_MD5=$(md5sum "$HTML/index.html" | cut -d' ' -f1)"
curl -s -o /dev/null -w "SITE_HTTP=%{{http_code}}\\n" http://127.0.0.1/
"""


def deploy(client: paramiko.SSHClient, archive: Path) -> str:
    step("上传产物")
    sftp = client.open_sftp()
    try:
        sftp.put(str(archive), REMOTE_TAR)
        print(f"已上传 -> {REMOTE_TAR} ({archive.stat().st_size / 1024:.0f} KB)")
    finally:
        sftp.close()

    step("服务器解包到 deploy/html")
    out = run_remote(client, DEPLOY_SCRIPT.format(tar=REMOTE_TAR, html=HTML_DIR))
    match = re.search(r"INDEX_MD5=(\w+)", out)
    return match.group(1) if match else ""


def verify(html_md5: str, site: str) -> None:
    step(f"校验 {site}")
    index_local = (DIST / "index.html").read_text(encoding="utf-8")
    bundle = re.search(r"assets/index-[A-Za-z0-9_-]+\.js", index_local)
    if not bundle:
        print("!! 本地 index.html 里没找到入口 bundle，跳过校验")
        return

    with urllib.request.urlopen(f"{site}/", timeout=20) as response:
        served = response.read().decode("utf-8", "replace")
    if bundle.group(0) not in served:
        raise SystemExit(f"校验失败：站点首页未引用 {bundle.group(0)}")
    print(f"OK 站点已引用新入口: {bundle.group(0)}")

    if html_md5:
        print(f"OK 服务器 index.html md5: {html_md5}")


def main() -> int:
    parser = argparse.ArgumentParser(description="本地构建并发布前端")
    parser.add_argument("--skip-build", action="store_true", help="跳过 npm build")
    parser.add_argument("--site", default=f"http://{HOST}", help="校验用的站点地址")
    args = parser.parse_args()

    print(build_frontend(args.skip_build))
    archive = make_tarball()

    client = connect()
    try:
        md5 = deploy(client, archive)
        verify(md5, args.site)
    finally:
        client.close()

    print("\n发布完成。浏览器用 Ctrl+F5 强刷一次即可看到新版本。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
