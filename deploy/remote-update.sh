#!/usr/bin/env bash
# 服务器端更新脚本（由 GitHub Actions SSH 调用，也可手动执行）
# 用法: bash deploy/remote-update.sh
# 环境变量: APP_DIR 默认 /opt/stock-analysis, DEPLOY_BRANCH 默认 main
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/stock-analysis}"
BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

echo "==> 拉取代码 ($BRANCH)"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

echo "==> 更新 Python 依赖"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

mkdir -p output/web_cache

echo "==> 同步 Nginx 配置"
sudo cp deploy/nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis
sudo nginx -t
sudo systemctl reload nginx

echo "==> 重启应用"
sudo cp deploy/stock-analysis.service /etc/systemd/system/stock-analysis.service
# 确保路径与用户正确（首次 install.sh 已 sed，此处再覆盖模板时需替换）
APP_USER="$(stat -c '%U' "$APP_DIR")"
sudo sed -i "s|/opt/stock-analysis|$APP_DIR|g; s|User=ubuntu|User=$APP_USER|g" \
  /etc/systemd/system/stock-analysis.service
sudo systemctl daemon-reload
sudo systemctl restart stock-analysis

sleep 2
curl -sf http://127.0.0.1:8000/health >/dev/null
echo "✅ 部署成功: $(date -Iseconds)"
