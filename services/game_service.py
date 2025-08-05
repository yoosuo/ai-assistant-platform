#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏服务 - 处理AI游戏逻辑
"""

import uuid
import json
import random
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService
from utils.database import DatabaseManager

class GameService:
    """游戏服务基类"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.db = DatabaseManager()
        
        # 游戏配置
        self.game_configs = {
            'ai_script_host': {
                'name': 'AI剧本杀主持人',
                'icon': '🎭',
                'description': 'AI生成剧本，扮演所有NPC，为您提供沉浸式剧本杀体验',
                'theme': 'script-host'
            },
            'ai_detective_game': {
                'name': 'AI推理侦探游戏',
                'icon': '🔍',
                'description': '面对面审问嫌疑人，分析证据，找出真凶',
                'theme': 'detective'
            },
            'ai_werewolf_judge': {
                'name': 'AI狼人杀法官',
                'icon': '🐺',
                'description': 'AI扮演法官和玩家，体验完整狼人杀游戏',
                'theme': 'werewolf'
            }
        }
    
    def get_game_config(self, game_type: str) -> Optional[Dict]:
        """获取游戏配置"""
        return self.game_configs.get(game_type)
    
    def get_all_games(self) -> List[Dict]:
        """获取所有游戏信息"""
        games = []
        for game_id, config in self.game_configs.items():
            games.append({
                'id': game_id,
                'name': config['name'],
                'icon': config['icon'],
                'description': config['description'],
                'theme': config['theme']
            })
        return games
    
    def create_game_session(self, game_type: str, user_id: int = 1) -> str:
        """创建游戏会话"""
        session_id = str(uuid.uuid4())
        
        initial_state = {
            'game_type': game_type,
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'user_id': user_id
        }
        
        self.db.save_game_session(session_id, game_type, initial_state, user_id)
        return session_id
    
    def save_game_state(self, session_id: str, state: Dict):
        """保存游戏状态"""
        state['updated_at'] = datetime.now().isoformat()
        self.db.update_game_state(session_id, state)
    
    def load_game_state(self, session_id: str) -> Optional[Dict]:
        """加载游戏状态"""
        return self.db.get_game_state(session_id)

