"""
竞赛智能客服系统 - 配置文件
包含系统关键配置项和环境变量处理
"""
import os
import logging
import sys
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import json

# 确保中文路径处理正确
if sys.platform == 'win32':
    # 在Windows上使用UTF-8编码
    os.environ["PYTHONIOENCODING"] = "utf-8"

# 尝试导入代理设置，但不阻止系统运行
try:
    from app.proxy_settings import PROXY_CONFIG
except ImportError:
    PROXY_CONFIG = {}
    # 如果文件不存在，创建一个简单的模板
    os.makedirs("app", exist_ok=True)
    proxy_template = {
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "NO_PROXY": "localhost,127.0.0.1"
    }
    with open("app/proxy_settings.py", "w") as f:
        f.write(f"PROXY_CONFIG = {proxy_template}\n")

# 获取当前项目根目录的绝对路径
def get_project_root():
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(current_file)
    project_root = os.path.dirname(app_dir)
    return project_root

PROJECT_ROOT = get_project_root()

# 规范化路径，避免编码问题
def normalize_path(path):
    """标准化路径，避免编码问题"""
    # 转换为前斜杠格式以提高跨平台兼容性
    path = path.replace('\\', '/')
    # 如果是相对路径，从项目根目录计算
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_ROOT, path).replace('\\', '/')
        
    # 确保附件1路径正确 (修复teddy-docs错误)
    path = path.replace('teddy-docs', 'docs')
    
    return path

# 加载.env文件
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("config")

