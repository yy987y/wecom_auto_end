#!/usr/bin/env python3
"""日志模块"""
import logging
from pathlib import Path
from datetime import datetime

def setup_logger(name='wecom_auto', log_dir=None):
    """设置日志"""
    if log_dir is None:
        log_dir = Path(__file__).parent / 'logs'
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件名：wecom_auto_2026-03-16.log
    log_file = log_dir / f'{name}_{datetime.now().strftime("%Y-%m-%d")}.log'
    
    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 清除已有的 handlers
    logger.handlers.clear()
    
    # 文件 handler（详细日志）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台 handler（简洁输出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
