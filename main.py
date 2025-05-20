"""
竞赛智能客服系统 - 主应用文件
提供Web界面和API接口，支持竞赛智能问答
"""

import os
import logging
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import sys

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# 导入配置和模型
from app.config import settings as config, normalize_path
from app.models.SimpleMCPWithRAG import SimpleMCPWithRAG
from app.models.SimpleRAG import SimpleRAG
from app.models.MCPWithContext import MCPWithContext

# 导入中间件和工具
from app.utils.middleware import EnhancedRequestMiddleware
from app.utils.question_enhancer import enhance_question, is_low_quality_answer, generate_backup_answer
from app.utils.response_formatter import standardize_response, format_error_response

# 引入结构化知识库和查询路由器
from app.models.structured_kb import StructuredCompetitionKB
from app.models.query_router import QueryRouter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(normalize_path("logs/app.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="竞赛智能客服系统",
    description="提供竞赛相关问答服务",
    version="1.0"
)

# 添加请求增强中间件
app.add_middleware(EnhancedRequestMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=normalize_path("app/static")), name="static")

# 设置模板
templates = Jinja2Templates(directory=normalize_path("app/templates"))

# 初始化简化版MCP+RAG引擎
qa_engine = SimpleMCPWithRAG()

# 定义请求和响应模型
class QuestionRequest(BaseModel):
    """问题请求模型"""
    text: str  # 前端传入的问题字段
    session_id: Optional[str] = None

class RebuildIndexRequest(BaseModel):
    """重建索引请求模型"""
    force: bool = False

# 会话存储
active_sessions = {}

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """获取首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """
    处理问题API
    """
    start_time = time.time()
    question = request.text.strip()
    session_id = request.session_id
    
    if not question:
        logger.warning("收到空问题")
        return standardize_response({
            "answer": "问题不能为空", 
            "confidence": 0.0
        }, session_id, start_time)
    
    logger.info(f"收到问题: '{question}', 会话ID: {session_id}")
    
    try:
        # 使用问题增强器处理问题
        try:
            enhanced_question = enhance_question(question)
            logger.info(f"增强后问题: {enhanced_question}")
            question = enhanced_question
        except Exception as e:
            logger.error(f"问题增强失败: {str(e)}")
        
        # 使用统一查询引擎处理问题，加入超时保护
        try:
            result = await asyncio.wait_for(
                qa_engine.route_query(question=question, session_id=session_id),
                timeout=15.0  # 设置15秒超时
            )
        except asyncio.TimeoutError:
            logger.error("问题处理超时")
            return standardize_response({
                "answer": "处理您的问题时花费了太长时间，请尝试简化问题或稍后再试。",
                "confidence": 0.3
            }, session_id, start_time)
        
        # 使用响应格式化工具确保一致性
        response = standardize_response(result, session_id, start_time)
        
        logger.info(f"问题处理完成，置信度: {response.get('confidence', 'N/A')}, 耗时: {response.get('processing_time', 'N/A')}秒")
        return response
        
    except Exception as e:
        logger.error(f"处理问题时出错: {str(e)}", exc_info=True)
        # 使用错误响应格式化工具
        return format_error_response(e, session_id, start_time)

@app.post("/api/rebuild_index")
async def rebuild_index(request: RebuildIndexRequest):
    """
    重建索引
    :param request: 重建索引请求
    :return: 重建结果
    """
    try:
        logger.info("收到重建索引请求")
        
        # 简化版引擎不支持直接重建索引，使用原有引擎重建
        from app.models.SimpleRAG import SimpleRAG
        rag = SimpleRAG(rebuild_index=True)
        
        return {"status": "success", "message": "索引重建成功"}
    except Exception as e:
        logger.error(f"重建索引时出错: {str(e)}")
        return {
            "status": "error", 
            "message": f"重建索引时出错: {str(e)}"
        }

@app.get("/api/status")
async def get_status():
    """
    获取系统状态
    :return: 系统状态信息
    """
    try:
        # 获取诊断信息
        diag = await qa_engine.diagnose()
        return {
            "status": "ok",
            "version": config.VERSION,
            "uptime": time.time() - start_time,
            "diagnostics": diag
        }
    except Exception as e:
        logger.error(f"获取系统状态时出错: {str(e)}")
        return {
            "status": "error", 
            "message": f"获取系统状态时出错: {str(e)}"
        }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket端点，支持实时问答
    :param websocket: WebSocket连接
    """
    session_id = f"ws_{uuid.uuid4().hex}"
    
    try:
        await websocket.accept()
        logger.info(f"新WebSocket连接已建立: {session_id}")
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connection_established",
            "status": "connected",
            "session_id": session_id,
            "timestamp": time.time()
        })
        
        while True:
            try:
                # 接收消息
                data = await websocket.receive_json()
                start_time = time.time()
                
                # 处理初始化消息
                if data.get("action") == "init" and "session_id" in data:
                    session_id = data["session_id"]
                    logger.info(f"WebSocket会话ID已更新: {session_id}")
                    await websocket.send_json({
                        "type": "init_ack",
                        "session_id": session_id,
                        "status": "connected",
                        "timestamp": time.time()
                    })
                    continue
                
                # 获取问题文本
                question = data.get("text", "")
                if not question:
                    logger.warning(f"收到空问题: {data}")
                    empty_response = standardize_response({
                        "answer": "请提供有效的问题",
                        "confidence": 0.0
                    }, session_id, start_time)
                    empty_response["error"] = "问题不能为空"
                    
                    await websocket.send_json(empty_response)
                    continue
                
                logger.info(f"WebSocket收到问题: {question} (会话: {session_id})")
                
                # 使用问题增强器处理问题
                try:
                    enhanced_question = enhance_question(question)
                    logger.info(f"增强后问题: {enhanced_question}")
                    question = enhanced_question
                except Exception as e:
                    logger.error(f"问题增强失败: {str(e)}")
                
                # 使用统一查询引擎处理问题，加入超时保护
                try:
                    result = await asyncio.wait_for(
                        qa_engine.route_query(question=question, session_id=session_id),
                        timeout=15.0  # 设置15秒超时
                    )
                except asyncio.TimeoutError:
                    logger.error("WebSocket问题处理超时")
                    timeout_response = standardize_response({
                        "answer": "处理您的问题时间过长，请尝试简化问题或稍后再试。",
                        "confidence": 0.3,
                        "error": "处理超时"
                    }, session_id, start_time)
                    
                    await websocket.send_json(timeout_response)
                    continue
                
                # 使用响应格式化工具确保一致性
                response = standardize_response(result, session_id, start_time)
                
                logger.info(f"WebSocket问题处理完成，置信度: {response.get('confidence', 'N/A')}, 耗时: {response.get('processing_time', 'N/A')}秒")
                
                # 确保WebSocket仍然连接
                try:
                    await websocket.send_json(response)
                except RuntimeError as e:
                    if "websocket disconnected" in str(e).lower():
                        logger.info(f"发送响应时WebSocket已断开: {session_id}")
                        break
                    else:
                        raise
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket客户端断开连接: {session_id}")
                break
            except json.JSONDecodeError as json_err:
                logger.error(f"接收到非法JSON格式数据: {str(json_err)}")
                try:
                    error_response = format_error_response(json_err, session_id)
                    error_response["error"] = "接收到非法JSON格式数据"
                    error_response["answer"] = "请发送有效的JSON数据"
                    
                    await websocket.send_json(error_response)
                except Exception:
                    logger.error("无法发送错误消息，连接可能已关闭")
                    break
            except Exception as e:
                logger.error(f"接收WebSocket消息时出错: {str(e)}", exc_info=True)
                try:
                    error_response = format_error_response(e, session_id, start_time)
                    await websocket.send_json(error_response)
                except Exception:
                    logger.error("无法发送错误消息，连接可能已关闭")
                    break
    except Exception as e:
        logger.error(f"WebSocket处理过程中出错: {str(e)}", exc_info=True)
    finally:
        logger.info(f"WebSocket连接已关闭: {session_id}")

