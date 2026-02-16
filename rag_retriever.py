"""
RAG检索器
实现混合检索策略和重排序
"""

import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

from rag_config import RAGConfig
from rag_knowledge_base import KnowledgeBase


class RAGRetriever:
    """RAG检索器，支持多种检索策略"""

    def __init__(self, knowledge_base: KnowledgeBase, config: RAGConfig):
        self.kb = knowledge_base
        self.config = config

    def retrieve(self, query: str,
                strategy: str = "hybrid",
                category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检索相关文档

        Args:
            query: 查询文本
            strategy: 检索策略
                - "vector": 纯向量检索
                - "keyword": 纯关键词检索
                - "hybrid": 混合检索（向量+关键词）
            category: 分类过滤

        Returns:
            检索结果列表
        """
        if strategy == "vector":
            results = self._vector_search(query, category)
        elif strategy == "keyword":
            results = self._keyword_search(query, category)
        elif strategy == "hybrid":
            results = self._hybrid_search(query, category)
        else:
            raise ValueError(f"不支持的检索策略: {strategy}")

        # 重排序
        if self.config.use_rerank and len(results) > 0:
            results = self._rerank(query, results)

        # 截断到rerank_top_k
        if self.config.use_rerank:
            results = results[:self.config.rerank_top_k]

        return results

    def _vector_search(self, query: str,
                      category: Optional[str] = None) -> List[Dict[str, Any]]:
        """纯向量检索"""
        return self.kb.search(
            query=query,
            top_k=self.config.top_k * 2,  # 获取更多候选用于重排序
            category=category
        )

    def _keyword_search(self, query: str,
                       category: Optional[str] = None) -> List[Dict[str, Any]]:
        """纯关键词检索（BM25）"""
        # TODO: 实现BM25或类似算法
        # 临时方案：使用简单的词频统计
        all_results = self.kb.search(
            query="".join(query.split()),  # 移除空格进行模糊匹配
            top_k=1000,
            category=category,
            score_threshold=0.0  # 不限制阈值
        )

        # 计算关键词匹配分数
        keywords = self._extract_keywords(query)
        scored_results = []

        for result in all_results:
            content = result['payload'].get('content', '').lower()
            title = result['payload'].get('title', '').lower()

            score = 0.0
            for keyword in keywords:
                if keyword in content:
                    score += content.count(keyword) * 0.1
                if keyword in title:
                    score += title.count(keyword) * 0.2

            if score > 0:
                result['score'] = score
                scored_results.append(result)

        # 排序并返回
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        return scored_results[:self.config.top_k]

    def _hybrid_search(self, query: str,
                      category: Optional[str] = None) -> List[Dict[str, Any]]:
        """混合检索（向量+关键词）"""
        # 获取向量检索结果
        vector_results = self._vector_search(query, category)

        # 获取关键词检索结果
        keyword_results = self._keyword_search(query, category)

        # 合并结果
        combined = self._merge_results(vector_results, keyword_results)

        return combined[:self.config.top_k]

    def _merge_results(self, vector_results: List[Dict],
                      keyword_results: List[Dict],
                      alpha: float = 0.7) -> List[Dict]:
        """
        合并向量和关键词检索结果

        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            alpha: 向量检索权重（0-1）

        Returns:
            合并后的结果
        """
        # 创建ID到结果的映射
        result_map = {}

        # 添加向量检索结果（归一化分数）
        if vector_results:
            max_vector_score = max(r['score'] for r in vector_results)
            for result in vector_results:
                doc_id = result['id']
                normalized_score = result['score'] / max_vector_score if max_vector_score > 0 else 0
                result_map[doc_id] = {
                    **result,
                    'vector_score': normalized_score,
                    'keyword_score': 0.0,
                    'combined_score': alpha * normalized_score
                }

        # 合并关键词检索结果
        if keyword_results:
            max_keyword_score = max(r['score'] for r in keyword_results)
            for result in keyword_results:
                doc_id = result['id']
                normalized_score = result['score'] / max_keyword_score if max_keyword_score > 0 else 0

                if doc_id in result_map:
                    # 文档在两个结果中都存在
                    result_map[doc_id]['keyword_score'] = normalized_score
                    result_map[doc_id]['combined_score'] = (
                        alpha * result_map[doc_id]['vector_score'] +
                        (1 - alpha) * normalized_score
                    )
                else:
                    # 文档只在关键词结果中
                    result_map[doc_id] = {
                        **result,
                        'vector_score': 0.0,
                        'keyword_score': normalized_score,
                        'combined_score': (1 - alpha) * normalized_score
                    }

        # 按合并分数排序
        merged = list(result_map.values())
        merged.sort(key=lambda x: x['combined_score'], reverse=True)

        # 恢复原始score字段
        for result in merged:
            result['score'] = result['combined_score']

        return merged

    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        重排序检索结果

        Args:
            query: 原始查询
            results: 检索结果

        Returns:
            重排序后的结果
        """
        # 方案1: 使用重排序模型（如Cohere Rerank, BGE Reranker）
        # 这里使用简单的基于规则的重排序

        scored = []
        for result in results:
            score = result['score']
            content = result['payload'].get('content', '')
            title = result['payload'].get('title', '')

            # 提升标题匹配的分数
            query_lower = query.lower()
            if query_lower in title.lower():
                score *= 1.2

            # 提升包含关键词的内容
            keywords = self._extract_keywords(query)
            keyword_match_count = sum(1 for kw in keywords if kw in content.lower())
            if keyword_match_count > 0:
                score *= (1 + 0.1 * keyword_match_count)

            # 降低过短内容的分数
            content_length = len(content)
            if content_length < 100:
                score *= 0.7
            elif content_length > 1000:
                score *= 1.1

            scored.append({**result, 'score': score})

        # 重新排序
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的中文分词（基于规则）
        # 实际生产环境应使用jieba等分词工具

        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)

        # 分词（按空格和常见词边界）
        words = text.split()

        # 过滤停用词（简化版）
        stopwords = {'的', '是', '在', '和', '了', '有', '不', '这', '我', '他', '她', '它',
                    'what', 'is', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at'}

        keywords = [w.lower() for w in words if len(w) > 1 and w.lower() not in stopwords]

        return keywords

    def format_context(self, results: List[Dict], max_length: int = 4000) -> str:
        """
        格式化检索结果为上下文

        Args:
            results: 检索结果
            max_length: 最大长度（字符数）

        Returns:
            格式化的上下文字符串
        """
        if not results:
            return ""

        context_parts = []
        current_length = 0

        for i, result in enumerate(results, 1):
            title = result['payload'].get('title', 'Untitled')
            content = result['payload'].get('content', '')
            score = result['score']
            source = result['payload'].get('source', '')

            # 截断过长的内容
            if len(content) > 500:
                content = content[:500] + "..."

            part = f"""
【参考文档{i}】
标题: {title}
相似度: {score:.3f}
来源: {source}
内容: {content}
"""

            if current_length + len(part) > max_length:
                break

            context_parts.append(part)
            current_length += len(part)

        return "\n".join(context_parts)


class RAGAugmenter:
    """RAG增强器，将检索结果整合到LLM提示中"""

    def __init__(self, retriever: RAGRetriever, config: RAGConfig):
        self.retriever = retriever
        self.config = config

    def augment_prompt(self, query: str, strategy: str = "hybrid",
                      category: Optional[str] = None) -> str:
        """
        增强提示词（添加检索到的上下文）

        Args:
            query: 用户查询
            strategy: 检索策略
            category: 分类过滤

        Returns:
            增强后的提示词
        """
        # 检索相关文档
        results = self.retriever.retrieve(query, strategy=strategy, category=category)

        if not results:
            return query

        # 格式化上下文
        context = self.retriever.format_context(results)

        # 构建增强提示词
        augmented_prompt = f"""
参考以下文档内容回答用户问题：

{context}

用户问题: {query}

请基于上述参考文档内容回答问题。如果参考文档中没有相关信息，请明确说明。
"""

        return augmented_prompt

    def augment_with_sources(self, query: str, strategy: str = "hybrid",
                           category: Optional[str] = None) -> Dict[str, Any]:
        """
        增强提示词并返回来源信息

        Returns:
            包含以下字段的字典:
                - augmented_prompt: 增强后的提示词
                - sources: 来源文档列表
                - retrieval_metadata: 检索元数据
        """
        results = self.retriever.retrieve(query, strategy=strategy, category=category)

        context = self.retriever.format_context(results)

        # 提取来源信息
        sources = []
        seen_sources = set()

        for result in results:
            source = result['payload'].get('source', 'Unknown')
            title = result['payload'].get('title', 'Untitled')

            # 去重
            source_key = f"{source} - {title}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    'title': title,
                    'source': source,
                    'score': result['score']
                })

        augmented_prompt = f"""
参考以下文档内容回答用户问题：

{context}

用户问题: {query}

请基于上述参考文档内容回答问题。如果参考文档中没有相关信息，请明确说明。
"""

        return {
            'augmented_prompt': augmented_prompt,
            'sources': sources,
            'retrieval_metadata': {
                'num_results': len(results),
                'strategy': strategy,
                'category': category
            }
        }
