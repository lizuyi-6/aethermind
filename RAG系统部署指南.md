# RAG系统配置和部署指南

## 概述

RAG（Retrieval-Augmented Generation，检索增强生成）系统可以显著降低AI幻觉率，提升回答准确性。系统支持：
- 多种向量数据库（Qdrant/Milvus）
- 多种嵌入模型（OpenAI/通义千问/本地模型）
- 混合检索策略（向量+关键词）
- 多数据源（文档、网页、对话历史）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建`.env`文件或设置环境变量：

```bash
# 向量数据库选择（qdrant/milvus/chroma）
VECTOR_DB_TYPE=qdrant

# Qdrant配置（推荐用于生产）
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # 云服务需要，本地可省略
QDRANT_COLLECTION=knowledge_base

# 或使用Milvus
# MILVUS_HOST=localhost
# MILVUS_PORT=19530
# MILVUS_USER=root
# MILVUS_PASSWORD=

# 嵌入模型选择
EMBEDDING_MODEL=openai-3-small  # openai-ada, openai-3-large, tongyi-embedding, bge-m3等

# OpenAI嵌入API
EMBEDDING_API_KEY=your-api-key-here
EMBEDDING_API_BASE=  # 可选，自定义API端点

# 或通义千问嵌入
# DASHSCOPE_API_KEY=your-key

# 检索配置
RAG_TOP_K=5  # 返回前5个相关文档
RAG_SCORE_THRESHOLD=0.7  # 相似度阈值
RAG_USE_RERANK=true  # 是否重排序
RAG_RERANK_TOP_K=3  # 重排序后返回数量

# 文档分块配置
CHUNK_SIZE=500  # 文档块大小（字符数）
CHUNK_OVERLAP=50  # 块重叠大小

# 知识库存储路径
KNOWLEDGE_BASE_DIR=./knowledge_base
```

### 3. 启动向量数据库

#### 方案A: 使用Qdrant（推荐）

**Docker方式（最简单）：**
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

**本地安装：**
```bash
# 从GitHub下载
wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-linux-x86_64.tar.gz
tar -xzf qdrant-linux-x86_64.tar.gz
./qdrant

# 或使用cargo
cargo install qdrant-server
qdrant
```

**云服务：**
访问 https://cloud.qdrant.io/ 注册并获取API密钥

#### 方案B: 使用Milvus

```bash
# Docker Compose方式
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

### 4. 启动应用

```bash
python app.py
```

访问 RAG管理页面: http://localhost:5001/rag

## 使用指南

### 1. 添加文档

#### 通过Web界面
访问 http://localhost:5001/rag，点击"添加文档"标签

#### 通过API
```python
import requests

# 添加单个文档
response = requests.post('http://localhost:5001/api/rag/add', json={
    'documents': [{
        'title': '政策文件示例',
        'content': '文档内容...',
        'source': 'https://example.com/policy'
    }],
    'category': 'policy'
})

# 从URL添加网页
response = requests.post('http://localhost:5001/api/rag/add/url', json={
    'url': 'https://www.gov.cn/policy.html',
    'category': 'policy'
})

# 批量添加目录
response = requests.post('http://localhost:5001/api/rag/add/directory', json={
    'directory': './documents',
    'category': 'report',
    'extensions': ['.md', '.pdf', '.txt']
})
```

#### 通过代码
```python
from rag_config import RAGConfig
from rag_knowledge_base import KnowledgeBase

# 初始化
config = RAGConfig()
kb = KnowledgeBase(config)

# 添加文档
documents = [{
    'title': '文档标题',
    'content': '文档内容',
    'source': '来源'
}]
doc_ids = kb.add_documents(documents, category='general')

# 从文件添加
kb.add_file('report.pdf', category='report')

