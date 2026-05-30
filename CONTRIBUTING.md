# 贡献指南

感谢你对本项目的关注！

## 如何贡献

### 报告Bug

在 [Issues](https://github.com/mingli30119/stock-analysis/issues) 中提交，请包含：
- 问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息（Python版本、操作系统）

### 提交功能建议

在 [Issues](https://github.com/mingli30119/stock-analysis/issues) 中提交，请说明：
- 功能描述
- 使用场景
- 预期效果

### 提交代码

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

### 代码规范

- 遵循PEP 8
- 添加必要的注释
- 更新相关文档
- 添加测试用例

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/mingli30119/stock-analysis.git
cd stock-analysis

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/
```

## 提交规范

- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例：
```
feat: 添加自动对标分析功能
fix: 修复K线数据获取失败的问题
docs: 更新使用指南
```

## 行为准则

- 尊重他人
- 建设性反馈
- 专注于问题本身
- 保持友好和专业
