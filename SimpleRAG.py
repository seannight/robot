"""
竞赛智能客服系统 - 简化版RAG实现
使用轻量级文本检索代替向量存储，按竞赛类别建立索引
"""

import os
import re
import logging
import jieba
import jieba.posseg as pseg  # 使用词性标注
import math
import json
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional, Set
import fitz  # PyMuPDF
import time

from app.config import settings

logger = logging.getLogger(__name__)

# 竞赛专用术语和关键词 (从mcp_engine.py整合)
COMPETITION_TERMS = {
    # 竞赛类型
    "竞赛类型": [
        "人工智能创新挑战赛", "3D编程模型创新设计专项赛", "机器人工程挑战赛",
        "极地资源勘探设计大赛", "竞技机器人专项赛", "开源鸿蒙专项赛", 
        "人工智能综合创新专项赛", "三维程序创意设计大赛", "生成式人工智能应用专项赛",
        "太空电梯设计专项赛", "太空探索智能机器人大赛", "虚拟仿真平台创新设计专项赛",
        "智能数据采集与处理专项赛", "智能芯片创新设计大赛", "计算思维与人工智能专项赛",
        "未来校园智能应用专项赛"
    ],
    
    # 竞赛阶段
    "竞赛阶段": [
        "报名", "初赛", "复赛", "决赛", "作品提交", "结果公布",
        "颁奖", "开幕式", "闭幕式", "答辩", "评审"
    ],
    
    # 竞赛要素
    "竞赛要素": [
        "参赛资格", "参赛条件", "参赛要求", "参赛流程", "评分标准",
        "奖项设置", "报名方式", "报名费用", "报名时间", "比赛时间",
        "提交要求", "提交方式", "提交时间", "评审方式", "评审标准"
    ],
    
    # 竞赛内容
    "竞赛内容": [
        "赛题", "题目", "任务", "要求", "目标", "创新点",
        "技术路线", "解决方案", "实现方法", "评价指标", "验收标准"
    ],
    
    # 参赛作品
    "参赛作品": [
        "论文", "代码", "设计", "模型", "方案", "报告",
        "演示", "展示", "答辩", "PPT", "视频", "海报"
    ]
}

