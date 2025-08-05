#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI剧本杀主持人游戏 - 完全重构版
"""

import json
import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService
from services.ai_character_manager import AICharacterManager
from services.game_automation import GameAutomation
from utils.database import DatabaseManager
from prompts.game_prompts import get_script_prompt, GameContentGenerator


class ScriptHostGame:
    """AI剧本杀主持人游戏"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.character_manager = AICharacterManager()
        self.automation = GameAutomation()
        self.db = DatabaseManager()
    
    def create_new_game(self, user_id: int = 1) -> str:
        """创建新游戏"""
        session_id = str(uuid.uuid4())
        
        # 随机选择剧本类型
        script_type = GameContentGenerator.generate_random_script_type()
        
        # 创建游戏会话
        config = {
            'script_type': script_type,
            'max_players': 6,
            'current_phase': 'preparation'
        }
        
        self.db.create_game_session(session_id, 'ai_script_host', user_id, config)
        
        # 立即开始游戏初始化
        self._initialize_game(session_id, script_type)
        
        return session_id
    
    def load_game_state(self, session_id: str) -> Optional[Dict]:
        """加载游戏状态"""
        return self.db.get_game_session(session_id)
    
    def get_game_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取游戏消息"""
        return self.db.get_game_messages(session_id, limit)
    
    def _initialize_game(self, session_id: str, script_type: str):
        """初始化游戏"""
        # 1. 生成剧本
        script_data = self._generate_script(script_type)
        
        # 2. 保存剧本数据
        self.db.set_game_state(session_id, 'script_data', json.dumps(script_data))
        self.db.set_game_state(session_id, 'truth', json.dumps(script_data.get('truth', {})))
        
        # 3. 创建AI角色
        self._create_ai_characters(session_id, script_data)
        
        # 4. 分配用户角色
        user_character = self._assign_user_character(session_id, script_data)
        self.db.set_game_state(session_id, 'user_character', json.dumps(user_character))
        
        # 5. 发送开场消息
        self._send_introduction(session_id, script_data, user_character)
        
        # 6. 启动游戏自动化
        self.automation.start_game_automation(session_id, 'ai_script_host')
    
    def _generate_script(self, script_type: str) -> Dict:
        """生成剧本"""
        prompt = get_script_prompt(script_type)
        
        # 使用AI生成剧本
        script_content = self.ai_service.chat(
            messages=[{"role": "user", "content": prompt}]
        )['content']
        
        try:
            # 尝试解析JSON
            script_data = json.loads(script_content)
            return script_data
        except json.JSONDecodeError:
            # 如果解析失败，生成默认剧本
            return self._generate_fallback_script(script_type)
    
    def _generate_fallback_script(self, script_type: str) -> Dict:
        """生成备用剧本"""
        character_names = GameContentGenerator.generate_character_names(6)
        
        if script_type == 'modern_campus':
            return {
                'case_info': {
                    'title': '校园夜惊魂',
                    'background': '深夜的图书馆里，学生会主席被发现死在阅览室，门窗紧闭，没有外人进入的痕迹...',
                    'location': '大学图书馆阅览室',
                    'time': '周三晚上11点30分',
                    'victim': character_names[0]
                },
                'characters': [
                    {
                        'name': character_names[1],
                        'role': '室友',
                        'background': f'死者{character_names[0]}的室友，最后见到死者的人',
                        'personality': '紧张敏感，容易激动',
                        'secret': '当晚偷偷出门见网友，没有不在场证明',
                        'motive': '无直接动机，但行为可疑'
                    },
                    {
                        'name': character_names[2],
                        'role': '副主席',
                        'background': '学生会副主席，一直想要主席的位置',
                        'personality': '野心勃勃，善于伪装',
                        'secret': '已经暗中联络了大部分学生会成员',
                        'motive': '夺取学生会控制权'
                    },
                    {
                        'name': character_names[3],
                        'role': '前恋人',
                        'background': f'死者的前男/女友，最近刚分手',
                        'personality': '情绪化，容易冲动',
                        'secret': '分手是因为发现死者背叛',
                        'motive': '感情报复'
                    },
                    {
                        'name': character_names[4],
                        'role': '学霸',
                        'background': '成绩优异的学生，与死者有学术竞争',
                        'personality': '理性冷静，逻辑性强',
                        'secret': '曾经因为死者作弊被举报而失去奖学金',
                        'motive': '学术报复'
                    },
                    {
                        'name': character_names[5],
                        'role': '保安',
                        'background': '夜班保安，负责图书馆安全',
                        'personality': '老实本分，但有心事',
                        'secret': '当晚睡着了，没有履行职责',
                        'motive': '失职恐惧，想要掩盖真相'
                    }
                ],
                'clues': [
                    {'id': 'clue_1', 'description': '死者手机上的神秘短信', 'location': '现场', 'importance': 5},
                    {'id': 'clue_2', 'description': '图书馆门禁记录异常', 'location': '保安室', 'importance': 4},
                    {'id': 'clue_3', 'description': '死者桌上的学生会改选计划', 'location': '现场', 'importance': 3},
                    {'id': 'clue_4', 'description': '垃圾桶里的撕碎情书', 'location': '现场附近', 'importance': 4},
                    {'id': 'clue_5', 'description': '监控摄像头的盲区分析', 'location': '保安室', 'importance': 5},
                    {'id': 'clue_6', 'description': '死者最近的银行流水', 'location': '调查获得', 'importance': 3},
                    {'id': 'clue_7', 'description': '奖学金评选的争议记录', 'location': '教务处', 'importance': 4},
                    {'id': 'clue_8', 'description': '保安值班记录的涂改', 'location': '保安室', 'importance': 5}
                ],
                'truth': {
                    'culprit': character_names[2],  # 副主席
                    'method': '趁死者独自在图书馆时，用书本砸击头部',
                    'motive': '为了夺取学生会主席位置，消除唯一的竞争对手',
                    'evidence': '门禁记录显示副主席当晚进入过图书馆，但监控被人为破坏'
                }
            }
        else:
            # 其他剧本类型的默认实现
            return {
                'case_info': {
                    'title': f'{script_type}剧本杀',
                    'background': '一个神秘的案件等待您的推理...',
                    'location': '神秘地点',
                    'time': '神秘时间',
                    'victim': character_names[0]
                },
                'characters': [
                    {
                        'name': name,
                        'role': f'角色{i+1}',
                        'background': f'神秘角色{i+1}的背景',
                        'personality': random.choice(GameContentGenerator.generate_personalities()),
                        'secret': f'角色{i+1}的秘密',
                        'motive': '未知动机'
                    }
                    for i, name in enumerate(character_names[1:])
                ],
                'clues': [
                    {'id': f'clue_{i+1}', 'description': f'线索{i+1}', 'importance': random.randint(1, 5)}
                    for i in range(8)
                ],
                'truth': {
                    'culprit': character_names[2],
                    'method': '未知手段',
                    'motive': '未知动机'
                }
            }
    
    def _create_ai_characters(self, session_id: str, script_data: Dict):
        """创建AI角色"""
        characters = script_data.get('characters', [])
        
        for char_data in characters:
            character_id = self.character_manager.create_character(
                session_id=session_id,
                name=char_data['name'],
                character_type='npc',
                personality=char_data.get('personality', '普通性格'),
                background=char_data.get('background', ''),
                secrets=char_data.get('secret', '')
            )
            
            # 添加初始记忆
            self.character_manager.update_character_memory(
                session_id, character_id,
                f"我是{char_data['name']}，身份是{char_data.get('role', '未知')}",
                f"背景：{char_data.get('background', '')}"
            )
    
    def _assign_user_character(self, session_id: str, script_data: Dict) -> Dict:
        """分配用户角色"""
        # 用户扮演一个参与推理的侦探角色，不是剧本中的嫌疑人
        user_character = {
            'name': '侦探',
            'role': 'detective',
            'background': '专业侦探，负责调查案件真相',
            'abilities': ['调查现场', '询问角色', '分析线索', '进行推理'],
            'known_info': script_data['case_info']
        }
        
        return user_character
    
    def _send_introduction(self, session_id: str, script_data: Dict, user_character: Dict):
        """发送开场介绍"""
        case_info = script_data['case_info']
        
        introduction = f"""
