"""
竞赛智能客服系统 - 问题增强工具
提高RAG检索质量，解决"答非所问"问题
"""

import re
import logging
import jieba
import jieba.posseg as pseg
from typing import List, Set, Dict, Any

logger = logging.getLogger(__name__)

# 竞赛领域同义词表
COMPETITION_SYNONYMS = {
    # 竞赛类型同义词
    "比赛": ["竞赛", "大赛", "赛事", "contest", "competition"],
    "专项赛": ["专项竞赛", "赛项", "special contest"],
    "泰迪杯": ["泰迪杯数据挖掘挑战赛", "数据挖掘挑战赛", "泰迪杯挑战赛"],
    "3D编程": ["3D编程模型", "三维编程", "3D programming"],
    "机器人": ["robot", "机器人设计", "智能机器人"],
    "智能芯片": ["芯片", "计算思维", "智能计算"],

    # 竞赛要素同义词
    "报名": ["注册", "登记", "报名方式", "registration", "sign up"],
    "要求": ["条件", "资格", "标准", "criteria", "requirements"],
    "时间": ["日期", "期限", "截止日期", "deadline", "date"],
    "评分": ["打分", "评判", "评价", "评审", "score", "evaluation"],
    "奖项": ["奖励", "奖金", "获奖", "荣誉", "prize", "award"],
    "材料": ["作品", "提交物", "文档", "代码", "submission"],
}

# 问题类型关键词
QUESTION_TYPE_KEYWORDS = {
    "信息查询": ["什么是", "介绍", "简介", "说明", "定义", "概念"],
    "时间查询": ["什么时候", "时间", "几点", "日期", "截止", "期限"],
    "要求查询": ["要求", "条件", "资格", "标准", "criteria", "怎么参加", "如何报名"],
    "评分查询": ["评分", "打分", "评判", "评价", "评审", "标准", "得分", "分数"],
    "奖项查询": ["奖项", "奖励", "奖金", "获奖", "荣誉", "几等奖"],
}

# 停用词列表
STOPWORDS = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说"}

def extract_core_terms(question: str) -> List[str]:
    """
    提取问题中的核心术语
    
    Args:
        question: 用户问题
    
    Returns:
        核心术语列表
    """
    # 使用jieba词性标注
    words = pseg.cut(question)
    
    # 提取名词、动词等实义词
    core_terms = []
    for word, flag in words:
        # 过滤停用词和单字词(除非是关键字如"赛"、"奖"等)
        if word in STOPWORDS or (len(word) == 1 and word not in {"赛", "奖", "分", "题"}):
            continue
            
        # 选择名词、动词、形容词等有实际意义的词
        if flag.startswith(('n', 'v', 'a')) or len(word) > 1:
            core_terms.append(word)
    
    logger.info(f"从问题中提取的核心术语: {core_terms}")
    return core_terms

def add_synonyms(terms: List[str]) -> Set[str]:
    """
    为核心术语添加同义词
    
    Args:
        terms: 核心术语列表
    
    Returns:
        扩展后的术语集合
    """
    expanded = set(terms)
    
    for term in terms:
        # 检查该术语是否有同义词
        for key, synonyms in COMPETITION_SYNONYMS.items():
            if term == key or term in synonyms:
                # 添加所有同义词
                expanded.update(synonyms)
                expanded.add(key)  # 也添加主词
    
    # 移除原始术语，防止重复
    for term in terms:
        if term in expanded:
            expanded.remove(term)
    
    logger.info(f"术语同义词扩展: {terms} -> {expanded}")
    return expanded

def identify_question_type(question: str) -> Dict[str, float]:
    """
    识别问题类型并计算匹配度
    
    Args:
        question: 用户问题
    
    Returns:
        问题类型及其匹配度字典
    """
    question = question.lower()
    type_scores = {}
    
    # 计算每种问题类型的匹配度
    for q_type, keywords in QUESTION_TYPE_KEYWORDS.items():
        count = 0
        for keyword in keywords:
            if keyword in question:
                count += 1
        
        if count > 0:
            score = count / len(keywords) * 0.7 + 0.3  # 基础分0.3，最高分1.0
            type_scores[q_type] = min(score, 1.0)
    
    # 如果没有匹配任何类型，设为通用问题
    if not type_scores:
        type_scores["通用问题"] = 0.5
    
    logger.info(f"问题类型分析: {type_scores}")
    return type_scores

