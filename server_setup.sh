#!/bin/bash

# AI助手平台服务器快速部署脚本
# 在服务器上执行此脚本来快速创建项目结构

echo "🚀 开始创建AI助手平台项目结构..."

# 创建基本目录结构
mkdir -p /home/ai_assistant_platform/{data,config,logs,static/{css,js},templates/{assistants,auth,games,admin},services,utils,prompts,deploy}

cd /home/ai_assistant_platform

# 创建requirements.txt
cat > requirements.txt << 'EOF'
Flask==2.3.3
Flask-CORS==4.0.0
python-dotenv==1.0.0
requests==2.31.0
gunicorn==21.2.0
EOF

# 创建.env文件
cat > .env << 'EOF'
FLASK_ENV=production
DEBUG=False
SECRET_KEY=ai-assistant-platform-secret-key-2024-production
HOST=0.0.0.0
PORT=5000
DATABASE_PATH=/home/aiplatform/ai_assistant_platform/data/conversations.db
EOF

# 创建config.py
cat > config.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'ai-assistant-platform-secret-key-2024')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = 30 * 24 * 60 * 60
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/conversations.db')
    CONFIG_FILE = 'config/settings.json'
    
    DEFAULT_TEXT_MODEL = 'qwen-plus'
    DEFAULT_IMAGE_MODEL = 'wan2.2-t2i-flash'
    
    DASHSCOPE_API_URL = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
    
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    MAX_CONVERSATION_HISTORY = 20
    MAX_INPUT_LENGTH = 4000
    
    @classmethod
    def load_api_config(cls):
        try:
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
        
        return {
            "dashscope_api_key": "",
            "openrouter_api_key": "",
            "current_platform": "dashscope",
            "current_model": cls.DEFAULT_TEXT_MODEL,
            "image_model": cls.DEFAULT_IMAGE_MODEL
        }
    
    @classmethod
    def save_api_config(cls, config_data):
        try:
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

class ProductionConfig(Config):
    DEBUG = False

def get_config(config_name=None):
    return ProductionConfig
EOF

# 创建简化版app.py
cat > app.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from config import Config, get_config

def create_app(config_name=None):
    app = Flask(__name__)
    
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    CORS(app)
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/config')
    def config_page():
        return render_template('config.html')
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        if request.method == 'GET':
            config_data = Config.load_api_config()
            return jsonify(config_data)
        
        elif request.method == 'POST':
            config_data = request.get_json()
            if Config.save_api_config(config_data):
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "error"}), 500
    
    @app.route('/assistants/chat')
    def chat():
        return render_template('assistants/chat.html')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

# 创建start.py
cat > start.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from app import create_app

def main():
    print("🚀 智能AI工具平台启动中...")
    
    os.makedirs('data', exist_ok=True)
    os.makedirs('config', exist_ok=True)
    
    app = create_app('production')
    
    print(f"🌟 服务器启动成功！")
    print(f"📍 访问地址: http://0.0.0.0:5000")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
EOF

# 创建基本HTML模板
mkdir -p templates
cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}AI智能助手平台{% endblock %}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 15px; color: #007bff; text-decoration: none; }
        .nav a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/">首页</a>
            <a href="/assistants/chat">AI聊天</a>
            <a href="/config">配置</a>
        </div>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
EOF

cat > templates/index.html << 'EOF'
{% extends "base.html" %}
{% block content %}
<h1>🎉 AI智能助手平台</h1>
<div style="text-align: center; margin: 40px 0;">
    <h2>欢迎使用AI智能助手平台！</h2>
    <p>这是一个强大的AI对话和工具平台</p>
    <div style="margin: 30px 0;">
        <a href="/assistants/chat" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px;">开始聊天</a>
        <a href="/config" style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px;">配置设置</a>
    </div>
</div>
{% endblock %}
EOF

cat > templates/config.html << 'EOF'
{% extends "base.html" %}
{% block content %}
<h1>⚙️ 系统配置</h1>
<div style="max-width: 600px; margin: 0 auto;">
    <form id="configForm">
        <div style="margin-bottom: 20px;">
            <label>阿里云百炼API密钥:</label><br>
            <input type="text" id="dashscope_api_key" style="width: 100%; padding: 8px; margin-top: 5px;">
        </div>
        <div style="margin-bottom: 20px;">
            <label>OpenRouter API密钥:</label><br>
            <input type="text" id="openrouter_api_key" style="width: 100%; padding: 8px; margin-top: 5px;">
        </div>
        <div style="margin-bottom: 20px;">
            <label>当前平台:</label><br>
            <select id="current_platform" style="width: 100%; padding: 8px; margin-top: 5px;">
                <option value="dashscope">阿里云百炼</option>
                <option value="openrouter">OpenRouter</option>
            </select>
        </div>
        <button type="submit" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px;">保存配置</button>
    </form>
</div>

<script>
// 加载配置
fetch('/api/config')
    .then(response => response.json())
    .then(data => {
        document.getElementById('dashscope_api_key').value = data.dashscope_api_key || '';
        document.getElementById('openrouter_api_key').value = data.openrouter_api_key || '';
        document.getElementById('current_platform').value = data.current_platform || 'dashscope';
    });

// 保存配置
document.getElementById('configForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const config = {
        dashscope_api_key: document.getElementById('dashscope_api_key').value,
        openrouter_api_key: document.getElementById('openrouter_api_key').value,
        current_platform: document.getElementById('current_platform').value
    };
    
    fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('配置保存成功！');
        } else {
            alert('配置保存失败！');
        }
    });
});
</script>
{% endblock %}
EOF

mkdir -p templates/assistants
cat > templates/assistants/chat.html << 'EOF'
{% extends "base.html" %}
{% block content %}
<h1>💬 AI智能聊天</h1>
<div style="max-width: 800px; margin: 0 auto;">
    <div id="chatMessages" style="height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; background: #fafafa;">
        <div style="text-align: center; color: #666; margin-top: 150px;">
            欢迎使用AI聊天助手！<br>
            请先在配置页面设置API密钥
        </div>
    </div>
    <div style="display: flex;">
        <input type="text" id="messageInput" placeholder="输入您的消息..." style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px 0 0 5px;">
        <button onclick="sendMessage()" style="background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 0 5px 5px 0;">发送</button>
    </div>
</div>

<script>
function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (!message) return;
    
    const chatMessages = document.getElementById('chatMessages');
    
    // 添加用户消息
    chatMessages.innerHTML += `
        <div style="margin-bottom: 10px; text-align: right;">
            <span style="background: #007bff; color: white; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                ${message}
            </span>
        </div>
    `;
    
    // 添加AI回复（模拟）
    setTimeout(() => {
        chatMessages.innerHTML += `
            <div style="margin-bottom: 10px;">
                <span style="background: #e9ecef; color: #333; padding: 8px 12px; border-radius: 15px; display: inline-block; max-width: 70%;">
                    您好！我是AI助手。目前需要配置API密钥才能正常工作，请访问配置页面设置。
                </span>
            </div>
        `;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1000);
    
    input.value = '';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

document.getElementById('messageInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
</script>
{% endblock %}
EOF

# 设置权限
sudo chown -R ubuntu:ubuntu /home/ai_assistant_platform
chmod +x start.py

echo "✅ 项目结构创建完成！"
echo "📁 项目位置: /home/ai_assistant_platform"
echo "🚀 下一步: 执行部署脚本"
EOF

chmod +x server_setup.sh