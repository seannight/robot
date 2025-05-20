"""
竞赛智能客服系统 - MCP上下文模块
使用模型上下文协议(MCP)与提供的上下文一起回答用户问题
"""

import os
import logging
import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple

from app.models.mcp_engine import generate_response
from app.config import settings

logger = logging.getLogger(__name__)

class MCPWithContext:
    """使用上下文增强的MCP模型"""
    
    def __init__(self):
        """初始化MCP上下文模型"""
        # 配置参数
        self.model = settings.LLM_MODEL
        self.api_key = settings.DASHSCOPE_API_KEY
        
        # 检查API密钥
        if not self.api_key:
            logger.warning("未设置DASHSCOPE_API_KEY环境变量，MCP功能可能无法正常工作")
        
        # 提示模版
        self.prompt_template = """你是一个专业的竞赛智能客服，负责回答用户关于各类竞赛的问题。
你的回答必须基于提供的上下文信息，不要使用你自己的知识。

提供的上下文信息如下:
{context}

用户问题: {question}

请根据上述上下文，简明扼要地回答用户问题。如果上下文中没有足够的相关信息，请直接回复"无法回答"，不要编造答案。"""

    async def query(self, question: str, context: Union[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        使用给定上下文回答用户问题
        
        Args:
            question: 用户问题
            context: 上下文文本或文档列表
        
        Returns:
            包含回答和元数据的字典
        """
        start_time = time.time()
        logger.info(f"MCPWithContext接收问题: {question}")
        
        try:
            # 处理上下文
            if isinstance(context, list):
                # 如果是文档列表，提取内容
                context_texts = []
                for doc in context:
                    if isinstance(doc, dict) and "content" in doc:
                        context_texts.append(doc["content"])
                context_text = "\n\n".join(context_texts)
            else:
                # 直接使用上下文文本
                context_text = context
            
            # 记录上下文长度
            logger.info(f"上下文长度: {len(context_text)} 字符")
            
            # 构建提示
            prompt = self.prompt_template.format(
                context=context_text,
                question=question
            )
            
            # 调用模型生成回答
            raw_response = await generate_response(
                prompt=prompt,
                model=self.model,
                api_key=self.api_key
            )
            
            # 记录原始响应
            logger.info(f"模型原始响应: {raw_response[:100]}...")
            
            # 预处理回答（去除引号、多余空格等）
            answer = raw_response.strip().strip('"\'')
            
            # 计算置信度 - 基于回答长度和质量
            confidence = self._calculate_confidence(answer)
            
            # 检查是否无法回答
            has_answer = True
            if "无法回答" in answer or "抱歉" in answer:
                confidence = min(confidence, 0.3)  # 降低置信度
                has_answer = False
            
            # 记录处理时间
            processing_time = time.time() - start_time
            logger.info(f"MCP处理完成，耗时: {processing_time:.2f}秒，置信度: {confidence:.2f}")
            
            # 返回标准格式响应
            response = {
                "answer": answer,
                "confidence": confidence,
                "processing_time": processing_time,
                "has_answer": has_answer,
                "timestamp": time.time()
            }
            
            # 确保返回字典
            return response
            
        except Exception as e:
            logger.error(f"MCPWithContext处理过程中出错: {str(e)}", exc_info=True)
            
            # 发生错误时，返回标准格式的错误响应
            processing_time = time.time() - start_time
            return {
                "answer": f"抱歉，系统暂时无法处理您的问题: {str(e)}",
                "confidence": 0.1,
                "processing_time": processing_time,
                "has_answer": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _calculate_confidence(self, answer: str) -> float:
        """
        计算回答的置信度
        
        Args:
            answer: 回答文本
        
        Returns:
            置信度分数(0.0-1.0)
        """
        # 基于回答长度的基础置信度
        if len(answer) < 10:
            base_confidence = 0.2
        elif len(answer) < 50:
            base_confidence = 0.6
        else:
            base_confidence = 0.8
        
        # 降低含有犹豫词语的回答的置信度
        uncertainty_words = ["可能", "或许", "也许", "不确定", "不清楚", "猜测"]
        for word in uncertainty_words:
            if word in answer:
                base_confidence *= 0.8  # 降低20%
        
        # 如果回答中包含"无法回答"等词语，大幅降低置信度
        rejection_words = ["无法", "抱歉", "找不到", "没有相关", "不知道"]
        for word in rejection_words:
            if word in answer:
                base_confidence *= 0.4  # 降低60%
        
        return round(min(base_confidence, 1.0), 2)  # 确保置信度不超过1.0 