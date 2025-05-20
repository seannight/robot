"""
竞赛智能客服系统 - 中间件模块
处理请求与响应，提高问答质量
"""

import json
import logging
import time
from typing import Dict, Any, Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# 导入问题增强工具
from app.utils.question_enhancer import enhance_question, is_low_quality_answer, generate_backup_answer

logger = logging.getLogger(__name__)

class EnhancedRequestMiddleware(BaseHTTPMiddleware):
    """增强请求中间件，改进问题质量"""
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        处理请求和响应
        
        Args:
            request: 原始请求
            call_next: 下一个处理函数
            
        Returns:
            处理后的响应
        """
        # 只处理'/api/ask'端点的POST请求
        if request.url.path == "/api/ask" and request.method == "POST":
            # 标记处理开始时间
            start_time = time.time()
            
            # 保存原始请求体
            body = await request.body()
            
            try:
                # 解析请求体
                data = json.loads(body)
                original_question = data.get("text", "")
                
                if original_question:
                    # 增强问题
                    enhanced_question = enhance_question(original_question)
                    
                    # 创建增强版请求体
                    data["text"] = enhanced_question
                    data["original_question"] = original_question
                    
                    # 将修改后的请求体替换原始请求体
                    body = json.dumps(data).encode()
                    
                    # 记录增强前后的差异
                    logger.info(f"请求增强: 原始=[{original_question}], 增强后=[{enhanced_question}], 耗时={time.time()-start_time:.2f}秒")
                
                # 重新构建请求对象
                async def receive():
                    return {"type": "http.request", "body": body}
                
                # 创建新的请求对象，保持原始请求的scope但替换body
                request._receive = receive
            
            except Exception as e:
                logger.error(f"处理请求过程中出错: {str(e)}")
                # 失败时使用原始请求继续
            
            # 继续处理请求
            response = await call_next(request)
            
            # 尝试对响应进行后处理
            if response.status_code == 200:
                # 读取响应体
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                try:
                    # 解析响应体
                    data = json.loads(response_body)
                    
                    # 检查回答质量
                    answer = data.get("answer", "")
                    
                    if is_low_quality_answer(answer):
                        logger.warning(f"检测到低质量回答: [{answer}]")
                        
                        # 生成备用回答
                        original_question = original_question or data.get("original_query", "")
                        if original_question:
                            backup_answer = await generate_backup_answer(original_question)
                            
                            # 替换回答
                            data["answer"] = backup_answer
                            data["confidence"] = max(data.get("confidence", 0.1), 0.6)  # 增加置信度
                            data["is_backup"] = True
                            
                            logger.info(f"使用备用回答: [{backup_answer}]")
                    
                    # 创建新的响应体
                    new_response_body = json.dumps(data).encode()
                    
                    # 返回修改后的响应
                    return Response(
                        content=new_response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                    
                except Exception as e:
                    logger.error(f"处理响应过程中出错: {str(e)}")
                    # 失败时使用原始响应
                
                # 重新构建原始响应
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            
            return response
        
        # 其他请求直接传递
        return await call_next(request) 