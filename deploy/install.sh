#!/usr/bin/env bash
# 腾讯轻量 / Ubuntu 22.04 一键安装
# 用法: sudo bash deploy/install.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_USER="${SUDO_USER:-$USER}"
SERVICE_NAME="stock-analysis"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请使用 root 执行: sudo bash deploy/install.sh"
  exit 1
fi

echo "==> 安装系统包"
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx git

echo "==> Python 虚拟环境与依赖"
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv .venv
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip -q
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r requirements.txt -q

echo "==> 创建输出目录"
sudo -u "$APP_USER" mkdir -p "$APP_DIR/output/web_cache"

echo "==> 安装 systemd 服务"
sed "s|/opt/stock-analysis|$APP_DIR|g; s|User=ubuntu|User=$APP_USER|g" \
  "$APP_DIR/deploy/stock-analysis.service" > "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "==> 配置 Nginx"
cp "$APP_DIR/deploy/nginx-stock-analysis.conf" /etc/nginx/sites-available/stock-analysis
ln -sf /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/stock-analysis
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo ""
echo "✅ 部署完成"
echo "   访问: http://$(curl -s --max-time 2 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')/"
echo "   状态: systemctl status $SERVICE_NAME"
echo "   日志: journalctl -u $SERVICE_NAME -f"
