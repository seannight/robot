"""
竞赛智能客服系统 - 响应格式化工具
确保所有API和WebSocket响应格式一致
"""

import time
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

def standardize_response(result: Union[Dict[str, Any], str, None], 
                         session_id: Optional[str] = None,
                         start_time: Optional[float] = None) -> Dict[str, Any]:
    """
    标准化响应格式，确保所有输出格式一致
    
    Args:
        result: 原始响应，可能是字典、字符串或None
        session_id: 会话ID
        start_time: 处理开始时间，用于计算处理耗时
        
    Returns:
        标准化的响应字典
    """
    # 计算处理时间
    processing_time = 0
    if start_time:
        processing_time = time.time() - start_time
    
    # 处理None结果
    if result is None:
        logger.warning("收到空响应，转换为标准格式")
        return {
            "answer": "无法回答此问题",
            "confidence": 0.0,
            "has_answer": False,
            "processing_time": processing_time,
            "timestamp": time.time(),
            "session_id": session_id or f"session_{int(time.time())}"
        }
    
    # 处理字符串结果
    if isinstance(result, str):
        logger.info("将字符串响应转换为标准格式")
        return {
            "answer": result,
            "confidence": 0.5,  # 默认中等置信度
            "has_answer": bool(result.strip()),
            "processing_time": processing_time,
            "timestamp": time.time(),
            "session_id": session_id or f"session_{int(time.time())}"
        }
    
    # 处理字典结果，确保包含所有需要的字段
    if isinstance(result, dict):
        # 确保关键字段存在
        if "answer" not in result:
            # 尝试从response字段获取答案
            if "response" in result:
                result["answer"] = result["response"]
            else:
                result["answer"] = "无法回答此问题"
                logger.warning("响应字典缺少answer字段，已添加默认值")
        
        # 添加其他必要字段
        if "confidence" not in result:
            result["confidence"] = 0.5
        
        if "has_answer" not in result:
            result["has_answer"] = bool(result["answer"].strip())
        
        if "processing_time" not in result and start_time:
            result["processing_time"] = processing_time
        
        if "timestamp" not in result:
            result["timestamp"] = time.time()
        
        if "session_id" not in result and session_id:
            result["session_id"] = session_id
        elif "session_id" not in result:
            result["session_id"] = f"session_{int(time.time())}"
        
        return result
    
    # 处理其他类型的结果
    logger.warning(f"收到非预期类型的响应: {type(result)}")
    return {
        "answer": str(result),
        "confidence": 0.3,
        "has_answer": True,
        "processing_time": processing_time,
        "timestamp": time.time(),
        "session_id": session_id or f"session_{int(time.time())}"
    }

def format_error_response(error: Exception, 
                          session_id: Optional[str] = None,
                          start_time: Optional[float] = None) -> Dict[str, Any]:
    """
    格式化错误响应
    
    Args:
        error: 异常对象
        session_id: 会话ID
        start_time: 处理开始时间
        
    Returns:
        标准化的错误响应
    """
    processing_time = 0
    if start_time:
        processing_time = time.time() - start_time
    
    error_message = str(error)
    
    # 对常见错误类型进行用户友好的提示
    user_friendly_message = "抱歉，处理您的问题时出现错误，请稍后再试。"
    
    if "timeout" in error_message.lower():
        user_friendly_message = "处理您的问题时间过长，请尝试简化问题或稍后再试。"
    elif "connection" in error_message.lower():
        user_friendly_message = "系统连接出现问题，请刷新页面后再试。"
    elif "memory" in error_message.lower():
        user_friendly_message = "系统资源不足，请稍后再试。"
    
    return {
        "answer": user_friendly_message,
        "error": error_message,
        "confidence": 0.0,
        "has_answer": False,
        "is_error": True,
        "processing_time": processing_time,
        "timestamp": time.time(),
        "session_id": session_id or f"session_{int(time.time())}"
    } 