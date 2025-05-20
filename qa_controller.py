"""
竞赛智能客服系统 - 问答控制器
处理用户问题和系统回答
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
import uuid
import time

from ..services.knowledge.knowledge_service import KnowledgeService
from ..models.mcp_engine import MCPEngine, QueryContext
from ..models.RAG_LLM import RAGLLMKnowledgeBase
from ..config import settings

# 配置日志
logger = logging.getLogger(__name__)

class QAController:
    """问答控制器：处理用户问题和获取答案"""
    
    def __init__(self, 
                 knowledge_service: Optional[KnowledgeService] = None, 
                 mcp_engine: Optional[MCPEngine] = None,
                 rag_llm: Optional[RAGLLMKnowledgeBase] = None):
        """
        初始化问答控制器
        
        Args:
            knowledge_service: 知识服务实例
            mcp_engine: MCP引擎实例
            rag_llm: RAG知识库实例
        """
        self.logger = logging.getLogger(__name__)
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.mcp_engine = mcp_engine or MCPEngine()
        self.rag_llm = rag_llm
        
        # 会话管理
        self.sessions = {}  # 存储会话信息
        self.logger.info("问答控制器初始化完成")
    
    def create_session(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        创建新会话
        
        Args:
            user_id: 用户ID（可选）
            
        Returns:
            会话信息
        """
        session_id = str(uuid.uuid4())
        
        # 创建会话
        self.sessions[session_id] = {
            "id": session_id,
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "history": []
        }
        
        # 创建对应的查询上下文
        query_context = QueryContext(session_id, user_id)
        
        self.logger.info(f"创建新会话: {session_id}")
        return {
            "session_id": session_id,
            "created_at": self.sessions[session_id]["created_at"]
        }
    
    def process_question(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户问题
        
        Args:
            question: 用户问题
            session_id: 会话ID
            
        Returns:
            包含答案的响应
        """
        start_time = time.time()
        
        # 获取或创建会话
        if not session_id or session_id not in self.sessions:
            session_info = self.create_session()
            session_id = session_info["session_id"]
        
        try:
            # 更新会话活动时间
            self.sessions[session_id]["last_activity"] = time.time()
            
            # 记录问题
            self.sessions[session_id]["history"].append({
                "role": "user",
                "content": question,
                "timestamp": time.time()
            })
            
            # 步骤1: 检查问题是否在范围内
            in_scope = True
            # 只有明显不相关的话题才拒绝
            irrelevant_topics = ["天气", "股票", "游戏", "电影", "音乐", "旅游", "美食", "体育", "购物", "医疗", "政治"]
            if any(topic in question for topic in irrelevant_topics) and not self.knowledge_service.is_in_scope(question):
                in_scope = False
                
            if not in_scope:
                answer = "抱歉，您的问题似乎超出了竞赛的范围。我只能回答与各类竞赛相关的问题。"
                response = self._create_response(session_id, question, answer, 
                                               confidence=0.0, 
                                               source="范围检查",
                                               processing_time=time.time() - start_time)
                return response
            
            # 步骤2: 如果启用了RAG，优先使用RAG
            if settings.RAG_ENABLED and self.rag_llm:
                try:
                    # 获取会话历史
                    history = self.get_session_history(session_id)
                    # 使用RAG生成答案
                    answer, confidence = self.rag_llm.query(question, history)
                    
                    if confidence >= settings.RAG_CONFIDENCE_THRESHOLD:
                        response = self._create_response(session_id, question, answer,
                                                       confidence=confidence,
                                                       source="RAG",
                                                       processing_time=time.time() - start_time)
                        # 记录回答
                        self.sessions[session_id]["history"].append({
                            "role": "assistant",
                            "content": answer,
                            "timestamp": time.time()
                        })
                        return response
                except Exception as e:
                    self.logger.error(f"RAG处理失败: {e}")
            
            # 步骤3: 使用MCP引擎处理问题
            answer = self.mcp_engine.process_question(question)
            source = "MCP引擎"
            confidence = 0.8
            
            # 步骤4: 如果MCP引擎没有明确答案，使用知识服务查找
            if "抱歉" in answer and "未找到" in answer:
                knowledge_result = self.knowledge_service.get_answer(question)
                
                if knowledge_result["confidence"] > 0.4:  # 降低阈值
                    answer = knowledge_result["answer"]
                    confidence = knowledge_result["confidence"]
                    source = knowledge_result["source"]
                # 尝试智能组合回答处理开放性问题
                elif self._is_open_question(question):
                    partial_results = self.knowledge_service.search(question, top_k=5)
                    if partial_results and len(partial_results) >= 1:  # 只需要一个相关结果就可尝试回答
                        # 组合多个部分答案形成完整回答
                        combined_answer = self._generate_composite_answer(question, partial_results)
                        if combined_answer:
                            answer = combined_answer
                            confidence = 0.6  # 提高信心度
                            source = "组合知识"
                else:
                    confidence = 0.3
            
            # 创建响应
            response = self._create_response(session_id, question, answer, 
                                           confidence=confidence, 
                                           source=source,
                                           processing_time=time.time() - start_time)
            
            # 记录回答
            self.sessions[session_id]["history"].append({
                "role": "assistant",
                "content": answer,
                "timestamp": time.time()
            })
            
            return response
            
        except Exception as e:
            self.logger.error(f"处理问题时出错: {e}")
            return {
                "session_id": session_id,
                "question": question,
                "answer": "抱歉，系统处理您的问题时出现了错误，请稍后再试。",
                "confidence": 0,
                "source": "错误处理",
                "processing_time": time.time() - start_time
            }
    
    def _is_open_question(self, question: str) -> bool:
        """判断是否为开放性问题"""
        # 开放性问题通常以这些词开头或包含这些词
        open_question_starters = [
            "为什么", "如何", "怎样", "怎么", "什么方法", 
            "哪些方式", "如果", "能否", "是否可以", "可不可以",
            "应该", "建议", "有什么", "有哪些", "需要"
        ]
        
        for starter in open_question_starters:
            if starter in question:
                return True
                
        # 包含比较和分析的问题
        if any(term in question for term in ["比较", "区别", "差异", "优缺点", "利弊", "建议", "推荐", "困难", "挑战", "问题"]):
            return True
            
        # 如果是简短的疑问句，也视为开放性问题
        if len(question) < 15 and question.endswith("?") or question.endswith("？"):
            return True
            
        # 如果问题包含"我"或"你"等人称代词，可能是个性化问题
        if any(term in question for term in ["我", "你", "他", "她", "我们", "学生", "参赛者", "选手"]):
            return True
            
        return False
    
    def _generate_composite_answer(self, question: str, results: List[Dict[str, Any]]) -> Optional[str]:
        """根据多个搜索结果生成组合答案"""
        try:
            # 提取关键段落
            key_paragraphs = []
            for result in results:
                if result["score"] > 0.1:  # 降低相关度阈值，接受更多的相关段落
                    # 提取前150个字符，但尝试保持语句完整
                    text = result["text"][:200]
                    # 如果句子被截断，尝试在句号处截断
                    last_period = text.rfind("。")
                    if last_period > 100:  # 确保至少保留一定长度
                        text = text[:last_period+1]
                    key_paragraphs.append(text)
            
            if not key_paragraphs:
                return None
            
            # 根据问题类型生成不同的答案模板
            if "如何" in question or "怎样" in question:
                answer = f"您可以这样做：\n"
                for i, para in enumerate(key_paragraphs, 1):
                    answer += f"{i}. {para}\n"
            elif "为什么" in question:
                answer = f"这是因为：\n{key_paragraphs[0]}"
                if len(key_paragraphs) > 1:
                    answer += f"\n\n此外：\n{key_paragraphs[1]}"
            elif "有什么" in question or "有哪些" in question:
                answer = "主要包括以下几个方面：\n"
                for i, para in enumerate(key_paragraphs, 1):
                    answer += f"{i}. {para}\n"
            else:
                # 默认模板
                answer = key_paragraphs[0]
                if len(key_paragraphs) > 1:
                    answer += f"\n\n补充说明：\n{key_paragraphs[1]}"
            
            return answer
            
        except Exception as e:
            self.logger.error(f"生成组合答案时出错: {e}")
            return None
    
    def _create_response(self, session_id: str, question: str, answer: str, **kwargs) -> Dict[str, Any]:
        """创建标准响应格式"""
        return {
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "confidence": kwargs.get("confidence", 0.0),
            "source": kwargs.get("source", "未知"),
            "processing_time": kwargs.get("processing_time", 0.0)
        }
    
    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话ID
            limit: 返回的最大记录数
            
        Returns:
            历史记录列表
        """
        if session_id not in self.sessions:
            return []
            
        history = self.sessions[session_id]["history"]
        return history[-limit:] if limit > 0 else history
    
    def clear_session(self, session_id: str) -> bool:
        """
        清除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功清除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False 