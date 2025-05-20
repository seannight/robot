#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
结构化竞赛知识库
预处理所有竞赛文档为结构化JSON数据，支持精确检索
"""

import os
import json
import re
import logging
import glob
from pathlib import Path
import jieba
import jieba.posseg as pseg
from tqdm import tqdm
from typing import Dict, List, Set, Tuple, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StructuredCompetitionKB:
    """结构化竞赛知识库，提供精确信息检索"""
    
    def __init__(self, docs_path: str, rebuild: bool = False):
        """
        初始化结构化竞赛知识库
        
        Args:
            docs_path: 知识库文档路径
            rebuild: 是否强制重建索引
        """
        self.docs_path = docs_path
        self.kb_file = Path("data/kb/structured_kb.json")
        self.kb: Dict[str, Dict[str, str]] = {}  # 结构化知识库
        self.competition_aliases: Dict[str, str] = self._build_competition_aliases()
        self.info_types: Dict[str, List[str]] = self._build_info_type_map()
        
        # 初始化知识库
        if not rebuild and os.path.exists(self.kb_file):
            self._load_kb()
        else:
            self._build_kb()
            
        # 记录统计信息
        self.competition_types = set(self.kb.keys())
        logger.info(f"结构化知识库初始化完成，共 {len(self.competition_types)} 个竞赛类型")
        
        # 加载竞赛关键词匹配表
        self._load_competition_keywords()
    
    def _build_competition_aliases(self) -> Dict[str, str]:
        """构建竞赛别名映射"""
        return {
            "泰迪杯": "泰迪杯数据挖掘挑战赛",
            "3D编程": "3D编程模型创新设计专项赛",
            "3D创新": "3D编程模型创新设计专项赛",
            "编程创作": "编程创作与信息学专项赛",
            "信息学": "编程创作与信息学专项赛",
            "机器人工程": "机器人工程设计专项赛",
            "极地资源": "极地资源勘探专项赛",
            "极地勘探": "极地资源勘探专项赛",
            "竞技机器人": "竞技机器人专项赛",
            "开源鸿蒙": "开源鸿蒙机器人专项赛",
            "人工智能创新": "人工智能综合创新专项赛",
            "AI创新": "人工智能综合创新专项赛",
            "三维程序": "三维程序创意设计专项赛",
            "生成式AI": "生成式人工智能应用专项赛",
            "AIGC": "生成式人工智能应用专项赛",
            "太空电梯": "太空电梯工程设计专项赛",
            "智能机器人": "太空探索智能机器人专项赛",
            "太空探索": "太空探索智能机器人专项赛",
            "虚拟仿真": "虚拟仿真平台创新设计专项赛",
            "数据采集": "智能数据采集装置设计专项赛",
            "智能芯片": "智能芯片与计算思维专项赛",
            "计算思维": "智能芯片与计算思维专项赛",
            "未来校园": "未来校园智能应用专项赛"
        }
    
    def _build_info_type_map(self) -> Dict[str, List[str]]:
        """构建信息类型及其别名和关键词列表"""
        return {
            "报名时间": ["报名时间", "报名日期", "注册时间", "注册日期", "报名截止", "何时报名", "什么时候报名", "报名信息"],
            "评分标准": ["评分标准", "评分规则", "评价标准", "评判标准", "评判规则", "如何评分", "打分标准", "评分依据", "成绩评定"],
            "参赛要求": ["参赛要求", "参赛条件", "参赛资格", "必备条件", "需要具备", "参赛选手", "参赛对象", "面向对象", "参赛者"],
            "竞赛简介": ["竞赛简介", "比赛简介", "竞赛介绍", "比赛介绍", "竞赛概述", "赛事简介", "什么比赛", "竞赛背景", "比赛信息"],
            "提交材料": ["提交材料", "提交内容", "作品要求", "提交要求", "作品形式", "提交形式", "提交什么", "需要提交", "最终提交"],
            "奖项设置": ["奖项设置", "奖励设置", "奖项内容", "有什么奖", "比赛奖金", "奖励方式", "奖励内容", "获奖奖励", "奖励标准"],
            "赛程安排": ["赛程安排", "比赛流程", "竞赛阶段", "竞赛流程", "比赛日程", "竞赛进程", "赛事安排", "比赛时间", "竞赛时间"],
            "联系方式": ["联系方式", "联系人", "咨询方式", "联系电话", "联系邮箱", "联系微信", "比赛咨询", "赛事咨询"]
        }
    
    def _load_kb(self):
        """从文件加载知识库"""
        try:
            with open(self.kb_file, 'r', encoding='utf-8') as f:
                self.kb = json.load(f)
            logger.info(f"从 {self.kb_file} 加载结构化知识库成功")
        except Exception as e:
            logger.error(f"加载结构化知识库失败: {e}")
            self._build_kb()  # 加载失败则重建
    
    def _build_kb(self):
        """构建结构化知识库"""
        logger.info("开始构建结构化知识库...")
        
        # 确保kb目录存在
        os.makedirs(os.path.dirname(self.kb_file), exist_ok=True)
        
        # 扫描所有txt文件
        txt_files = []
        for root, dirs, files in os.walk(self.docs_path):
            for file in files:
                if file.endswith(".txt"):
                    txt_files.append(os.path.join(root, file))
        
        # 解析每个文件提取结构化知识
        for txt_file in tqdm(txt_files, desc="处理竞赛文档"):
            self._process_file(txt_file)
        
        # 保存知识库
        with open(self.kb_file, 'w', encoding='utf-8') as f:
            json.dump(self.kb, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结构化知识库构建完成，保存至 {self.kb_file}")
    
    def _process_file(self, file_path: str):
        """处理单个文件，提取结构化信息"""
        try:
            # 从文件名中提取竞赛类型
            file_name = os.path.basename(file_path)
            competition_type = self._extract_competition_type(file_name)
            
            if not competition_type:
                logger.warning(f"无法识别文件 {file_name} 的竞赛类型，跳过")
                return
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取结构化信息
            info_dict = self._extract_structured_info(content)
            
            # 更新知识库
            if competition_type not in self.kb:
                self.kb[competition_type] = {}
            
            self.kb[competition_type].update(info_dict)
            
        except Exception as e:
            logger.error(f"处理文件 {file_path} 失败: {e}")
    
    def _extract_competition_type(self, file_name: str) -> Optional[str]:
        """从文件名中提取竞赛类型"""
        # 尝试从文件名中直接匹配完整竞赛名称
        for comp_type in self.competition_aliases.values():
            if comp_type in file_name:
                return comp_type
        
        # 尝试从文件名中匹配别名
        for alias, comp_type in self.competition_aliases.items():
            if alias in file_name:
                return comp_type
        
        return None
    
    def _extract_structured_info(self, content: str) -> Dict[str, str]:
        """从文本中提取结构化信息"""
        result = {}
        
        # 定义信息提取模式
        patterns = {
            "报名时间": r"报名时间[:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "评分标准": r"评[分价][标规则]准[:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "参赛要求": r"参赛[要条件][求件][:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "竞赛简介": r"[竞比赛][赛事]简介[:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "提交材料": r"提交[材要][料求][:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "奖项设置": r"奖[项励][设内]置[:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "赛程安排": r"[赛比][程赛]安排[:：]?(.*?)(?=\n\n|\n[^\n]|$)",
            "联系方式": r"联系方式[:：]?(.*?)(?=\n\n|\n[^\n]|$)"
        }
        
        # 尝试每种模式进行提取
        for info_type, pattern in patterns.items():
            matches = re.search(pattern, content, re.DOTALL)
            if matches:
                info_text = matches.group(1).strip()
                result[info_type] = info_text
        
        # 如果没有找到竞赛简介，尝试从开头提取
        if "竞赛简介" not in result:
            intro = content.split("\n\n")[0].strip()
            if len(intro) > 50:  # 只有足够长的文本才视为简介
                result["竞赛简介"] = intro
        
        return result
    
    def _load_competition_keywords(self):
        """加载竞赛关键词匹配表"""
        self.competition_keywords = {}
        for comp_type in self.kb:
            # 提取竞赛名称中的关键词
            words = list(jieba.cut(comp_type))
            significant_words = [w for w in words if len(w) > 1]  # 只保留多字符词
            self.competition_keywords[comp_type] = significant_words
    
    def get_competition_type(self, question: str) -> Optional[str]:
        """从问题中识别竞赛类型"""
        # 直接匹配竞赛名称
        for comp_type in self.kb:
            if comp_type in question:
                return comp_type
        
        # 匹配竞赛别名
        for alias, comp_type in self.competition_aliases.items():
            if alias in question and comp_type in self.kb:
                return comp_type
        
        # 关键词匹配
        matches = []
        for comp_type, keywords in self.competition_keywords.items():
            for keyword in keywords:
                if keyword in question:
                    matches.append((comp_type, len(keyword)))
        
        # 返回匹配度最高的竞赛类型
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)  # 按关键词长度排序
            return matches[0][0]
        
        return None
    
    def get_info_type(self, question: str) -> Optional[str]:
        """从问题中识别信息类型"""
        # 遍历所有信息类型及其关键词
        matches = []
        for info_type, keywords in self.info_types.items():
            for keyword in keywords:
                if keyword in question:
                    matches.append((info_type, len(keyword)))
        
        # 返回匹配度最高的信息类型
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)  # 按关键词长度排序
            return matches[0][0]
        
        return None
    
    def query(self, competition_type: Optional[str], info_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        从结构化知识库中精确查询信息
        
        Args:
            competition_type: 竞赛类型
            info_type: 信息类型
            
        Returns:
            Dict: 包含answer和confidence的结果，或None表示未找到
        """
        if not competition_type or not info_type:
            return None
        
        if competition_type in self.kb and info_type in self.kb[competition_type]:
            return {
                "answer": self.kb[competition_type][info_type],
                "confidence": 1.0,
                "source": f"{competition_type}-{info_type}",
                "competition_type": competition_type,
                "info_type": info_type
            }
        
        return None
    
    def get_all_competition_info(self, competition_type: str) -> Optional[Dict[str, str]]:
        """获取指定竞赛的所有信息"""
        if competition_type in self.kb:
            return self.kb[competition_type]
        return None
    
    def diagnose(self) -> Dict[str, Any]:
        """返回知识库诊断信息"""
        result = {
            "competition_count": len(self.kb),
            "competition_types": list(self.kb.keys()),
            "info_types": list(self.info_types.keys()),
            "competition_details": {}
        }
        
        # 记录每个竞赛有哪些信息类型
        for comp_type, info in self.kb.items():
            result["competition_details"][comp_type] = list(info.keys())
        
        return result 