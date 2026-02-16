"""
RAG配置文件
管理向量数据库和嵌入模型的配置
"""

import os
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class VectorDBType(Enum):
    """支持的向量数据库类型"""
    QDRANT = "qdrant"
    MILVUS = "milvus"
    CHROMA = "chroma"  # 本地开发用


class EmbeddingModel(Enum):
    """支持的嵌入模型"""
    # OpenAI兼容API
    OPENAI_ADA = "openai-ada"  # text-embedding-ada-002
    OPENAI_3_SMALL = "openai-3-small"  # text-embedding-3-small
    OPENAI_3_LARGE = "openai-3-large"  # text-embedding-3-large

    # 本地模型（需要额外部署）
    BGE_M3 = "bge-m3"  # BAAI/bge-m3 (多语言)
    BGE_LARGE_ZH = "bge-large-zh"  # BAAI/bge-large-zh-v1.5
    M3E_BASE = "m3e-base"  # m3e-base

    # 通义千问
    TONGYI_EMBEDDING = "tongyi-embedding"


class RAGConfig:
    """RAG系统配置类"""

    def __init__(self):
        """从环境变量初始化配置"""

        # 向量数据库类型
        db_type = os.getenv('VECTOR_DB_TYPE', 'qdrant').lower()
        try:
            self.vector_db_type = VectorDBType(db_type)
        except ValueError:
            print(f"警告: 未知的向量数据库类型 '{db_type}'，使用默认值 'qdrant'")
            self.vector_db_type = VectorDBType.QDRANT

        # 嵌入模型类型
        embedding_model = os.getenv('EMBEDDING_MODEL', 'openai-3-small').lower()
        try:
            self.embedding_model = EmbeddingModel(embedding_model)
        except ValueError:
            print(f"警告: 未知的嵌入模型 '{embedding_model}'，使用默认值 'openai-3-small'")
            self.embedding_model = EmbeddingModel.OPENAI_3_SMALL

        # Qdrant配置
        self.qdrant_host = os.getenv('QDRANT_HOST', 'localhost')
        self.qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
        self.qdrant_api_key = os.getenv('QDRANT_API_KEY', None)  # 云服务需要
        self.qdrant_collection = os.getenv('QDRANT_COLLECTION', 'knowledge_base')

        # Milvus配置
        self.milvus_host = os.getenv('MILVUS_HOST', 'localhost')
        self.milvus_port = int(os.getenv('MILVUS_PORT', '19530'))
        self.milvus_user = os.getenv('MILVUS_USER', 'root')
        self.milvus_password = os.getenv('MILVUS_PASSWORD', '')
        self.milvus_collection = os.getenv('MILVUS_COLLECTION', 'knowledge_base')

        # Chroma配置（本地开发）
        self.chroma_persist_dir = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')

        # 嵌入模型配置
        self.embedding_api_key = os.getenv('EMBEDDING_API_KEY', '')
        self.embedding_api_base = os.getenv('EMBEDDING_API_BASE', '')
        self.embedding_dimension = int(os.getenv('EMBEDDING_DIMENSION', '1536'))  # 默认ada-002维度

        # 根据模型设置维度
        self._set_embedding_dimension()

        # 检索配置
        self.top_k = int(os.getenv('RAG_TOP_K', '5'))  # 返回前K个相关文档
        self.score_threshold = float(os.getenv('RAG_SCORE_THRESHOLD', '0.7'))  # 相似度阈值
        self.use_rerank = os.getenv('RAG_USE_RERANK', 'true').lower() == 'true'  # 是否重排序
        self.rerank_top_k = int(os.getenv('RAG_RERANK_TOP_K', '3'))  # 重排序后返回数量

        # 文档分块配置
        self.chunk_size = int(os.getenv('CHUNK_SIZE', '500'))  # 字符数
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '50'))  # 重叠字符数

        # 知识库存储路径
        self.knowledge_base_dir = os.getenv('KNOWLEDGE_BASE_DIR', './knowledge_base')
        self.web_cache_dir = os.path.join(self.knowledge_base_dir, 'web_cache')

        # 爬虫配置
        self.web_scrape_timeout = int(os.getenv('WEB_SCRAPE_TIMEOUT', '30'))
        self.max_pages_per_site = int(os.getenv('MAX_PAGES_PER_SITE', '100'))

        # 对话历史存储（作为知识库）
        self.save对话_to_kb = os.getenv('SAVE_DIALOG_TO_KB', 'false').lower() == 'true'
        self.dialog_min_length = int(os.getenv('DIALOG_MIN_LENGTH', '100'))  # 对话最短长度

        # 验证配置
        self._validate_config()

        # 创建必要的目录
        self._ensure_directories()

    def _set_embedding_dimension(self):
        """根据嵌入模型设置向量维度"""
        dimension_map = {
            EmbeddingModel.OPENAI_ADA: 1536,
            EmbeddingModel.OPENAI_3_SMALL: 1536,
            EmbeddingModel.OPENAI_3_LARGE: 3072,
            EmbeddingModel.BGE_M3: 1024,
            EmbeddingModel.BGE_LARGE_ZH: 1024,
            EmbeddingModel.M3E_BASE: 768,
            EmbeddingModel.TONGYI_EMBEDDING: 1024,
        }

        if self.embedding_model in dimension_map:
            self.embedding_dimension = dimension_map[self.embedding_model]

    def _validate_config(self):
        """验证配置"""
        if not self.embedding_api_key and self.embedding_model.value.startswith('openai'):
            print("警告: OpenAI嵌入模型需要设置EMBEDDING_API_KEY")

        if self.vector_db_type == VectorDBType.QDRANT:
            print(f"[RAG配置] 使用Qdrant: {self.qdrant_host}:{self.qdrant_port}")
        elif self.vector_db_type == VectorDBType.MILVUS:
            print(f"[RAG配置] 使用Milvus: {self.milvus_host}:{self.milvus_port}")
        else:
            print(f"[RAG配置] 使用Chroma本地存储: {self.chroma_persist_dir}")

        print(f"[RAG配置] 嵌入模型: {self.embedding_model.value}, 维度: {self.embedding_dimension}")
        print(f"[RAG配置] 检索配置: top_k={self.top_k}, 阈值={self.score_threshold}")

    def _ensure_directories(self):
        """确保必要的目录存在"""
        import os
        dirs = [
            self.knowledge_base_dir,
            self.web_cache_dir,
            os.path.join(self.knowledge_base_dir, 'documents'),
            os.path.join(self.knowledge_base_dir, 'reports'),
            os.path.join(self.knowledge_base_dir, 'dialogs'),
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)

    @property
    def embedding_model_name(self) -> str:
        """获取嵌入模型名称（用于API调用）"""
        model_name_map = {
            EmbeddingModel.OPENAI_ADA: "text-embedding-ada-002",
            EmbeddingModel.OPENAI_3_SMALL: "text-embedding-3-small",
            EmbeddingModel.OPENAI_3_LARGE: "text-embedding-3-large",
            EmbeddingModel.BGE_M3: "BAAI/bge-m3",
            EmbeddingModel.BGE_LARGE_ZH: "BAAI/bge-large-zh-v1.5",
            EmbeddingModel.M3E_BASE: "m3e-base",
            EmbeddingModel.TONGYI_EMBEDDING: "text-embedding-v3",
        }
        return model_name_map.get(self.embedding_model, "text-embedding-3-small")

    def __repr__(self):
        return (f"RAGConfig(db={self.vector_db_type.value}, "
                f"embedding={self.embedding_model.value}, "
                f"dimension={self.embedding_dimension})")