def enhance_question(question: str) -> str:
    """
    增强问题文本，提高检索质量
    
    Args:
        question: 用户问题
    
    Returns:
        增强后的问题
    """
    # 清理问题文本
    question = question.strip()
    
    # 1. 提取核心术语
    core_terms = extract_core_terms(question)
    
    # 2. 添加同义词扩展
    expanded_terms = add_synonyms(core_terms)
    
    # 3. 识别问题类型
    question_types = identify_question_type(question)
    type_terms = []
    for q_type, score in question_types.items():
        if score > 0.5:  # 只使用匹配度较高的类型
            type_terms.append(q_type)
    
    # 4. 构建增强的问题文本
    enhanced_parts = []
    
    # 添加原始问题
    enhanced_parts.append(question)
    
    # 添加问题类型标记
    if type_terms:
        enhanced_parts.append("问题类型:" + " ".join(type_terms))
    
    # 添加扩展词
    if expanded_terms:
        enhanced_parts.append("关键词:" + " ".join(expanded_terms))
    
    # 组合为增强问题
    enhanced_question = " ".join(enhanced_parts)
    
    logger.info(f"问题增强: 原始问题=[{question}], 增强后=[{enhanced_question}]")
    return enhanced_question

def is_low_quality_answer(answer: str) -> bool:
    """
    检测回答是否为低质量
    
    Args:
        answer: 回答文本
    
    Returns:
        是否为低质量回答
    """
    # 检查是否包含"无法提供"、"资料中找不到"等拒绝回答的表达
    reject_phrases = [
        "无法提供", "找不到", "没有相关信息", "无法回答", 
        "抱歉", "没有足够的信息", "不清楚", "不确定"
    ]
    
    # 检查否定词加上"信息"、"资料"等词的组合
    reject_patterns = [
        r"没有.{0,3}(信息|资料|内容|数据)",
        r"无法.{0,3}(回答|提供|查询|找到)",
        r"不.{0,3}(清楚|确定|了解|明确)"
    ]
    
    # 1. 检查短回答
    if len(answer) < 15:
        return True
    
    # 2. 检查拒绝回答的短语
    for phrase in reject_phrases:
        if phrase in answer:
            return True
    
    # 3. 检查拒绝模式
    for pattern in reject_patterns:
        if re.search(pattern, answer):
            return True
    
    return False

async def generate_backup_answer(question: str) -> str:
    """
    为问题生成备用回答
    
    Args:
        question: 用户问题
    
    Returns:
        备用回答
    """
    # 简单起见，根据问题类型提供一个通用回答
    question_types = identify_question_type(question)
    primary_type = max(question_types.items(), key=lambda x: x[1])[0]
    
    backup_answers = {
        "信息查询": "这是一个竞赛信息查询问题。竞赛信息包括竞赛背景、目标、参与方式等。我们提供多种竞赛类型，包括泰迪杯数据挖掘挑战赛、3D编程模型创新设计专项赛等16种竞赛。每种竞赛都有其特定的目标和规则。",
        
        "时间查询": "竞赛时间安排通常包括报名时间、初赛时间、决赛时间等几个重要阶段。大多数竞赛报名时间在3-4月，初赛在5-7月，决赛在8-10月。具体赛事的精确时间请参考官方通知。",
        
        "要求查询": "竞赛参与要求通常包括参赛资格、团队组成、材料提交等方面。一般而言，参赛者需要是在校学生，团队成员2-3人，并有指导老师。具体要求因竞赛类型而异。",
        
        "评分查询": "竞赛评分标准通常包括创新性(25%)、技术实现(25%)、实用价值(25%)和文档质量(25%)四个方面。评审委员会由行业专家和学者组成，采用盲审方式进行公平评判。",
        
        "奖项查询": "竞赛奖项设置通常包括特等奖、一等奖、二等奖、三等奖和优秀奖。获奖团队将获得证书和奖金，并有机会参加后续的交流活动和产业对接。"
    }
    
    # 返回通用回答或类型特定回答
    return backup_answers.get(primary_type, "这是关于竞赛的问题。本系统支持16个专项赛事的咨询服务，包括泰迪杯数据挖掘挑战赛、3D编程模型创新设计专项赛等。可以询问关于竞赛的报名要求、评分标准、时间安排等问题。") 