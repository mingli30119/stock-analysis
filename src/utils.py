#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""工具函数"""

import logging
from pathlib import Path


def setup_logger(name='stock_analysis', level=logging.INFO):
    """设置日志"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def ensure_dir(path):
    """确保目录存在"""
    Path(path).mkdir(parents=True, exist_ok=True)