class Settings(BaseSettings):
    """系统配置类，使用pydantic处理环境变量和默认值"""
    
    # 基础配置
    APP_NAME: str = "竞赛智能客服系统"
    VERSION: str = "5.0.0"
    DEBUG: bool = Field(default=True)
    
    # 路径配置 - 使用相对路径，在运行时转换为绝对路径
    BASE_DIR: str = Field(default="data", description="基础数据目录")
    KNOWLEDGE_BASE_PATH: str = Field(
        default="data/knowledge/docs/附件1",
        description="知识库路径，包含PDF文档"
    )
    VECTOR_STORE_PATH: str = Field(
        default="data/knowledge/vectors",
        description="向量存储路径"
    )
    SESSION_STORAGE_PATH: str = Field(
        default="data/sessions",
        description="会话存储路径"
    )
    INDEX_PATH: str = Field(
        default="data/knowledge/index",
        description="索引文件路径"
    )
    TXT_PATH: str = Field(
        default="data/knowledge/txt",
        description="文本文件路径"
    )
    
    # API服务配置
    API_HOST: str = Field(default="0.0.0.0", description="API服务绑定地址")
    API_PORT: int = Field(default=53085, description="API服务端口")
    WORKERS: int = Field(default=1, description="工作进程数")
    
    # RAG配置
    RAG_API_KEY: str = Field(
        default="sk-1f612e9e2ca145ae9d892e6ae7a7eebe",
        description="RAG API密钥"
    )
    DASHSCOPE_API_KEY: str = Field(
        default="sk-1f612e9e2ca145ae9d892e6ae7a7eebe",
        description="DashScope API密钥"
    )
    LLM_MODEL: str = Field(default="qwen-max", description="大语言模型名称")
    RAG_ENABLED: bool = Field(default=True, description="是否启用RAG")
    RAG_TOP_K: int = Field(default=20, description="RAG检索结果数量")
    RAG_RERANK_TOP_K: int = Field(default=10, description="RAG重排序结果数量")
    RAG_CHUNK_SIZE: int = Field(default=1500, description="RAG文本分块大小")
    RAG_CHUNK_OVERLAP: int = Field(default=400, description="RAG文本分块重叠大小")
    RAG_SCORE_THRESHOLD: float = Field(default=0.03, description="RAG相似度阈值")
    
    # 新增的RAG微调参数
    MAX_KEYWORDS_PER_QUERY: int = Field(default=20, description="针对用户查询提取的最大关键词数量")
    MAX_KEYWORDS_PER_CHUNK: int = Field(default=40, description="为文档块索引时提取的最大关键词数量")
    COMPETITION_TYPE_BOOST_FACTOR: float = Field(default=2.5, description="匹配到特定竞赛类型时的得分提升因子")
    KEYWORD_MATCH_BASE_WEIGHT: float = Field(default=1.5, description="基础关键词匹配权重")
    DIRECT_QUERY_MATCH_BONUS: float = Field(default=4.0, description="用户原始查询在文档中直接匹配的额外加分")
    CRITICAL_PHRASES_SCORING: Dict[str, float] = Field(
        default={
            "报名截止": 3.0,
            "提交时间": 2.8,
            "参赛要求": 2.7,
            "参赛资格": 2.5,
            "参赛对象": 2.5,
            "评分标准": 2.5,
            "评审方式": 2.3,
            "奖项设置": 2.3,
            "比赛流程": 2.2,
            "官方网站": 2.0,
            "联系方式": 2.0,
            "介绍": 2.0,
            "简介": 2.0,
            "是什么": 2.0,
            "怎么样": 1.8,
            "如何": 1.8,
            "要求": 1.8,
            "标准": 1.7,
            "截止日期": 2.5,
            "评分规则": 2.3,
            "作品提交": 2.5,
            "参赛条件": 2.5,
            "参赛组别": 2.3,
            "获奖条件": 2.2,
            "奖金": 2.0,
            "时间安排": 2.3,
            "内容要求": 2.2,
            "报名方式": 2.3,
            "作品要求": 2.5
        },
        description="关键短语及其对应的额外加分"
    )
    STOPWORDS_FILE_PATH: Optional[str] = Field(
        default=normalize_path("data/stopwords/common_stopwords.txt"), 
        description="停用词文件路径, 为None则不加载停用词"
    )
    # RAG_CONTEXT_MAX_TOKENS: int = Field(default=2000, description="传递给LLM的RAG上下文最大token数")
    
    # MCP配置
    MCP_CONFIDENCE_THRESHOLD: float = Field(default=0.6, description="MCP置信度阈值")
    MCP_MAX_HISTORY: int = Field(default=5, description="MCP最大历史记录数")
    MCP_ENABLE_CONTEXT: bool = Field(default=True, description="是否启用上下文理解")
    
    # 代理配置
    PROXY_ENABLED: bool = Field(default=False, description="是否启用代理")
    PROXY_CONFIG: Dict = Field(default=PROXY_CONFIG, description="代理配置")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    LOG_FILE: str = Field(
        default="logs/app.log",
        description="日志文件路径"
    )
    
    # 会话配置
    SESSION_EXPIRE_DAYS: int = Field(default=7, description="会话过期天数")
    MAX_SESSION_HISTORY: int = Field(default=50, description="最大会话历史记录数")
    
    # 系统性能配置
    MAX_WORKERS: int = Field(default=4, description="最大工作进程数")
    TIMEOUT: int = Field(default=30, description="请求超时时间(秒)")
    MAX_REQUEST_SIZE: int = Field(default=1024*1024, description="最大请求大小(字节)")
    
    # 竞赛配置
    COMPETITION_TYPES: List[str] = Field(
        default=[
            "人工智能创新挑战赛", "3D编程模型创新设计专项赛", "机器人工程挑战赛",
            "极地资源勘探设计大赛", "竞技机器人专项赛", "开源鸿蒙专项赛", 
            "人工智能综合创新专项赛", "三维程序创意设计大赛", "生成式人工智能应用专项赛",
            "太空电梯设计专项赛", "太空探索智能机器人大赛", "虚拟仿真平台创新设计专项赛",
            "智能数据采集与处理专项赛", "智能芯片创新设计大赛", "计算思维与人工智能专项赛",
            "未来校园智能应用专项赛"
        ],
        description="支持的竞赛类型列表"
    )
    
    # 竞赛关键词 - 用于检测和增强查询
    COMPETITION_KEYWORDS: List[str] = Field(
        default=[
            "泰迪杯", "数据挖掘挑战赛", "3D编程模型", "机器人工程",
            "极地资源勘探", "竞技机器人", "开源鸿蒙", 
            "人工智能综合创新", "三维程序创意", "生成式人工智能",
            "太空电梯", "太空探索", "虚拟仿真平台", 
            "智能数据采集", "智能芯片", "计算思维", "未来校园"
        ],
        description="竞赛关键词列表，用于检测和增强查询"
    )
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """验证并转换日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            logger.warning(f"无效的日志级别: {v}，使用默认值'INFO'")
            return "INFO"
        return v
    
    # 规范化所有路径字段
    @validator("BASE_DIR", "KNOWLEDGE_BASE_PATH", "VECTOR_STORE_PATH", 
              "SESSION_STORAGE_PATH", "INDEX_PATH", "TXT_PATH", "LOG_FILE")
    def normalize_paths(cls, v):
        """规范化路径，转换为项目根目录下的绝对路径"""
        return normalize_path(v)
    
    class Config:
        """配置元设置"""
        env_file = ".env"
        case_sensitive = True

# 创建设置实例
settings = Settings()

# 应用日志配置
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# 确保日志目录存在
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=log_level_map.get(settings.LOG_LEVEL, logging.INFO),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(settings.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 配置代理
if settings.PROXY_ENABLED and settings.PROXY_CONFIG:
    proxy_config = settings.PROXY_CONFIG
    os.environ["HTTP_PROXY"] = proxy_config.get("HTTP_PROXY", "")
    os.environ["HTTPS_PROXY"] = proxy_config.get("HTTPS_PROXY", "")
    os.environ["NO_PROXY"] = proxy_config.get("NO_PROXY", "")
    logger.info(f"已启用网络代理: {proxy_config.get('HTTP_PROXY', '')}")

# 初始化函数
def init_app_directories():
    """初始化应用所需的目录结构"""
    paths = [
        settings.KNOWLEDGE_BASE_PATH,
        settings.VECTOR_STORE_PATH,
        settings.SESSION_STORAGE_PATH,
        settings.INDEX_PATH,
        settings.TXT_PATH,
        normalize_path("app/static/css"),
        normalize_path("app/static/js"),
        normalize_path("app/templates"),
        os.path.dirname(settings.LOG_FILE)
    ]
    
    for path in paths:
        os.makedirs(path, exist_ok=True)
        logger.debug(f"已确保目录存在: {path}")

# 检查和初始化目录结构
init_app_directories()

# 输出配置信息
logger.info(f"系统配置已加载: {settings.APP_NAME} v{settings.VERSION}")
logger.info(f"API服务: {settings.API_HOST}:{settings.API_PORT}")
logger.info(f"知识库路径: {settings.KNOWLEDGE_BASE_PATH}")
logger.info(f"TXT路径: {settings.TXT_PATH}")
logger.info(f"日志级别: {settings.LOG_LEVEL}")
logger.info(f"RAG状态: {'已启用' if settings.RAG_ENABLED else '未启用'}")
logger.info(f"支持的竞赛数量: {len(settings.COMPETITION_TYPES)}")

def get_settings():
    """返回配置对象，用于依赖注入"""
    return settings