# 🤖 AetherMind - 智能体项目

> 一个本地智能体，能够对用户的自然语言做出回复，通过 API 调用大模型

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)

---

## ✨ 功能特性

- 🤖 **多模型支持** - OpenAI / 通义千问 / 自定义 API
- 💬 **交互式对话** - 命令行 + Web 界面双模式
- 📝 **对话历史** - 自动保存上下文
- 🌊 **流式输出** - 实时显示回复内容
- 📄 **文件上传** - 支持 PDF/Word/Excel 等格式分析
- 📱 **微信小程序** - 移动端支持

---

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

创建 `.env` 文件：

```bash
# OpenAI
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-3.5-turbo

# 通义千问
# MODEL_PROVIDER=tongyi
# DASHSCOPE_API_KEY=your-key
# MODEL_NAME=qwen-turbo
```

### 启动

**命令行模式**:
```bash
python agent.py
```

**Web 界面** (推荐):
```bash
python app.py
```
访问 http://localhost:5000

---

## 📁 项目结构

```
.
├── app.py                      # Flask Web 应用
├── agent.py                    # 命令行智能体
├── config.py                   # 配置文件
├── file_processor.py           # 文件处理模块
├── templates/                  # HTML 模板
├── static/                     # 静态资源
└── miniprogram/                # 微信小程序
```

---

## 🎯 使用场景

- 📊 **可行性研究报告生成** - 自动生成 50 万字详细报告
- 📄 **文档分析** - PDF/Word/Excel 内容提取与总结
- 💡 **智能问答** - 基于上下文的连续对话
- 🔍 **数据分析** - 表格数据趋势分析

---

## 📱 微信小程序

小程序代码位于 `miniprogram/` 目录，支持：
- ✅ 智能对话
- ✅ 流式输出
- ✅ 文件上传
- ✅ 对话历史管理

详见 [miniprogram/快速开始.md](miniprogram/快速开始.md)

---

## 🛠️ 扩展开发

### 添加新模型提供商

1. 在 `config.py` 添加枚举值
2. 在 `agent.py` 添加初始化逻辑

### 添加持久化存储

修改 `agent.py` 添加数据库支持

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 📫 联系方式

- **Author**: Abraham Li (李祖祎)
- **Email**: 2251213429@qq.com
- **Company**: 杭州视界奇点科技有限公司

---

<div align="center">

**🌱 成长不止，代码不息**

*Made with ❤️ by Abraham Li*

</div>
