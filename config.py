#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能AI工具平台配置文件
"""

import os
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'ai-assistant-platform-secret-key-2024')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = 30 * 24 * 60 * 60  # 30天（秒）
    SESSION_COOKIE_SECURE = False  # 在HTTPS下应设为True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 数据库配置
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/conversations.db')
    
    # AI平台配置文件路径
    CONFIG_FILE = 'config/settings.json'
    
    # 默认AI配置
    DEFAULT_TEXT_MODEL = 'qwen-plus'
    DEFAULT_IMAGE_MODEL = 'wan2.2-t2i-flash'
    
    # 阿里云百炼API配置
    DASHSCOPE_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    DASHSCOPE_IMAGE_URL = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'
    DASHSCOPE_TASK_URL = 'https://dashscope.aliyuncs.com/api/v1/tasks'
    
    # OpenRouter API配置
    OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
    OPENROUTER_MODELS_URL = 'https://openrouter.ai/api/v1/models'
    
    # 应用设置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # AI参数配置
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    MAX_CONVERSATION_HISTORY = 20
    
    # 安全配置
    MAX_INPUT_LENGTH = 4000
    
    @classmethod
    def load_api_config(cls):
        """加载API配置"""
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        
        # 返回默认配置
        return {
            "dashscope_api_key": "",
            "openrouter_api_key": "",
            "current_platform": "dashscope",
            "current_model": cls.DEFAULT_TEXT_MODEL,
            "image_model": cls.DEFAULT_IMAGE_MODEL
        }
    
    @classmethod
    def save_api_config(cls, config_data):
        """保存API配置"""
        try:
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 配置字典
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """获取配置"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')
    
    return config_map.get(config_name, DevelopmentConfig)