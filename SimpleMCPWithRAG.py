"""
竞赛智能客服系统 - 极简化版MCP+RAG引擎
简化架构，确保响应格式一致性
"""

import logging
import time
import random
import json
from typing import Dict, List, Any, Optional

from app.models.MCPWithContext import MCPWithContext
from app.models.SimpleRAG import SimpleRAG
from app.models.RAGAdapter import RAGAdapter
from app.config import settings

# 导入问题增强工具
from app.utils.question_enhancer import is_low_quality_answer, generate_backup_answer

logger = logging.getLogger(__name__)

class SimpleMCPWithRAG:
    """极简化版MCP+RAG引擎"""
    
    def __init__(self):
        """初始化简化版MCP+RAG引擎"""
        self.mcp = MCPWithContext()
        # 使用RAGAdapter适配SimpleRAG，避免接口不一致问题
        self.rag = RAGAdapter(SimpleRAG(rebuild_index=False))
        logger.info("极简化版MCP+RAG引擎初始化完成")
        
    async def query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户问题并返回回答
        
        Args:
            question: 用户问题
            session_id: 会话ID
        
        Returns:
            包含回答和元数据的字典
        """
        start_time = time.time()
        logger.info(f"SimpleMCPWithRAG接收问题: {question}")
        
        try:
            # 记录原始问题，用于错误处理和分析
            original_question = question
            
            # 1. 直接搜索文档 - 通过适配器调用
            docs = await self.rag.search(question)
            
            # 构建标准响应格式
            response = {
                "answer": "",
                "confidence": 0.0,
                "sources": [],
                "has_answer": False,
                "competition_type": "未知竞赛",
                "processing_time": 0,
                "timestamp": time.time(),
                "session_id": session_id or f"session_{int(time.time())}"
            }
            
            # 如果没有文档，直接返回无法回答
            if not docs or len(docs) == 0:
                logger.warning(f"未找到与问题相关的文档: {question}")
                
                # 尝试生成备用回答
                backup_answer = await generate_backup_answer(question)
                
                response["answer"] = backup_answer
                response["confidence"] = 0.4  # 低置信度
                response["has_answer"] = True  # 依然返回了答案
                response["is_backup"] = True
                response["processing_time"] = time.time() - start_time
                
                return response
            
            # 2. 处理文档
            sources = []
            contexts = []
            for doc in docs:
                content = doc.get("content", "")
                source = doc.get("source", "未知来源")
                score = doc.get("score", 0)
                
                if not content:
                    continue
                    
                # 添加到上下文
                contexts.append(content)
                
                # 添加到来源 - 只包含部分文本
                if len(content) > 100:
                    text_preview = content[:100] + "..."
                else:
                    text_preview = content
                    
                sources.append({
                    "text": text_preview,
                    "source": source,
                    "score": round(score, 4)
                })
            
            # 获取竞赛类型（从第一个文档）
            competition_type = "未知竞赛"
            if docs and len(docs) > 0 and "competition_type" in docs[0]:
                competition_type = docs[0].get("competition_type", "未知竞赛")
            
            logger.info(f"读取到{len(contexts)}段上下文，竞赛类型: {competition_type}")
            
            # 3. 使用MCP生成回答
            if contexts:
                # 限制上下文总长度，防止过长
                full_context = "\n\n".join(contexts)
                if len(full_context) > 6000:  # 适当限制上下文长度
                    full_context = full_context[:6000] + "..."
                
                # 调用MCP生成回答
                mcp_response = await self.mcp.query(question, full_context)
                
                # 提取回答和置信度
                if isinstance(mcp_response, dict):
                    answer = mcp_response.get("answer", "")
                    confidence = mcp_response.get("confidence", 0.0)
                else:
                    # 处理可能返回元组的情况
                    logger.warning(f"MCP返回了非预期格式: {type(mcp_response)}")
                    answer = str(mcp_response) if mcp_response else ""
                    confidence = 0.5  # 默认中等置信度
                
                # 检查回答质量
                if is_low_quality_answer(answer):
                    logger.warning(f"检测到MCP生成的低质量回答: [{answer}]")
                    
                    # 尝试生成备用回答
                    backup_answer = await generate_backup_answer(question)
                    
                    logger.info(f"使用备用回答: [{backup_answer}]")
                    answer = backup_answer
                    confidence = 0.5  # 中等置信度
                    
                response["answer"] = answer
                response["confidence"] = confidence
                response["sources"] = sources
                response["has_answer"] = bool(answer.strip())
                response["competition_type"] = competition_type
            else:
                # 没有有效上下文内容
                logger.warning("没有有效的上下文内容")
                
                # 生成备用回答
                backup_answer = await generate_backup_answer(question)
                
                response["answer"] = backup_answer
                response["confidence"] = 0.4
                response["has_answer"] = True
                response["is_backup"] = True
            
            # 计算处理时间
            response["processing_time"] = time.time() - start_time
            
            logger.info(f"回答生成完成，置信度: {response['confidence']:.2f}, 耗时: {response['processing_time']:.2f}秒")
            
            return response
            
        except Exception as e:
            logger.error(f"SimpleMCPWithRAG查询过程中出错: {str(e)}", exc_info=True)
            
            # 发生错误时，返回标准格式的错误响应
            processing_time = time.time() - start_time
            
            # 尝试生成备用回答
            backup_answer = "抱歉，系统暂时无法回答您的问题，请尝试换一种方式提问。"
            try:
                # 尝试调用备用回答生成器
                backup_answer = await generate_backup_answer(question)
            except:
                # 如果备用生成器也失败，使用默认回答
                pass
                
            return {
                "answer": backup_answer,
                "confidence": 0.3,
                "sources": [],
                "has_answer": True,
                "competition_type": "未知竞赛",
                "processing_time": processing_time,
                "timestamp": time.time(),
                "session_id": session_id or f"session_{int(time.time())}",
                "is_error_response": True,
                "error_message": str(e)
            }
    
    async def route_query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        统一的查询路由方法，提供标准化响应
        
        Args:
            question: 用户问题
            session_id: 会话ID
            
        Returns:
            标准化响应字典
        """
        try:
            # 调用查询方法处理问题
            result = await self.query(question, session_id)
            
            # 确保结果是字典类型
            if not isinstance(result, dict):
                logger.warning(f"查询结果不是字典类型: {type(result)}")
                result = {
                    "answer": str(result) if result else "无法回答此问题",
                    "confidence": 0.3
                }
            
            # 确保关键字段存在
            if "answer" not in result:
                result["answer"] = result.get("response", "无法回答此问题")
            
            if "confidence" not in result:
                result["confidence"] = 0.5
            
            # 添加时间戳和会话ID
            result["timestamp"] = time.time()
            result["session_id"] = session_id or f"session_{int(time.time())}"
            
            return result
            
        except Exception as e:
            logger.error(f"路由查询出错: {str(e)}", exc_info=True)
            
            # 返回错误响应
            return {
                "answer": f"处理问题时出错: {str(e)}",
                "confidence": 0.0,
                "error": str(e),
                "timestamp": time.time(),
                "session_id": session_id or f"session_{int(time.time())}"
            }
            
    async def diagnose(self) -> Dict[str, Any]:
        """系统诊断"""
        try:
            # 获取RAG诊断信息
            rag_info = await self.rag.diagnose()
            
            return {
                "system_status": "运行中",
                "engine_type": "SimpleMCPWithRAG",
                "mcp_engine": "MCPWithContext",
                "rag_engine": rag_info.get("implementation", "RAGAdapter"),
                "model": settings.LLM_MODEL,
                "rag_status": rag_info,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"诊断失败: {str(e)}")
            return {"system_status": "错误", "error": str(e)} 