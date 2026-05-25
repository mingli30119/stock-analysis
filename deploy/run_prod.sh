#!/usr/bin/env bash
# 生产环境前台启动（调试用；正式部署请用 systemd）
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
exec uvicorn web.app:app --host 127.0.0.1 --port 8000 --workers 1
