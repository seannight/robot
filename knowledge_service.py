"""
竞赛智能客服系统 - 知识服务模块
负责文档索引、检索和相关度计算
"""
import os
import logging
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import math
import shutil

# 配置日志
logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识服务：管理各类竞赛文档的索引和检索"""
    
    def __init__(self, knowledge_base_path: str = "data/knowledge/docs/附件1"):
        """
        初始化知识服务
        
        Args:
            knowledge_base_path: 知识库路径
        """
        self.knowledge_base_path = Path(knowledge_base_path)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"知识服务初始化，知识库路径: {self.knowledge_base_path}")
        
        # 存储结构
        self.documents = {}  # 文档内容
        self.paragraphs = {}  # 段落内容
        self.index = {}  # 倒排索引
        self.idf_values = {}  # 词频-逆文档频率值
        
        # 加载或创建索引
        self._load_or_create_index()
        
        # 各类竞赛关键词和专有名词
        self.competition_keywords = {
            # 竞赛类型
            "人工智能创新挑战赛", "3D编程模型创新设计专项赛", "机器人工程挑战赛",
            "极地资源勘探设计大赛", "竞技机器人专项赛", "开源鸿蒙专项赛", 
            "人工智能综合创新专项赛", "三维程序创意设计大赛", "生成式人工智能应用专项赛",
            "太空电梯设计专项赛", "太空探索智能机器人大赛", "虚拟仿真平台创新设计专项赛",
            "智能数据采集与处理专项赛", "智能芯片创新设计大赛", "计算思维与人工智能专项赛",
            "未来校园智能应用专项赛",
            
            # 通用竞赛术语
            "竞赛规则", "评分标准", "报名", "参赛", "奖项设置", 
            "截止日期", "参赛资格", "获奖", "评审", "赛题", 
            "数据集", "提交", "作品", "大赛", "初赛", "复赛", "决赛",
            "答辩", "开幕式", "闭幕式", "颁奖", "作品提交", "结果公布",
            
            # 竞赛要素
            "参赛条件", "参赛要求", "参赛流程", "报名方式", "报名费用",
            "报名时间", "比赛时间", "提交要求", "提交方式", "提交时间",
            "评审方式", "评审标准",
            
            # 竞赛内容
            "题目", "任务", "要求", "目标", "创新点", "技术路线",
            "解决方案", "实现方法", "评价指标", "验收标准",
            
            # 参赛作品
            "论文", "代码", "设计", "模型", "方案", "报告", "演示",
            "展示", "答辩", "PPT", "视频", "海报"
        }
        
    def _load_or_create_index(self):
        """加载或创建知识库索引"""
        index_file = Path("data/knowledge/index.json")
        documents_file = Path("data/knowledge/documents.json")
        paragraphs_file = Path("data/knowledge/paragraphs.json")
        
        if index_file.exists() and documents_file.exists() and paragraphs_file.exists():
            try:
                # 加载现有索引
                with open(index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
                with open(documents_file, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                with open(paragraphs_file, 'r', encoding='utf-8') as f:
                    self.paragraphs = json.load(f)
                
                # 加载IDF值
                idf_file = Path("data/knowledge/idf_values.json")
                if idf_file.exists():
                    with open(idf_file, 'r', encoding='utf-8') as f:
                        self.idf_values = json.load(f)
                
                self.logger.info(f"已加载知识库索引，包含{len(self.documents)}个文档和{len(self.paragraphs)}个段落")
                return
            except Exception as e:
                self.logger.error(f"加载索引失败: {e}")
        
        # 创建新索引
        self.logger.info("正在创建新的知识库索引...")
        self._create_index()
        self._save_index()
        self.logger.info("知识库索引创建完成")
    
    def _create_index(self):
        """创建知识库索引"""
        if not self.knowledge_base_path.exists():
            self.logger.error(f"知识库路径不存在: {self.knowledge_base_path}")
            return
        
        # 读取所有文档
        doc_id = 0
        paragraph_id = 0
        term_document_count = {}  # 记录每个词出现在几个文档中
        
        # 遍历所有文档
        for file_path in self.knowledge_base_path.glob("**/*.*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.pdf', '.docx', '.md']:
                try:
                    doc_id += 1
                    doc_key = f"doc_{doc_id}"
                    self.documents[doc_key] = {
                        "path": str(file_path),
                        "title": file_path.stem,
                        "paragraphs": []
                    }
                    
                    # 读取文档内容
                    content = self._read_document(file_path)
                    if not content:
                        continue
                    
                    # 分段处理
                    paragraphs = self._split_paragraphs(content)
                    
                    # 文档使用的所有术语
                    doc_terms = set()
                    
                    for para_text in paragraphs:
                        if len(para_text.strip()) < 10:  # 忽略太短的段落
                            continue
                            
                        paragraph_id += 1
                        para_key = f"para_{paragraph_id}"
                        
                        # 保存段落
                        self.paragraphs[para_key] = {
                            "doc_id": doc_key,
                            "text": para_text,
                            "terms": {}  # 词频统计
                        }
                        self.documents[doc_key]["paragraphs"].append(para_key)
                        
                        # 分词和索引
                        terms = self._tokenize(para_text)
                        term_freq = {}  # 词频统计
                        
                        for term in terms:
                            term_freq[term] = term_freq.get(term, 0) + 1
                            doc_terms.add(term)
                            
                            # 更新倒排索引
                            if term not in self.index:
                                self.index[term] = []
                            if para_key not in [item[0] for item in self.index[term]]:
                                self.index[term].append((para_key, term_freq.get(term, 1)))
                        
                        # 保存段落中的词频
                        self.paragraphs[para_key]["terms"] = term_freq
                    
                    # 更新文档频率统计
                    for term in doc_terms:
                        term_document_count[term] = term_document_count.get(term, 0) + 1
                    
                except Exception as e:
                    self.logger.error(f"处理文档时出错 {file_path}: {e}")
        
        # 计算IDF值
        total_docs = max(len(self.documents), 1)
        self.idf_values = {}
        for term, doc_count in term_document_count.items():
            self.idf_values[term] = math.log(total_docs / (1 + doc_count))
    
    def _read_document(self, file_path: Path) -> str:
        """读取文档内容"""
        try:
            # 根据文件类型不同，使用不同的读取方法
            if file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif file_path.suffix.lower() == '.pdf':
                try:
                    import fitz  # PyMuPDF
                    
                    # 打开PDF文件
                    doc = fitz.open(file_path)
                    
                    # 提取所有页面的文本
                    content = ""
                    for page in doc:
                        content += page.get_text()
                    
                    return content
                except ImportError:
                    self.logger.error("未安装PyMuPDF库，无法处理PDF文件")
                    return f"需要安装PyMuPDF库以处理PDF文件: {file_path.name}"
            else:
                return f"未处理的文件类型 {file_path.suffix}"
        except Exception as e:
            self.logger.error(f"读取文档时出错 {file_path}: {e}")
            return ""
    
    def _tokenize(self, text: str) -> List[str]:
        """
        将文本分词
        
        Args:
            text: 输入文本
            
        Returns:
            分词结果列表
        """
        # 移除标点符号
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 分词（简单按空格分割）
        words = text.split()
        
        # 移除停用词和过短的词
        stop_words = {'的', '了', '和', '是', '在', '有', '与', '及', '或', '等', '中', '为', '以', '对', '将'}
        words = [w for w in words if w not in stop_words and len(w) > 1]
        
        return words
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """
        将文本分段
        
        Args:
            text: 输入文本
            
        Returns:
            段落列表
        """
        # 按换行符分段
        paragraphs = text.split('\n')
        
        # 清理和合并段落
        cleaned_paragraphs = []
        current_paragraph = ""
        
        for p in paragraphs:
            p = p.strip()
            if not p:  # 空行
                if current_paragraph:
                    cleaned_paragraphs.append(current_paragraph)
                    current_paragraph = ""
            else:
                if current_paragraph:
                    current_paragraph += " "
                current_paragraph += p
        
        # 添加最后一个段落
        if current_paragraph:
            cleaned_paragraphs.append(current_paragraph)
        
        return cleaned_paragraphs
    
    def _save_index(self):
        """保存索引到文件"""
        try:
            # 确保目录存在
            os.makedirs("data/knowledge", exist_ok=True)
            
            # 保存索引
            with open("data/knowledge/index.json", 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
            
            # 保存文档信息
            with open("data/knowledge/documents.json", 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, indent=2)
            
            # 保存段落信息
            with open("data/knowledge/paragraphs.json", 'w', encoding='utf-8') as f:
                json.dump(self.paragraphs, f, ensure_ascii=False, indent=2)
            
            # 保存IDF值
            with open("data/knowledge/idf_values.json", 'w', encoding='utf-8') as f:
                json.dump(self.idf_values, f, ensure_ascii=False, indent=2)
            
            self.logger.info("索引保存成功")
        except Exception as e:
            self.logger.error(f"保存索引失败: {e}")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相关段落
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            相关段落列表
        """
        # 分词
        query_terms = self._tokenize(query)
        
        # 计算每个段落的得分
        scores = {}
        for term in query_terms:
            if term in self.index:
                idf = self.idf_values.get(term, 0.1)
                for para_key, term_freq in self.index[term]:
                    if para_key not in scores:
                        scores[para_key] = 0
                    # TF-IDF得分
                    scores[para_key] += term_freq * idf
        
        # 排序并返回结果
        results = []
        for para_key, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]:
            para_info = self.paragraphs[para_key]
            doc_info = self.documents[para_info["doc_id"]]
            
            results.append({
                "text": para_info["text"],
                "score": score,
                "doc_title": doc_info["title"],
                "doc_path": doc_info["path"]
            })
        
        return results
    
    def get_answer(self, query: str) -> Dict[str, Any]:
        """
        获取问题的答案
        
        Args:
            query: 用户问题
            
        Returns:
            答案信息
        """
        # 搜索相关段落
        results = self.search(query, top_k=3)
        
        if not results:
            return {
                "answer": "抱歉，我没有找到相关的信息。",
                "confidence": 0.0,
                "source": "未找到"
            }
        
        # 获取最相关的段落
        best_match = results[0]
        confidence = min(0.9, best_match["score"] / 10)  # 将得分映射到0-0.9范围
        
        # 如果得分太低，返回未找到
        if confidence < 0.3:
            return {
                "answer": "抱歉，我没有找到足够相关的信息。",
                "confidence": confidence,
                "source": "相关度低"
            }
        
        # 根据问题类型生成答案
        answer = best_match["text"]
        
        # 如果有多个相关段落，可能需要组合答案
        if len(results) > 1 and results[1]["score"] > best_match["score"] * 0.8:
            answer += f"\n\n此外：\n{results[1]['text']}"
        
        return {
            "answer": answer,
            "confidence": confidence,
            "source": f"来自 {best_match['doc_title']}"
        }
    
    def is_in_scope(self, query: str) -> bool:
        """
        检查问题是否在范围内
        
        Args:
            query: 用户问题
            
        Returns:
            是否在范围内
        """
        # 检查是否包含竞赛关键词
        query_terms = self._tokenize(query)
        for term in query_terms:
            if term in self.competition_keywords:
                return True
        
        # 如果问题很短，可能是跟进问题
        if len(query) < 15:
            return True
        
        # 搜索相关段落
        results = self.search(query, top_k=1)
        if results and results[0]["score"] > 0.5:
            return True
        
        return False
    
    def process_pdf(self, pdf_path: str):
        """
        处理PDF文档并更新知识库
        
        Args:
            pdf_path: PDF文件路径
        """
        try:
            # 将PDF转换为文本
            import fitz
            
            # 打开PDF文件
            doc = fitz.open(pdf_path)
            
            # 创建txt目录
            txt_dir = Path("data/knowledge/txt")
            os.makedirs(txt_dir, exist_ok=True)
            
            # 提取文本并保存
            txt_path = txt_dir / f"{Path(pdf_path).stem}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                for page in doc:
                    text = page.get_text()
                    f.write(text)
            
            # 更新索引
            self._create_index()
            self._save_index()
            
            self.logger.info(f"PDF处理完成: {pdf_path}")
            
        except Exception as e:
            self.logger.error(f"处理PDF时出错: {e}")
    
    def update_knowledge_base(self, new_docs_path: str):
        """
        更新知识库
        
        Args:
            new_docs_path: 新文档路径
        """
        try:
            # 备份当前知识库
            backup_path = Path("data/knowledge/backup")
            os.makedirs(backup_path, exist_ok=True)
            
            # 复制现有文件到备份目录
            for file in Path("data/knowledge").glob("*.json"):
                shutil.copy2(file, backup_path)
            
            # 更新知识库路径
            self.knowledge_base_path = Path(new_docs_path)
            
            # 重新创建索引
            self._create_index()
            self._save_index()
            
            self.logger.info(f"知识库更新完成: {new_docs_path}")
            
        except Exception as e:
            self.logger.error(f"更新知识库时出错: {e}")
            # 恢复备份
            for file in backup_path.glob("*.json"):
                shutil.copy2(file, "data/knowledge") 