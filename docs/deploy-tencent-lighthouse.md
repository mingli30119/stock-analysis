# 腾讯轻量应用服务器部署指南

本文说明如何将 **个股深度分析网页端** 部署到 [腾讯云轻量应用服务器](https://cloud.tencent.com/product/lighthouse)（Lighthouse），通过域名或公网 IP 访问。

---

## 一、服务器准备

### 1. 购买与规格建议

| 项目 | 建议 |
|------|------|
| 地域 | **中国大陆**（akshare 数据源在国内更稳定） |
| 镜像 | **Ubuntu 22.04 LTS** |
| 配置 | 最低 2核2G；频繁生成报告建议 **2核4G** |
| 带宽 | 3Mbps 起 |

### 2. 控制台放行端口

路径：**轻量服务器 → 你的实例 → 防火墙**

| 端口 | 用途 |
|------|------|
| 22 | SSH |
| 80 | HTTP（Nginx） |
| 443 | HTTPS（可选，配置证书后） |

> 应用本身监听 `127.0.0.1:8000`，**不要**把 8000 直接暴露公网，由 Nginx 反向代理。

### 3. SSH 登录

```bash
ssh ubuntu@你的公网IP
# 或使用控制台「登录」→ Web SSH
```

---

## 二、一键安装（推荐）

在服务器上执行（将仓库地址换成你的）：

```bash
sudo apt update && sudo apt install -y git
cd /opt
sudo git clone https://github.com/piwang1994/stock-analysis.git
cd stock-analysis
sudo bash deploy/install.sh
```

安装脚本会完成：

- 安装 Python3、venv、Nginx
- 创建虚拟环境并安装依赖
- 注册 systemd 服务 `stock-analysis`
- 配置 Nginx 反向代理到 `127.0.0.1:8000`

完成后浏览器访问：`http://你的公网IP/`

---

## 二点五、GitHub Actions 自动部署（推荐长期维护）

**首次**仍需在服务器执行上一节「一键安装」。之后每次合并到 `main`，Actions 会自动 SSH 更新代码并重启服务。

### 1. 服务器：配置免密 sudo（部署用户）

以 `ubuntu` 为例：

```bash
sudo tee /etc/sudoers.d/stock-analysis-deploy <<'EOF'
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart stock-analysis, /bin/systemctl reload stock-analysis, /bin/systemctl daemon-reload, /bin/systemctl enable stock-analysis, /usr/sbin/nginx, /bin/cp
EOF
sudo chmod 440 /etc/sudoers.d/stock-analysis-deploy
```

### 2. 本机：生成部署专用 SSH 密钥

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/lighthouse_deploy -N ""
```

把 **公钥** 写入服务器：

```bash
ssh-copy-id -i ~/.ssh/lighthouse_deploy.pub ubuntu@你的公网IP
```

### 3. GitHub 仓库配置 Secrets

路径：**仓库 → Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 内容 |
|-------------|------|
| `DEPLOY_HOST` | 公网 IP 或域名 |
| `DEPLOY_USER` | `ubuntu`（与服务器登录用户一致） |
| `DEPLOY_SSH_KEY` | `~/.ssh/lighthouse_deploy` **私钥** 全文 |
| `DEPLOY_PORT` | （可选）默认 22 |
| `DEPLOY_PATH` | （可选）默认 `/opt/stock-analysis` |

可选 **Variables**（非敏感）：

| Variable | 说明 |
|----------|------|
| `DEPLOY_URL` | 如 `http://你的公网IP`，用于部署后 curl `/health` |

### 4. 触发方式

- 推送到 **`main`** 分支自动部署（见 `.github/workflows/deploy.yml`）
- 或 **Actions → Deploy to Lighthouse → Run workflow** 手动触发

### 5. 流程说明

```
git push main → GitHub Actions → SSH 到轻量服务器 → deploy/remote-update.sh
  → git pull → pip install → reload nginx → restart stock-analysis → /health 检查
```

---

## 三、手动部署流程

### 步骤 1：系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### 步骤 2：拉取代码

```bash
sudo mkdir -p /opt
sudo chown $USER:$USER /opt
cd /opt
git clone https://github.com/piwang1994/stock-analysis.git
cd stock-analysis
```

### 步骤 3：Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 步骤 4：试运行

```bash
source .venv/bin/activate
uvicorn web.app:app --host 127.0.0.1 --port 8000
```

另开终端测试：

```bash
curl http://127.0.0.1:8000/health
# 应返回 {"status":"ok"}
```

Ctrl+C 停止后进入下一步。

### 步骤 5：systemd 常驻服务

```bash
sudo cp deploy/stock-analysis.service /etc/systemd/system/
sudo sed -i "s|/opt/stock-analysis|$(pwd)|g" /etc/systemd/system/stock-analysis.service
sudo systemctl daemon-reload
sudo systemctl enable stock-analysis
sudo systemctl start stock-analysis
sudo systemctl status stock-analysis
```

### 步骤 6：Nginx 反向代理

```bash
sudo cp deploy/nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis
sudo ln -sf /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 步骤 7：验证

- 本机：`curl -I http://127.0.0.1/`
- 浏览器：`http://公网IP/`

---

## 四、HTTPS（可选）

### 方式 A：腾讯云控制台免费证书

1. **SSL 证书** 控制台申请免费 DV 证书（绑定域名）
2. 下载 Nginx 格式证书，上传到服务器 `/etc/nginx/ssl/`
3. 修改 `deploy/nginx-stock-analysis.conf` 中 `listen 443 ssl` 段并 `reload nginx`

### 方式 B：Let's Encrypt（需已解析域名到服务器 IP）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 五、日常运维

```bash
# 查看应用日志
sudo journalctl -u stock-analysis -f

# 重启应用
sudo systemctl restart stock-analysis

# 更新代码
cd /opt/stock-analysis
git pull
source .venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart stock-analysis
```

| 目录 | 说明 |
|------|------|
| `/opt/stock-analysis/output/web_cache/` | HTML 报告缓存（1 小时） |
| `/opt/stock-analysis/output/` | JSON 等中间文件 |

---

## 六、常见问题

### 1. 生成报告很慢或超时

- akshare 需访问国内数据源，**勿**使用境外节点期望同等速度
- Nginx 默认代理超时较短，已在配置中设为 `proxy_read_timeout 600s`（10 分钟）
- 若仍超时，可改用「先访问一次生成缓存，再刷新查看」

### 2. `ModuleNotFoundError: pandas` / akshare

```bash
cd /opt/stock-analysis && source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart stock-analysis
```

### 3. 502 Bad Gateway

```bash
sudo systemctl status stock-analysis
curl http://127.0.0.1:8000/health
```

服务未启动则查 `journalctl -u stock-analysis -n 50`。

### 4. 防火墙已开 80 仍无法访问

- 确认腾讯云 **实例防火墙** 与 **轻量防火墙** 均已放行 80
- 本机 `sudo ufw status`，若 active 需 `sudo ufw allow 80`

---

## 七、安全建议

- 仅开放 22 / 80 / 443，不要公网暴露 8000
- SSH 建议改用密钥登录，关闭密码登录
- 定期 `apt upgrade` 与 `git pull` 更新依赖
- 本工具仅供研究，勿对外承诺投资建议

---

## 八、架构示意

```
用户浏览器
    ↓ :80 / :443
  Nginx (反向代理, 长超时)
    ↓ 127.0.0.1:8000
  uvicorn → FastAPI (web.app)
    ↓ 线程池
  akshare collect → render_html → 浏览器展示
```