🎭 **{case_info['title']}**

欢迎来到今晚的剧本杀！

**案件背景**：
{case_info['background']}

**基本信息**：
- 📍 地点：{case_info['location']}
- ⏰ 时间：{case_info['time']}
- 💀 受害者：{case_info['victim']}

**您的身份**：{user_character['name']}
您将作为侦探参与这次调查，可以：
- 🔍 调查现场寻找线索
- 💬 询问在场人员
- 🧠 进行逻辑推理
- ⚖️ 最终指控真凶

游戏即将开始，各位角色已经就位。您可以随时开始调查！
        """
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content=introduction,
            phase='introduction'
        )
    
    def handle_user_action(self, session_id: str, action: Dict) -> Dict:
        """处理用户行动"""
        action_type = action.get('type')
        
        if action_type == 'investigate':
            return self._handle_investigation(session_id, action)
        elif action_type == 'question_character':
            return self._handle_character_question(session_id, action)
        elif action_type == 'analyze_clue':
            return self._handle_clue_analysis(session_id, action)
        elif action_type == 'make_accusation':
            return self._handle_accusation(session_id, action)
        elif action_type == 'get_status':
            return self._get_game_status(session_id)
        else:
            return {'success': False, 'error': '未知的行动类型'}
    
    def _handle_investigation(self, session_id: str, action: Dict) -> Dict:
        """处理调查行动"""
        target = action.get('target', '现场')
        
        # 获取剧本数据
        script_data_str = self.db.get_game_state(session_id, 'script_data')
        if not script_data_str:
            return {'success': False, 'error': '游戏数据不存在'}
        
        script_data = json.loads(script_data_str)
        clues = script_data.get('clues', [])
        
        # 根据调查目标返回相关线索
        available_clues = [clue for clue in clues if target.lower() in clue.get('location', '').lower()]
        
        if not available_clues:
            # 如果没有特定线索，返回一般调查结果
            result = f"您仔细调查了{target}，但没有发现明显的线索。也许需要换个角度思考。"
        else:
            # 随机返回一个线索
            clue = random.choice(available_clues)
            result = f"🔍 **发现线索**：{clue['description']}\n\n这条线索的重要性：{'⭐' * clue.get('importance', 1)}"
            
            # 记录已发现的线索
            discovered_clues = self.db.get_game_state(session_id, 'discovered_clues')
            if discovered_clues:
                discovered_list = json.loads(discovered_clues)
            else:
                discovered_list = []
            
            if clue['id'] not in discovered_list:
                discovered_list.append(clue['id'])
                self.db.set_game_state(session_id, 'discovered_clues', json.dumps(discovered_list))
        
        # 记录行动
        self.db.add_game_action(
            session_id, 'user', 'investigate',
            {'target': target}, result
        )
        
        # 添加到消息记录
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='user',
            speaker_name='侦探',
            speaker_type='user',
            content=f"调查了{target}",
            phase='investigation'
        )
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='system',
            speaker_name='系统',
            speaker_type='system',
            content=result,
            phase='investigation'
        )
        
        return {'success': True, 'result': result}
    
    def _handle_character_question(self, session_id: str, action: Dict) -> Dict:
        """处理角色询问"""
        character_name = action.get('character')
        question = action.get('question')
        
        if not character_name or not question:
            return {'success': False, 'error': '缺少角色名称或问题'}
        
        # 找到对应的AI角色
        characters = self.character_manager.get_all_characters(session_id)
        target_character = None
        
        for char in characters:
            if char.name == character_name:
                target_character = char
                break
        
        if not target_character:
            return {'success': False, 'error': f'未找到角色：{character_name}'}
        
        # 获取游戏背景信息
        script_data_str = self.db.get_game_state(session_id, 'script_data')
        script_data = json.loads(script_data_str) if script_data_str else {}
        
        game_context = f"案件：{script_data.get('case_info', {}).get('title', '未知案件')}"
        
        # 生成AI角色回应
        response = self.character_manager.generate_character_response(
            session_id, target_character.character_id,
            question, game_context, 'dialogue'
        )
        
        # 添加到消息记录
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='user',
            speaker_name='侦探',
            speaker_type='user',
            content=f"询问{character_name}：{question}",
            phase='investigation'
        )
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id=target_character.character_id,
            speaker_name=character_name,
            speaker_type='npc',
            content=response,
            phase='investigation'
        )
        
        return {
            'success': True,
            'character': character_name,
            'response': response
        }
    
    def _handle_clue_analysis(self, session_id: str, action: Dict) -> Dict:
        """处理线索分析"""
        clue_description = action.get('clue', '')
        
        # 使用AI分析线索
        analysis_prompt = f"""
