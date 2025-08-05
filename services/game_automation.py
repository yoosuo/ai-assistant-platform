#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏自动化管理器 - 处理AI游戏的自动推进和AI行动
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from services.ai_service import AIService
from services.ai_character_manager import AICharacterManager
from utils.database import DatabaseManager


class GameAutomation:
    """游戏自动化管理器"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.character_manager = AICharacterManager()
        self.db = DatabaseManager()
        self.active_games = {}  # session_id -> game_thread
        self.game_timers = {}   # session_id -> timer_info
    
    def start_game_automation(self, session_id: str, game_type: str):
        """启动游戏自动化"""
        if session_id in self.active_games:
            return  # 游戏已经在运行
        
        # 创建游戏线程
        game_thread = threading.Thread(
            target=self._run_game_loop,
            args=(session_id, game_type),
            daemon=True
        )
        game_thread.start()
        self.active_games[session_id] = game_thread
    
    def stop_game_automation(self, session_id: str):
        """停止游戏自动化"""
        if session_id in self.active_games:
            del self.active_games[session_id]
        if session_id in self.game_timers:
            del self.game_timers[session_id]
    
    def _run_game_loop(self, session_id: str, game_type: str):
        """游戏主循环"""
        try:
            if game_type == 'ai_script_host':
                self._run_script_host_game(session_id)
            elif game_type == 'ai_detective_game':
                self._run_detective_game(session_id)
            elif game_type == 'ai_werewolf_judge':
                self._run_werewolf_game(session_id)
        except Exception as e:
            print(f"游戏循环错误 {session_id}: {e}")
        finally:
            self.stop_game_automation(session_id)
    
    def _run_script_host_game(self, session_id: str):
        """运行剧本杀游戏"""
        # 加载角色
        self.character_manager.load_characters(session_id)
        
        # 游戏阶段
        phases = ['introduction', 'free_discussion', 'investigation', 'final_reasoning', 'revelation']
        
        for phase in phases:
            if session_id not in self.active_games:
                break
            
            self.db.update_game_phase(session_id, phase)
            
            if phase == 'introduction':
                self._script_host_introduction(session_id)
                time.sleep(5)  # 给玩家时间阅读
                
            elif phase == 'free_discussion':
                self._script_host_discussion(session_id, duration=300)  # 5分钟讨论
                
            elif phase == 'investigation':
                self._script_host_investigation(session_id, duration=180)  # 3分钟调查
                
            elif phase == 'final_reasoning':
                self._script_host_final_reasoning(session_id, duration=120)  # 2分钟推理
                
            elif phase == 'revelation':
                self._script_host_revelation(session_id)
                break  # 游戏结束
    
    def _script_host_introduction(self, session_id: str):
        """剧本杀开场介绍"""
        # 获取游戏配置
        game_session = self.db.get_game_session(session_id)
        if not game_session:
            return
        
        # AI主持人介绍案件
        host_prompt = """
你是剧本杀主持人，现在要开始介绍案件背景。

请生成一个引人入胜的开场白，包括：
1. 欢迎各位玩家
2. 简单介绍案件背景（不要透露太多细节）
3. 告诉玩家游戏规则
4. 引导进入讨论阶段

要求：语言生动，营造悬疑氛围，控制在200字以内。
        """
        
        introduction = self.ai_service.generate_content(host_prompt)
        
        # 保存主持人消息
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content=introduction,
            phase='introduction'
        )
    
    def _script_host_discussion(self, session_id: str, duration: int):
        """剧本杀自由讨论阶段"""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        characters = self.character_manager.get_characters_by_type(session_id, 'npc')
        
        while datetime.now() < end_time and session_id in self.active_games:
            # 随机选择一个NPC发言
            if characters:
                import random
                speaker = random.choice(characters)
                
                # 生成NPC发言
                speech = self._generate_npc_speech(session_id, speaker.character_id, 'discussion')
                
                if speech:
                    self.db.add_game_message(
                        session_id=session_id,
                        speaker_id=speaker.character_id,
                        speaker_name=speaker.name,
                        speaker_type='npc',
                        content=speech,
                        phase='free_discussion'
                    )
            
            time.sleep(30)  # 每30秒一次NPC发言
    
    def _generate_npc_speech(self, session_id: str, character_id: str, context: str) -> str:
        """生成NPC发言"""
        character = self.character_manager.get_character(session_id, character_id)
        if not character:
            return ""
        
        # 获取最近的游戏消息作为上下文
        recent_messages = self.db.get_game_messages(session_id, limit=5)
        context_text = "\n".join([
            f"{msg['speaker_name']}: {msg['content']}" 
            for msg in recent_messages
        ])
        
        prompt = f"""
你正在扮演剧本杀角色：{character.name}

**角色信息**：
- 性格：{character.personality}
- 背景：{character.background}
- 秘密：{character.secrets}

**最近对话**：
{context_text}

**当前阶段**：{context}

请以这个角色的身份发言，要求：
1. 符合角色性格和背景
2. 可以分享一些信息，但要保护自己的秘密
3. 语言自然，有个性
4. 控制在50字以内

