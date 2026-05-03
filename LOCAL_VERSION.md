# 本地版本说明

> 本地开发版本，已配置MCP搜索

---

## 与GitHub版本的区别

| 特性 | GitHub版本 | 本地版本 |
|------|-----------|---------|
| 核心功能 | ✅ 完整 | ✅ 完整 |
| Web搜索 | ⚠️ 需手动配置 | ✅ 已配置 |
| MCP服务器 | ❌ 需自行安装 | ✅ 已安装 |
| 环境变量 | ❌ 需手动设置 | ✅ 已设置 |
| 知识库 | 📦 基础版 | 📦 完整版 |

---

## 本地版本优势

1. **开箱即用** - MCP搜索已配置好
2. **完整知识库** - 包含行业数据、政策信息
3. **调试友好** - 详细的日志输出
4. **快速迭代** - 无需重新配置

---

## 使用方法

```bash
# 直接运行
python main.py 600737

# 批量分析
python main.py --batch 600737 000858 600519
```

---

## 配置文件

本地版本使用 `config.local.yaml`（不会上传到GitHub）：

```yaml
# 本地配置
data:
  cache_dir: "./cache"
  cache_ttl: 3600

# MCP搜索（已配置）
mcp:
  zhipu_api_key: "${ZHIPU_API_KEY}"
  tavily_api_key: "${TAVILY_API_KEY}"

# 调试模式
debug:
  enabled: true
  log_level: "DEBUG"
```

---

## 环境变量

本地版本的环境变量已在 `.env` 文件中配置（不会上传到GitHub）：

```bash
# .env
ZHIPU_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
HTTP_PROXY=http://127.0.0.1:7890
```

---

## 目录结构

```
本地版本/
├── .env                    # 环境变量（不上传）
├── config.local.yaml       # 本地配置（不上传）
├── knowledge_base/         # 完整知识库（不上传）
│   ├── industries/         # 行业数据
│   ├── policies/           # 政策信息
│   └── companies/          # 公司数据
└── ... (其他文件同GitHub版本)
```

---

## 同步到GitHub

如果要将本地改动同步到GitHub版本：

```bash
# 1. 确保敏感信息不会上传
git status

# 2. .gitignore已配置忽略
# .env
# config.local.yaml
# knowledge_base/

# 3. 提交代码
git add .
git commit -m "feat: 新功能"
git push
```

---

## 注意事项

1. **不要上传API Key** - 已在.gitignore中配置
2. **不要上传知识库** - 可能包含敏感信息
3. **不要上传缓存** - cache/目录已忽略

---

**本地版本专为开发和测试优化，享受更流畅的体验！**
