"""
日志工具模块 - 提供项目统一的日志处理功能
"""

import os
import sys
import logging
import platform
from logging import StreamHandler
from datetime import datetime

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

class EncodingSafeStreamHandler(StreamHandler):
    """
    编码安全的流处理器，处理Windows终端上的编码问题
    
    在GBK编码的Windows终端上，会自动从特殊字符中清除emoji和非ASCII字符
    """
    
    def __init__(self, stream=None):
        """初始化处理器"""
        super().__init__(stream)
        self.is_windows = platform.system() == "Windows"
        
    def emit(self, record):
        """发送日志记录，安全处理编码问题"""
        try:
            msg = self.format(record)
            
            # 在Windows终端上，清除可能导致编码错误的字符
            if self.is_windows and hasattr(self.stream, "encoding") and self.stream.encoding == "cp936":
                # GBK编码在Windows终端上
                msg = self._clean_for_gbk(msg)
                
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)
    
    def _clean_for_gbk(self, text):
        """清理GBK无法显示的字符"""
        if not text:
            return text
            
        # 常见会导致问题的Emoji及特殊字符映射到替代字符
        emoji_map = {
            "🔄": "(重载)",
            "🌐": "(网络)",
            "📂": "(文件)",
            "💻": "(电脑)",
            "🧠": "(内存)",
            "🐍": "(Python)",
            "🚀": "(启动)",
            "⚙️": "(配置)",
            "📊": "(统计)",
            "🔍": "(搜索)",
            "📝": "(记录)",
            "⚠️": "(警告)",
            "❌": "(错误)",
            "✅": "(成功)",
        }
        
        # 替换Emoji
        for emoji, replacement in emoji_map.items():
            if emoji in text:
                text = text.replace(emoji, replacement)
        
        # 移除其他可能导致问题的字符
        result = ""
        for char in text:
            try:
                # 尝试编码为GBK来测试兼容性
                char.encode("gbk")
                result += char
            except UnicodeEncodeError:
                # 替换无法编码的字符为问号
                result += "?"
                
        return result

def setup_encoding_safe_logging(level=logging.INFO):
    """
    设置编码安全的日志
    
    Args:
        level: 日志级别
    """
    root_logger = logging.getLogger()
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建编码安全的处理器
    console_handler = EncodingSafeStreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # 添加处理器到根日志
    root_logger.addHandler(console_handler)
    root_logger.setLevel(level)
    
    return root_logger

def init_safe_logging(level=logging.INFO, logger_name=None):
    """
    初始化编码安全的日志
    
    Args:
        level: 日志级别
        logger_name: 日志器名称，None则使用根日志器
        
    Returns:
        配置好的日志器
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
        # 清除现有的处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        # 创建编码安全的处理器
        console_handler = EncodingSafeStreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        logger.setLevel(level)
        return logger
    else:
        return setup_encoding_safe_logging(level)

def get_logger(name=None, level="info", log_file=None):
    """
    获取配置好的日志器
    
    Args:
        name: 日志器名称
        level: 日志级别("debug", "info", "warning", "error", "critical")
        log_file: 可选的日志文件路径
        
    Returns:
        配置好的日志器
    """
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger = init_safe_logging(log_level, name)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        try:
            # 确保目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # 创建文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            
            # 添加到日志器
            logger.addHandler(file_handler)
            logger.info(f"日志将同时写入文件: {log_file}")
        except Exception as e:
            logger.error(f"设置日志文件失败: {str(e)}")
    
    return logger

def configure_for_tests():
    """配置用于测试的日志"""
    # 创建测试日志目录
    test_log_dir = os.path.join("logs", "tests")
    if not os.path.exists(test_log_dir):
        os.makedirs(test_log_dir, exist_ok=True)
    
    # 创建时间戳文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(test_log_dir, f"test_{timestamp}.log")
    
    # 获取测试日志器
    return get_logger("test", "debug", log_file)

# 默认项目日志器
default_logger = get_logger("teddy_cup")

if __name__ == "__main__":
    # 测试日志工具
    logger = get_logger("logging_test", "debug")
    logger.debug("这是一条调试消息")
    logger.info("这是一条信息消息")
    logger.warning("这是一条警告消息")
    logger.error("这是一条错误消息")
    logger.critical("这是一条严重错误消息")
    
    # 测试带文件的日志
    test_logger = get_logger(
        "file_test", 
        "info", 
        os.path.join("logs", "test.log")
    )
    test_logger.info("此消息应同时写入控制台和文件")