直接说话，不要包含角色名称：
        """
        
        speech = self.ai_service.generate_content(prompt)
        
        # 更新角色记忆
        self.character_manager.update_character_memory(
            session_id, character_id,
            f"在{context}阶段发言", speech
        )
        
        return speech
    
    def _script_host_investigation(self, session_id: str, duration: int):
        """剧本杀调查阶段"""
        # 发布调查开始消息
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content="现在进入调查阶段！各位可以搜查现场，寻找线索。时间有限，请抓紧！",
            phase='investigation'
        )
        
        # 等待调查时间结束
        time.sleep(duration)
    
    def _script_host_final_reasoning(self, session_id: str, duration: int):
        """剧本杀最终推理阶段"""
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content="现在进入最终推理阶段！请各位整理线索，准备指出真凶！",
            phase='final_reasoning'
        )
        
        time.sleep(duration)
    
    def _script_host_revelation(self, session_id: str):
        """剧本杀真相揭晓"""
        # 获取游戏状态中的真相
        truth = self.db.get_game_state(session_id, 'truth')
        
        if truth:
            truth_data = json.loads(truth)
            revelation = f"""
真相大白！

🎭 真凶是：{truth_data.get('culprit', '未知')}
🔍 作案手法：{truth_data.get('method', '未知')}
💭 作案动机：{truth_data.get('motive', '未知')}

感谢各位的精彩表演！
            """
        else:
            revelation = "游戏结束！感谢各位参与！"
        
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='host',
            speaker_name='主持人',
            speaker_type='host',
            content=revelation,
            phase='revelation'
        )
    
    def _run_detective_game(self, session_id: str):
        """运行推理侦探游戏"""
        # 加载嫌疑人角色
        self.character_manager.load_characters(session_id)
        
        # 设置游戏阶段
        self.db.update_game_phase(session_id, 'investigation')
        
        # 发布开始消息
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='system',
            speaker_name='系统',
            speaker_type='system',
            content="案件调查开始！您可以审讯嫌疑人、分析证据。请仔细寻找破绽！",
            phase='investigation'
        )
        
        # 等待玩家行动（侦探游戏主要是玩家驱动）
        while session_id in self.active_games:
            time.sleep(10)
            
            # 检查是否有自动事件需要触发
            self._check_detective_auto_events(session_id)
    
    def _check_detective_auto_events(self, session_id: str):
        """检查侦探游戏自动事件"""
        # 获取游戏进度
        investigation_count = len(self.db.get_game_actions(session_id, 'investigation'))
        
        # 如果调查次数过多，给出提示
        if investigation_count > 10:
            self.db.add_game_message(
                session_id=session_id,
                speaker_id='system',
                speaker_name='系统',
                speaker_type='system',
                content="💡 提示：证据已经收集得差不多了，是时候进行最终推理了！",
                phase='investigation'
            )
    
    def _run_werewolf_game(self, session_id: str):
        """运行狼人杀游戏"""
        # 加载AI玩家
        self.character_manager.load_characters(session_id)
        
        day_count = 1
        
        while session_id in self.active_games:
            # 夜晚阶段
            self.db.update_game_phase(session_id, f'night_{day_count}')
            self._werewolf_night_phase(session_id, day_count)
            
            if session_id not in self.active_games:
                break
            
            # 白天阶段
            self.db.update_game_phase(session_id, f'day_{day_count}')
            game_continues = self._werewolf_day_phase(session_id, day_count)
            
            if not game_continues:
                break
            
            day_count += 1
    
    def _werewolf_night_phase(self, session_id: str, day_count: int):
        """狼人杀夜晚阶段"""
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='judge',
            speaker_name='法官',
            speaker_type='judge',
            content=f"第{day_count}天夜晚降临，所有人请闭眼...",
            phase=f'night_{day_count}'
        )
        
        # AI玩家执行夜晚行动
        characters = self.character_manager.get_all_characters(session_id)
        for character in characters:
            if character.is_alive and character.character_type == 'player':
                self._execute_werewolf_night_action(session_id, character, day_count)
        
        time.sleep(10)  # 夜晚持续时间
    
    def _execute_werewolf_night_action(self, session_id: str, character, day_count: int):
        """执行狼人杀夜晚行动"""
        # 根据角色身份执行不同行动
        role = character.background  # 假设角色身份存储在background中
        
        if 'werewolf' in role.lower():
            # 狼人杀人
            self._werewolf_kill_action(session_id, character.character_id, day_count)
        elif 'seer' in role.lower():
            # 预言家查验
            self._seer_check_action(session_id, character.character_id, day_count)
        elif 'doctor' in role.lower():
            # 医生救人
            self._doctor_heal_action(session_id, character.character_id, day_count)
    
    def _werewolf_day_phase(self, session_id: str, day_count: int) -> bool:
        """狼人杀白天阶段，返回游戏是否继续"""
        # 公布夜晚结果
        self._announce_night_results(session_id, day_count)
        
        # AI玩家讨论
        self._werewolf_discussion(session_id, day_count)
        
        # AI玩家投票
        eliminated = self._werewolf_voting(session_id, day_count)
        
        # 检查游戏是否结束
        return self._check_werewolf_game_end(session_id, eliminated)
    
    def _werewolf_discussion(self, session_id: str, day_count: int):
        """狼人杀讨论阶段"""
        characters = [c for c in self.character_manager.get_all_characters(session_id) 
                     if c.is_alive and c.character_type == 'player']
        
        # 每个AI玩家发言
        for character in characters:
            speech = self._generate_werewolf_speech(session_id, character.character_id, day_count)
            if speech:
                self.db.add_game_message(
                    session_id=session_id,
                    speaker_id=character.character_id,
                    speaker_name=character.name,
                    speaker_type='player',
                    content=speech,
                    phase=f'day_{day_count}'
                )
            time.sleep(2)  # 发言间隔
    
    def _generate_werewolf_speech(self, session_id: str, character_id: str, day_count: int) -> str:
        """生成狼人杀发言"""
        character = self.character_manager.get_character(session_id, character_id)
        if not character:
            return ""
        
        role = character.background
        recent_messages = self.db.get_game_messages(session_id, f'day_{day_count}', limit=3)
        
        prompt = f"""
