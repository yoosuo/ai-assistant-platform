#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI角色管理器 - 处理游戏中的AI角色扮演和记忆
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService
from utils.database import DatabaseManager


class AICharacter:
    """单个AI角色类"""
    
    def __init__(self, character_id: str, name: str, character_type: str, 
                 personality: str, background: str, secrets: str = ""):
        self.character_id = character_id
        self.name = name
        self.character_type = character_type  # 'player', 'npc', 'judge', 'suspect'
        self.personality = personality
        self.background = background
        self.secrets = secrets
        self.memory = []  # 存储对话记忆
        self.is_alive = True
        
    def add_memory(self, event: str, context: str = ""):
        """添加记忆"""
        memory_item = {
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'context': context
        }
        self.memory.append(memory_item)
        
        # 只保留最近50条记忆，避免记忆过长
        if len(self.memory) > 50:
            self.memory = self.memory[-50:]
    
    def get_recent_memory(self, limit: int = 10) -> str:
        """获取最近的记忆摘要"""
        if not self.memory:
            return "暂无记忆"
        
        recent_memories = self.memory[-limit:]
        memory_text = "\n".join([
            f"- {item['event']}" for item in recent_memories
        ])
        return memory_text
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'character_id': self.character_id,
            'name': self.name,
            'character_type': self.character_type,
            'personality': self.personality,
            'background': self.background,
            'secrets': self.secrets,
            'memory': self.memory,
            'is_alive': self.is_alive
        }


class AICharacterManager:
    """AI角色管理器"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.db = DatabaseManager()
        self.characters = {}  # session_id -> {character_id: AICharacter}
    
    def create_character(self, session_id: str, name: str, character_type: str,
                        personality: str, background: str, secrets: str = "") -> str:
        """创建AI角色"""
        character_id = str(uuid.uuid4())[:8]
        
        character = AICharacter(
            character_id=character_id,
            name=name,
            character_type=character_type,
            personality=personality,
            background=background,
            secrets=secrets
        )
        
        # 保存到内存
        if session_id not in self.characters:
            self.characters[session_id] = {}
        self.characters[session_id][character_id] = character
        
        # 保存到数据库
        self.db.add_game_character(
            session_id=session_id,
            character_id=character_id,
            name=name,
            character_type=character_type,
            personality=personality,
            background=background,
            secrets=secrets,
            memory=json.dumps(character.memory)
        )
        
        return character_id
    
    def load_characters(self, session_id: str):
        """从数据库加载角色"""
        characters_data = self.db.get_game_characters(session_id)
        
        if session_id not in self.characters:
            self.characters[session_id] = {}
        
        for char_data in characters_data:
            character = AICharacter(
                character_id=char_data['character_id'],
                name=char_data['character_name'],
                character_type=char_data['character_type'],
                personality=char_data['personality'] or "",
                background=char_data['background'] or "",
                secrets=char_data['secrets'] or ""
            )
            
            # 加载记忆
            if char_data['memory']:
                try:
                    character.memory = json.loads(char_data['memory'])
                except:
                    character.memory = []
            
            character.is_alive = bool(char_data['is_alive'])
            self.characters[session_id][character.character_id] = character
    
    def get_character(self, session_id: str, character_id: str) -> Optional[AICharacter]:
        """获取角色"""
        if session_id in self.characters:
            return self.characters[session_id].get(character_id)
        return None
    
    def get_all_characters(self, session_id: str) -> List[AICharacter]:
        """获取会话中的所有角色"""
        if session_id in self.characters:
            return list(self.characters[session_id].values())
        return []
    
    def update_character_memory(self, session_id: str, character_id: str, event: str, context: str = ""):
        """更新角色记忆"""
        character = self.get_character(session_id, character_id)
        if character:
            character.add_memory(event, context)
            
            # 保存到数据库
            memory_json = json.dumps(character.memory)
            self.db.update_character_memory(session_id, character_id, memory_json)
    
    def generate_character_response(self, session_id: str, character_id: str, 
                                  user_input: str, game_context: str = "",
                                  response_type: str = "dialogue") -> str:
        """生成AI角色回应"""
        character = self.get_character(session_id, character_id)
        if not character:
            return "角色未找到"
        
        # 构建角色扮演提示词
        prompt = self._build_character_prompt(character, user_input, game_context, response_type)
        
        # 生成回应
        response = self.ai_service.chat(
            messages=[{"role": "user", "content": prompt}]
        )['content']
        
        # 更新角色记忆
        self.update_character_memory(
            session_id, character_id,
            f"回应了玩家的话: {user_input[:50]}...",
            f"我的回答: {response[:50]}..."
        )
        
        return response
    
    def _build_character_prompt(self, character: AICharacter, user_input: str, 
                               game_context: str, response_type: str) -> str:
        """构建角色扮演提示词"""
        base_prompt = f"""
你现在要扮演一个游戏角色：{character.name}

**角色信息**：
- 性格：{character.personality}
- 背景：{character.background}
- 秘密：{character.secrets}
- 当前状态：{'存活' if character.is_alive else '已死亡'}

**最近记忆**：
{character.get_recent_memory()}

**游戏背景**：
{game_context}

**玩家说**："{user_input}"

**回应要求**：
1. 严格按照角色的性格和背景来回应
2. 保持角色一致性，记住之前的对话
3. 根据秘密信息，可以隐瞒真相但不要完全说谎
4. 回应要自然、有戏剧性
5. 控制回应长度在100字以内
"""
        
        if response_type == "accusation":
            base_prompt += "\n6. 这是一个指控场景，要表现出相应的情绪反应"
        elif response_type == "investigation":
            base_prompt += "\n6. 这是调查场景，根据你的角色提供合理的信息"
        elif response_type == "voting":
            base_prompt += "\n6. 这是投票场景，解释你的投票理由"
        
        base_prompt += "\n\n请直接回应，不要包含角色名称前缀："
        
        return base_prompt
    
    def get_characters_by_type(self, session_id: str, character_type: str) -> List[AICharacter]:
        """根据类型获取角色"""
        all_chars = self.get_all_characters(session_id)
        return [char for char in all_chars if char.character_type == character_type]
    
    def kill_character(self, session_id: str, character_id: str):
        """杀死角色"""
        character = self.get_character(session_id, character_id)
        if character:
            character.is_alive = False
            self.update_character_memory(session_id, character_id, "我被杀死了", "游戏结束")
    
    def revive_character(self, session_id: str, character_id: str):
        """复活角色"""
        character = self.get_character(session_id, character_id)
        if character:
            character.is_alive = True
            self.update_character_memory(session_id, character_id, "我被复活了", "重新回到游戏")