作为剧本杀主持人，请分析以下线索：

线索：{clue_description}

请提供：
1. 这条线索可能指向什么
2. 与其他信息的关联性
3. 推理方向建议
4. 注意事项

要求：
- 不要直接透露答案
- 提供有用的分析方向
- 保持悬疑感
- 控制在150字以内
        """
        
        analysis = self.ai_service.generate_content(analysis_prompt)
        
        # 添加到消息记录
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='user',
            speaker_name='侦探',
            speaker_type='user',
            content=f"分析线索：{clue_description}",
            phase='investigation'
        )
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='system',
            speaker_name='分析系统',
            speaker_type='system',
            content=f"🧠 **线索分析**：\n{analysis}",
            phase='investigation'
        )
        
        return {'success': True, 'analysis': analysis}
    
    def _handle_accusation(self, session_id: str, action: Dict) -> Dict:
        """处理指控"""
        accused = action.get('accused', '')
        reasoning = action.get('reasoning', '')
        
        # 获取真相
        truth_str = self.db.get_game_state(session_id, 'truth')
        if not truth_str:
            return {'success': False, 'error': '游戏真相数据缺失'}
        
        truth = json.loads(truth_str)
        correct_culprit = truth.get('culprit', '')
        
        is_correct = accused.lower() == correct_culprit.lower()
        
        if is_correct:
            result_message = f"""