class SimpleRAG:
    """简化版RAG引擎，使用文本索引代替向量存储"""
    
    def __init__(self, rebuild_index=False):
        """
        初始化简化版RAG引擎
        :param rebuild_index: 是否重建索引
        """
        self.knowledge_base_path = settings.KNOWLEDGE_BASE_PATH
        self.index_path = settings.INDEX_PATH
        os.makedirs(self.index_path, exist_ok=True)
        
        # 竞赛类型和关键词
        self.competition_types = settings.COMPETITION_TYPES
        self.competition_keywords = settings.COMPETITION_KEYWORDS
        
        # 整合术语库
        self.competition_terms = COMPETITION_TERMS
        
        # 文档索引结构
        self.index = {}  # 词 -> 文档ID列表
        self.documents = {}  # 文档ID -> 文档内容
        self.competition_docs = defaultdict(list)  # 竞赛类型 -> 文档ID列表
        
        # 检索参数设置 - 从新的配置项中加载
        self.score_threshold = settings.RAG_SCORE_THRESHOLD
        self.chunk_size = settings.RAG_CHUNK_SIZE
        self.chunk_overlap = settings.RAG_CHUNK_OVERLAP
        
        # 关键词参数
        self.max_keywords_per_query = settings.MAX_KEYWORDS_PER_QUERY
        self.max_keywords_per_chunk = settings.MAX_KEYWORDS_PER_CHUNK
        
        # 评分参数
        self.competition_type_boost_factor = settings.COMPETITION_TYPE_BOOST_FACTOR
        self.keyword_match_base_weight = settings.KEYWORD_MATCH_BASE_WEIGHT
        self.direct_query_match_bonus = settings.DIRECT_QUERY_MATCH_BONUS
        self.critical_phrases_scoring = settings.CRITICAL_PHRASES_SCORING
        
        # 加载停用词
        self.stopwords = set()
        if hasattr(settings, 'STOPWORDS_FILE_PATH') and settings.STOPWORDS_FILE_PATH and os.path.exists(settings.STOPWORDS_FILE_PATH):
            try:
                with open(settings.STOPWORDS_FILE_PATH, 'r', encoding='utf-8') as f:
                    self.stopwords = {word.strip() for word in f.read().split('、') if word.strip()}
                logger.info(f"成功加载 {len(self.stopwords)} 个停用词")
            except Exception as e:
                logger.error(f"加载停用词失败: {str(e)}")
        else:
            logger.warning("停用词文件不存在或未配置，将不使用停用词过滤")
        
        # 问题类型模板 (从mcp_engine.py整合)
        self.question_patterns = {
            "竞赛信息": {
                "patterns": [
                    r"(什么是|介绍|简介|说明).*(竞赛|比赛|大赛)",
                    r".*竞赛.*(内容|主题|方向|类型)",
                    r".*赛题.*(类型|方向|领域|范围)"
                ]
            },
            "参赛要求": {
                "patterns": [
                    r"(如何|怎么|怎样).*(参赛|报名)",
                    r".*(参赛|报名).*(条件|要求|资格|限制)",
                    r".*(需要|必须|可以).*(参加|报名)"
                ]
            },
            "时间安排": {
                "patterns": [
                    r".*(时间|日期|截止|期限)",
                    r".*什么时候.*(开始|结束|截止)",
                    r".*(报名|提交|答辩).*(时间|日期)"
                ]
            },
            "评分标准": {
                "patterns": [
                    r".*(评分|评审|打分).*(标准|方式|规则)",
                    r".*(如何|怎么).*(评判|评估|评价)",
                    r".*(分数|成绩).*(构成|组成|计算)"
                ]
            },
            "奖项设置": {
                "patterns": [
                    r".*(奖项|奖励|奖金).*(设置|情况|多少)",
                    r".*(可以|能够).*(获得|拿到).*(什么|哪些).*奖",
                    r".*有.*(什么|哪些).*(奖|奖励)"
                ]
            }
        }
        
        # 加载或创建索引
        if rebuild_index or not self._index_exists():
            self._build_index()
        else:
            self._load_index()
        
        logger.info(f"简化版RAG引擎初始化完成，索引包含 {len(self.documents)} 个文档片段，阈值设置为 {self.score_threshold}")
    
    def _index_exists(self) -> bool:
        """检查索引文件是否存在"""
        index_file = os.path.join(self.index_path, "index.json")
        docs_file = os.path.join(self.index_path, "documents.json")
        comp_file = os.path.join(self.index_path, "competition_docs.json")
        return os.path.exists(index_file) and os.path.exists(docs_file) and os.path.exists(comp_file)
    
    def _build_index(self):
        """构建文本索引"""
        logger.info("开始构建文本索引...")
        
        # 检查知识库路径
        if not os.path.exists(self.knowledge_base_path):
            logger.error(f"知识库路径不存在: {self.knowledge_base_path}")
            return
        
        # 清空现有索引
        self.index = {}
        self.documents = {}
        self.competition_docs = defaultdict(list)
        
        # 处理所有PDF文件
        pdf_files = []
        for root, _, files in os.walk(self.knowledge_base_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        logger.info(f"发现 {len(pdf_files)} 个PDF文件")
        
        doc_id = 0
        for pdf_path in pdf_files:
            try:
                # 提取竞赛类型
                file_name = os.path.basename(pdf_path)
                competition_type = self._detect_competition_type(file_name)
                
                # 处理PDF文件
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    # 按页面分割，每页作为一个文档片段
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if not text.strip():
                        continue
                    
                    # 以设置的块大小为单位进一步分割长文本
                    chunks = self._split_text(text)
                    for chunk in chunks:
                        if not chunk.strip():
                            continue
                        
                        # 为每个文本块分配ID
                        doc_id += 1
                        doc_key = f"doc_{doc_id}"
                        
                        # 存储文档内容
                        self.documents[doc_key] = {
                            "content": chunk,
                            "source": file_name,
                            "page": page_num + 1,
                            "competition": competition_type
                        }
                        
                        # 分词并创建索引 - 使用新的参数
                        keywords = self._extract_keywords(chunk, max_count=self.max_keywords_per_chunk, for_query=False)
                        for keyword in keywords:
                            if keyword not in self.index:
                                self.index[keyword] = []
                            self.index[keyword].append(doc_key)
                        
                        # 按竞赛类型索引
                        if competition_type:
                            self.competition_docs[competition_type].append(doc_key)
                
                logger.info(f"索引文件: {file_name}, 竞赛类型: {competition_type or '未知'}")
            
            except Exception as e:
                logger.error(f"处理文件 {pdf_path} 时出错: {str(e)}")
        
        # 保存索引
        self._save_index()
        logger.info(f"索引构建完成，包含 {doc_id} 个文档片段，{len(self.index)} 个关键词")
    
    def _save_index(self):
        """保存索引到文件"""
        try:
            # 保存索引文件
            with open(os.path.join(self.index_path, "index.json"), "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False)
            
            # 保存文档内容
            with open(os.path.join(self.index_path, "documents.json"), "w", encoding="utf-8") as f:
                json.dump(self.documents, f, ensure_ascii=False)
            
            # 保存竞赛文档映射
            with open(os.path.join(self.index_path, "competition_docs.json"), "w", encoding="utf-8") as f:
                json.dump(dict(self.competition_docs), f, ensure_ascii=False)
            
            logger.info("索引文件保存成功")
        except Exception as e:
            logger.error(f"保存索引失败: {str(e)}")
    
    def _load_index(self):
        """从文件加载索引"""
        try:
            # 加载索引文件
            with open(os.path.join(self.index_path, "index.json"), "r", encoding="utf-8") as f:
                self.index = json.load(f)
            
            # 加载文档内容
            with open(os.path.join(self.index_path, "documents.json"), "r", encoding="utf-8") as f:
                self.documents = json.load(f)
            
            # 加载竞赛文档映射
            with open(os.path.join(self.index_path, "competition_docs.json"), "r", encoding="utf-8") as f:
                self.competition_docs = defaultdict(list, json.load(f))
            
            logger.info(f"成功加载索引，包含 {len(self.documents)} 个文档，{len(self.index)} 个关键词")
        except Exception as e:
            logger.error(f"加载索引失败: {str(e)}，将重建索引")
            self._build_index()
    
    def _detect_competition_type(self, text: str) -> Optional[str]:
        """
        检测文本中的竞赛类型
        :param text: 输入文本
        :return: 竞赛类型或None
        """
        # 直接匹配竞赛类型
        for comp_type in self.competition_types:
            if comp_type in text:
                return comp_type
        
        # 使用关键词判断
        for keyword in self.competition_keywords:
            if keyword in text:
                # 根据关键词找到对应的竞赛类型
                for comp_type in self.competition_types:
                    if keyword in comp_type:
                        return comp_type
        
        return None
    
    def classify_question(self, question: str) -> Tuple[str, float]:
        """
        分类问题类型 (从mcp_engine.py整合)
        :param question: 用户问题
        :return: (问题类型, 置信度)
        """
        # 清理和标准化问题
        question = question.lower()
        question = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
        
        # 匹配问题模式
        best_match = None
        best_score = 0.0
        
        for q_type, pattern_info in self.question_patterns.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, question):
                    score = 0.8  # 基础匹配分数
                    if score > best_score:
                        best_score = score
                        best_match = q_type
        
        # 如果没有找到匹配
        if not best_match:
            return "未知", 0.0
            
        return best_match, best_score
    
    def _extract_keywords(self, text: str, max_count: Optional[int] = None, for_query: bool = False) -> List[str]:
        """
        从文本中提取关键词，使用词性标注提高质量
        :param text: 输入文本
        :param max_count: 返回关键词的最大数量，默认根据for_query参数决定
        :param for_query: 是否为查询提取关键词（影响默认max_count）
        :return: 关键词列表
        """
        if not text:
            return []
        
        # 如果未指定max_count，根据for_query设置默认值
        if max_count is None:
            max_count = self.max_keywords_per_query if for_query else self.max_keywords_per_chunk
        
        # 提前检查是否包含竞赛专有名词
        competition_keywords = []
        for comp_type in self.competition_types:
            if comp_type in text:
                competition_keywords.append(comp_type)
        
        # 词性筛选：保留名词、动词、形容词、专名等有实际意义的词
        # n-名词, v-动词, a-形容词, nr-人名, ns-地名, nt-机构团体名, nz-其他专名
        # vn-名动词, an-名形词, j-简称, i-成语, l-习语, eng-英文, nrt-音译人名
        allowed_pos = {'n', 'v', 'a', 'nr', 'ns', 'nt', 'nz', 'vn', 'an', 'j', 'i', 'l', 'eng', 'nrt'}
        
        # 使用jieba进行分词和词性标注
        words_with_pos = pseg.lcut(text)
        
        # 扩展对竞赛术语的识别
        competition_terms_set = set()
        for category, terms in self.competition_terms.items():
            for term in terms:
                competition_terms_set.add(term)
        
        # 过滤停用词和单字词
        keywords = []
        seen_keywords = set()  # 去重
        
        # 首先添加竞赛专有名词（最高优先级）
        for comp_type in competition_keywords:
            if comp_type not in seen_keywords:
                keywords.append(comp_type)
                seen_keywords.add(comp_type)
                logger.info(f"检测到竞赛专有名词: {comp_type}")
        
        # 然后处理竞赛术语 - 优先添加
        for term in competition_terms_set:
            if term in text and term not in seen_keywords and len(term) > 1:
                keywords.append(term)
                seen_keywords.add(term)
        
        # 然后处理词性标注结果
        for word, flag in words_with_pos:
            word = word.strip().lower()
            # 过滤条件：词性在允许列表中、不是停用词、长度大于1（避免单字）
            if flag in allowed_pos and word not in self.stopwords and len(word) > 1:
                if word not in seen_keywords:
                    keywords.append(word)
                    seen_keywords.add(word)
        
        # 如果是查询，并且提取的关键词太少，尝试降低要求（包含单字和更多词性）
        if for_query and len(keywords) < 3:
            for word, flag in words_with_pos:
                word = word.strip().lower()
                # 单字词中，只选择名词
                if word and word not in self.stopwords and word not in seen_keywords:
                    # 对于长度为1的词，要求必须是名词
                    if len(word) == 1 and flag.startswith('n'):
                        keywords.append(word)
                        seen_keywords.add(word)
                    # 对于长度大于1的词，放宽词性要求
                    elif len(word) > 1:
                        keywords.append(word)
                        seen_keywords.add(word)
                    # 如果已经达到最大数量，停止添加
                    if len(keywords) >= max_count:
                        break
        
        # 限制关键词数量
        if len(keywords) > max_count:
            keywords = keywords[:max_count]
        
        if for_query:
            logger.info(f"从查询 '{text}' 中提取关键词: {keywords}")
        else:
            logger.debug(f"从文档块中提取了 {len(keywords)} 个关键词")
        
        return keywords
    
    def _split_text(self, text: str, chunk_size=None) -> List[str]:
        """将文本分割成固定大小的块"""
        if chunk_size is None:
            chunk_size = self.chunk_size
            
        chunks = []
        # 按段落分割
        paragraphs = text.split('\n')
        current_chunk = ""
        
        for para in paragraphs:
            if not para.strip():
                continue
                
            if len(current_chunk) + len(para) <= chunk_size:
                current_chunk += para + "\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # 添加重叠
                    words = current_chunk.split()
                    if len(words) > self.chunk_overlap // 10:  # 大约每10个字符一个词
                        overlap_text = " ".join(words[-self.chunk_overlap // 10:])
                        current_chunk = overlap_text + "\n" + para + "\n"
                    else:
                        current_chunk = para + "\n"
                else:
                    current_chunk = para + "\n"
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def search(self, query: str, competition_type: Optional[str] = None, top_n: int = 5, score_threshold: Optional[float] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索相关文档
        :param query: 用户查询
        :param competition_type: 竞赛类型，可选
        :param top_n: 返回结果数量
        :param score_threshold: 相似度阈值，可选
        :param top_k: 搜索前K个结果
        :return: 相关文档列表，按相似度降序排列
        """
        # 使用配置值或默认值
        score_threshold = score_threshold if score_threshold is not None else self.score_threshold
        top_k = top_k if top_k is not None else settings.RAG_TOP_K
        
        try:
            # 提取关键词，使用参数来限制关键词数量
            keywords = self._extract_keywords(query, max_count=self.max_keywords_per_query, for_query=True)
            
            # 如果没有找到关键词，使用整个查询语句切分
            if not keywords:
                keywords = [w for w in query.split() if w.strip()]
                logger.warning(f"没有提取到关键词，使用查询语句直接切分: {keywords}")
            
            logger.info(f"提取的关键词: {keywords}")
            
            # 检测查询中的竞赛类型
            detected_type = None
            if not competition_type:
                detected_type = self._detect_competition_type(query)
                if detected_type:
                    logger.info(f"检测到竞赛类型: {detected_type}")
                    competition_type = detected_type
            
            # 创建一个集合存储已处理的文档ID，避免重复
            processed_doc_ids = set()
            
            # 创建文档得分字典
            doc_scores = {}
            
            # 首先，查找与检测到的竞赛类型匹配的文档
            comp_docs = []
            if competition_type and competition_type in self.competition_docs:
                # 获取该竞赛类型下的所有文档
                comp_docs = self.competition_docs[competition_type]
                logger.info(f"找到{len(comp_docs)}个与竞赛类型'{competition_type}'相关的文档")
            
            # 优先评分竞赛类型相关文档
            for doc_id in comp_docs:
                if doc_id in processed_doc_ids:
                    continue
                
                doc = self.documents.get(doc_id)
                if not doc:
                    continue
                
                doc_text = doc.get("content", "")
                # 计算文档与查询的相似度分数
                score = self._calculate_score(query, doc_text, keywords, doc.get("competition"), competition_type)
                
                # 增加竞赛类型文档的得分
                score *= self.competition_type_boost_factor
                
                doc_scores[doc_id] = score
                processed_doc_ids.add(doc_id)
            
            # 然后，对所有关键词搜索所有文档
            for keyword in keywords:
                if keyword in self.index:
                    matching_docs = self.index[keyword]
                    for doc_id in matching_docs:
                        if doc_id in processed_doc_ids:
                            continue
                        
                        doc = self.documents.get(doc_id)
                        if not doc:
                            continue
                        
                        doc_text = doc.get("content", "")
                        # 计算相似度分数
                        score = self._calculate_score(query, doc_text, keywords, doc.get("competition"), competition_type)
                        
                        # 如果是竞赛相关文档，给予适当加分
                        doc_competition = doc.get("competition")
                        if doc_competition and competition_type and doc_competition == competition_type:
                            score *= 1.5
                        
                        doc_scores[doc_id] = score
                        processed_doc_ids.add(doc_id)
            
            # 从得分最高的文档开始，构建结果列表
            results = []
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
            
            # 使用两阶段策略：首先收集高于阈值的结果
            above_threshold = []
            for doc_id, score in sorted_docs:
                if score >= score_threshold:
                    doc = self.documents.get(doc_id).copy()  # 复制文档以避免修改原始数据
                    doc["score"] = score
                    above_threshold.append(doc)
            
            logger.info(f"找到{len(above_threshold)}个相似度大于阈值({score_threshold})的文档")
            
            # 如果高于阈值的结果数量不足，降低阈值
            if len(above_threshold) < top_n:
                logger.info(f"相似度高于阈值的文档不足{top_n}个，扩大搜索范围")
                
                # 首先，降低二分之一的阈值尝试
                relaxed_threshold = score_threshold / 2
                relaxed_results = []
                
                for doc_id, score in sorted_docs:
                    if score >= relaxed_threshold and doc_id not in [d.get("id") for d in above_threshold]:
                        doc = self.documents.get(doc_id).copy()
                        doc["score"] = score
                        relaxed_results.append(doc)
                        if len(above_threshold) + len(relaxed_results) >= top_n:
                            break
                
                logger.info(f"降低阈值至{relaxed_threshold}，额外找到{len(relaxed_results)}个文档")
                results = above_threshold + relaxed_results
                
                # 如果仍然不足，添加其他文档直到达到要求
                if len(results) < top_n and len(sorted_docs) > len(results):
                    remaining_count = top_n - len(results)
                    logger.info(f"仍需{remaining_count}个文档，将添加相似度较低的文档")
                    
                    # 从剩余的排序文档中添加
                    existing_doc_ids = set(d.get("id") for d in results)
                    for doc_id, score in sorted_docs:
                        if doc_id not in existing_doc_ids:
                            doc = self.documents.get(doc_id).copy()
                            doc["score"] = max(score, 0.01)  # 确保分数至少为正
                            results.append(doc)
                            if len(results) >= top_n:
                                break
            else:
                # 高于阈值的结果足够，直接使用
                results = above_threshold[:top_n]
            
            # 确保结果中的所有文档都有得分
            for doc in results:
                if "score" not in doc:
                    doc["score"] = 0.01  # 设置一个最低分数
            
            # 对结果进行最终排序
            results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            
            # 限制返回数量
            results = results[:top_n]
            
            # 如果结果为空，尝试返回一些随机文档作为后备
            if not results:
                logger.warning("未找到相关文档，将返回随机文档作为后备")
                import random
                all_docs = list(self.documents.keys())
                # 随机选择文档
                for _ in range(min(top_n, len(all_docs))):
                    random_doc_id = random.choice(all_docs)
                    doc = self.documents.get(random_doc_id).copy()
                    doc["score"] = 0.01  # 最低分数
                    doc["is_fallback"] = True  # 标记为后备文档
                    results.append(doc)
            
            # 确保返回列表从不为None
            if results is None:
                results = []
                logger.error("搜索结果是None，返回空列表")
            
            logger.info(f"最终返回{len(results)}个相关文档")
            return results
            
        except Exception as e:
            logger.error(f"搜索文档时出错: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 出错时返回空列表而不是抛出异常
            return []
    
    def _calculate_score(self, query: str, doc_text: str, keywords: List[str], doc_competition: str, competition_type: Optional[str]) -> float:
        """
        计算文档与查询的相关性得分
        :param query: 查询文本
        :param doc_text: 文档文本
        :param keywords: 查询关键词列表
        :param doc_competition: 文档竞赛类型
        :param competition_type: 指定竞赛类型，如果为None则搜索全部文档
        :return: 相关性得分
        """
        if not doc_text or not (keywords or query):
            return 0.0
        
        # 文本预处理
        doc_lower = doc_text.lower()
        query_lower = query.lower()
        
        total_score = 0.0
        score_details = []  # 用于记录得分明细
        
        # 1. 关键词匹配得分 - 增强版：考虑词长，位置，频率
        keyword_score = 0.0
        matched_keywords = set()
        
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in doc_lower:
                # 基础权重：考虑关键词长度（越长越重要）
                length_factor = 1.0 + min(len(kw) / 5.0, 2.0)  # 最多加权到3倍
                
                # 计算关键词在块中出现的频率
                kw_count = doc_lower.count(kw_lower)
                frequency_factor = min(1.0 + kw_count / 10.0, 2.0)  # 最多因频率加权到2倍
                
                # 关键词位置因子：在前20%的文本中出现的关键词更重要
                position_index = doc_lower.find(kw_lower)
                position_factor = 1.0
                if position_index >= 0:
                    relative_position = position_index / len(doc_lower)
                    if relative_position < 0.2:  # 在文本前20%
                        position_factor = 1.5
                    elif relative_position < 0.5:  # 在文本前50%
                        position_factor = 1.25
                
                # 竞赛术语加成
                term_bonus = 1.0
                for category, terms in self.competition_terms.items():
                    if kw in terms:
                        term_bonus = 1.5  # 竞赛术语加成50%
                        break
                
                # 综合权重
                kw_weight = self.keyword_match_base_weight * length_factor * frequency_factor * position_factor * term_bonus
                keyword_score += kw_weight
                matched_keywords.add(kw)
                
                score_details.append(f"关键词 '{kw}' (长度={len(kw)}, 频率={kw_count}, 位置因子={position_factor:.2f}, 术语加成={term_bonus:.1f}) 得分: +{kw_weight:.2f}")
        
        total_score += keyword_score
        
        # 2. 关键词覆盖率调整 - 使用更平滑的曲线
        if keywords:
            coverage = len(matched_keywords) / len(keywords)
            # 调整系数：完全覆盖时为1.5，覆盖率50%时为1.0，无覆盖时为0.5
            coverage_factor = 0.5 + 1.0 * coverage
            
            if total_score > 0:  # 只有存在基础分时才应用覆盖率
                old_score = total_score
                total_score *= coverage_factor
                score_details.append(f"关键词覆盖率: {coverage:.2f} ({len(matched_keywords)}/{len(keywords)}), "
                                   f"调整系数: {coverage_factor:.2f}, 得分调整: {old_score:.2f} -> {total_score:.2f}")
        
        # 3. 直接查询匹配奖励 - 增强版
        # 检查原始查询的各种部分是否存在于文档中
        if len(query_lower) > 2:
            # 完整查询匹配
            if query_lower in doc_lower:
                direct_match_bonus = self.direct_query_match_bonus * 2.0  # 完整匹配奖励加倍
                total_score += direct_match_bonus
                score_details.append(f"完整查询匹配奖励: +{direct_match_bonus:.2f}")
            else:
                # 查询子句匹配（按照标点和连词分割）
                query_parts = re.split(r'[,，.。;；?？!！、\s]', query_lower)
                query_parts = [p for p in query_parts if len(p) > 3]  # 只考虑长度大于3的子句
                
                for part in query_parts:
                    if part in doc_lower:
                        part_match_bonus = self.direct_query_match_bonus * (0.5 + 0.5 * len(part) / len(query_lower))
                        total_score += part_match_bonus
                        score_details.append(f"查询子句 '{part}' 匹配奖励: +{part_match_bonus:.2f}")
        
        # 4. 关键短语奖励
        for phrase, bonus in self.critical_phrases_scoring.items():
            if phrase.lower() in doc_lower:
                phrase_bonus = bonus
                if phrase.lower() in query_lower:  # 如果短语同时出现在查询和文档中
                    phrase_bonus *= 2.0  # 提高奖励
                    score_details.append(f"关键短语(同时出现) '{phrase}': +{phrase_bonus:.2f}")
                else:
                    score_details.append(f"关键短语 '{phrase}': +{phrase_bonus:.2f}")
                total_score += phrase_bonus
        
        # 5. 特定竞赛类型文档加成 - 更强的加成
        if competition_type and doc_competition:
            # 更灵活的匹配，允许部分匹配
            if (competition_type.lower() in doc_competition.lower() or 
                doc_competition.lower() in competition_type.lower() or
                query in doc_competition):
                old_score = total_score
                boost_factor = self.competition_type_boost_factor
                # 对低得分文档适用更高的加成，以保证相关文档不被漏掉
                if total_score < 0.2:
                    boost_factor *= 1.5
                
                total_score *= boost_factor
                score_details.append(f"特定竞赛类型加成: x{boost_factor:.2f}, "
                                   f"得分调整: {old_score:.2f} -> {total_score:.2f}")
        
        # 6. 段落长度调整 - 偏好中等长度的文本块
        word_count = len(doc_lower.split())
        length_factor = 1.0
        if word_count < 20:  # 太短的段落可能信息不完整
            length_factor = 0.8 + 0.2 * (word_count / 20.0)
        elif word_count > 200:  # 太长的段落可能不够聚焦
            length_factor = 1.0 - 0.2 * min((word_count - 200) / 300.0, 1.0)
        
        if length_factor != 1.0 and total_score > 0:
            old_score = total_score
            total_score *= length_factor
            score_details.append(f"段落长度调整 (词数={word_count}): x{length_factor:.2f}, "
                              f"得分调整: {old_score:.2f} -> {total_score:.2f}")
        
        # 日志记录得分详情
        log_message = f"文档得分详情: 查询='{query[:30]}...', 关键词={keywords}, " + \
                     ", ".join(score_details) + f", 最终得分: {total_score:.4f}"
        logger.debug(log_message)
        
        return total_score
    
    def rebuild_index(self) -> bool:
        """重建索引"""
        try:
            logger.info("开始重建索引...")
            start_time = time.time()
            self._build_index()
            elapsed_time = time.time() - start_time
            logger.info(f"索引重建完成，耗时 {elapsed_time:.2f}秒，包含 {len(self.documents)} 个文档片段，{len(self.index)} 个关键词")
            return True
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return False
    
    def diagnose_knowledge_base(self) -> Dict[str, Any]:
        """
        诊断知识库状态，返回统计信息
        :return: 知识库统计信息
        """
        competition_doc_counts = {}
        
        # 统计各竞赛类型文档数量
        for doc_id, doc in self.documents.items():
            comp_type = doc.get("competition", "未知竞赛")
            competition_doc_counts[comp_type] = competition_doc_counts.get(comp_type, 0) + 1
        
        # 生成诊断报告
        diagnostics = {
            "total_documents": len(self.documents),
            "total_keywords": len(self.index),
            "competition_document_counts": competition_doc_counts,
            "knowledge_base_path": self.knowledge_base_path,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "score_threshold": self.score_threshold
        }
        
        return diagnostics

    # 添加特定竞赛过滤的搜索方法
    def search_with_filter(self, query: str, filter_by_comp_type: Optional[str] = None, 
                          score_threshold: Optional[float] = None, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        执行带有竞赛类型过滤的文档搜索
        
        Args:
            query: 搜索查询
            filter_by_comp_type: 过滤的竞赛类型
            score_threshold: 相似度阈值，如果为None使用默认阈值
            max_results: 返回结果的最大数量
            
        Returns:
            相关文档列表
        """
        logger.info(f"执行过滤搜索: 查询='{query}', 竞赛类型='{filter_by_comp_type}'")
        
        try:
            # 使用默认阈值
            if score_threshold is None:
                score_threshold = self.score_threshold
            
            # 提取关键词
            keywords = self._extract_keywords(query, max_count=self.max_keywords_per_query, for_query=True)
            if not keywords:
                logger.warning(f"未能从查询中提取关键词: {query}")
                return []
            
            logger.info(f"提取的关键词: {', '.join(keywords)}")
            
            # 标识当前搜索使用了过滤
            is_filtered_search = filter_by_comp_type is not None
            
            # 收集匹配的文档ID
            doc_ids = set()
            for keyword in keywords:
                if keyword in self.index:
                    doc_ids.update(self.index[keyword])
            
            # 按竞赛类型过滤文档
            filtered_doc_ids = set()
            if is_filtered_search and filter_by_comp_type and filter_by_comp_type in self.competition_docs:
                comp_doc_ids = set(self.competition_docs[filter_by_comp_type])
                filtered_doc_ids = doc_ids.intersection(comp_doc_ids)
                logger.info(f"按竞赛类型'{filter_by_comp_type}'过滤后剩余 {len(filtered_doc_ids)} 个文档")
            else:
                filtered_doc_ids = doc_ids
                logger.info(f"未使用竞赛类型过滤，共 {len(filtered_doc_ids)} 个文档")
            
            if not filtered_doc_ids:
                logger.warning("过滤后无匹配文档")
                return []
            
            # 计算文档分数
            results = []
            for doc_id in filtered_doc_ids:
                if doc_id not in self.documents:
                    continue
                
                doc = self.documents[doc_id]
                doc_text = doc.get("content", "")
                doc_comp_type = doc.get("competition", "")
                
                # 计算相似度分数 - 更灵活的计算方法
                score = self._calculate_score(query, doc_text, keywords, doc_comp_type, filter_by_comp_type)
                
                # 应用阈值过滤
                if score >= score_threshold:
                    result = {
                        "content": doc_text,
                        "source": doc.get("source", "未知来源"),
                        "competition_type": doc_comp_type,
                        "score": score,
                        "id": doc_id
                    }
                    results.append(result)
            
            # 按分数排序
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # 限制结果数量
            results = results[:max_results]
            
            logger.info(f"过滤搜索返回 {len(results)} 个结果，最高分数: {results[0]['score'] if results else 0}")
            
            return results
        except Exception as e:
            logger.error(f"过滤搜索时出错: {str(e)}", exc_info=True)
            return [] 