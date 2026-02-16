"""
知识库管理模块
支持文档的增删改查和多种数据源
"""

import os
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from rag_config import RAGConfig
from rag_vector_store import create_vector_store
from rag_embeddings import create_embedding_model, TextChunker


class KnowledgeBase:
    """知识库管理类"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.vector_store = create_vector_store(config)
        self.embedding_model = create_embedding_model(config)
        self.chunker = TextChunker(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

        # 初始化集合
        self.collection_name = config.qdrant_collection  # 或 milvus_collection
        self.vector_store.init_collection(
            self.collection_name,
            config.embedding_dimension
        )

    def add_documents(self, documents: List[Dict[str, str]],
                     category: str = "general",
                     auto_chunk: bool = True) -> List[str]:
        """
        添加文档到知识库

        Args:
            documents: 文档列表，每个文档包含:
                - title: 标题
                - content: 内容
                - source: 来源（可选）
            category: 分类（政策文件、行业报告、对话历史等）
            auto_chunk: 是否自动分块

        Returns:
            文档ID列表
        """
        if not documents:
            return []

        # 添加元数据
        for doc in documents:
            doc['id'] = doc.get('id', str(uuid.uuid4()))
            doc['category'] = category
            doc['created_at'] = datetime.now().isoformat()

        # 文本分块
        if auto_chunk:
            documents = self.chunker.split_documents(documents)

        # 生成向量
        print(f"[知识库] 正在为 {len(documents)} 个文档块生成向量...")
        texts = [doc['content'] for doc in documents]
        vectors = self.embedding_model.batch_encode(texts)

        # 准备插入数据
        insert_docs = []
        for doc, vector in zip(documents, vectors):
            insert_docs.append({
                'id': doc['id'],
                'vector': vector,
                'payload': {
                    'title': doc.get('title', ''),
                    'content': doc['content'],
                    'source': doc.get('source', ''),
                    'category': category,
                    'created_at': doc.get('created_at', ''),
                    'chunk_index': doc.get('chunk_index', 0),
                    'parent_id': doc.get('parent_id', ''),
                }
            })

        # 插入向量数据库
        self.vector_store.insert_documents(self.collection_name, insert_docs)

        print(f"[知识库] 成功添加 {len(insert_docs)} 个文档块")
        return [doc['id'] for doc in documents]

    def add_file(self, file_path: str, category: str = "document") -> List[str]:
        """
        从文件添加文档

        Args:
            file_path: 文件路径
            category: 分类

        Returns:
            文档ID列表
        """
        from file_processor import FileProcessor

        processor = FileProcessor()
        content, file_type = processor.process_file(file_path)

        # 提取标题
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]

        document = {
            'title': title,
            'content': content,
            'source': file_path,
            'file_type': file_type
        }

        return self.add_documents([document], category=category)

    def add_directory(self, directory: str,
                     category: str = "document",
                     extensions: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        批量添加目录下的文件

        Args:
            directory: 目录路径
            category: 分类
            extensions: 文件扩展名过滤（如: ['.md', '.pdf']）

        Returns:
            {filename: document_ids} 字典
        """
        if extensions is None:
            extensions = ['.md', '.txt', '.pdf', '.docx']

        results = {}
        valid_extensions = set(ext.lower() for ext in extensions)

        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                if ext in valid_extensions:
                    try:
                        print(f"[知识库] 正在处理: {file_path}")
                        doc_ids = self.add_file(file_path, category=category)
                        results[file_path] = doc_ids
                    except Exception as e:
                        print(f"[知识库] 处理文件失败 {file_path}: {e}")

        return results

    def add_dialog_history(self, dialogs: List[Dict[str, str]],
                          min_length: int = 100) -> List[str]:
        """
        添加对话历史到知识库

        Args:
            dialogs: 对话列表，每个对话包含:
                - question: 用户问题
                - answer: 智能体回答
            min_length: 最短文本长度（过滤无意义对话）

        Returns:
            文档ID列表
        """
        documents = []

        for dialog in dialogs:
            question = dialog.get('question', '').strip()
            answer = dialog.get('answer', '').strip()

            # 合并问答
            content = f"问题: {question}\n回答: {answer}"

            # 过滤太短的对话
            if len(content) < min_length:
                continue

            # 使用问题作为标题
            title = question[:50] + "..." if len(question) > 50 else question

            doc = {
                'title': title,
                'content': content,
                'source': 'dialog_history',
                'dialog_date': dialog.get('created_at', datetime.now().isoformat())
            }

            documents.append(doc)

        return self.add_documents(documents, category="dialog_history")

    def search(self, query: str,
              top_k: int = None,
              category: Optional[str] = None,
              score_threshold: float = None) -> List[Dict[str, Any]]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量（默认使用配置）
            category: 分类过滤
            score_threshold: 相似度阈值（默认使用配置）

        Returns:
            检索结果列表
        """
        if top_k is None:
            top_k = self.config.top_k
        if score_threshold is None:
            score_threshold = self.config.score_threshold

        # 生成查询向量
        query_vector = self.embedding_model.encode(query)

        # 构建过滤条件
        filter_conditions = {"category": category} if category else None

        # 执行检索
        results = self.vector_store.search(
            self.collection_name,
            query_vector,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions
        )

        return results

    def delete_documents(self, document_ids: List[str]):
        """删除文档"""
        if document_ids:
            self.vector_store.delete_documents(self.collection_name, document_ids)
            print(f"[知识库] 删除了 {len(document_ids)} 个文档")

    def delete_by_category(self, category: str):
        """按分类删除所有文档"""
        # TODO: 需要向量存储支持批量按条件删除
        # 临时方案：先检索该分类的所有文档，然后删除
        results = self.search(query="", category=category, top_k=1000)

        if results:
            doc_ids = [r['id'] for r in results]
            self.delete_documents(doc_ids)

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        info = self.vector_store.get_collection_info(self.collection_name)

        stats = {
            'collection_name': self.collection_name,
            'total_documents': info.get('vectors_count', 0),
            'status': info.get('status', 'unknown'),
            'embedding_model': self.config.embedding_model.value,
            'embedding_dimension': self.config.embedding_dimension,
        }

        return stats

    def clear_all(self):
        """清空知识库"""
        try:
            self.vector_store.drop_collection(self.collection_name)
            self.vector_store.init_collection(
                self.collection_name,
                self.config.embedding_dimension
            )
            print(f"[知识库] 已清空知识库")
        except Exception as e:
            print(f"[知识库] 清空失败: {e}")

    def export_knowledge_base(self, output_file: str):
        """导出知识库（用于备份）"""
        import json

        # TODO: 实现导出逻辑（需要向量存储支持导出）
        # 临时方案：导出元数据
        results = self.search(query="", top_k=10000)

        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_documents': len(results),
            'documents': results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        print(f"[知识库] 已导出到: {output_file}")


class WebScraper:
    """网页爬取器（用于构建知识库）"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self.cache_dir = config.web_cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def scrape_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        爬取单个网页

        Args:
            url: 网页URL

        Returns:
            包含title和content的字典，失败返回None
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            # 请求网页
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.config.web_scrape_timeout)
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.find('title')
            title = title.get_text().strip() if title else url

            # 提取正文（去除脚本和样式）
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            content = soup.get_text(separator='\n', strip=True)

            # 保存到缓存
            cached_file = self._save_to_cache(url, title, content)

            return {
                'title': title,
                'content': content,
                'source': url,
                'cached_file': cached_file
            }

        except Exception as e:
            print(f"[爬虫] 爬取失败 {url}: {e}")
            return None

    def _save_to_cache(self, url: str, title: str, content: str) -> str:
        """保存到缓存文件"""
        # 生成文件名（URL的hash）
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename = f"{url_hash}.txt"
        filepath = os.path.join(self.cache_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Title: {title}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"\n{'='*50}\n\n")
            f.write(content)

        return filepath

    def scrape_multiple(self, urls: List[str]) -> List[Dict[str, str]]:
        """批量爬取网页"""
        results = []

        for url in urls:
            print(f"[爬虫] 正在爬取: {url}")
            data = self.scrape_url(url)
            if data:
                results.append(data)

        return results

    def scrape_sitemap(self, sitemap_url: str, limit: int = None) -> List[Dict[str, str]]:
        """
        从sitemap爬取网站

        Args:
            sitemap_url: sitemap.xml URL
            limit: 最大页面数

        Returns:
            爬取结果列表
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'xml')
            urls = [loc.text for loc in soup.find_all('loc')]

            if limit:
                urls = urls[:limit]

            print(f"[爬虫] 从sitemap发现 {len(urls)} 个URL")
            return self.scrape_multiple(urls)

        except Exception as e:
            print(f"[爬虫] 解析sitemap失败: {e}")
            return []
