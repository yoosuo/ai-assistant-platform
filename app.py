#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能AI工具平台 - Flask应用主文件
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, Response, stream_template, redirect, url_for
from flask_cors import CORS

from config import Config, get_config
from utils.database import DatabaseManager
from utils.auth import AuthManager, require_auth, require_admin, get_client_ip
from services.ai_service import AIService
# from services.memory_service import MemoryService
from services.prompt_guard import PromptGuard
from services.user_service import UserService
from prompts.assistant_prompts import get_assistant_prompt, get_all_assistants
from prompts.game_prompts import get_game_prompt, get_all_games


def create_app(config_name=None):
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 加载配置
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # 启用CORS
    CORS(app)
    
    # 初始化服务
    # memory_service = MemoryService()  # 暂时禁用
    prompt_guard = PromptGuard()
    auth_manager = AuthManager(app.config['DATABASE_PATH'])
    user_service = UserService(app.config['DATABASE_PATH'])
    
    # 初始化游戏服务
    from services.chat_service import ChatService
    from services.script_host_game import ScriptHostGame
    from services.detective_game import DetectiveGame
    from services.werewolf_game import WerewolfGame
    
    chat_service = ChatService()
    script_game = ScriptHostGame()
    detective_game = DetectiveGame()

    werewolf_game = WerewolfGame()
    
    # ==================== 认证路由 ====================
    
    @app.route('/login')
    def login_page():
        """登录页面"""
        return render_template('auth/login.html')
    
    @app.route('/register') 
    def register_page():
        """注册页面"""
        return render_template('auth/register.html')
    
    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        """用户注册API"""
        try:
            data = request.get_json()
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            
            # 基本验证
            if not username or not email or not password:
                return jsonify({"success": False, "error": "请填写完整的注册信息"})
            
            if len(username) < 3 or len(username) > 20:
                return jsonify({"success": False, "error": "用户名长度应为3-20个字符"})
            
            if not username.replace('_', '').isalnum():
                return jsonify({"success": False, "error": "用户名只能包含字母、数字和下划线"})
            
            if len(password) < 8:
                return jsonify({"success": False, "error": "密码至少需要8个字符"})
            
            if password != confirm_password:
                return jsonify({"success": False, "error": "两次输入的密码不一致"})
            
            # 注册用户
            result = auth_manager.register_user(username, email, password)
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"success": False, "error": "注册失败，请稍后重试"})
    
    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        """用户登录API"""
        try:
            data = request.get_json()
            
            username = data.get('username', '').strip()
            password = data.get('password', '')
            remember_me = data.get('remember_me', False)
            
            if not username or not password:
                return jsonify({"success": False, "error": "请填写用户名和密码"})
            
            # 获取客户端信息
            ip_address = get_client_ip()
            user_agent = request.headers.get('User-Agent', '')
            
            # 登录验证
            result = auth_manager.authenticate_user(username, password, ip_address, user_agent)
            
            if result['success']:
                # 设置会话
                session['session_token'] = result['session_token']
                session['user_id'] = result['user']['id']
                session['username'] = result['user']['username']
                session['role'] = result['user']['role']
                
                # 如果选择记住登录，设置较长的会话期限
                if remember_me:
                    session.permanent = True
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"success": False, "error": "登录失败，请稍后重试"})
    
    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        """用户退出API"""
        try:
            session_token = session.get('session_token')
            
            if session_token:
                auth_manager.logout_user(session_token)
            
            # 清除会话
            session.clear()
            
            return jsonify({"success": True, "message": "退出成功"})
            
        except Exception as e:
            return jsonify({"success": False, "error": "退出失败"})
    
    @app.route('/api/auth/validate', methods=['GET'])
    def api_validate_session():
        """验证会话有效性API"""
        try:
            session_token = session.get('session_token') or request.headers.get('Authorization', '').replace('Bearer ', '')
            
            if not session_token:
                return jsonify({"success": False, "error": "未登录"})
            
            user_info = auth_manager.validate_session(session_token)
            
            if not user_info:
                session.clear()
                return jsonify({"success": False, "error": "会话已过期"})
            
            return jsonify({"success": True, "user": user_info})
            
        except Exception as e:
            return jsonify({"success": False, "error": "验证失败"})
    
    @app.route('/api/auth/change-password', methods=['POST'])
    @require_auth
    def api_change_password():
        """修改密码API"""
        try:
            data = request.get_json()
            
            old_password = data.get('old_password', '') or data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '') or new_password
            
            if not old_password or not new_password:
                return jsonify({"success": False, "error": "请填写完整的密码信息"})
            
            if len(new_password) < 8:
                return jsonify({"success": False, "error": "新密码至少需要8个字符"})
            
            if new_password != confirm_password:
                return jsonify({"success": False, "error": "两次输入的新密码不一致"})
            
            user_id = request.current_user['user_id']
            result = auth_manager.change_password(user_id, old_password, new_password)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"success": False, "error": "修改密码失败"})
    
    # ==================== 管理员路由 ====================
    
    @app.route('/admin')
    @require_admin
    def admin_dashboard():
        """管理员仪表板"""
        stats = user_service.get_system_stats()
        return render_template('admin/dashboard.html', stats=stats.get('stats', {}))
    
    @app.route('/admin/users')
    @require_admin
    def admin_users():
        """管理员用户管理页面"""
        page = request.args.get('page', 1, type=int)
        users_data = user_service.get_all_users(page)
        return render_template('admin/users.html', 
                             users=users_data.get('users', []),
                             pagination=users_data.get('pagination', {}))
    
    @app.route('/api/admin/users', methods=['GET'])
    @require_admin
    def api_admin_get_users():
        """获取用户列表API"""
        page = request.args.get('page', 1, type=int)
        result = user_service.get_all_users(page)
        return jsonify(result)
    
    @app.route('/api/admin/users/<int:user_id>', methods=['GET'])
    @require_admin
    def api_admin_get_user_detail(user_id):
        """获取用户详情API"""
        result = user_service.get_user_detail(user_id)
        return jsonify(result)
    
    @app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
    @require_admin
    def api_admin_update_user(user_id):
        """更新用户信息API"""
        try:
            data = request.get_json()
            result = user_service.update_user(user_id, data)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": "更新用户失败"})
    
    @app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @require_admin
    def api_admin_reset_password(user_id):
        """重置用户密码API"""
        try:
            data = request.get_json()
            new_password = data.get('new_password')
            
            if not new_password or len(new_password) < 8:
                return jsonify({"success": False, "error": "密码至少需要8个字符"})
            
            result = user_service.reset_user_password(user_id, new_password)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": "重置密码失败"})
    
    @app.route('/api/admin/users/<int:user_id>/toggle-status', methods=['POST'])
    @require_admin
    def api_admin_toggle_user_status(user_id):
        """切换用户状态API"""
        result = user_service.toggle_user_status(user_id)
        return jsonify(result)
    
    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    @require_admin
    def api_admin_delete_user(user_id):
        """删除用户API"""
        result = user_service.delete_user(user_id)
        return jsonify(result)
    
    @app.route('/api/admin/stats', methods=['GET'])
    @require_admin
    def api_admin_get_stats():
        """获取系统统计API"""
        result = user_service.get_system_stats()
        return jsonify(result)
    
    @app.route('/api/admin/logs', methods=['GET'])
    @require_admin
    def api_admin_get_logs():
        """获取登录日志API"""
        page = request.args.get('page', 1, type=int)
        result = user_service.get_login_logs(page)
        return jsonify(result)
    
    # ==================== 主要页面路由 ====================
    
    @app.route('/')
    @require_auth
    def index():
        """主页 - 助手选择"""
        # 直接使用chat_service获取助手列表，确保数据一致性
        try:
            # 延迟导入chat_service，确保在创建后使用
            from services.chat_service import ChatService
            temp_chat_service = ChatService()
            assistants = temp_chat_service.get_all_assistants()
            # 转换为模板需要的格式
            assistants_list = [(a['id'], a['name'], a['description'], a['icon']) for a in assistants]
        except Exception as e:
            print(f"获取助手列表失败: {e}")
            assistants_list = get_all_assistants()  # 备用方案
        
        games = get_all_games()
        recent_conversations = []
        
        return render_template('index.html', 
                             assistants=assistants_list,
                             games=games,
                             recent_conversations=recent_conversations)
    

    
    @app.route('/config')
    @require_auth
    def config_page():
        """配置页面"""
        # 加载当前配置
        current_config = Config.load_api_config()
        
        return render_template('config.html',
                             current_config=current_config)
    
    @app.route('/user-center')
    @require_auth
    def user_center_page():
        """用户中心页面"""
        try:
            # 从session获取用户信息
            user_id = session.get('user_id')
            username = session.get('username', 'Unknown')
            
            if not user_id:
                return redirect(url_for('login_page'))
            
            # 简化的用户统计数据，避免复杂的数据库查询错误
            user_stats = {
                "total_conversations": 0,
                "total_messages": 0,
                "days_since_created": 1,
                "login_count": 1,
                "last_login": "最近"
            }
            
            # 简化的用户信息
            user = {
                "id": user_id,
                "username": username,
                "email": f"{username}@example.com",
                "role": "user",
                "is_active": True,
                "created_at": "2024-01-01",
                "last_login": "最近"
            }
            
            # 空的最近活动
            recent_activities = []
            
            return render_template('user_center.html', 
                                 user=user, 
                                 user_stats=user_stats, 
                                 recent_activities=recent_activities)
        except Exception as e:
            print(f"用户中心错误: {e}")
            # 如果出错，直接返回基本页面
            return render_template('user_center.html', 
                                 user={"username": "User", "email": "user@example.com"},
                                 user_stats={"total_conversations": 0, "total_messages": 0, "days_since_created": 1, "login_count": 1, "last_login": "最近"},
                                 recent_activities=[])
    

    

    
    @app.route('/api/config', methods=['POST'])
    @require_auth
    def api_save_config():
        """保存配置API"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"success": False, "error": "无效的请求数据"})
            
            # 验证必要字段
            required_fields = ['platform', 'api_key', 'model']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({"success": False, "error": f"缺少字段: {field}"})
            
            # 构建配置
            config_data = {
                "dashscope_api_key": data.get('api_key') if data['platform'] == 'dashscope' else data.get('dashscope_api_key', ''),
                "openrouter_api_key": data.get('api_key') if data['platform'] == 'openrouter' else data.get('openrouter_api_key', ''),
                "current_platform": data['platform'],
                "current_model": data['model'],
                "image_model": data.get('image_model', Config.DEFAULT_IMAGE_MODEL)
            }
            
            # 调试信息：显示接收到的配置数据
            print(f"🔍 配置数据调试:")
            print(f"  平台: {config_data.get('current_platform', 'Unknown')}")
            print(f"  模型: {config_data.get('current_model', 'Unknown')}")
            
            # 验证API密钥
            if config_data['current_platform'] == 'openrouter':
                api_key = config_data.get('openrouter_api_key', '')
                print(f"🔍 OpenRouter密钥长度: {len(api_key)}")
                print(f"🔍 OpenRouter密钥前缀: {api_key[:15] if len(api_key) > 15 else api_key}...")
                test_ai_service = AIService(api_key=api_key, platform='openrouter')
            elif config_data['current_platform'] == 'dashscope':
                api_key = config_data.get('dashscope_api_key', '')
                print(f"🔍 DashScope密钥长度: {len(api_key)}")
                print(f"🔍 DashScope密钥前缀: {api_key[:15] if len(api_key) > 15 else api_key}...")
                if not api_key:
                    return jsonify({"success": False, "error": "请提供百炼API密钥"})
                test_ai_service = AIService(api_key=api_key, platform='dashscope')
            else:
                return jsonify({"success": False, "error": f"不支持的平台: {config_data['current_platform']}"})
            
            print(f"🔍 开始验证API密钥...")
            validation_result = test_ai_service.validate_api_key()
            print(f"🔍 验证结果: {validation_result}")
            
            if not validation_result:
                return jsonify({"success": False, "error": "API密钥验证失败，请检查密钥是否正确"})
            
            # 保存配置
            if Config.save_api_config(config_data):
                return jsonify({"success": True, "message": "配置保存成功"})
            else:
                return jsonify({"success": False, "error": "配置保存失败"})
                
        except Exception as e:
            return jsonify({"success": False, "error": f"保存配置时发生错误: {str(e)}"})
    
    @app.route('/api/models')
    @require_auth
    def api_get_models():
        """获取可用模型列表"""
        try:
            platform = request.args.get('platform', 'openrouter')
            
            # 创建临时AI服务实例获取模型列表
            if platform == 'openrouter':
                temp_ai_service = AIService(api_key="temp", platform='openrouter')
                models = temp_ai_service.get_available_models()
            elif platform == 'dashscope':
                temp_ai_service = AIService(api_key="temp", platform='dashscope')
                models = temp_ai_service.get_available_models()
            else:
                models = []
            
            return jsonify({
                "success": True,
                "models": models
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"获取模型列表失败: {str(e)}",
                "models": []
            })
    

    
    @app.route('/api/image', methods=['POST'])
    @require_auth
    def api_generate_image():
        """图像生成API"""
        try:
            data = request.get_json()
            prompt = data.get('prompt', '').strip()
            
            if not prompt:
                return jsonify({"success": False, "error": "请提供图像描述"})
            
            # 获取API配置
            api_config = Config.load_api_config()
            
            if api_config['current_platform'] != 'dashscope':
                return jsonify({"success": False, "error": "图像生成仅支持阿里云百炼平台"})
            
            # 初始化AI服务
            ai_service = AIService(
                platform='dashscope',
                api_key=api_config['dashscope_api_key'],
                model=api_config['image_model']
            )
            
            # 生成图像
            result = ai_service.generate_image(prompt)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"图像生成失败: {str(e)}"
            })
    
    @app.route('/api/image/result/<task_id>')
    @require_auth
    def api_get_image_result(task_id):
        """获取图像生成结果"""
        try:
            # 获取API配置
            api_config = Config.load_api_config()
            
            # 初始化AI服务
            ai_service = AIService(
                platform='dashscope',
                api_key=api_config['dashscope_api_key']
            )
            
            # 获取结果
            result = ai_service.get_image_result(task_id)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"获取图像结果失败: {str(e)}"
            })
    
    @app.route('/favicon.ico')
    def favicon():
        """Favicon处理"""
        return app.send_static_file('favicon.ico')
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    # ==================== 新增功能路由 ====================
    
    # ===== AI助手对话路由 =====
    @app.route('/assistant/<assistant_type>')
    @require_auth
    def assistant_chat(assistant_type):
        """AI助手对话页面 - 优化版本"""
        assistant_config = chat_service.get_assistant_config(assistant_type)
        if not assistant_config:
            return "助手类型不存在", 404
        
        session_id = request.args.get('session_id')
        # 优化：减少重定向，直接在前端处理新会话创建
        history = []
        if session_id:
            # 只有在存在session_id时才查询历史
            history = chat_service.get_conversation_history(session_id)
        
        # 延迟加载会话列表，通过AJAX获取
        return render_template('assistants/chat_v3.html',
                             assistant_config=assistant_config,
                             assistant_type=assistant_type,
                             session_id=session_id,
                             history=history)
    
    @app.route('/api/conversations/create', methods=['POST'])
    @require_auth
    def api_create_conversation():
        """创建新会话API"""
        try:
            data = request.get_json()
            assistant_type = data.get('assistant_type')
            
            if not assistant_type:
                return jsonify({'success': False, 'error': '缺少助手类型参数'})
            
            session_id = chat_service.create_conversation(assistant_type)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'redirect_url': f'/assistant/{assistant_type}?session_id={session_id}'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/conversations/list')
    @require_auth  
    def api_conversation_list():
        """获取会话列表API"""
        try:
            conversations = chat_service.get_conversation_list()
            return jsonify({'success': True, 'conversations': conversations})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/conversations/<session_id>', methods=['DELETE'])
    @require_auth
    def api_delete_conversation(session_id):
        """删除会话API"""
        try:
            success = chat_service.delete_conversation(session_id)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/assistant/chat', methods=['POST'])
    @require_auth
    def api_assistant_chat():
        """AI助手对话API"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            message = data.get('message', '').strip()
            stream = data.get('stream', False)
            
            if not session_id or not message:
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            if stream:
                return Response(
                    chat_service.process_message(session_id, message, stream=True),
                    mimetype='text/plain'
                )
            else:
                result = chat_service.process_message(session_id, message, stream=False)
                return jsonify(result)
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    

    

    # ===== AI游戏路由 =====
    
    # 剧本杀游戏
    @app.route('/game/script-host')
    @require_auth
    def script_host_game():
        """AI剧本杀主持人游戏页面"""
        session_id = request.args.get('session_id')
        if not session_id:
            # 创建新游戏
            session_id = script_game.create_new_game(user_id=session.get('user_id', 1))
            return redirect(url_for('script_host_game', session_id=session_id))
        
        # 获取游戏状态和最近消息
        game_state = script_game.load_game_state(session_id)
        recent_messages = script_game.get_game_messages(session_id, limit=20)
        
        return render_template('games/script_host.html',
                             session_id=session_id,
                             game_state=game_state,
                             recent_messages=recent_messages)
    
    @app.route('/api/game/script-host/start', methods=['POST'])
    @require_auth
    def api_start_script_game():
        """开始剧本杀游戏"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            script_type = data.get('script_type', 'modern_campus')
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少会话ID"})
            
            result = script_game.start_game(session_id, script_type)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/script-host/action', methods=['POST'])
    @require_auth
    def api_script_game_action():
        """处理剧本杀游戏行动"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            action = data.get('action', {})
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少会话ID"})
            
            result = script_game.handle_user_action(session_id, action)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # 推理侦探游戏
    @app.route('/game/detective')
    @require_auth
    def detective_game_page():
        """AI推理侦探游戏页面"""
        session_id = request.args.get('session_id')
        if not session_id:
            session_id = detective_game.create_new_game(user_id=session.get('user_id', 1))
            return redirect(url_for('detective_game_page', session_id=session_id))
        
        game_state = detective_game.load_game_state(session_id)
        recent_messages = detective_game.get_game_messages(session_id, limit=20)
        
        return render_template('games/detective.html',
                             session_id=session_id,
                             game_state=game_state,
                             recent_messages=recent_messages)
    
    @app.route('/api/game/detective/start', methods=['POST'])
    @require_auth
    def api_start_detective_game():
        """开始推理侦探游戏"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            case_type = data.get('case_type', 'murder')
            
            result = detective_game.start_case(session_id, case_type)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/detective/interrogate', methods=['POST'])
    @require_auth
    def api_detective_interrogate():
        """审讯嫌疑人"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            suspect_name = data.get('suspect_name')
            question = data.get('question', '')
            
            if not all([session_id, suspect_name, question]):
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            result = detective_game.interrogate_suspect(session_id, suspect_name, question)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/detective/analyze', methods=['POST'])
    @require_auth
    def api_detective_analyze():
        """分析证据"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            evidence_name = data.get('evidence_name')
            
            if not all([session_id, evidence_name]):
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            result = detective_game.analyze_evidence(session_id, evidence_name)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/detective/evidence', methods=['GET'])
    @require_auth
    def api_detective_evidence_list():
        """获取证据列表"""
        try:
            session_id = request.args.get('session_id')
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少session_id参数"})
            
            result = detective_game.get_evidence_list(session_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/detective/messages', methods=['GET'])
    @require_auth
    def api_detective_messages():
        """获取游戏消息"""
        try:
            session_id = request.args.get('session_id')
            limit = request.args.get('limit', 20)
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少session_id参数"})
            
            messages = detective_game.get_game_messages(session_id, limit=int(limit))
            return jsonify({
                "success": True,
                "messages": messages
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/detective/conclude', methods=['POST'])
    @require_auth
    def api_detective_conclude():
        """提交推理结论"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            suspect = data.get('suspect')
            reasoning = data.get('reasoning')
            
            if not all([session_id, suspect, reasoning]):
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            result = detective_game.submit_conclusion(session_id, suspect, reasoning)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # 狼人杀游戏
    @app.route('/game/werewolf')
    @require_auth
    def werewolf_game_page():
        """AI狼人杀法官游戏页面"""
        session_id = request.args.get('session_id')
        if not session_id:
            session_id = werewolf_game.create_new_game()
            return redirect(url_for('werewolf_game_page', session_id=session_id))
        
        game_state = werewolf_game.load_game_state(session_id)
        messages = werewolf_game.get_game_messages(session_id)
        current_phase = werewolf_game.get_current_phase(session_id)
        player_role = werewolf_game.get_player_role(session_id)
        alive_players = werewolf_game.get_alive_players(session_id)
        
        return render_template('games/werewolf.html',
                             session_id=session_id,
                             game_state=game_state,
                             messages=messages,
                             current_phase=current_phase,
                             player_role=player_role,
                             alive_players=alive_players)
    
    @app.route('/api/game/werewolf/speak', methods=['POST'])
    @require_auth
    def api_werewolf_speak():
        """狼人杀玩家发言"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            message = data.get('message', '').strip()
            
            if not session_id or not message:
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            success = werewolf_game.player_speak(session_id, message)
            
            if success:
                # 获取最新消息
                messages = werewolf_game.get_game_messages(session_id, limit=10)
                return jsonify({
                    "success": True,
                    "messages": messages
                })
            else:
                return jsonify({"success": False, "error": "发言失败"})
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/werewolf/vote', methods=['POST'])
    @require_auth
    def api_werewolf_vote():
        """狼人杀投票"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            target_number = data.get('target_number')
            
            if not session_id or target_number is None:
                return jsonify({"success": False, "error": "缺少必要参数"})
            
            success = werewolf_game.player_vote(session_id, int(target_number))
            
            if success:
                # 获取最新消息和游戏状态
                messages = werewolf_game.get_game_messages(session_id, limit=10)
                current_phase = werewolf_game.get_current_phase(session_id)
                alive_players = werewolf_game.get_alive_players(session_id)
                
                return jsonify({
                    "success": True,
                    "messages": messages,
                    "current_phase": current_phase,
                    "alive_players": alive_players
                })
            else:
                return jsonify({"success": False, "error": "投票失败"})
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/werewolf/start-voting', methods=['POST'])
    @require_auth
    def api_werewolf_start_voting():
        """开始投票阶段"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少session_id"})
            
            success = werewolf_game.start_voting(session_id)
            
            if success:
                messages = werewolf_game.get_game_messages(session_id, limit=5)
                return jsonify({
                    "success": True,
                    "messages": messages,
                    "current_phase": "day_voting"
                })
            else:
                return jsonify({"success": False, "error": "开始投票失败"})
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/api/game/werewolf/status', methods=['GET'])
    @require_auth
    def api_werewolf_status():
        """获取狼人杀游戏状态"""
        try:
            session_id = request.args.get('session_id')
            
            if not session_id:
                return jsonify({"success": False, "error": "缺少session_id"})
            
            messages = werewolf_game.get_game_messages(session_id, limit=20)
            current_phase = werewolf_game.get_current_phase(session_id)
            player_role = werewolf_game.get_player_role(session_id)
            alive_players = werewolf_game.get_alive_players(session_id)
            
            return jsonify({
                "success": True,
                "messages": messages,
                "current_phase": current_phase,
                "player_role": player_role,
                "alive_players": alive_players
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # ===== 模型切换API =====
    @app.route('/api/model/switch', methods=['POST'])
    @require_auth
    def api_switch_model():
        """切换AI模型"""
        try:
            data = request.get_json()
            model = data.get('model')
            
            if not model:
                return jsonify({"success": False, "error": "缺少模型参数"})
            
            success = chat_service.set_ai_model(model)
            if success:
                return jsonify({"success": True, "message": f"已切换到{model}模型"})
            else:
                return jsonify({"success": False, "error": "不支持的模型"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    

    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )