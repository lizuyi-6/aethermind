"""
文档向量化模块
支持多种嵌入模型
"""

import os
from typing import List, Union, Dict
from abc import ABC, abstractmethod
from rag_config import RAGConfig, EmbeddingModel


class EmbeddingModel(ABC):
    """嵌入模型抽象基类"""

    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        将文本编码为向量

        Args:
            texts: 单个文本或文本列表

        Returns:
            单个向量或向量列表
        """
        pass

    @abstractmethod
    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        批量编码（优化性能）

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            向量列表
        """
        pass


class OpenAIEmbedding(EmbeddingModel):
    """OpenAI兼容的嵌入模型"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            from openai import OpenAI

            self.client = OpenAI(
                api_key=self.config.embedding_api_key or os.getenv('OPENAI_API_KEY'),
                base_url=self.config.embedding_api_base,
                timeout=60,
                max_retries=2
            )

            print(f"[OpenAI嵌入] 初始化成功: {self.config.embedding_model_name}")
        except Exception as e:
            raise ConnectionError(f"初始化OpenAI嵌入客户端失败: {e}")

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本"""
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        try:
            # 调用API
            response = self.client.embeddings.create(
                model=self.config.embedding_model_name,
                input=texts
            )

            # 提取向量
            vectors = [item.embedding for item in response.data]

            return vectors[0] if is_single else vectors
        except Exception as e:
            raise Exception(f"OpenAI嵌入失败: {e}")

    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量编码"""
        all_vectors = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vectors = self.encode(batch)
            all_vectors.extend(vectors)

        return all_vectors


class TongyiEmbedding(EmbeddingModel):
    """通义千问嵌入模型"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化通义千问客户端"""
        try:
            from openai import OpenAI

            api_key = self.config.embedding_api_key or os.getenv('DASHSCOPE_API_KEY')
            base_url = self.config.embedding_api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"

            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=60
            )

            print(f"[通义千问嵌入] 初始化成功: {self.config.embedding_model_name}")
        except Exception as e:
            raise ConnectionError(f"初始化通义千问嵌入客户端失败: {e}")

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本"""
        is_single = isinstance(texts, str)
        if is_single:
            texts = [texts]

        try:
            response = self.client.embeddings.create(
                model=self.config.embedding_model_name,
                input=texts
            )

            vectors = [item.embedding for item in response.data]

            return vectors[0] if is_single else vectors
        except Exception as e:
            raise Exception(f"通义千问嵌入失败: {e}")

    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量编码"""
        all_vectors = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vectors = self.encode(batch)
            all_vectors.extend(vectors)

        return all_vectors


class LocalEmbedding(EmbeddingModel):
    """本地嵌入模型（使用SentenceTransformers）"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.model = None
        self._init_model()

    def _init_model(self):
        """初始化本地模型"""
        try:
            from sentence_transformers import SentenceTransformer

            # 加载模型
            device = 'cuda' if os.getenv('USE_CUDA', 'false').lower() == 'true' else 'cpu'
            self.model = SentenceTransformer(self.config.embedding_model_name, device=device)

            print(f"[本地嵌入] 初始化成功: {self.config.embedding_model_name} (设备: {device})")
        except ImportError:
            raise ImportError("需要安装sentence-transformers: pip install sentence-transformers")
        except Exception as e:
            raise ConnectionError(f"初始化本地嵌入模型失败: {e}")

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """编码文本"""
        try:
            return self.model.encode(texts, convert_to_numpy=True).tolist()
        except Exception as e:
            raise Exception(f"本地嵌入失败: {e}")

    def batch_encode(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量编码"""
        try:
            return self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            ).tolist()
        except Exception as e:
            raise Exception(f"批量嵌入失败: {e}")


def create_embedding_model(config: RAGConfig) -> EmbeddingModel:
    """工厂函数：根据配置创建嵌入模型"""
    model_type = config.embedding_model

    if model_type in [EmbeddingModel.OPENAI_ADA,
                      EmbeddingModel.OPENAI_3_SMALL,
                      EmbeddingModel.OPENAI_3_LARGE]:
        return OpenAIEmbedding(config)
    elif model_type == EmbeddingModel.TONGYI_EMBEDDING:
        return TongyiEmbedding(config)
    elif model_type in [EmbeddingModel.BGE_M3,
                       EmbeddingModel.BGE_LARGE_ZH,
                       EmbeddingModel.M3E_BASE]:
        return LocalEmbedding(config)
    else:
        raise ValueError(f"不支持的嵌入模型: {model_type}")


class TextChunker:
    """文本分块器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        分割文本为块

        Args:
            text: 输入文本

        Returns:
            文本块列表
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + self.chunk_size

            # 如果不是最后一块，尝试在句子边界分割
            if end < text_length:
                # 寻找最近的句子结束符
                for delimiter in ['。', '！', '？', '\n', '.', '!', '?']:
                    last_delimiter = text.rfind(delimiter, start, end)
                    if last_delimiter != -1 and last_delimiter > start:
                        end = last_delimiter + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 移动起始位置（带重叠）
            start = end - self.chunk_overlap

        return chunks

    def split_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        分割文档列表

        Args:
            documents: 文档列表，每个文档包含 content 字段

        Returns:
            分块后的文档列表
        """
        chunked_docs = []

        for doc in documents:
            content = doc.get('content', '')
            if not content:
                continue

            chunks = self.split_text(content)

            for i, chunk in enumerate(chunks):
                chunked_doc = {
                    'content': chunk,
                    'title': f"{doc.get('title', 'Untitled')} - Part {i+1}",
                    'source': doc.get('source', ''),
                    'category': doc.get('category', 'general'),
                    'chunk_index': i,
                    'parent_id': doc.get('id', ''),
                }
                chunked_docs.append(chunked_doc)

        return chunked_docs
