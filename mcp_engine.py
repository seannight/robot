"""
竞赛智能客服系统 - MCP引擎
实现问题理解和回答生成
"""
import os
import logging
import re
import time
import random
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import asyncio

from langchain_community.chat_models.tongyi import ChatTongyi

# 配置日志
logger = logging.getLogger(__name__)

# 添加generate_response函数
async def generate_response(prompt: str, model: str, api_key: str) -> str:
    """
    使用ChatTongyi模型生成回答
    
    Args:
        prompt: 提示文本
        model: 模型名称
        api_key: API密钥
        
    Returns:
        生成的回答文本
    """
    try:
        logger.info(f"调用模型 {model} 生成回答，提示长度: {len(prompt)}")
        
        # 初始化ChatTongyi模型
        llm = ChatTongyi(
            model=model,
            dashscope_api_key=api_key
        )
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个专业的竞赛智能客服，负责回答用户关于各类竞赛的问题。"},
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"开始调用模型API")
        start_time = time.time()
        
        # 调用大模型生成回答
        try:
            response = await asyncio.to_thread(
                lambda: llm.invoke(messages)
            )
            
            # 记录响应对象类型和属性
            logger.info(f"模型响应类型: {type(response)}, 属性: {dir(response)}")
            
            # 提取回答内容
            if hasattr(response, 'content'):
                answer = response.content
                logger.info(f"从content属性提取回答，长度: {len(answer)}")
            else:
                answer = str(response)
                logger.info(f"使用str(response)作为回答，长度: {len(answer)}")
            
            logger.info(f"模型生成回答成功，耗时: {time.time() - start_time:.2f}秒，回答长度: {len(answer)}")
            logger.info(f"回答开头: {answer[:100]}...")
            return answer
            
        except Exception as api_error:
            logger.error(f"调用模型API失败: {str(api_error)}")
            raise api_error
        
    except Exception as e:
        logger.error(f"模型生成回答失败: {str(e)}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return "抱歉，模型生成回答时出现错误，请稍后再试。"

# 竞赛专用术语和关键词
COMPETITION_TERMS = {
    # 竞赛类型
    "竞赛类型": [
        "人工智能创新挑战赛", "3D编程模型创新设计专项赛", "机器人工程挑战赛",
        "极地资源勘探设计大赛", "竞技机器人专项赛", "开源鸿蒙专项赛", 
        "人工智能综合创新专项赛", "三维程序创意设计大赛", "生成式人工智能应用专项赛",
        "太空电梯设计专项赛", "太空探索智能机器人大赛", "虚拟仿真平台创新设计专项赛",
        "智能数据采集与处理专项赛", "智能芯片创新设计大赛", "计算思维与人工智能专项赛",
        "未来校园智能应用专项赛"
    ],
    
    # 竞赛阶段
    "竞赛阶段": [
        "报名", "初赛", "复赛", "决赛", "作品提交", "结果公布",
        "颁奖", "开幕式", "闭幕式", "答辩", "评审"
    ],
    
    # 竞赛要素
    "竞赛要素": [
        "参赛资格", "参赛条件", "参赛要求", "参赛流程", "评分标准",
        "奖项设置", "报名方式", "报名费用", "报名时间", "比赛时间",
        "提交要求", "提交方式", "提交时间", "评审方式", "评审标准"
    ],
    
    # 竞赛内容
    "竞赛内容": [
        "赛题", "题目", "任务", "要求", "目标", "创新点",
        "技术路线", "解决方案", "实现方法", "评价指标", "验收标准"
    ],
    
    # 参赛作品
    "参赛作品": [
        "论文", "代码", "设计", "模型", "方案", "报告",
        "演示", "展示", "答辩", "PPT", "视频", "海报"
    ]
}

class QueryContext:
    """
    查询上下文类，用于管理用户查询的上下文信息
    跟踪用户查询历史、当前话题和相关信息
    """
    
    def __init__(self, session_id: str, user_id: str = None):
        """
        初始化查询上下文
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选）
        """
        self.session_id = session_id
        self.user_id = user_id
        self.history = []  # 历史查询列表
        self.current_topic = None  # 当前话题
        self.context_data = {}  # 上下文相关数据
        self.created_at = time.time()
        self.last_updated = time.time()
        
        logger.info(f"创建新的查询上下文: session_id={session_id}, user_id={user_id}")
    
    def add_query(self, query: str, response: str, confidence: float = 0.0):
        """
        添加查询及其响应到历史记录
        
        Args:
            query: 用户查询
            response: 系统响应
            confidence: 回答的置信度
        """
        self.history.append({
            "query": query,
            "response": response,
            "confidence": confidence,
            "timestamp": time.time()
        })
        self.last_updated = time.time()
    
    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取最近的查询历史
        
        Args:
            limit: 返回的最大历史记录数
            
        Returns:
            最近的查询历史记录
        """
        return self.history[-limit:] if self.history else []
    
    def update_topic(self, topic: str):
        """
        更新当前话题
        
        Args:
            topic: 新话题
        """
        self.current_topic = topic
        self.last_updated = time.time()
    
    def add_context_data(self, key: str, value: Any):
        """
        添加上下文数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.context_data[key] = value
        self.last_updated = time.time()
    
    def get_context_data(self, key: str) -> Any:
        """
        获取上下文数据
        
        Args:
            key: 数据键
            
        Returns:
            数据值，如果不存在则返回None
        """
        return self.context_data.get(key)

class MCPEngine:
    """
    MCP (Multi-stage Cognition Processing) 引擎
    实现多阶段的问题理解和回答生成
    """
    
    def __init__(self, config_path: str = "app/config.py"):
        """
        初始化MCP引擎
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化MCP引擎")
        
        # 加载配置
        self.config = {}
        self._load_config(config_path)
        
        # 会话上下文
        self.contexts = {}  # session_id -> QueryContext
        
        # 竞赛专用术语和关键词
        self.competition_terms = COMPETITION_TERMS
        
        # 竞赛知识库
        self.knowledge_base = self._load_knowledge_base()
        
        # 问题类型模板
        self.question_patterns = {
            "竞赛信息": {
                "patterns": [
                    r"(什么是|介绍|简介|说明).*(竞赛|比赛|大赛)",
                    r".*竞赛.*(内容|主题|方向|类型)",
                    r".*赛题.*(类型|方向|领域|范围)"
                ],
                "response_template": "这是一个{competition_type}竞赛，主要面向{target_audience}。竞赛内容包括{content}。{additional_info}"
            },
            "参赛要求": {
                "patterns": [
                    r"(如何|怎么|怎样).*(参赛|报名)",
                    r".*(参赛|报名).*(条件|要求|资格|限制)",
                    r".*(需要|必须|可以).*(参加|报名)"
                ],
                "response_template": "参赛要求如下：\n1. 参赛资格：{eligibility}\n2. 团队要求：{team_requirements}\n3. 报名方式：{registration_method}\n4. 注意事项：{notes}"
            },
            "时间安排": {
                "patterns": [
                    r".*(时间|日期|截止|期限)",
                    r".*什么时候.*(开始|结束|截止)",
                    r".*(报名|提交|答辩).*(时间|日期)"
                ],
                "response_template": "重要时间节点：\n1. 报名时间：{registration_time}\n2. 初赛时间：{preliminary_time}\n3. 决赛时间：{final_time}\n4. 结果公布：{result_time}"
            },
            "评分标准": {
                "patterns": [
                    r".*(评分|评审|打分).*(标准|方式|规则)",
                    r".*(如何|怎么).*(评判|评估|评价)",
                    r".*(分数|成绩).*(构成|组成|计算)"
                ],
                "response_template": "评分标准包括：\n1. {criteria_1}：{weight_1}%\n2. {criteria_2}：{weight_2}%\n3. {criteria_3}：{weight_3}%\n4. {criteria_4}：{weight_4}%"
            },
            "奖项设置": {
                "patterns": [
                    r".*(奖项|奖励|奖金).*(设置|情况|多少)",
                    r".*(可以|能够).*(获得|拿到).*(什么|哪些).*奖",
                    r".*有.*(什么|哪些).*(奖|奖励)"
                ],
                "response_template": "奖项设置如下：\n1. 特等奖：{special_prize}\n2. 一等奖：{first_prize}\n3. 二等奖：{second_prize}\n4. 三等奖：{third_prize}\n{additional_prizes}"
            }
        }
    
    def _load_config(self, config_path: str):
        """加载配置"""
        try:
            # 设置默认配置
            self.config = {
                "max_history_length": 10,
                "default_confidence_threshold": 0.6,
                "knowledge_base_path": os.getenv("KNOWLEDGE_BASE_PATH", "data/knowledge/docs/附件1"),
                "session_storage_path": os.getenv("SESSION_STORAGE_PATH", "data/sessions"),
                "rag_enabled": True,  # 启用RAG集成
                "rag_confidence_threshold": 0.7,  # RAG置信度阈值
                "use_context": True,  # 启用上下文理解
                "max_context_turns": 3  # 最大上下文轮次
            }
            self.logger.info("已加载默认配置")
        except Exception as e:
            self.logger.error(f"加载配置出错: {e}")
            # 使用默认配置
            self.config = {
                "max_history_length": 10,
                "default_confidence_threshold": 0.6,
                "knowledge_base_path": "data/knowledge/docs/附件1",
                "session_storage_path": "data/sessions",
                "rag_enabled": True,
                "rag_confidence_threshold": 0.7,
                "use_context": True,
                "max_context_turns": 3
            }
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """
        加载知识库
        
        Returns:
            知识库字典
        """
        # 预设的竞赛常见问题回答
        knowledge_base = {
            "竞赛总体介绍": {
                "answer": "本系统支持16个专项赛事的咨询服务，包括人工智能创新挑战赛、3D编程模型创新设计专项赛等。每个赛事都有其特定的参赛要求、评分标准和奖项设置。",
                "keywords": ["介绍", "简介", "说明", "竞赛", "比赛", "专项赛"],
                "confidence": 0.9
            },
            "参赛基本要求": {
                "answer": "参赛要求因赛事不同而异，但通常包括：1. 参赛资格：全国高校在校学生；2. 团队要求：2-3人组队，需有指导教师；3. 报名方式：通过官方网站在线报名；4. 材料提交：包括作品、设计文档等。",
                "keywords": ["参赛", "要求", "条件", "资格", "如何参加", "怎么报名"],
                "confidence": 0.85
            },
            "评分标准通用说明": {
                "answer": "竞赛评分通常包括以下几个方面：1. 创新性（25%）：方案的创新程度和独特性；2. 技术实现（25%）：技术路线的可行性和完整性；3. 实用价值（25%）：解决实际问题的效果；4. 文档质量（25%）：文档的规范性和完整性。",
                "keywords": ["评分", "标准", "打分", "评审", "如何评", "评判"],
                "confidence": 0.85
            },
            "奖项设置通用说明": {
                "answer": "竞赛通常设置多个奖项层次：1. 特等奖：奖金XX元，获奖证书；2. 一等奖：奖金XX元，获奖证书；3. 二等奖：奖金XX元，获奖证书；4. 三等奖：奖金XX元，获奖证书；5. 优秀奖：获奖证书。具体奖项设置请参考各赛项具体通知。",
                "keywords": ["奖项", "奖励", "奖金", "几等奖", "获奖", "奖状"],
                "confidence": 0.8
            }
        }
        
        # 为每个竞赛类型添加特定知识
        for competition_type in self.competition_terms["竞赛类型"]:
            knowledge_base[f"{competition_type}_介绍"] = {
                "answer": f"{competition_type}是面向高校学生的专业竞赛，旨在培养学生的创新能力和实践技能。具体竞赛内容和要求请参考官方通知。",
                "keywords": [competition_type, "介绍", "简介", "说明"],
                "confidence": 0.8
            }
        
        self.logger.info(f"已加载预设知识库，包含{len(knowledge_base)}个问题类型")
        return knowledge_base
    
    def get_or_create_context(self, session_id: str, user_id: Optional[str] = None) -> QueryContext:
        """
        获取或创建查询上下文
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选）
            
        Returns:
            查询上下文对象
        """
        if session_id not in self.contexts:
            self.contexts[session_id] = QueryContext(session_id, user_id)
        return self.contexts[session_id]
    
    def process_question(self, question: str, session_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
        """
        处理用户问题，生成回答
        
        Args:
            question: 用户问题
            session_id: 会话ID（可选）
            user_id: 用户ID（可选）
            
        Returns:
            生成的回答
        """
        try:
            # 使用随机session_id如果未提供
            if not session_id:
                session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # 获取或创建上下文
            context = self.get_or_create_context(session_id, user_id)
            
            # 记录问题处理开始
            self.logger.info(f"处理问题: {question} (session_id={session_id})")
            
            # 步骤1: 理解问题类型和意图
            question_type, confidence, competition_type = self._understand_question(question, context)
            
            # 步骤2: 从知识库中查找相关回答
            answer, final_confidence = self._generate_answer(question, question_type, competition_type, context)
            
            # 记录到上下文
            context.add_query(question, answer, final_confidence)
            
            return answer
            
        except Exception as e:
            self.logger.error(f"处理问题时出错: {e}")
            return "抱歉，系统处理您的问题时出现了错误，请稍后再试。"
    
    def _understand_question(self, question: str, context: QueryContext) -> Tuple[str, float, Optional[str]]:
        """
        理解问题类型和意图
        
        Args:
            question: 用户问题
            context: 查询上下文
            
        Returns:
            (问题类型, 置信度, 竞赛类型)的元组
        """
        # 清理和标准化问题
        question = question.lower()
        question = re.sub(r'[^\w\s\u4e00-\u9fff]', '', question)
        
        # 检查是否是跟进问题
        if len(question) < 15 and context.history:
            last_query = context.history[-1]["query"]
            question = f"{last_query} {question}"
        
        # 识别竞赛类型
        competition_type = None
        for comp_type in self.competition_terms["竞赛类型"]:
            if comp_type in question:
                competition_type = comp_type
                break
        
        # 匹配问题模式
        best_match = None
        best_score = 0.0
        
        for q_type, pattern_info in self.question_patterns.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, question):
                    score = 0.8  # 基础匹配分数
                    if competition_type:
                        score += 0.1  # 如果识别出竞赛类型，增加分数
                    if score > best_score:
                        best_score = score
                        best_match = q_type
        
        # 如果没有找到匹配，尝试关键词匹配
        if not best_match:
            for q_type, info in self.knowledge_base.items():
                score = 0
                for keyword in info["keywords"]:
                    if keyword in question:
                        score += 1
                score = score / max(len(info["keywords"]), 1)
                if score > best_score:
                    best_score = score
                    best_match = q_type
        
        # 如果仍然没有找到匹配
        if not best_match:
            return "未知", 0.0, competition_type
            
        return best_match, best_score, competition_type
    
    def _generate_answer(self, question: str, question_type: str, competition_type: Optional[str], context: QueryContext) -> Tuple[str, float]:
        """
        生成回答
        
        Args:
            question: 用户问题
            question_type: 问题类型
            competition_type: 竞赛类型
            context: 查询上下文
            
        Returns:
            (生成的回答, 置信度)的元组
        """
        # 如果是未知类型或置信度太低
        if question_type == "未知":
            # 检查是否包含竞赛相关术语
            has_competition_term = False
            for term_category in self.competition_terms.values():
                if isinstance(term_category, list):
                    for term in term_category:
                        if term in question:
                            has_competition_term = True
                            break
                if has_competition_term:
                    break
            
            if has_competition_term:
                return ("抱歉，我需要更多信息来准确回答您的问题。您可以：\n"
                       "1. 说明具体想了解哪个竞赛\n"
                       "2. 询问具体的方面（如报名、评分、奖项等）\n"
                       "3. 查看示例问题获取参考", 0.5)
            else:
                return ("抱歉，您的问题可能超出了我的知识范围。我可以回答：\n"
                       "1. 16个专项赛事的相关信息\n"
                       "2. 参赛要求和流程\n"
                       "3. 评分标准和奖项设置\n"
                       "请尝试询问这些方面的问题。", 0.4)
        
        # 获取知识库中的基础回答
        answer_info = self.knowledge_base.get(question_type, {})
        base_answer = answer_info.get("answer", "")
        base_confidence = answer_info.get("confidence", 0.6)
        
        # 如果有特定竞赛类型，尝试获取该竞赛的特定回答
        if competition_type:
            specific_answer_info = self.knowledge_base.get(f"{competition_type}_介绍", {})
            specific_answer = specific_answer_info.get("answer", "")
            if specific_answer:
                base_answer = f"{specific_answer}\n\n{base_answer}"
                base_confidence = max(base_confidence, specific_answer_info.get("confidence", 0.6))
        
        # 获取最近上下文
        recent_history = context.get_recent_history(self.config["max_context_turns"])
        
        # 根据上下文调整回答
        if recent_history and self.config["use_context"]:
            last_query = recent_history[-1]["query"]
            last_response = recent_history[-1]["response"]
            
            # 如果当前问题是跟进问题
            if len(question) < 15 and ("什么" in question or "怎么" in question or "谁" in question or "为什么" in question):
                # 组合上下文信息
                base_answer = f"{base_answer}\n\n基于您之前的问题，补充说明：{last_response}"
                base_confidence *= 0.9  # 略微降低置信度
        
        # 如果启用了RAG且置信度不够高
        if self.config["rag_enabled"] and base_confidence < self.config["rag_confidence_threshold"]:
            try:
                # TODO: 调用RAG获取补充答案
                pass
            except Exception as e:
                self.logger.error(f"RAG处理失败: {e}")
        
        # 返回最终答案和置信度
        return base_answer, base_confidence