# 批量添加目录
kb.add_directory('./reports', category='report', extensions=['.md', '.pdf'])
```

### 2. 检索测试

访问管理页面的"检索测试"标签，输入查询并选择策略：
- **混合检索**（推荐）：结合向量和关键词检索
- **向量检索**：纯语义相似度检索
- **关键词检索**：基于关键词匹配

### 3. 对话中使用RAG

RAG系统已自动集成到智能体中，无需额外配置。当用户提问时：
1. 系统自动检索相关文档
2. 将检索结果添加到上下文
3. LLM基于检索内容回答

**示例对话：**
```
用户: 什么是新能源补贴政策？
系统: [自动检索相关政策文件]
AI: 根据最新政策文件，新能源补贴政策包括...
```

### 4. 管理知识库

- **查看统计**：访问统计标签页查看文档数量、维度等信息
- **清空知识库**：管理标签页 → 清空知识库（谨慎操作）
- **导出知识库**：管理标签页 → 导出（备份到JSON文件）

## 配置选项详解

### 向量数据库选择

| 数据库 | 优点 | 缺点 | 推荐场景 |
|--------|------|------|----------|
| Qdrant | 轻量、易部署、高性能 | 社区相对较小 | 中小规模、快速验证 |
| Milvus | 功能强大、可扩展 | 配置复杂 | 大规模生产环境 |
| Chroma | 本地存储、零配置 | 性能较低 | 开发测试 |

### 嵌入模型选择

| 模型 | 维度 | 优点 | 缺点 | 成本 |
|------|------|------|------|------|
| text-embedding-3-small | 1536 | 速度快、成本低 | 中文效果一般 | $ |
| text-embedding-3-large | 3072 | 效果最好 | 成本较高 | $$$ |
| bge-m3 | 1024 | 多语言、开源 | 需要本地部署 | 免费 |
| tongyi-embedding | 1024 | 中文优化 | 需要阿里云 | ¥ |

**推荐配置：**
- 开发/测试：`openai-3-small` + Qdrant
- 生产环境（中文）：`tongyi-embedding` + Qdrant
- 本地部署：`bge-m3` + Qdrant

### 检索参数调优

**RAG_TOP_K**：返回文档数量
- 默认: 5
- 推荐: 3-10
- 过大：上下文过长，影响响应速度
- 过小：可能遗漏相关信息

**RAG_SCORE_THRESHOLD**：相似度阈值
- 默认: 0.7
- 推荐: 0.6-0.8
- 过高：可能检索不到结果
- 过低：返回不相关文档

**RAG_USE_RERANK**：是否重排序
- 默认: true
- 关闭可提高速度，但准确性略降

**CHUNK_SIZE**：文档块大小
- 默认: 500字符
- 推荐: 300-800
- 过大：检索粒度太粗
- 过小：文档碎片化严重

## 常见问题

### 1. RAG系统初始化失败

**错误信息：** `RAG系统初始化失败`

**解决方法：**
```bash
# 检查向量数据库是否运行
curl http://localhost:6333  # Qdrant
curl http://localhost:19530  # Milvus

# 检查API密钥
echo $EMBEDDING_API_KEY

# 查看详细日志
python app.py 2>&1 | grep -i rag
```

### 2. 检索结果不准确

**可能原因和解决方法：**
1. **文档分块太大**：降低`CHUNK_SIZE`
2. **相似度阈值太高**：降低`RAG_SCORE_THRESHOLD`
3. **嵌入模型不匹配**：切换到中文优化模型（如tongyi-embedding）
4. **文档太少**：添加更多相关文档到知识库

### 3. 性能优化

**向量化速度慢：**
```bash
# 使用本地模型
EMBEDDING_MODEL=bge-m3
# 启用GPU
USE_CUDA=true
```

**检索速度慢：**
```bash
# 减少返回数量
RAG_TOP_K=3
# 关闭重排序
RAG_USE_RERANK=false
```

### 4. 部署到服务器

**systemd服务配置：**

创建`/etc/systemd/system/rag-app.service`:
```ini
[Unit]
Description=RAG Flask Application
After=network.target qdrant.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/test_2
Environment="VECTOR_DB_TYPE=qdrant"
Environment="QDRANT_HOST=localhost"
Environment="EMBEDDING_MODEL=openai-3-small"
Environment="EMBEDDING_API_KEY=your-key"
ExecStart=/usr/local/python3.11/bin/python3 app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-app
sudo systemctl start rag-app
sudo systemctl status rag-app
```

## 最佳实践

### 1. 数据准备

- **文档格式**：使用结构化格式（Markdown、PDF）
- **文档质量**：确保文档准确、权威、最新
- **分类管理**：按类别组织文档（政策、报告、对话等）

### 2. 知识库构建

- **增量添加**：逐步添加文档，避免一次性导入过多
- **定期更新**：定期更新过期内容
- **版本控制**：导出备份，方便回滚

### 3. 检索优化

- **混合策略**：优先使用混合检索
- **分类过滤**：根据问题类型选择对应分类
- **参数调优**：根据实际效果调整参数

### 4. 监控维护

- **定期检查统计**：查看文档数量、状态
- **测试检索效果**：定期用已知问题测试
- **查看日志**：关注RAG相关日志

## 示例代码

### 完整的RAG集成示例

```python
from rag_config import RAGConfig
from rag_knowledge_base import KnowledgeBase
from rag_retriever import RAGAugmenter
from agent import IntelligentAgent
from config import Config

# 初始化配置
config = Config()
rag_config = RAGConfig()

# 初始化知识库
kb = KnowledgeBase(rag_config)

# 添加文档
documents = [{
    'title': '新能源产业政策',
    'content': '新能源产业政策包括...',
    'source': 'gov.cn'
}]
kb.add_documents(documents, category='policy')

# 创建带RAG的智能体
agent = IntelligentAgent(config, enable_rag=True)

# 对话（自动使用RAG）
response, usage = agent.chat("新能源有哪些补贴政策？")

print(response)
# 系统会自动检索相关文档并基于检索内容回答
```

## 更新日志

- **v1.0** (2025-01-XX)
  - 支持Qdrant/Milvus向量数据库
  - 支持OpenAI/通义千问/本地嵌入模型
  - 实现混合检索策略
  - Web管理界面
  - API接口

## 技术支持

如有问题，请查看：
- 日志文件：`app_5001.log`
- RAG配置：`.env`文件或环境变量
- 向量数据库状态：http://localhost:6333/dashboard (Qdrant)
