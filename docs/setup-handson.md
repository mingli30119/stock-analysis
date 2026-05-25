# 手把手：腾讯轻量 + GitHub Actions 自动部署

按顺序做，**不要跳步**。预计 20–40 分钟（不含买服务器）。

---

## 第 0 步：准备清单

- [ ] 腾讯云账号
- [ ] GitHub 仓库：`piwang1994/stock-analysis`（你有推送权限）
- [ ] 本机已安装终端（Windows 用 PowerShell / Git Bash 均可）

记下后面要填的空白（可复制到记事本）：

```
公网 IP：________________
SSH 用户：ubuntu（Ubuntu 镜像默认）
项目目录：/opt/stock-analysis
```

---

## 第 1 步：购买轻量服务器

1. 打开 https://cloud.tencent.com/product/lighthouse
2. **立即选购**
3. 建议：
   - 地域：**上海 / 广州** 等大陆节点
   - 镜像：**Ubuntu 22.04 LTS**
   - 套餐：**2核2G** 起
4. 购买后记下 **公网 IP**，填入上面空白

### 放行防火墙

1. 控制台 → **轻量应用服务器** → 点进你的实例
2. 左侧 **防火墙** → **添加规则**
3. 添加：

| 协议 | 端口 | 策略 |
|------|------|------|
| TCP | 22 | 允许 |
| TCP | 80 | 允许 |
| TCP | 443 | 允许（可选） |

---

## 第 2 步：SSH 登录服务器

本机终端执行（把 IP 换成你的）：

```bash
ssh ubuntu@你的公网IP
```

第一次会问 `yes/no`，输入 `yes`。

- 若提示 Permission denied：在腾讯云控制台 **重置密码**，或用控制台 **登录**（Web SSH）

登录成功后提示符类似：`ubuntu@VM-xxx:~$`

---

## 第 3 步：服务器首次安装（只做一次）

在 **服务器** 上依次执行：

```bash
sudo apt update
sudo apt install -y git
```

```bash
sudo mkdir -p /opt
sudo chown ubuntu:ubuntu /opt
cd /opt
git clone https://github.com/piwang1994/stock-analysis.git
cd stock-analysis
```

```bash
sudo bash deploy/install.sh
```

看到 `✅ 部署完成` 后，浏览器打开：

```
http://你的公网IP/
```

能看到首页即成功。

---

## 第 4 步：配置自动部署用的 sudo（服务器）

仍在 **服务器** 上执行：

```bash
sudo tee /etc/sudoers.d/stock-analysis-deploy <<'EOF'
ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart stock-analysis, /bin/systemctl reload stock-analysis, /bin/systemctl daemon-reload, /bin/systemctl enable stock-analysis, /usr/sbin/nginx, /bin/cp
EOF
sudo chmod 440 /etc/sudoers.d/stock-analysis-deploy
```

验证（应 **不** 再问密码）：

```bash
sudo systemctl status stock-analysis
```

---

## 第 5 步：本机生成部署密钥

在 **你自己的电脑**（不是服务器）执行：

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/lighthouse_deploy -N ""
```

会生成两个文件：

- `~/.ssh/lighthouse_deploy` → **私钥**（给 GitHub）
- `~/.ssh/lighthouse_deploy.pub` → **公钥**（给服务器）

把公钥加到服务器：

```bash
ssh-copy-id -i ~/.ssh/lighthouse_deploy.pub ubuntu@你的公网IP
```

测试免密登录：

```bash
ssh -i ~/.ssh/lighthouse_deploy ubuntu@你的公网IP
```

能直接登录即 OK，输入 `exit` 退出。

---

## 第 6 步：GitHub 配置 Secrets

1. 浏览器打开：  
   https://github.com/piwang1994/stock-analysis/settings/secrets/actions
2. 点 **New repository secret**，逐个添加：

### Secret 1：`DEPLOY_HOST`

- Name: `DEPLOY_HOST`
- Value: 你的公网 IP（或域名），例如 `123.45.67.89`

### Secret 2：`DEPLOY_USER`

- Name: `DEPLOY_USER`
- Value: `ubuntu`

### Secret 3：`DEPLOY_SSH_KEY`

- Name: `DEPLOY_SSH_KEY`
- Value: **私钥全文**

本机查看私钥并复制（Mac/Linux）：

```bash
cat ~/.ssh/lighthouse_deploy
```

从 `-----BEGIN OPENSSH PRIVATE KEY-----` 到 `-----END OPENSSH PRIVATE KEY-----` **全部复制**，粘贴到 Secret Value。

> Windows PowerShell：`Get-Content $env:USERPROFILE\.ssh\lighthouse_deploy`

### 可选 Secret

| Name | Value |
|------|--------|
| `DEPLOY_PORT` | `22` |
| `DEPLOY_PATH` | `/opt/stock-analysis` |

### 可选 Variable（非敏感）

https://github.com/piwang1994/stock-analysis/settings/variables/actions

- Name: `DEPLOY_URL`
- Value: `http://你的公网IP`

用于部署后自动访问 `/health` 检查。

---

## 第 7 步：触发第一次自动部署

### 方式 A：手动触发（推荐先测）

1. 打开 https://github.com/piwang1994/stock-analysis/actions
2. 左侧选 **Deploy to Lighthouse**
3. 右侧 **Run workflow** → Branch 选 `main` → **Run workflow**
4. 点进正在运行的任务，看日志

成功标志：最后一步绿色，服务器上版本已更新。

### 方式 B：推代码触发

以后任意推送到 `main` 都会自动部署：

```bash
git commit --allow-empty -m "chore: trigger deploy"
git push origin main
```

---

## 第 8 步：验收

1. **GitHub Actions** 全部绿色 ✓
2. 浏览器 `http://公网IP/` 正常
3. 服务器上：

```bash
ssh -i ~/.ssh/lighthouse_deploy ubuntu@你的公网IP
curl http://127.0.0.1:8000/health
# 应输出 {"status":"ok"}
sudo journalctl -u stock-analysis -n 20 --no-pager
```

---

## 常见失败对照

| 现象 | 原因 | 处理 |
|------|------|------|
| `缺少 DEPLOY_HOST` | Secret 未配 | 完成第 6 步 |
| `ssh: handshake failed` | IP/端口错或防火墙未开 22 | 检查 IP、防火墙 |
| `Permission denied (publickey)` | 公钥未加到服务器 | 重做第 5 步 ssh-copy-id |
| `sudo: a password is required` | 第 4 步 sudoers 未配 | 重做第 4 步 |
| `bash: deploy/remote-update.sh: No such file` | 未 clone 或路径错 | 检查 `DEPLOY_PATH`，重做第 3 步 |
| `git pull` 失败 | 服务器目录不是 git 仓库 | 重做第 3 步 clone |

---

## 完成后日常用法

- 改代码 → 合并到 `main` → 自动部署，无需再登录服务器
- 要看日志：服务器执行 `sudo journalctl -u stock-analysis -f`
- 要临时重启：`sudo systemctl restart stock-analysis`
