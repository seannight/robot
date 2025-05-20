"""
智能客服机器人 - 统一路由模块
功能：处理所有页面路由和API请求
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional
import time
import json

from ..api.session import SessionManager
from ..models.mcp_engine import MCPEngine
from ..services.data import DataProcessor

# 初始化组件
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
session_manager = SessionManager()
mcp_engine = MCPEngine()
data_processor = DataProcessor()

# 页面路由
@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """仪表板页面"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

# API路由
@router.post("/api/query")
async def process_query(query: str, session_id: str):
    """处理用户查询"""
    try:
        # 验证会话
        if not session_manager.get_session(session_id):
            raise HTTPException(status_code=400, detail="无效的会话ID")
        
        # 处理查询
        response = mcp_engine.process_query(query, session_id)
        
        # 更新会话历史
        session_manager.update_session(session_id, query, response)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/upload")
async def upload_document(file_path: str):
    """上传并处理文档"""
    try:
        result = data_processor.process_document(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/session/{session_id}")
async def get_session_history(session_id: str):
    """获取会话历史"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"history": session.get('history', [])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    try:
        # 获取活跃会话数
        active_sessions = len(session_manager.sessions)
        
        # 获取今日查询数
        today_queries = sum(
            len(session.get('history', []))
            for session in session_manager.sessions.values()
        )
        
        # 获取平均响应时间
        avg_response_time = 100  # 示例值，实际应从性能监控中获取
        
        # 获取准确率
        accuracy = 95  # 示例值，实际应从评估系统中获取
        
        return {
            "active_sessions": active_sessions,
            "today_queries": today_queries,
            "avg_response_time": avg_response_time,
            "accuracy": accuracy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))