# 添加简单的WebSocket测试端点
@app.websocket("/ws_test")
async def websocket_test(websocket: WebSocket):
    """
    简单WebSocket测试端点
    :param websocket: WebSocket连接
    """
    test_session_id = f"test_{uuid.uuid4().hex}"
    
    try:
        await websocket.accept()
        logger.info(f"WebSocket测试连接已建立: {test_session_id}")
        
        # 发送欢迎消息
        await websocket.send_json({
            "message": "欢迎使用WebSocket测试接口",
            "status": "connected",
            "session_id": test_session_id,
            "timestamp": time.time()
        })
        
        # 处理消息
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"WebSocket测试收到消息: {data}")
                
                # 返回消息
                response = {
                    "echo": data,
                    "timestamp": time.time(),
                    "session_id": test_session_id
                }
                
                await websocket.send_json(response)
            except WebSocketDisconnect:
                logger.info(f"WebSocket测试客户端断开连接: {test_session_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket测试接收消息时出错: {str(e)}")
                try:
                    # 确保连接仍然打开再发送
                    error_response = format_error_response(e, test_session_id)
                    await websocket.send_json(error_response)
                except Exception:
                    # 连接可能已关闭，忽略二次错误
                    logger.error("无法发送错误消息，连接可能已关闭")
                    break
    except Exception as e:
        logger.error(f"WebSocket测试处理过程中出错: {str(e)}")
    finally:
        logger.info(f"WebSocket测试连接已关闭: {test_session_id}")

# 记录系统启动时间
start_time = time.time()

# 初始化目录
os.makedirs(normalize_path("logs"), exist_ok=True)

logger.info(f"系统启动 - 版本: {config.VERSION}")
logger.info(f"API服务运行在: http://{config.API_HOST}:{config.API_PORT}")
logger.info(f"知识库路径: {config.KNOWLEDGE_BASE_PATH}")
logger.info(f"使用SimpleMCPWithRAG引擎")

# 在main函数中添加初始化代码
@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化工作"""
    global qa_engine

    try:
        # 创建日志目录
        os.makedirs("logs", exist_ok=True)
        
        # 初始化知识库索引
        rebuild = False
        if not os.path.exists(config.INDEX_PATH) or "--rebuild" in sys.argv:
            rebuild = True
            logger.info("开始重建索引...")
        
        # 加载结构化知识库
        structured_kb = StructuredCompetitionKB(
            docs_path=config.KNOWLEDGE_BASE_PATH,
            rebuild=rebuild
        )
        
        # 加载语义搜索引擎
        rag_engine = SimpleRAG(
            rebuild_index=rebuild
        )
        
        # 创建MCP引擎
        mcp_engine = MCPWithContext()
        
        # 初始化语义RAG引擎
        semantic_rag = SimpleMCPWithRAG()
        
        # 初始化查询路由器
        qa_engine = QueryRouter(
            structured_kb=structured_kb,
            semantic_rag=semantic_rag
        )
        
        logger.info(f"系统启动 - 版本: {config.VERSION}")
        logger.info(f"API服务运行在: http://{config.API_HOST}:{config.API_PORT}")
        logger.info(f"知识库路径: {config.KNOWLEDGE_BASE_PATH}")
        logger.info("使用双引擎问答系统 (结构化知识库 + 语义搜索)")
        
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.DEBUG,
        workers=config.WORKERS
    )