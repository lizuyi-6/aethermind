"""
向量数据库连接层
支持Qdrant和Milvus
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from rag_config import RAGConfig, VectorDBType


class VectorStore(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    def init_collection(self, collection_name: str, dimension: int):
        """初始化集合"""
        pass

    @abstractmethod
    def insert_documents(self, collection_name: str, documents: List[Dict[str, Any]]):
        """
        插入文档

        Args:
            collection_name: 集合名称
            documents: 文档列表，每个文档包含:
                - id: 唯一标识
                - vector: 向量
                - payload: 元数据 (title, content, source, category, etc.)
        """
        pass

    @abstractmethod
    def search(self, collection_name: str, query_vector: List[float],
               top_k: int = 5, score_threshold: float = 0.0,
               filter_conditions: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        向量检索

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回结果数量
            score_threshold: 相似度阈值
            filter_conditions: 过滤条件 (如: {"category": "政策文件"})

        Returns:
            检索结果列表，每个结果包含:
                - id: 文档ID
                - score: 相似度分数
                - payload: 元数据
        """
        pass

    @abstractmethod
    def delete_documents(self, collection_name: str, document_ids: List[str]):
        """删除文档"""
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        pass

    @abstractmethod
    def drop_collection(self, collection_name: str):
        """删除集合"""
        pass


