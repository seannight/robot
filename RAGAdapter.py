"""
竞赛智能客服系统 - RAG接口适配器
统一不同RAG实现的接口，解决组件间接口不一致问题
"""

import logging
import inspect
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

class RAGAdapter:
    """
    RAG接口适配器，统一不同RAG实现的接口，自动处理参数兼容性
    """
    
    def __init__(self, rag_implementation):
        """
        初始化RAG适配器
        
        Args:
            rag_implementation: 实际的RAG实现对象
        """
        self.rag = rag_implementation
        
        # 获取实际支持的参数列表
        if hasattr(self.rag, 'search'):
            self.supported_search_params = inspect.signature(self.rag.search).parameters.keys()
            logger.info(f"RAGAdapter: 搜索方法支持的参数: {', '.join(self.supported_search_params)}")
        else:
            self.supported_search_params = []
            logger.warning("RAGAdapter: 底层RAG实现没有search方法")
            
        # 获取search_with_filter方法的参数
        if hasattr(self.rag, 'search_with_filter'):
            self.supported_filter_params = inspect.signature(self.rag.search_with_filter).parameters.keys()
        else:
            self.supported_filter_params = []
            
        logger.info(f"RAGAdapter: 初始化完成，适配 {self.rag.__class__.__name__} 接口")
    
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        统一的搜索接口，自动过滤不支持的参数
        
        Args:
            query: 搜索查询
            **kwargs: 其他搜索参数，会根据底层实现自动过滤
            
        Returns:
            搜索结果列表
        """
        try:
            # 记录原始参数
            original_params = {**kwargs}
            
            # 检查是否需要调用search_with_filter
            if "filter_by_comp_type" in kwargs and kwargs["filter_by_comp_type"] and hasattr(self.rag, 'search_with_filter'):
                logger.info(f"RAGAdapter: 使用search_with_filter方法，竞赛类型过滤: {kwargs['filter_by_comp_type']}")
                
                # 准备参数
                filter_params = {k: v for k, v in kwargs.items() if k in self.supported_filter_params}
                
                # 转换一些可能的同义参数
                if "max_results" in kwargs and "top_n" in self.supported_filter_params and "max_results" not in self.supported_filter_params:
                    filter_params["top_n"] = kwargs["max_results"]
                    
                if "competition_type" in kwargs and "filter_by_comp_type" in self.supported_filter_params:
                    filter_params["filter_by_comp_type"] = kwargs["competition_type"]
                
                logger.info(f"RAGAdapter: 过滤后的参数: {filter_params}")
                
                # 调用search_with_filter方法
                return await self.rag.search_with_filter(query, **filter_params)
            
            # 普通搜索调用
            if hasattr(self.rag, 'search'):
                # 过滤参数，只保留支持的参数
                filtered_params = {k: v for k, v in kwargs.items() if k in self.supported_search_params}
                
                # 转换一些可能的同义参数
                if "max_results" in kwargs and "top_n" in self.supported_search_params and "max_results" not in self.supported_search_params:
                    filtered_params["top_n"] = kwargs["max_results"]
                    
                if "filter_by_comp_type" in kwargs and "competition_type" in self.supported_search_params:
                    filtered_params["competition_type"] = kwargs["filter_by_comp_type"]
                
                # 记录参数过滤情况
                if len(filtered_params) != len(original_params):
                    removed_params = set(original_params.keys()) - set(filtered_params.keys())
                    logger.info(f"RAGAdapter: 移除了不兼容的参数: {', '.join(removed_params)}")
                
                logger.info(f"RAGAdapter: 调用search方法，过滤后的参数: {filtered_params}")
                
                # 调用实际的搜索方法
                return await self.rag.search(query, **filtered_params)
            else:
                logger.warning("RAGAdapter: 底层RAG实现没有search方法")
                return []
                
        except Exception as e:
            logger.error(f"RAGAdapter: 搜索过程出错: {str(e)}", exc_info=True)
            # 出错时返回空列表，而不是抛出异常
            return []
    
    async def rebuild_index(self) -> bool:
        """
        重建索引的统一接口
        
        Returns:
            重建是否成功
        """
        try:
            if hasattr(self.rag, 'rebuild_index'):
                return await self.rag.rebuild_index()
            elif hasattr(self.rag, 'rebuild_index') and not inspect.iscoroutinefunction(self.rag.rebuild_index):
                # 处理同步rebuild_index方法
                return self.rag.rebuild_index()
            else:
                logger.warning("RAGAdapter: 底层RAG实现没有rebuild_index方法")
                return False
        except Exception as e:
            logger.error(f"RAGAdapter: 重建索引过程出错: {str(e)}", exc_info=True)
            return False
    
    async def diagnose(self) -> Dict[str, Any]:
        """
        诊断RAG系统状态
        
        Returns:
            诊断信息字典
        """
        try:
            if hasattr(self.rag, 'diagnose_knowledge_base'):
                if inspect.iscoroutinefunction(self.rag.diagnose_knowledge_base):
                    return await self.rag.diagnose_knowledge_base()
                else:
                    return self.rag.diagnose_knowledge_base()
            else:
                return {
                    "status": "可用",
                    "adapter": "RAGAdapter",
                    "implementation": self.rag.__class__.__name__,
                    "has_search": hasattr(self.rag, 'search'),
                    "has_search_with_filter": hasattr(self.rag, 'search_with_filter'),
                    "message": "底层实现没有诊断方法"
                }
        except Exception as e:
            logger.error(f"RAGAdapter: 诊断过程出错: {str(e)}", exc_info=True)
            return {"status": "错误", "error": str(e)} 