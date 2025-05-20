#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询路由器
根据问题类型决定使用结构化查询还是语义搜索
"""

import re
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union

logger = logging.getLogger(__name__)

class QueryRouter:
    """查询路由器，管理多引擎查询策略"""
    
    def __init__(self, structured_kb, semantic_rag):
        """
        初始化查询路由器
        
        Args:
            structured_kb: 结构化知识库
            semantic_rag: 语义搜索引擎
        """
        self.structured_kb = structured_kb
        self.semantic_rag = semantic_rag
        self.pattern_recognizer = self._build_patterns()
        logger.info("查询路由器初始化完成，已加载结构化查询和语义搜索引擎")
    
    def _build_patterns(self) -> Dict[str, List[str]]:
        """构建常见问题模式"""
        return {
            "报名时间": [
                r".*[什怎如]么时候.*报名",
                r".*报名.*[时日截]期",
                r".*报名.*开始",
                r".*报名.*结束",
                r".*[什怎如]么时候.*注册"
            ],
            "评分标准": [
                r".*[如怎]何评[分判]",
                r".*评分标准",
                r".*评分规则",
                r".*[如怎]何打分",
                r".*成绩.*计算"
            ],
            "参赛要求": [
                r".*参赛.*[要需]求",
                r".*参赛.*条件",
                r".*参赛.*资格",
                r".*[谁哪]些人.*参[赛加]",
                r".*[限面]向.*[谁哪]些"
            ],
            "竞赛简介": [
                r".*[是为什]么[比赛竞]赛",
                r".*介绍一下.*[比赛竞]赛",
                r".*[简概]述.*[比赛竞]赛",
                r".*了解.*[比赛竞]赛"
            ],
            "提交材料": [
                r".*[需应要].*提交[什哪]些",
                r".*提交.*[什哪]些",
                r".*[需应要].*准备[什哪]些",
                r".*[作提]品.*[要需形]求"
            ],
            "奖项设置": [
                r".*[有能会][获得].*[什哪]些奖",
                r".*奖[金项].*[多有是]少",
                r".*[获得]奖.*[福好处]",
                r".*奖[项励].*设置"
            ]
        }
    
    def classify_question(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        """
        对问题进行分类，识别竞赛类型和信息类型
        
        Args:
            question: 用户问题
            
        Returns:
            Tuple: (竞赛类型, 信息类型)，均可能为None
        """
        # 从问题中识别竞赛类型
        competition_type = self.structured_kb.get_competition_type(question)
        
        # 从问题中识别信息类型 - 先用结构化方法
        info_type = self.structured_kb.get_info_type(question)
        
        # 如果无法识别信息类型，尝试使用模式匹配
        if not info_type:
            for type_name, patterns in self.pattern_recognizer.items():
                for pattern in patterns:
                    if re.match(pattern, question, re.IGNORECASE):
                        info_type = type_name
                        break
                if info_type:
                    break
        
        logger.info(f"问题分类: '{question}' => 竞赛类型: {competition_type or '未知'}, 信息类型: {info_type or '未知'}")
        return competition_type, info_type
    
    async def route_query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        根据问题类型路由到合适的查询引擎
        
        Args:
            question: 用户问题
            session_id: 会话ID
            
        Returns:
            Dict: 标准化的回答结果
        """
        start_time = time.time()
        
        # 分类问题
        competition_type, info_type = self.classify_question(question)
        
        # 尝试使用结构化查询
        if competition_type and info_type:
            result = self.structured_kb.query(competition_type, info_type)
            if result and result.get("confidence", 0) > 0.7:
                logger.info(f"使用结构化查询返回结果，竞赛: {competition_type}, 信息类型: {info_type}, 置信度: {result.get('confidence')}")
                
                # 添加处理时间
                result["process_time"] = time.time() - start_time
                return result
            
            logger.info(f"结构化查询未找到高质量结果，竞赛: {competition_type}, 信息类型: {info_type}")
        else:
            logger.info(f"无法精确分类问题: '{question}'，使用语义搜索")
        
        # 在结构化查询未能返回高质量结果时，使用语义搜索
        semantic_result = await self.semantic_rag.query(question=question, session_id=session_id)
        
        # 确保结果类型和格式正确
        if not isinstance(semantic_result, dict):
            logger.warning(f"语义搜索返回非字典结果: {type(semantic_result)}")
            if isinstance(semantic_result, tuple) and len(semantic_result) >= 2:
                semantic_result = {
                    "answer": semantic_result[0],
                    "confidence": semantic_result[1]
                }
            else:
                semantic_result = {
                    "answer": str(semantic_result),
                    "confidence": 0.5
                }
        
        # 确保必要字段存在
        if "answer" not in semantic_result:
            semantic_result["answer"] = semantic_result.get("response", "抱歉，无法回答此问题")
        
        # 添加处理时间
        semantic_result["process_time"] = time.time() - start_time
        
        # 添加分类信息（如果有）
        if competition_type:
            semantic_result["competition_type"] = competition_type
        if info_type:
            semantic_result["info_type"] = info_type
        
        logger.info(f"使用语义搜索返回结果，置信度: {semantic_result.get('confidence', 'N/A')}")
        return semantic_result
    
    def diagnose(self) -> Dict[str, Any]:
        """返回查询路由器诊断信息"""
        result = {
            "structured_kb_status": "可用" if self.structured_kb else "未配置",
            "semantic_rag_status": "可用" if self.semantic_rag else "未配置",
            "pattern_count": {
                type_name: len(patterns) for type_name, patterns in self.pattern_recognizer.items()
            }
        }
        
        # 获取结构化知识库诊断信息
        if hasattr(self.structured_kb, "diagnose"):
            result["structured_kb_info"] = self.structured_kb.diagnose()
        
        # 获取语义搜索引擎诊断信息
        if hasattr(self.semantic_rag, "diagnose"):
            result["semantic_rag_info"] = self.semantic_rag.diagnose()
        
        return result 