class QdrantVectorStore(VectorStore):
    """Qdrant向量存储实现"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化Qdrant客户端"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

            # 连接Qdrant
            if self.config.qdrant_api_key:
                # 云服务
                self.client = QdrantClient(
                    url=self.config.qdrant_host,
                    api_key=self.config.qdrant_api_key,
                    timeout=60
                )
            else:
                # 本地服务
                self.client = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                    timeout=60
                )

            print(f"[Qdrant] 成功连接到: {self.config.qdrant_host}:{self.config.qdrant_port}")
        except ImportError:
            raise ImportError("需要安装qdrant-client: pip install qdrant-client")
        except Exception as e:
            raise ConnectionError(f"连接Qdrant失败: {e}")

    def init_collection(self, collection_name: str, dimension: int):
        """初始化集合"""
        from qdrant_client.models import Distance, VectorParams

        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if collection_name not in collection_names:
                # 创建新集合
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=Distance.COSINE  # 使用余弦相似度
                    )
                )
                print(f"[Qdrant] 创建集合: {collection_name} (维度: {dimension})")
            else:
                print(f"[Qdrant] 集合已存在: {collection_name}")
        except Exception as e:
            raise Exception(f"初始化集合失败: {e}")

    def insert_documents(self, collection_name: str, documents: List[Dict[str, Any]]):
        """插入文档"""
        from qdrant_client.models import PointStruct

        try:
            points = []
            for doc in documents:
                points.append(PointStruct(
                    id=doc['id'],
                    vector=doc['vector'],
                    payload=doc['payload']
                ))

            # 批量插入
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            print(f"[Qdrant] 插入 {len(documents)} 个文档到 {collection_name}")
        except Exception as e:
            raise Exception(f"插入文档失败: {e}")

    def search(self, collection_name: str, query_vector: List[float],
               top_k: int = 5, score_threshold: float = 0.0,
               filter_conditions: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """向量检索"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            # 构建过滤条件
            search_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                search_filter = Filter(must=conditions)

            # 执行检索
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=top_k,
                score_threshold=score_threshold
            )

            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': str(result.id),
                    'score': result.score,
                    'payload': result.payload
                })

            return formatted_results
        except Exception as e:
            raise Exception(f"检索失败: {e}")

    def delete_documents(self, collection_name: str, document_ids: List[str]):
        """删除文档"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=document_ids
            )
            print(f"[Qdrant] 删除 {len(document_ids)} 个文档")
        except Exception as e:
            raise Exception(f"删除文档失败: {e}")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                'name': collection_name,
                'vectors_count': info.vectors_count,
                'indexed_vectors_count': info.indexed_vectors_count,
                'points_count': info.points_count,
                'status': info.status
            }
        except Exception as e:
            raise Exception(f"获取集合信息失败: {e}")

    def drop_collection(self, collection_name: str):
        """删除集合"""
        try:
            self.client.delete_collection(collection_name)
            print(f"[Qdrant] 删除集合: {collection_name}")
        except Exception as e:
            raise Exception(f"删除集合失败: {e}")


class MilvusVectorStore(VectorStore):
    """Milvus向量存储实现"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.connections = None
        self.collection = None
        self._init_client()

    def _init_client(self):
        """初始化Milvus客户端"""
        try:
            from pymilvus import connections, utility

            # 连接Milvus
            connections.connect(
                alias="default",
                host=self.config.milvus_host,
                port=self.config.milvus_port,
                user=self.config.milvus_user,
                password=self.config.milvus_password
            )

            self.connections = connections
            print(f"[Milvus] 成功连接到: {self.config.milvus_host}:{self.config.milvus_port}")
        except ImportError:
            raise ImportError("需要安装pymilvus: pip install pymilvus")
        except Exception as e:
            raise ConnectionError(f"连接Milvus失败: {e}")

    def init_collection(self, collection_name: str, dimension: int):
        """初始化集合"""
        from pymilvus import FieldSchema, CollectionSchema, DataType, Collection, utility

        try:
            # 检查集合是否存在
            if utility.has_collection(collection_name):
                print(f"[Milvus] 集合已存在: {collection_name}")
                self.collection = Collection(collection_name)
            else:
                # 定义schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
                    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=512),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
                    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=4096),
                ]

                schema = CollectionSchema(fields=fields, description="知识库集合")
                self.collection = Collection(name=collection_name, schema=schema)

                # 创建索引
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "COSINE",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(field_name="vector", index_params=index_params)

                print(f"[Milvus] 创建集合: {collection_name} (维度: {dimension})")
        except Exception as e:
            raise Exception(f"初始化集合失败: {e}")

    def insert_documents(self, collection_name: str, documents: List[Dict[str, Any]]):
        """插入文档"""
        try:
            data = {
                'id': [doc['id'] for doc in documents],
                'vector': [doc['vector'] for doc in documents],
                'title': [doc['payload'].get('title', '') for doc in documents],
                'content': [doc['payload'].get('content', '') for doc in documents],
                'source': [doc['payload'].get('source', '') for doc in documents],
                'category': [doc['payload'].get('category', 'general') for doc in documents],
                'metadata': [str(doc['payload'].get('metadata', {})) for doc in documents],
            }

            self.collection.insert([data[field] for field in data.keys()])
            self.collection.flush()
            print(f"[Milvus] 插入 {len(documents)} 个文档到 {collection_name}")
        except Exception as e:
            raise Exception(f"插入文档失败: {e}")

    def search(self, collection_name: str, query_vector: List[float],
               top_k: int = 5, score_threshold: float = 0.0,
               filter_conditions: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """向量检索"""
        try:
            self.collection.load()

            # 构建搜索参数
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            # 执行检索
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=None,  # TODO: 添加过滤条件
                output_fields=["title", "content", "source", "category"]
            )

            # 格式化结果
            formatted_results = []
            for result in results[0]:
                if result.distance >= score_threshold:
                    formatted_results.append({
                        'id': result.id,
                        'score': result.distance,
                        'payload': {
                            'title': result.entity.get('title'),
                            'content': result.entity.get('content'),
                            'source': result.entity.get('source'),
                            'category': result.entity.get('category')
                        }
                    })

            return formatted_results
        except Exception as e:
            raise Exception(f"检索失败: {e}")

    def delete_documents(self, collection_name: str, document_ids: List[str]):
        """删除文档"""
        try:
            self.collection.delete(expr=f"id in {document_ids}")
            print(f"[Milvus] 删除 {len(document_ids)} 个文档")
        except Exception as e:
            raise Exception(f"删除文档失败: {e}")

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            from pymilvus import utility

            info = self.collection.describe()
            num_entities = self.collection.num_entities

            return {
                'name': collection_name,
                'schema': info,
                'vectors_count': num_entities,
                'status': 'loaded' if self.collection.is_loaded else 'not_loaded'
            }
        except Exception as e:
            raise Exception(f"获取集合信息失败: {e}")

    def drop_collection(self, collection_name: str):
        """删除集合"""
        try:
            from pymilvus import utility
            utility.drop_collection(collection_name)
            print(f"[Milvus] 删除集合: {collection_name}")
        except Exception as e:
            raise Exception(f"删除集合失败: {e}")


def create_vector_store(config: RAGConfig) -> VectorStore:
    """工厂函数：根据配置创建向量存储实例"""
    if config.vector_db_type == VectorDBType.QDRANT:
        return QdrantVectorStore(config)
    elif config.vector_db_type == VectorDBType.MILVUS:
        return MilvusVectorStore(config)
    elif config.vector_db_type == VectorDBType.CHROMA:
        # Chroma实现（略，可使用类似模式）
        raise NotImplementedError("Chroma支持待实现")
    else:
        raise ValueError(f"不支持的向量数据库类型: {config.vector_db_type}")
