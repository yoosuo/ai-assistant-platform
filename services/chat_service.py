#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话管理服务 - 处理AI助手对话
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Optional, Generator
from utils.database import DatabaseManager
from services.ai_service import AIService
from prompts.assistant_prompts import get_assistant_prompt, ASSISTANT_PROMPTS

class ChatService:
    """对话管理服务"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ai_service = AIService()
        
        # 使用统一的助手配置
        self.assistant_configs = ASSISTANT_PROMPTS
    
    def get_assistant_config(self, assistant_type: str) -> Optional[Dict]:
        """获取助手配置"""
        return self.assistant_configs.get(assistant_type)
    
    def get_all_assistants(self) -> List[Dict]:
        """获取所有助手信息"""
        assistants = []
        for assistant_id, config in self.assistant_configs.items():
            assistants.append({
                'id': assistant_id,
                'name': config['name'],
                'icon': config['icon'],
                'description': config.get('description', config['system_prompt'][:100] + '...'),
                'theme_color': config.get('theme_color', '#6B7280'),
                'features': config.get('features', [])
            })
        return assistants
    
    def create_conversation(self, assistant_type: str, user_id: int = 1, title: str = None) -> str:
        """创建新对话"""
        session_id = str(uuid.uuid4())
        assistant_config = self.get_assistant_config(assistant_type)
        
        if not assistant_config:
            raise ValueError(f"未知的助手类型: {assistant_type}")
        
        if not title:
            title = f"与{assistant_config['name']}的对话"
        
        self.db.create_conversation(
            session_id=session_id,
            user_id=user_id,
            assistant_type=assistant_type,
            title=title
        )
        
        return session_id
    
    def rename_conversation(self, session_id: str, new_title: str) -> bool:
        """重命名对话"""
        return self.db.rename_conversation(session_id, new_title)
    
    def delete_conversation(self, session_id: str) -> bool:
        """删除对话"""
        return self.db.delete_conversation(session_id)
    
    def get_conversation_list(self, user_id: int = 1, limit: int = 20) -> List[Dict]:
        """获取对话列表"""
        conversations = self.db.get_user_conversations(user_id, limit)
        
        # 添加助手信息
        for conv in conversations:
            assistant_config = self.get_assistant_config(conv['assistant_type'])
            if assistant_config:
                conv['assistant_name'] = assistant_config['name']
                conv['assistant_icon'] = assistant_config['icon']
        
        return conversations
    
    def process_message(self, session_id: str, user_message: str, stream: bool = False) -> Dict:
        """处理用户消息"""
        # 获取对话信息
        conversation = self.db.get_conversation(session_id)
        if not conversation:
            return {'success': False, 'error': '对话不存在'}
        
        assistant_type = conversation['assistant_type']
        assistant_config = self.get_assistant_config(assistant_type)
        
        if not assistant_config:
            return {'success': False, 'error': '助手配置不存在'}
        
        # 保存用户消息
        self.db.add_message(session_id, 'user', user_message)
        
        # 构建对话上下文
        messages = self._build_conversation_context(session_id, assistant_config)
        
        # 调用AI生成回复
        if stream:
            return self._process_stream_response(session_id, messages)
        else:
            return self._process_sync_response(session_id, messages)
    
    def _build_conversation_context(self, session_id: str, assistant_config: Dict) -> List[Dict]:
        """构建对话上下文"""
        messages = [
            {'role': 'system', 'content': assistant_config['system_prompt']}
        ]
        
        # 获取历史消息
        history = self.db.get_conversation_history(session_id, limit=20)
        
        for msg in history:
            messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        return messages
    
    def _process_sync_response(self, session_id: str, messages: List[Dict]) -> Dict:
        """处理同步响应"""
        result = self.ai_service.chat(messages, stream=False)
        
        if result.get('success'):
            # 保存AI回复
            self.db.add_message(session_id, 'assistant', result['content'])
            
            return {
                'success': True,
                'content': result['content'],
                'usage': result.get('usage', {})
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '生成回复失败')
            }
    
    def _process_stream_response(self, session_id: str, messages: List[Dict]) -> Generator[str, None, None]:
        """处理流式响应"""
        try:
            full_response = ""
            
            for chunk in self.ai_service.chat(messages, stream=True):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            # 保存完整回复
            if full_response:
                self.db.add_message(session_id, 'assistant', full_response)
            
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取对话历史"""
        return self.db.get_conversation_history(session_id, limit)
    
    def export_conversation(self, session_id: str) -> Dict:
        """导出对话"""
        conversation = self.db.get_conversation(session_id)
        history = self.db.get_conversation_history(session_id)
        
        return {
            'conversation_info': conversation,
            'messages': history,
            'export_time': datetime.now().isoformat()
        }
    
    def delete_conversation(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        try:
            # 删除会话消息
            self.db.delete_conversation_messages(session_id)
            # 删除会话记录
            self.db.delete_conversation(session_id)
            return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False
    
    def set_ai_model(self, model: str) -> bool:
        """设置AI模型"""
        return self.ai_service.set_model(model)
    
    def get_available_models(self) -> List[str]:
        """获取可用模型"""
        return self.ai_service.get_available_models()