class ScriptHostGame(GameService):
    """AI剧本杀主持人游戏"""
    
    def start_game(self, session_id: str, script_type: str = 'modern_campus') -> Dict:
        """开始游戏"""
        try:
            # 生成剧本
            script = self.generate_script(script_type)
            
            # 生成角色
            characters = self.generate_characters(script, player_count=6)
            
            # 初始化游戏状态
            game_state = {
                'game_type': 'ai_script_host',
                'phase': 'character_assignment',
                'script': script,
                'characters': characters,
                'current_chapter': 1,
                'discovered_clues': [],
                'timeline': [],
                'player_notes': {},
                'votes': {},
                'game_log': [],
                'status': 'playing'
            }
            
            self.save_game_state(session_id, game_state)
            
            return {
                'success': True,
                'game_state': game_state,
                'intro_message': self.generate_intro_message(script, characters)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_script(self, script_type: str) -> Dict:
        """AI生成剧本"""
        prompts = {
            'modern_campus': '''
请生成一个现代校园题材的剧本杀案件，要求：

1. 案件背景：发生在大学校园的神秘事件
2. 受害者：一名大学生的意外死亡
3. 案发地点：校园内的具体场所
4. 时间线：详细的事件发生时间
5. 6个角色：每个都有完整背景、动机、关系
6. 线索：至少8条关键线索
7. 真相：完整的推理逻辑

以JSON格式返回，包含：
- case_info: {title, background, victim, location, timeline}
- characters: [{name, background, motive, secrets, relationships}]
- clues: [{id, description, location, importance}]
- truth: {culprit, method, motive, evidence}
            ''',
            
            'ancient_palace': '''
请生成一个古代宫廷题材的剧本杀案件，背景设定在皇宫内院...
[详细prompt类似]
            ''',
            
            'modern_office': '''
请生成一个现代职场题材的剧本杀案件，背景设定在大型公司...
[详细prompt类似]
            '''
        }
        
        prompt = prompts.get(script_type, prompts['modern_campus'])
        
        # 设置使用创意模型生成剧本
        script_content = self.ai_service.generate_content(prompt, model='gemini-pro')
        
        try:
            # 尝试解析JSON
            script_data = json.loads(script_content)
            return script_data
        except json.JSONDecodeError:
            # 如果不是标准JSON，进行文本解析
            return self.parse_script_content(script_content, script_type)
    
    def parse_script_content(self, content: str, script_type: str) -> Dict:
        """解析AI生成的剧本内容"""
        # 简化的解析逻辑，实际可以更复杂
        return {
            'case_info': {
                'title': f'{script_type}剧本杀',
                'background': content[:200] + '...',
                'victim': '张三',
                'location': '大学图书馆',
                'timeline': '2024年某日夜晚'
            },
            'characters': [
                {'name': f'角色{i+1}', 'background': f'角色{i+1}的背景', 'motive': '未知动机'}
                for i in range(6)
            ],
            'clues': [
                {'id': f'clue_{i+1}', 'description': f'线索{i+1}', 'importance': 3}
                for i in range(8)
            ],
            'truth': {
                'culprit': '角色3',
                'method': '未知手段',
                'motive': '复仇'
            }
        }
    
    def generate_characters(self, script: Dict, player_count: int = 6) -> List[Dict]:
        """生成角色信息"""
        characters = script.get('characters', [])
        
        # 确保有足够的角色
        while len(characters) < player_count:
            characters.append({
                'name': f'神秘角色{len(characters) + 1}',
                'background': '身份成谜的角色',
                'motive': '未知',
                'secrets': [],
                'relationships': {}
            })
        
        return characters[:player_count]
    
    def generate_intro_message(self, script: Dict, characters: List[Dict]) -> str:
        """生成游戏开场介绍"""
        case_info = script.get('case_info', {})
        
        intro = f"""
🎭 欢迎来到剧本杀游戏！

📖 **剧本**: {case_info.get('title', '神秘案件')}

🏢 **背景**: {case_info.get('background', '一个神秘的故事即将展开...')}

💀 **事件**: {case_info.get('victim', '某人')}在{case_info.get('location', '某地')}发生了意外

⏰ **时间**: {case_info.get('timeline', '某个夜晚')}

👥 **角色**: 共有{len(characters)}个角色参与此次事件

🔍 **任务**: 通过调查、对话和推理，找出事件的真相

准备好开始这段推理之旅了吗？
        """
        
        return intro.strip()
    
    def process_player_action(self, session_id: str, action: Dict) -> Dict:
        """处理玩家行动"""
        game_state = self.load_game_state(session_id)
        
        if not game_state:
            return {'success': False, 'error': '游戏状态不存在'}
        
        action_type = action.get('type')
        
        if action_type == 'investigate':
            return self.handle_investigation(session_id, game_state, action)
        elif action_type == 'question_character':
            return self.handle_character_question(session_id, game_state, action)
        elif action_type == 'make_accusation':
            return self.handle_accusation(session_id, game_state, action)
        elif action_type == 'vote':
            return self.handle_voting(session_id, game_state, action)
        else:
            return {'success': False, 'error': '未知的行动类型'}
    
    def handle_investigation(self, session_id: str, game_state: Dict, action: Dict) -> Dict:
        """处理调查行动"""
        target = action.get('target', '未知地点')
        method = action.get('method', 'general')
        
        investigation_prompt = f"""
你是剧本杀主持人，玩家正在调查：{target}
调查方式：{method}

剧本背景：{game_state['script'].get('case_info', {}).get('background', '')}
已发现线索：{game_state.get('discovered_clues', [])}

请生成调查结果，包括：
1. 发现的信息或线索
2. 调查过程描述
3. 是否有新发现

如果调查方向正确，给予有价值线索；如果错误，可给予无关信息。
        """
        
        result = self.ai_service.generate_content(investigation_prompt)
        
        # 更新游戏状态
        game_state['game_log'].append({
            'type': 'investigation',
            'action': action,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_game_state(session_id, game_state)
        
        return {
            'success': True,
            'result': result,
            'game_state': game_state
        }
    
    def handle_character_question(self, session_id: str, game_state: Dict, action: Dict) -> Dict:
        """处理向角色提问"""
        character = action.get('character', '未知角色')
        question = action.get('question', '')
        
        question_prompt = f"""
你是剧本杀中的角色：{character}
玩家问你：{question}

根据你的角色背景和秘密，给出符合角色身份的回答。
注意：
1. 保持角色一致性
2. 可以隐瞒部分真相
3. 但不能完全说谎
4. 回答要有戏剧性
        """
        
        result = self.ai_service.generate_content(question_prompt)
        
        # 更新游戏日志
        game_state['game_log'].append({
            'type': 'character_question',
            'character': character,
            'question': question,
            'answer': result,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_game_state(session_id, game_state)
        
        return {
            'success': True,
            'character': character,
            'answer': result,
            'game_state': game_state
        }
    
    def handle_accusation(self, session_id: str, game_state: Dict, action: Dict) -> Dict:
        """处理指控行动"""
        accused = action.get('accused', '')
        reasoning = action.get('reasoning', '')
        
        # 检查指控是否正确
        truth = game_state['script'].get('truth', {})
        correct_culprit = truth.get('culprit', '')
        
        is_correct = accused.lower() == correct_culprit.lower()
        
        result = {
            'accused': accused,
            'reasoning': reasoning,
            'is_correct': is_correct,
            'game_over': True
        }
        
        if is_correct:
            result['message'] = f"🎉 恭喜！你成功找出了真凶：{accused}！"
            game_state['status'] = 'won'
        else:
            result['message'] = f"❌ 很遗憾，{accused}不是真凶。真凶是：{correct_culprit}"
            game_state['status'] = 'lost'
        
        game_state['game_log'].append({
            'type': 'accusation',
            'action': action,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_game_state(session_id, game_state)
        
        return {
            'success': True,
            'result': result,
            'game_state': game_state
        }
    
    def handle_voting(self, session_id: str, game_state: Dict, action: Dict) -> Dict:
        """处理投票行动"""
        vote_target = action.get('target', '')
        voter = action.get('voter', 'player')
        
        if 'votes' not in game_state:
            game_state['votes'] = {}
        
        game_state['votes'][voter] = vote_target
        
        # 检查是否所有人都投票了
        characters = game_state.get('characters', [])
        total_voters = len(characters) + 1  # 包括玩家
        
        if len(game_state['votes']) >= total_voters:
            # 计算投票结果
            vote_count = {}
            for target in game_state['votes'].values():
                vote_count[target] = vote_count.get(target, 0) + 1
            
            # 找出得票最多的角色
            if vote_count:
                eliminated = max(vote_count.keys(), key=lambda x: vote_count[x])
                
                result = {
                    'eliminated': eliminated,
                    'vote_count': vote_count,
                    'voting_complete': True
                }
                
                # 检查游戏是否结束
                truth = game_state['script'].get('truth', {})
                if eliminated == truth.get('culprit'):
                    result['game_over'] = True
                    result['victory'] = True
                    game_state['status'] = 'won'
            else:
                result = {'error': '投票统计出错'}
        else:
            result = {
                'vote_recorded': True,
                'votes_needed': total_voters - len(game_state['votes'])
            }
        
        game_state['game_log'].append({
            'type': 'voting',
            'action': action,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        self.save_game_state(session_id, game_state)
        
        return {
            'success': True,
            'result': result,
            'game_state': game_state
        }

class DetectiveGame(GameService):
    """AI推理侦探游戏"""
    
    def start_case(self, session_id: str, case_type: str = 'murder') -> Dict:
        """开始案件"""
        try:
            # 生成案件
            case_info = self.generate_case(case_type)
            
            # 创建嫌疑人
            suspects = self.create_suspects(case_info)
            
            # 初始化游戏状态
            game_state = {
                'game_type': 'ai_detective_game',
                'phase': 'investigation',
                'case_info': case_info,
                'suspects': suspects,
                'evidence': case_info.get('initial_evidence', []),
                'interrogation_history': {suspect['id']: [] for suspect in suspects},
                'deduction_score': 0,
                'investigation_progress': 0,
                'status': 'playing'
            }
            
            self.save_game_state(session_id, game_state)
            
            return {
                'success': True,
                'case_info': case_info,
                'suspects': suspects,
                'initial_message': self.generate_case_intro(case_info)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_case(self, case_type: str) -> Dict:
        """生成案件"""
        prompt = f"""
请生成一个{case_type}案件，包含：

1. 案件概述：时间、地点、受害者
2. 现场情况和初步证据
3. 3-5个嫌疑人，每人都有动机和不在场证明
4. 隐藏线索和关键证据
5. 真相和推理路径

要求逻辑严密，有足够推理难度，嫌疑人个性鲜明。

以JSON格式返回，包含：
- summary: 案件概述
- scene: 现场描述
- victim: 受害者信息
- initial_evidence: 初始证据列表
- timeline: 时间线
- truth: 真相（包括真凶、手法、动机）
        """
        
        case_content = self.ai_service.generate_content(prompt, model='claude-opus')
        
        try:
            return json.loads(case_content)
        except json.JSONDecodeError:
            # 简化案件
            return {
                'summary': f'{case_type}案件正在调查中',
                'scene': '案发现场已被保护',
                'victim': '受害者张某',
                'initial_evidence': ['血迹', '脚印', '遗留物'],
                'timeline': '案发时间：昨晚10点',
                'truth': {'culprit': '嫌疑人C', 'method': '未知', 'motive': '仇杀'}
            }
    
    def create_suspects(self, case_info: Dict) -> List[Dict]:
        """创建嫌疑人"""
        suspects = []
        suspect_names = ['李明', '王红', '张强', '刘丽', '陈伟']
        
        for i, name in enumerate(suspect_names[:4]):  # 创建4个嫌疑人
            suspect = {
                'id': f'suspect_{i+1}',
                'name': name,
                'occupation': random.choice(['教师', '医生', '工人', '商人', '学生']),
                'background': f'{name}的详细背景信息',
                'motive': random.choice(['金钱纠纷', '感情纠纷', '工作冲突', '家庭矛盾']),
                'alibi': f'{name}声称的不在场证明',
                'personality': random.choice(['冷静', '紧张', '愤怒', '狡猾']),
                'is_culprit': i == 2,  # 第3个是真凶
                'suspicion_level': random.randint(1, 5)
            }
            suspects.append(suspect)
        
        return suspects
    
    def generate_case_intro(self, case_info: Dict) -> str:
        """生成案件介绍"""
        return f"""
🔍 **新案件报告**

📋 **案件概述**: {case_info.get('summary', '神秘案件')}

🏢 **现场情况**: {case_info.get('scene', '现场已保护')}

💀 **受害者**: {case_info.get('victim', '身份确认中')}

🕐 **时间线**: {case_info.get('timeline', '时间待确认')}

🔬 **初步证据**: {', '.join(case_info.get('initial_evidence', []))}

👮 **你的任务**: 审问嫌疑人，分析证据，找出真凶

准备开始调查了吗？
        """

class WerewolfGame(GameService):
    """AI狼人杀法官游戏"""
    
    def start_game(self, session_id: str, player_count: int = 8) -> Dict:
        """开始狼人杀游戏"""
        try:
            # 角色分配
            roles = self.assign_roles(player_count)
            
            # 创建AI玩家
            players = self.create_ai_players(roles)
            
            # 初始化游戏状态
            game_state = {
                'game_type': 'ai_werewolf_judge',
                'phase': 'night',
                'day_count': 1,
                'players': players,
                'alive_players': [p for p in players if p['alive']],
                'dead_players': [],
                'night_actions': {},
                'vote_history': [],
                'game_events': [],
                'current_speaker': None,
                'status': 'playing'
            }
            
            self.save_game_state(session_id, game_state)
            
            return {
                'success': True,
                'game_state': game_state,
                'player_role': self.get_player_role(players),
                'intro_message': self.generate_game_intro(game_state)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def assign_roles(self, player_count: int) -> List[str]:
        """分配角色"""
        if player_count == 6:
            roles = ['werewolf', 'werewolf', 'seer', 'doctor', 'villager', 'villager']
        elif player_count == 8:
            roles = ['werewolf', 'werewolf', 'werewolf', 'seer', 'doctor', 'hunter', 'villager', 'villager']
        else:
            # 默认配置
            wolf_count = max(1, player_count // 3)
            roles = ['werewolf'] * wolf_count
            roles.extend(['seer', 'doctor'])
            while len(roles) < player_count:
                roles.append('villager')
        
        random.shuffle(roles)
        return roles
    
    def create_ai_players(self, roles: List[str]) -> List[Dict]:
        """创建AI玩家"""
        names = ['小明', '小红', '小强', '小丽', '小伟', '小芳', '小刚', '小美']
        personalities = ['冷静分析型', '激进发言型', '保守观察型', '情绪化表达型']
        
        players = []
        for i, role in enumerate(roles):
            player = {
                'id': f'player_{i+1}',
                'position': i + 1,
                'name': names[i] if i < len(names) else f'玩家{i+1}',
                'role': role,
                'alive': True,
                'personality': random.choice(personalities),
                'suspicion_level': 0,
                'is_user': i == 0,  # 第一个玩家是用户
                'vote_target': None,
                'last_action': None
            }
            players.append(player)
        
        return players
    
    def get_player_role(self, players: List[Dict]) -> Dict:
        """获取用户角色"""
        user_player = next((p for p in players if p.get('is_user')), None)
        return user_player
    
    def generate_game_intro(self, game_state: Dict) -> str:
        """生成游戏介绍"""
        player_count = len(game_state['players'])
        alive_count = len(game_state['alive_players'])
        
        return f"""
🐺 **狼人杀游戏开始！**

👥 **玩家数量**: {player_count}人
❤️ **存活人数**: {alive_count}人
🌙 **当前阶段**: 第{game_state['day_count']}天夜晚

📋 **游戏规则**:
- 夜晚：狼人觉醒，选择猎物
- 白天：所有人讨论，投票淘汰可疑人员
- 胜利条件：狼人全部出局或狼人数量≥村民数量

🎭 **你的身份**: 游戏开始后将私下告知
🤐 **请保守秘密**: 不要透露你的真实身份

准备好了吗？夜晚即将降临...
        """