🎉 **恭喜！推理正确！**

您成功指出了真凶：**{accused}**

**真相揭露**：
- 凶手：{truth.get('culprit')}
- 作案手法：{truth.get('method')}
- 作案动机：{truth.get('motive')}
- 关键证据：{truth.get('evidence', '无')}

您的推理过程：
{reasoning}

感谢参与这次精彩的剧本杀体验！
            """
            game_status = 'won'
        else:
            result_message = f"""
❌ **推理有误**

您指控的是：**{accused}**
真正的凶手是：**{correct_culprit}**

**正确真相**：
- 凶手：{truth.get('culprit')}
- 作案手法：{truth.get('method')}
- 作案动机：{truth.get('motive')}

虽然这次没有猜中，但推理过程很精彩！
            """
            game_status = 'lost'
        
        # 更新游戏状态
        self.db.set_game_state(session_id, 'game_status', game_status)
        
        # 记录最终结果
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='user',
            speaker_name='侦探',
            speaker_type='user',
            content=f"指控{accused}为凶手。推理：{reasoning}",
            phase='accusation'
        )
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content=result_message,
            phase='revelation'
        )
        
        # 停止游戏自动化
        self.automation.stop_game_automation(session_id)
        
        return {
            'success': True,
            'correct': is_correct,
            'result': result_message,
            'truth': truth
        }
    
    def _get_game_status(self, session_id: str) -> Dict:
        """获取游戏状态"""
        # 获取基本游戏信息
        game_session = self.db.get_game_session(session_id)
        if not game_session:
            return {'success': False, 'error': '游戏不存在'}
        
        # 获取已发现的线索
        discovered_clues = self.db.get_game_state(session_id, 'discovered_clues')
        discovered_list = json.loads(discovered_clues) if discovered_clues else []
        
        # 获取角色列表
        characters = self.character_manager.get_all_characters(session_id)
        character_list = [
            {
                'name': char.name,
                'type': char.character_type,
                'background': char.background
            }
            for char in characters
        ]
        
        # 获取最近的消息
        recent_messages = self.db.get_game_messages(session_id, limit=10)
        
        return {
            'success': True,
            'session_id': session_id,
            'phase': game_session.get('current_phase', 'unknown'),
            'discovered_clues_count': len(discovered_list),
            'characters': character_list,
            'recent_messages': recent_messages
        }
    
    def get_game_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取游戏消息"""
        return self.db.get_game_messages(session_id, limit=limit)