你是狼人杀玩家：{character.name}
你的身份是：{role}
这是第{day_count}天的讨论。

根据你的身份，请发表合理的发言：
1. 如果你是狼人，要隐藏身份，误导其他人
2. 如果你是村民，要帮助找出狼人
3. 如果你是神职，要合理使用你的信息
4. 控制在30字以内

直接发言：
        """
        
        return self.ai_service.generate_content(prompt)
    
    def _werewolf_voting(self, session_id: str, day_count: int) -> Optional[str]:
        """狼人杀投票阶段"""
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='judge',
            speaker_name='法官',
            speaker_type='judge',
            content="现在开始投票！请选择你认为的狼人。",
            phase=f'day_{day_count}'
        )
        
        # AI玩家投票逻辑
        votes = {}
        characters = [c for c in self.character_manager.get_all_characters(session_id) 
                     if c.is_alive and c.character_type == 'player']
        
        for character in characters:
            # 简化的投票逻辑：随机投票（实际应该更智能）
            import random
            other_chars = [c for c in characters if c.character_id != character.character_id]
            if other_chars:
                target = random.choice(other_chars)
                votes[character.character_id] = target.character_id
        
        # 统计投票结果
        vote_count = {}
        for voter, target in votes.items():
            vote_count[target] = vote_count.get(target, 0) + 1
        
        if vote_count:
            eliminated_id = max(vote_count.keys(), key=lambda x: vote_count[x])
            eliminated_char = self.character_manager.get_character(session_id, eliminated_id)
            
            if eliminated_char:
                self.character_manager.kill_character(session_id, eliminated_id)
                
                self.db.add_game_message(
                    session_id=session_id,
                    speaker_id='judge',
                    speaker_name='法官',
                    speaker_type='judge',
                    content=f"{eliminated_char.name}被投票出局！",
                    phase=f'day_{day_count}'
                )
                
                return eliminated_id
        
        return None
    
    def _check_werewolf_game_end(self, session_id: str, eliminated_id: str = None) -> bool:
        """检查狼人杀游戏是否结束"""
        characters = self.character_manager.get_all_characters(session_id)
        alive_chars = [c for c in characters if c.is_alive and c.character_type == 'player']
        
        werewolves = [c for c in alive_chars if 'werewolf' in c.background.lower()]
        villagers = [c for c in alive_chars if 'werewolf' not in c.background.lower()]
        
        if len(werewolves) == 0:
            # 村民获胜
            self.db.add_game_message(
                session_id=session_id,
                speaker_id='judge',
                speaker_name='法官',
                speaker_type='judge',
                content="🎉 村民获胜！所有狼人已被消灭！",
                phase='game_end'
            )
            return False
        elif len(werewolves) >= len(villagers):
            # 狼人获胜
            self.db.add_game_message(
                session_id=session_id,
                speaker_id='judge',
                speaker_name='法官',
                speaker_type='judge',
                content="🐺 狼人获胜！狼人数量已达到或超过村民！",
                phase='game_end'
            )
            return False
        
        return True  # 游戏继续
    
    def _announce_night_results(self, session_id: str, day_count: int):
        """公布夜晚结果"""
        # 简化实现：随机一个死亡消息
        self.db.add_game_message(
            session_id=session_id,
            speaker_id='judge',
            speaker_name='法官',
            speaker_type='judge',
            content=f"第{day_count}天早上，大家醒来发现昨晚平安无事。",
            phase=f'day_{day_count}'
        )
    
    def _werewolf_kill_action(self, session_id: str, werewolf_id: str, day_count: int):
        """狼人杀人行动"""
        # 简化实现
        pass
    
    def _seer_check_action(self, session_id: str, seer_id: str, day_count: int):
        """预言家查验行动"""
        # 简化实现
        pass
    
    def _doctor_heal_action(self, session_id: str, doctor_id: str, day_count: int):
        """医生救人行动"""
        # 简化实现
        pass