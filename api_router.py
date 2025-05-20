"""
统一的API路由模块
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from ..models.mcp_engine import MCPEngine
from ..services.data import DataProcessor





router = APIRouter(prefix="/api")
mcp_engine = MCPEngine()
data_processor = DataProcessor()

@router.post("/query")
async def process_query(query: str, session_id: str):
    """
    处理用户查询
    """
    try:
        response = mcp_engine.process_query(query, session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(file_path: str):
    """
    上传并处理文档
    """
    try:
        result = data_processor.process_document(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
async def get_session_history(session_id: str):
    """
    获取会话历史
    """
    try:
        history = mcp_engine.session_history.get(session_id, [])
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))