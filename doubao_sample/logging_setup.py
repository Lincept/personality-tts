import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Optional
from schemas import LogConfig
from config import log_config

def setup_log_recording(
    log_config: LogConfig = log_config,
) -> Optional[str]:
    
    # 获取或创建 root logger
    logger = logging.getLogger()
    
    # 清除已有的 handlers，避免重复配置
    logger.handlers.clear()
    
    # 设置日志等级
    logger.setLevel(log_config.level)
    
    # 日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_config.level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if not log_config.save:
        return None

    # 创建日志根目录
    if not os.path.exists(log_config.save_dest):
        os.makedirs(log_config.save_dest)
    
    # 使用 TimedRotatingFileHandler 实现按天自动轮转
    # 日志文件名格式：app.log，自动轮转后变为 app.log.YYYY-MM-DD
    log_file = os.path.join(log_config.save_dest, "app.log")
    
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 间隔1天
        backupCount=30,  # 保留最近30天的日志
        encoding='utf-8',
        utc=False  # 使用本地时区
    )
    # 设置轮转后的文件名格式：app.log.YYYY-MM-DD
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(log_config.level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"日志系统已初始化 - 等级: {log_config.level}, 文件: {log_file}")
    
    return log_file
