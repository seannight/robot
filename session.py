"""
会话管理模块
"""
from typing import Dict, List, Optional
import time
import uuid

class SessionManager:
    """
    会话管理器
    """
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        
    def create_session(self) -> str:
        """
        创建新会话
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'created_at': time.time(),
            'last_active': time.time(),
            'history': []
        }
        return session_id
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        获取会话信息
        """
        return self.sessions.get(session_id)
        
    def update_session(self, session_id: str, query: str, response: Dict):
        """
        更新会话历史
        """
        if session_id in self.sessions:
            self.sessions[session_id]['last_active'] = time.time()
            self.sessions[session_id]['history'].append({
                'query': query,
                'response': response,
                'timestamp': time.time()
            })
            
    def delete_session(self, session_id: str):
        """
        删除会话
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            
    def cleanup_inactive_sessions(self, max_age: int = 3600):
        """
        清理不活跃的会话
        """
        current_time = time.time()
        for session_id, session in list(self.sessions.items()):
            if current_time - session['last_active'] > max_age:
                del self.sessions[session_id]