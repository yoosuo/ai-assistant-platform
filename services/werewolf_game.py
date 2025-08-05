#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI狼人杀法官游戏 - 完整实现
基于大模型实时生成，支持昼夜循环和AI自动行动
"""

import json
import uuid
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from services.ai_service import AIService
from services.ai_character_manager import AICharacterManager
from utils.database import DatabaseManager


class WerewolfGame:
    """AI狼人杀法官游戏"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.character_manager = AICharacterManager()
        self.db = DatabaseManager()
        
        # 角色配置（根据人数动态调整）
        self.role_configs = {
            6: {'werewolf': 2, 'villager': 3, 'seer': 1, 'witch': 0, 'hunter': 0},
            8: {'werewolf': 2, 'villager': 4, 'seer': 1, 'witch': 1, 'hunter': 0},
            10: {'werewolf': 3, 'villager': 5, 'seer': 1, 'witch': 1, 'hunter': 0},
            12: {'werewolf': 4, 'villager': 6, 'seer': 1, 'witch': 1, 'hunter': 0}
        }
        
        # 游戏阶段
        self.phases = ['night', 'day_discussion', 'day_voting', 'game_over']
        
    def create_new_game(self, user_id: int = 1, player_count: int = 8) -> str:
        """创建新的狼人杀游戏"""
        session_id = str(uuid.uuid4())
        
        # 确保玩家数量有效
        if player_count not in self.role_configs:
            player_count = 8
            
        config = {
            'game_type': 'ai_werewolf_judge',
            'player_count': player_count,
            'current_phase': 'night',
            'day_count': 1,
            'round_count': 1,
            'game_started': False
        }
        
        self.db.create_game_session(session_id, 'ai_werewolf_judge', user_id, config)
        
        # 立即初始化游戏
        self._initialize_game(session_id, player_count)
        
        return session_id
    
    def _initialize_game(self, session_id: str, player_count: int):
        """初始化游戏：分配角色、创建AI玩家"""
        
        # 获取角色配置
        roles = self._generate_roles(player_count)
        
        # 创建AI法官
        judge_id = self.character_manager.create_character(
            session_id=session_id,
            name="法官",
            character_type="judge",
            personality="公正严明，主持游戏节奏，营造紧张氛围",
            background="经验丰富的狼人杀法官，擅长调动气氛",
            secrets="负责维持游戏秩序，不偏不倚"
        )
        
        # 将玩家设为1号玩家
        player_role = roles[0]
        self.db.set_game_state(session_id, 'player_role', player_role)
        self.db.set_game_state(session_id, 'player_number', '1')
        
        # 创建AI玩家（2号到N号）
        ai_players = []
        for i in range(1, player_count):
            player_number = i + 1
            role = roles[i]
            
            # 为AI玩家生成个性
            personality = self._generate_ai_personality(role)
            
            character_id = self.character_manager.create_character(
                session_id=session_id,
                name=f"玩家{player_number}",
                character_type=role,
                personality=personality,
                background=f"狼人杀玩家，角色：{role}",
                secrets=f"真实身份：{role}，需要根据身份行动"
            )
            
            ai_players.append({
                'player_number': player_number,
                'character_id': character_id,
                'role': role,
                'alive': True
            })
        
        # 保存玩家信息
        self.db.set_game_state(session_id, 'ai_players', json.dumps(ai_players))
        self.db.set_game_state(session_id, 'all_roles', json.dumps(roles))
        self.db.set_game_state(session_id, 'judge_id', judge_id)
        self.db.set_game_state(session_id, 'game_started', 'true')
        
        # 法官开场白
        opening_message = self._generate_opening_message(player_count, roles)
        self.db.add_game_message(
            session_id, judge_id, "🎯 法官", "judge", opening_message
        )
        
        # 显示玩家角色信息（只给真实玩家）
        role_message = f"🎭 您的身份是：**{player_role}**\n\n" + self._get_role_description(player_role)
        self.db.add_game_message(
            session_id, 'system', "🎮 系统", "system", role_message
        )
        
        # 开始第一个夜晚
        self._start_night_phase(session_id)
    
    def _generate_roles(self, player_count: int) -> List[str]:
        """生成角色列表并打乱"""
        config = self.role_configs[player_count]
        roles = []
        
        # 添加各种角色
        roles.extend(['werewolf'] * config['werewolf'])
        roles.extend(['villager'] * config['villager'])
        roles.extend(['seer'] * config['seer'])
        if config['witch'] > 0:
            roles.extend(['witch'] * config['witch'])
        if config['hunter'] > 0:
            roles.extend(['hunter'] * config['hunter'])
            
        # 打乱角色顺序
        random.shuffle(roles)
        return roles
    
    def _generate_ai_personality(self, role: str) -> str:
        """为AI玩家生成个性"""
        personalities = {
            'werewolf': [
                "狡猾谨慎，善于伪装，会巧妙转移话题",
                "冷静理性，逻辑清晰，擅长混淆视听", 
                "表面友善，暗藏心机，善于栽赃嫁祸"
            ],
            'villager': [
                "正直善良，逻辑分析强，但容易被误导",
                "热情直率，敢于质疑，但有时冲动",
                "谨慎观察，不轻易发言，关键时刻表态"
            ],
            'seer': [
                "睿智冷静，善于引导讨论，保护身份",
                "低调谨慎，通过暗示传递信息",
                "机智勇敢，关键时刻敢于跳身份"
            ],
            'witch': [
                "神秘莫测，观察敏锐，药品使用谨慎",
                "理性分析，善于从细节发现线索"
            ]
        }
        
        return random.choice(personalities.get(role, ["普通玩家，随机应变"]))
    
    def _get_role_description(self, role: str) -> str:
        """获取角色描述"""
        descriptions = {
            'werewolf': "🐺 **狼人**\n夜晚可以与其他狼人讨论并杀死一名玩家。目标：消灭所有好人。",
            'villager': "👥 **村民**\n没有特殊技能，但可以在白天讨论中投票。目标：找出并投死所有狼人。",
            'seer': "🔮 **预言家**\n每晚可以查看一名玩家的身份。目标：利用信息帮助好人阵营获胜。",
            'witch': "🧪 **女巫**\n拥有解药和毒药各一瓶。解药可以救活被狼人杀死的玩家，毒药可以杀死一名玩家。",
            'hunter': "🏹 **猎人**\n被投票出局或被狼人杀死时，可以开枪带走一名玩家。"
        }
        return descriptions.get(role, "未知角色")
    
    def _generate_opening_message(self, player_count: int, roles: List[str]) -> str:
        """AI生成开场白"""
        try:
            role_counts = {}
            for role in roles:
                role_counts[role] = role_counts.get(role, 0) + 1
            
            role_desc = {
                'werewolf': '狼人',
                'villager': '村民', 
                'seer': '预言家',
                'witch': '女巫',
                'hunter': '猎人'
            }
            
            config_text = "、".join([f"{role_desc.get(role, role)}{count}人" for role, count in role_counts.items()])
            
            prompt = f"""作为一名专业的狼人杀法官，请为{player_count}人局游戏生成开场白。

游戏配置：
- 总人数：{player_count}人
- 角色配置：{config_text}

要求：
1. 营造神秘紧张的氛围，体现狼人杀的经典感
2. 简要介绍游戏背景（小镇、狼人入侵等）
3. 说明基本规则（昼夜循环、投票出局）
4. 宣布游戏开始，进入第一个夜晚
5. 语言要有代入感和仪式感
6. 控制在250字以内

请直接输出开场白内容："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            return response.strip()
            
        except Exception as e:
            print(f"AI生成开场白失败: {e}")
            return f"""🌙 **欢迎来到狼人杀的世界**

在这个宁静的小镇上，邪恶的狼人已经潜入了村民之中。每当夜幕降临，他们就会露出獠牙，残害无辜的村民。而白天，他们又会伪装成普通人，混在人群中。

本局游戏共{player_count}人参与，角色已秘密分配完毕。记住：**好人要团结一心找出狼人，狼人要隐藏身份消灭好人**。

现在，第一个夜晚降临了...请所有玩家闭上眼睛！"""
    
    def _start_night_phase(self, session_id: str):
        """开始夜晚阶段"""
        day_count = int(self.db.get_game_state_value(session_id, 'day_count') or 1)
        
        # 法官宣布夜晚开始
        night_message = self._generate_night_announcement(day_count)
        judge_id = self.db.get_game_state_value(session_id, 'judge_id')
        
        self.db.add_game_message(
            session_id, judge_id, "🌙 法官", "judge", night_message
        )
        
        # 设置当前阶段
        self.db.set_game_state(session_id, 'current_phase', 'night')
        
        # 开始AI夜晚行动
        self._execute_night_actions(session_id)
    
    def _generate_night_announcement(self, day_count: int) -> str:
        """AI生成夜晚宣告"""
        try:
            prompt = f"""作为狼人杀法官，请为第{day_count}个夜晚生成宣告词。

要求：
1. 营造神秘恐怖的夜晚氛围
2. 提醒各角色行动
3. 语言要有代入感
4. 控制在100字以内

请直接输出夜晚宣告："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            return response.strip()
            
        except Exception as e:
            print(f"AI生成夜晚宣告失败: {e}")
            return f"🌙 第{day_count}个夜晚降临，所有玩家请闭眼。各角色开始行动..."
    
    def _execute_night_actions(self, session_id: str):
        """执行夜晚行动（AI自动）"""
        
        # 获取存活的AI玩家
        ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
        ai_players = json.loads(ai_players_str) if ai_players_str else []
        alive_players = [p for p in ai_players if p['alive']]
        
        judge_id = self.db.get_game_state_value(session_id, 'judge_id')
        
        # 1. 狼人行动
        werewolves = [p for p in alive_players if p['role'] == 'werewolf']
        if werewolves:
            kill_target = self._werewolf_kill_action(session_id, werewolves, alive_players)
            if kill_target:
                self.db.set_game_state(session_id, 'night_kill_target', str(kill_target))
        
        # 2. 预言家行动
        seers = [p for p in alive_players if p['role'] == 'seer']
        if seers:
            self._seer_check_action(session_id, seers[0], alive_players)
        
        # 3. 女巫行动
        witches = [p for p in alive_players if p['role'] == 'witch']
        if witches:
            self._witch_action(session_id, witches[0], alive_players)
        
        # 夜晚结束，开始白天
        self._start_day_phase(session_id)
    
    def _werewolf_kill_action(self, session_id: str, werewolves: List[Dict], alive_players: List[Dict]) -> Optional[int]:
        """狼人杀人行动"""
        try:
            # 构建可选择的目标（排除狼人和已死亡玩家）
            targets = [p for p in alive_players if p['role'] != 'werewolf']
            if not targets:
                return None
            
            # 获取游戏历史信息用于AI决策
            recent_messages = self.db.get_game_messages(session_id, limit=20)
            game_context = "\n".join([f"{msg['speaker_name']}: {msg['content'][:100]}" for msg in recent_messages[-10:]])
            
            target_info = []
            for p in targets:
                # 为AI提供更多决策信息
                if p['player_number'] == 1:
                    target_info.append(f"{p['player_number']}号玩家（真实玩家）")
                else:
                    target_info.append(f"{p['player_number']}号玩家（AI玩家）")
            
            targets_text = "\n".join(target_info)
            
            prompt = f"""你是狼人阵营的智能决策者，现在是夜晚狼人行动时间。

当前存活的可击杀目标：
{targets_text}

最近的游戏情况：
{game_context}

狼人团队策略原则：
1. 优先击杀可能威胁最大的玩家
2. 如果有神职暴露，优先考虑击杀
3. 避免击杀可能是队友的可疑对象
4. 真实玩家(1号)通常威胁较大，可优先考虑
5. 综合考虑发言和行为判断威胁程度

请分析当前局势，选择最佳击杀目标。直接输出目标号码："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            # 解析目标
            try:
                target_number = int(response.strip())
                if any(p['player_number'] == target_number and p['role'] != 'werewolf' for p in alive_players):
                    # 记录狼人行动（内部日志）
                    print(f"狼人选择击杀{target_number}号玩家")
                    return target_number
            except ValueError:
                pass
            
            # 如果AI选择失败，使用智能随机选择
            # 优先选择真实玩家或可能的神职
            priority_targets = [p for p in targets if p['player_number'] == 1]  # 真实玩家
            if priority_targets:
                return priority_targets[0]['player_number']
            
            # 否则随机选择
            target = random.choice(targets)
            return target['player_number']
            
        except Exception as e:
            print(f"狼人行动失败: {e}")
            # 随机选择目标
            targets = [p for p in alive_players if p['role'] != 'werewolf']
            if targets:
                return random.choice(targets)['player_number']
            return None
    
    def _seer_check_action(self, session_id: str, seer: Dict, alive_players: List[Dict]):
        """预言家查人行动"""
        try:
            # 排除自己
            targets = [p for p in alive_players if p['player_number'] != seer['player_number']]
            if not targets:
                return
            
            # 获取预言家之前的查验记录
            character = self.character_manager.get_character(session_id, seer['character_id'])
            previous_checks = character.get_recent_memory() if character else ""
            
            # 获取游戏历史用于决策
            recent_messages = self.db.get_game_messages(session_id, limit=15)
            game_context = "\n".join([f"{msg['speaker_name']}: {msg['content'][:80]}" for msg in recent_messages[-8:]])
            
            target_info = []
            for p in targets:
                if p['player_number'] == 1:
                    target_info.append(f"{p['player_number']}号玩家（真实玩家）")
                else:
                    target_info.append(f"{p['player_number']}号玩家（AI玩家）")
            
            targets_text = "\n".join(target_info)
            
            prompt = f"""你是预言家，现在是夜晚查人时间。

可查验的玩家：
{targets_text}

你之前的查验记录：
{previous_checks or "暂无查验记录"}

最近的游戏情况：
{game_context}

预言家查人策略：
1. 避免重复查验已知身份的玩家
2. 优先查验发言可疑或行为异常的玩家
3. 考虑查验关键位置的玩家（如真实玩家）
4. 为白天发言收集更多有用信息
5. 如果有怀疑对象，优先查验确认

请分析当前局势，选择最值得查验的玩家。直接输出目标号码："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            # 解析目标
            try:
                target_number = int(response.strip())
                target_player = next((p for p in targets if p['player_number'] == target_number), None)
                if target_player:
                    is_werewolf = target_player['role'] == 'werewolf'
                    result = "狼人" if is_werewolf else "好人"
                    
                    # 记录查验结果（只有预言家知道）
                    self.db.add_game_message(
                        session_id, seer['character_id'], "🔮 预言家", "seer", 
                        f"🔍 查验{target_number}号玩家：**{result}**"
                    )
                    
                    # 保存查验信息供AI记忆
                    self.character_manager.update_character_memory(
                        session_id, seer['character_id'], 
                        f"第{self.db.get_game_state_value(session_id, 'day_count') or 1}夜查验{target_number}号玩家：{result}"
                    )
                    return
            except ValueError:
                pass
            
            # 如果AI选择失败，智能选择
            # 优先选择真实玩家或随机选择
            priority_targets = [p for p in targets if p['player_number'] == 1]
            if priority_targets:
                target = priority_targets[0]
            else:
                target = random.choice(targets)
            
            is_werewolf = target['role'] == 'werewolf'
            result = "狼人" if is_werewolf else "好人"
            
            self.db.add_game_message(
                session_id, seer['character_id'], "🔮 预言家", "seer", 
                f"🔍 查验{target['player_number']}号玩家：**{result}**"
            )
            
            # 保存查验信息
            self.character_manager.update_character_memory(
                session_id, seer['character_id'], 
                f"第{self.db.get_game_state_value(session_id, 'day_count') or 1}夜查验{target['player_number']}号玩家：{result}"
            )
            
        except Exception as e:
            print(f"预言家行动失败: {e}")
    
    def _witch_action(self, session_id: str, witch: Dict, alive_players: List[Dict]):
        """女巫行动"""
        try:
            # 检查是否还有药品
            poison_used = self.db.get_game_state_value(session_id, f'witch_poison_used_{witch["character_id"]}') == 'true'
            antidote_used = self.db.get_game_state_value(session_id, f'witch_antidote_used_{witch["character_id"]}') == 'true'
            
            night_kill_target = self.db.get_game_state_value(session_id, 'night_kill_target')
            day_count = int(self.db.get_game_state_value(session_id, 'day_count') or 1)
            
            # 获取游戏历史用于决策
            recent_messages = self.db.get_game_messages(session_id, limit=15)
            game_context = "\n".join([f"{msg['speaker_name']}: {msg['content'][:80]}" for msg in recent_messages[-8:]])
            
            actions = []
            if not antidote_used and night_kill_target:
                actions.append("使用解药救人")
            if not poison_used:
                actions.append("使用毒药杀人")
            actions.append("不使用任何药品")
            
            if len(actions) == 1:  # 只有"不使用"选项
                return
            
            available_actions = "\n".join(f"{i+1}. {action}" for i, action in enumerate(actions))
            
            # 分析被杀的玩家重要性
            kill_target_info = f"{night_kill_target}号玩家"
            if int(night_kill_target) == 1:
                kill_target_info += "（真实玩家）"
            else:
                kill_target_info += "（AI玩家）"
            
            prompt = f"""你是女巫，现在是夜晚行动时间（第{day_count}夜）。

今晚被狼人击杀的是：{kill_target_info}

药品状态：
- 解药：{'已使用' if antidote_used else '可用'}
- 毒药：{'已使用' if poison_used else '可用'}

你的选择：
{available_actions}

最近的游戏情况：
{game_context}

女巫策略考虑：
1. 解药珍贵，优先救重要玩家（如可能的神职或关键好人）
2. 毒药强力，用于确认的狼人或威胁玩家
3. 第一夜通常不救自己，除非确定必要
4. 考虑局势和剩余玩家数量
5. 保存药品等待更关键时刻

请根据当前局势做出最佳决策。输入选择的序号："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            try:
                choice = int(response.strip()) - 1
                if 0 <= choice < len(actions):
                    action = actions[choice]
                    
                    if action == "使用解药救人" and not antidote_used:
                        self.db.set_game_state(session_id, 'witch_save_target', night_kill_target)
                        self.db.set_game_state(session_id, f'witch_antidote_used_{witch["character_id"]}', 'true')
                        self.db.add_game_message(
                            session_id, witch['character_id'], "🧪 女巫", "witch",
                            f"💊 使用解药救了{night_kill_target}号玩家"
                        )
                        
                        # 记录决策原因到记忆
                        self.character_manager.update_character_memory(
                            session_id, witch['character_id'], 
                            f"第{day_count}夜使用解药救了{night_kill_target}号玩家"
                        )
                        
                    elif action == "使用毒药杀人" and not poison_used:
                        # 智能选择毒杀目标
                        poison_targets = [p for p in alive_players if p['player_number'] != witch['player_number']]
                        if poison_targets:
                            # 优先毒杀可疑的狼人或威胁大的玩家
                            # 这里可以根据AI分析选择，暂时随机
                            target = random.choice(poison_targets)
                            
                            self.db.set_game_state(session_id, 'witch_poison_target', str(target['player_number']))
                            self.db.set_game_state(session_id, f'witch_poison_used_{witch["character_id"]}', 'true')
                            self.db.add_game_message(
                                session_id, witch['character_id'], "🧪 女巫", "witch",
                                f"☠️ 使用毒药毒杀了{target['player_number']}号玩家"
                            )
                            
                            # 记录决策原因到记忆
                            self.character_manager.update_character_memory(
                                session_id, witch['character_id'], 
                                f"第{day_count}夜使用毒药毒杀了{target['player_number']}号玩家"
                            )
                    else:
                        # 不使用药品
                        self.db.add_game_message(
                            session_id, witch['character_id'], "🧪 女巫", "witch",
                            f"🤔 本轮不使用任何药品，保存实力"
                        )
            except ValueError:
                # AI选择失败，保守策略：不使用药品
                self.db.add_game_message(
                    session_id, witch['character_id'], "🧪 女巫", "witch",
                    f"🤔 本轮不使用任何药品"
                )
                
        except Exception as e:
            print(f"女巫行动失败: {e}")
    
    def _start_day_phase(self, session_id: str):
        """开始白天阶段"""
        # 处理夜晚结果
        deaths = self._process_night_results(session_id)
        
        # 检查游戏是否结束
        if self._check_game_over(session_id):
            return
        
        # 设置白天阶段
        self.db.set_game_state(session_id, 'current_phase', 'day_discussion')
        
        # 法官宣布白天开始和夜晚结果
        day_message = self._generate_day_announcement(deaths)
        judge_id = self.db.get_game_state_value(session_id, 'judge_id')
        
        self.db.add_game_message(
            session_id, judge_id, "☀️ 法官", "judge", day_message
        )
        
        # 开始讨论阶段提示
        discussion_prompt = "现在进入自由讨论阶段，请各位玩家发言。真实玩家可以输入发言内容参与讨论。"
        self.db.add_game_message(
            session_id, 'system', "💭 系统", "system", discussion_prompt
        )
    
    def _process_night_results(self, session_id: str) -> List[int]:
        """处理夜晚结果，返回死亡玩家列表"""
        deaths = []
        
        # 获取夜晚行动结果
        kill_target = self.db.get_game_state_value(session_id, 'night_kill_target')
        save_target = self.db.get_game_state_value(session_id, 'witch_save_target')
        poison_target = self.db.get_game_state_value(session_id, 'witch_poison_target')
        
        # 处理狼人击杀
        if kill_target and kill_target != save_target:
            deaths.append(int(kill_target))
        
        # 处理女巫毒杀
        if poison_target:
            deaths.append(int(poison_target))
        
        # 更新玩家状态
        if deaths:
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            
            for player in ai_players:
                if player['player_number'] in deaths:
                    player['alive'] = False
            
            self.db.set_game_state(session_id, 'ai_players', json.dumps(ai_players))
        
        # 清理夜晚状态
        self.db.set_game_state(session_id, 'night_kill_target', '')
        self.db.set_game_state(session_id, 'witch_save_target', '')
        self.db.set_game_state(session_id, 'witch_poison_target', '')
        
        return deaths
    
    def _generate_day_announcement(self, deaths: List[int]) -> str:
        """AI生成白天宣告"""
        try:
            if not deaths:
                prompt = "作为狼人杀法官，昨夜平安，没有玩家死亡。请生成白天开始的宣告词，要营造紧张气氛，控制在50字以内："
            else:
                death_list = "、".join([f"{d}号玩家" for d in deaths])
                prompt = f"作为狼人杀法官，昨夜{death_list}死亡。请生成白天开始的宣告词，要表达哀悼并推进游戏，控制在100字以内："
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            return response.strip()
            
        except Exception as e:
            print(f"AI生成白天宣告失败: {e}")
            if not deaths:
                return "☀️ 天亮了！昨夜风平浪静，所有玩家都安全度过了夜晚。现在进入讨论阶段。"
            else:
                death_list = "、".join([f"{d}号玩家" for d in deaths])
                return f"☀️ 天亮了！昨夜{death_list}遇害身亡。现在请为死者默哀，然后开始讨论。"
    
    def player_speak(self, session_id: str, message: str) -> bool:
        """玩家发言"""
        try:
            # 检查游戏状态
            current_phase = self.db.get_game_state_value(session_id, 'current_phase')
            if current_phase not in ['day_discussion', 'day_voting']:
                return False
            
            # 记录玩家发言
            self.db.add_game_message(
                session_id, 'player', "👤 玩家1", "player", message
            )
            
            # 触发AI玩家回应
            self._trigger_ai_responses(session_id, message)
            
            return True
            
        except Exception as e:
            print(f"玩家发言失败: {e}")
            return False
    
    def _trigger_ai_responses(self, session_id: str, player_message: str):
        """触发AI玩家的回应"""
        try:
            # 获取存活的AI玩家
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            print(f"🤖 存活AI玩家数量: {len(alive_ai_players)}")
            
            # 确保至少2-3个AI玩家回应
            num_responders = min(3, len(alive_ai_players))
            if num_responders > 0:
                responders = random.sample(alive_ai_players, num_responders)
                
                for i, ai_player in enumerate(responders):
                    response = self._generate_ai_response(session_id, ai_player, player_message)
                    if response:
                        self.db.add_game_message(
                            session_id, ai_player['character_id'], 
                            f"👤 玩家{ai_player['player_number']}", "ai_player", response
                        )
                        print(f"✅ AI玩家{ai_player['player_number']}已发言: {response[:50]}...")
                    else:
                        print(f"❌ AI玩家{ai_player['player_number']}发言失败")
            
            # 检查是否需要推进游戏阶段
            print(f"🎯 玩家发言后，检查阶段推进")
            self._check_phase_progression(session_id)
                    
        except Exception as e:
            print(f"AI回应失败: {e}")
    
    def _check_phase_progression(self, session_id: str):
        """检查并推进游戏阶段"""
        try:
            current_phase = self.db.get_game_state_value(session_id, 'current_phase')
            
            if current_phase == 'day_discussion':
                # 获取讨论轮数
                discussion_rounds = self.db.get_game_state_value(session_id, 'discussion_rounds')
                if not discussion_rounds:
                    discussion_rounds = 0
                else:
                    discussion_rounds = int(discussion_rounds)
                
                # 每3轮对话后推进到投票阶段
                recent_messages = self.db.get_game_messages(session_id, limit=15)
                player_messages = [msg for msg in recent_messages if msg.get('speaker_type') in ['player', 'ai_player']]
                
                print(f"🔍 阶段检查: 当前阶段={current_phase}, 玩家消息数={len(player_messages)}")
                
                if len(player_messages) >= 4:  # 降低到4次发言后开始投票
                    print("🚀 触发投票阶段")
                    self._start_voting_phase(session_id)
                elif len(player_messages) == 1:  # 如果只有1条消息，强制AI发言
                    print("🤖 强制AI发言推进游戏")
                    self._force_ai_discussion(session_id)
                    
        except Exception as e:
            print(f"阶段推进检查失败: {e}")
    
    def _force_ai_discussion(self, session_id: str):
        """强制AI玩家进行讨论"""
        try:
            # 获取存活的AI玩家
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            if not alive_ai_players:
                return
            
            # 让2-3个AI玩家主动发言
            num_speakers = min(3, len(alive_ai_players))
            speakers = random.sample(alive_ai_players, num_speakers)
            
            discussion_topics = [
                "现在让我们分析一下昨晚的结果，有什么可疑的地方吗？",
                "我觉得我们需要仔细观察每个人的发言，寻找线索。",
                "大家觉得谁的行为比较可疑？我们来讨论一下。"
            ]
            
            for i, ai_player in enumerate(speakers):
                if i < len(discussion_topics):
                    topic = discussion_topics[i]
                else:
                    topic = "让我说说我的看法..."
                
                response = self._generate_ai_discussion(session_id, ai_player, topic)
                if response:
                    self.db.add_game_message(
                        session_id, ai_player['character_id'], 
                        f"👤 玩家{ai_player['player_number']}", "ai_player", response
                    )
                    print(f"🗣️ AI玩家{ai_player['player_number']}主动发言: {response[:30]}...")
                    
        except Exception as e:
            print(f"强制AI讨论失败: {e}")
    
    def _generate_ai_discussion(self, session_id: str, ai_player: Dict, topic: str) -> str:
        """生成AI主动讨论内容"""
        try:
            day_count = int(self.db.get_game_state_value(session_id, 'day_count') or 1)
            alive_players = self._get_alive_players_info(session_id)
            
            prompt = f"""你是狼人杀游戏中的{ai_player['player_number']}号玩家，角色是{ai_player['role']}。

现在是第{day_count}天的讨论阶段，存活{len(alive_players)}人。

话题：{topic}

请结合你的角色身份，做出合理的分析和发言：
1. 如果你是狼人，要伪装成好人并制造混乱
2. 如果你是好人，要积极寻找狼人线索
3. 发言要简洁有力，30-50字即可
4. 要自然真实，符合狼人杀讨论氛围

请直接输出你的发言："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            return response.strip()
            
        except Exception as e:
            print(f"生成AI讨论失败: {e}")
            return f"我觉得我们需要仔细分析一下当前的情况。"
    
    def _start_voting_phase(self, session_id: str):
        """开始投票阶段"""
        try:
            self.db.set_game_state(session_id, 'current_phase', 'day_voting')
            
            # 法官宣布投票开始
            judge_id = self.db.get_game_state_value(session_id, 'judge_id')
            vote_message = "⏰ 讨论时间结束！现在开始投票阶段。请各位玩家投票决定今天要淘汰的玩家。"
            
            self.db.add_game_message(
                session_id, judge_id, "⚖️ 法官", "judge", vote_message
            )
            
            # 自动进行AI投票
            import threading
            timer = threading.Timer(3.0, self._auto_voting, args=[session_id])
            timer.start()
            
        except Exception as e:
            print(f"开始投票阶段失败: {e}")
    
    def _auto_voting(self, session_id: str):
        """自动投票逻辑"""
        try:
            # 获取存活玩家
            alive_players = self._get_alive_players_info(session_id)
            
            if len(alive_players) <= 2:
                self._check_game_over(session_id)
                return
            
            # AI玩家投票
            votes = {}
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            for ai_player in alive_ai_players:
                target = self._ai_vote_decision(session_id, ai_player, alive_players)
                if target:
                    votes[ai_player['player_number']] = target
                    self.db.add_game_message(
                        session_id, ai_player['character_id'],
                        f"🗳️ 玩家{ai_player['player_number']}", "vote",
                        f"我投票给 {target} 号玩家"
                    )
            
            # 处理投票结果
            self._process_voting_results(session_id, votes)
            
        except Exception as e:
            print(f"自动投票失败: {e}")
    
    def _ai_vote_decision(self, session_id: str, ai_player: Dict, alive_players: List[Dict]) -> Optional[int]:
        """AI投票决策"""
        try:
            # 获取可投票的目标（除自己外的存活玩家）
            targets = [p for p in alive_players if p['player_number'] != ai_player['player_number']]
            if not targets:
                return None
            
            # 狼人倾向于投票给好人，好人随机投票
            if ai_player.get('role') == 'werewolf':
                # 狼人优先投票给非狼人
                non_werewolf_targets = [p for p in targets if p.get('role') != 'werewolf']
                if non_werewolf_targets:
                    return random.choice(non_werewolf_targets)['player_number']
            
            # 随机投票
            return random.choice(targets)['player_number']
            
        except Exception as e:
            print(f"AI投票决策失败: {e}")
            return None
    
    def _process_voting_results(self, session_id: str, votes: Dict[int, int]):
        """处理投票结果"""
        try:
            # 统计投票
            vote_counts = {}
            for voter, target in votes.items():
                vote_counts[target] = vote_counts.get(target, 0) + 1
            
            if not vote_counts:
                # 没有投票，随机淘汰
                alive_players = self._get_alive_players_info(session_id)
                if alive_players:
                    eliminated = random.choice(alive_players)['player_number']
            else:
                # 找出得票最多的玩家
                max_votes = max(vote_counts.values())
                candidates = [player for player, votes in vote_counts.items() if votes == max_votes]
                eliminated = random.choice(candidates)
            
            # 淘汰玩家
            self._eliminate_player(session_id, eliminated)
            
            # 宣布投票结果
            judge_id = self.db.get_game_state_value(session_id, 'judge_id')
            result_message = f"📊 投票结果：{eliminated}号玩家被淘汰！"
            
            self.db.add_game_message(
                session_id, judge_id, "⚖️ 法官", "judge", result_message
            )
            
            # 检查游戏是否结束
            if not self._check_game_over(session_id):
                # 开始下一个夜晚
                import threading
                timer = threading.Timer(3.0, self._start_night_phase, args=[session_id])
                timer.start()
                
        except Exception as e:
            print(f"处理投票结果失败: {e}")
    
    def _eliminate_player(self, session_id: str, player_number: int):
        """淘汰玩家"""
        try:
            # 更新AI玩家状态
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            
            for player in ai_players:
                if player['player_number'] == player_number:
                    player['alive'] = False
                    break
            
            self.db.set_game_state(session_id, 'ai_players', json.dumps(ai_players))
            
        except Exception as e:
            print(f"淘汰玩家失败: {e}")
    
    def _generate_ai_response(self, session_id: str, ai_player: Dict, player_message: str) -> str:
        """生成AI玩家的回应"""
        try:
            # 获取AI角色的记忆
            character = self.character_manager.get_character(session_id, ai_player['character_id'])
            character_memory = character.get_recent_memory() if character else "无记忆"
            
            # 获取游戏历史和当前状态
            recent_messages = self.db.get_game_messages(session_id, limit=15)
            history = "\n".join([f"{msg['speaker_name']}: {msg['content'][:100]}" for msg in recent_messages[-8:]])
            
            # 获取游戏状态信息
            day_count = int(self.db.get_game_state_value(session_id, 'day_count') or 1)
            alive_players = self._get_alive_players_info(session_id)
            
            # 角色特定的发言指导
            role_guidance = {
                'werewolf': """作为狼人，你的策略：
                - 伪装成村民，表现出寻找狼人的样子
                - 适当时候转移话题或制造怀疑
                - 不要过分积极，也不要过分消极
                - 可以暗示其他人可疑，但要有逻辑
                - 避免与其他狼人表现得过于亲密""",
                
                'villager': """作为村民，你的策略：
                - 积极分析讨论，寻找狼人线索
                - 质疑可疑行为，但要有理有据
                - 保护可能的神职人员
                - 团结其他好人，共同找出狼人""",
                
                'seer': """作为预言家，你的策略：
                - 谨慎透露你掌握的信息
                - 在合适时机暗示某些玩家的身份
                - 不要过早暴露自己的身份
                - 引导讨论方向，但要巧妙
                - 如果掌握狼人信息，要想办法传达""",
                
                'witch': """作为女巫，你的策略：
                - 保持低调，不要暴露身份
                - 观察局势，寻找最佳时机发声
                - 如果使用过药品，要合理解释相关情况
                - 适当时候可以暗示你的特殊信息""",
                
                'hunter': """作为猎人，你的策略：
                - 表现得像普通村民
                - 不要过早暴露身份
                - 积极参与讨论，展现分析能力
                - 考虑在危险时刻透露身份威慑"""
            }
            
            prompt = f"""你是狼人杀游戏中的{ai_player['player_number']}号玩家，真实角色是{ai_player['role']}。

游戏状态：第{day_count}天，存活{len(alive_players)}人

你的个性：{ai_player.get('personality', '普通玩家')}
你的记忆：{character_memory}

{role_guidance.get(ai_player['role'], '')}

最近的对话：
{history}

玩家1刚才说："{player_message}"

请根据以上信息做出自然的回应：
1. 保持你的角色身份和个性特点
2. 回应要符合狼人杀游戏的讨论氛围
3. 控制在30-60字之间，要简洁有力
4. 可以提出疑问、分析、或表达观点
5. 语言要自然，避免机械化表达

请直接输出你的发言："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            # 更新AI角色记忆
            self.character_manager.update_character_memory(
                session_id, ai_player['character_id'], 
                f"第{day_count}天对玩家1发言的回应：{response.strip()}"
            )
            
            return response.strip()
            
        except Exception as e:
            print(f"生成AI回应失败: {e}")
            return ""
    
    def _get_alive_players_info(self, session_id: str) -> List[Dict]:
        """获取存活玩家信息"""
        try:
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_players = [p for p in ai_players if p['alive']]
            
            # 添加真实玩家
            player_alive = self.db.get_game_state_value(session_id, 'player_alive') != 'false'
            if player_alive:
                alive_players.append({'player_number': 1, 'alive': True})
            
            return alive_players
        except Exception as e:
            print(f"获取存活玩家信息失败: {e}")
            return []
    
    def start_voting(self, session_id: str) -> bool:
        """开始投票阶段"""
        try:
            # 设置投票阶段
            self.db.set_game_state(session_id, 'current_phase', 'day_voting')
            
            # 法官宣布投票开始
            judge_id = self.db.get_game_state_value(session_id, 'judge_id')
            voting_message = "🗳️ 讨论结束，现在开始投票！请所有玩家选择要投票出局的玩家。"
            
            self.db.add_game_message(
                session_id, judge_id, "🗳️ 法官", "judge", voting_message
            )
            
            return True
            
        except Exception as e:
            print(f"开始投票失败: {e}")
            return False
    
    def player_vote(self, session_id: str, target_number: int) -> bool:
        """玩家投票"""
        try:
            # 检查是否在投票阶段
            current_phase = self.db.get_game_state_value(session_id, 'current_phase')
            if current_phase != 'day_voting':
                return False
            
            # 记录玩家投票
            self.db.set_game_state(session_id, 'player_vote', str(target_number))
            
            self.db.add_game_message(
                session_id, 'player', "👤 玩家1", "player", 
                f"投票选择：{target_number}号玩家"
            )
            
            # 进行AI投票
            self._conduct_ai_voting(session_id)
            
            # 统计投票结果
            self._process_voting_results(session_id)
            
            return True
            
        except Exception as e:
            print(f"玩家投票失败: {e}")
            return False
    
    def _conduct_ai_voting(self, session_id: str):
        """进行AI投票"""
        try:
            # 获取存活的AI玩家
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            # 获取所有存活玩家（包括真实玩家）
            all_alive = [1] + [p['player_number'] for p in alive_ai_players]
            
            votes = {}
            
            for ai_player in alive_ai_players:
                # AI选择投票目标
                target = self._ai_choose_vote_target(session_id, ai_player, all_alive)
                if target:
                    votes[ai_player['player_number']] = target
                    
                    self.db.add_game_message(
                        session_id, ai_player['character_id'], 
                        f"👤 玩家{ai_player['player_number']}", "ai_player", 
                        f"我投票给{target}号玩家"
                    )
            
            # 保存AI投票结果
            self.db.set_game_state(session_id, 'ai_votes', json.dumps(votes))
            
        except Exception as e:
            print(f"AI投票失败: {e}")
    
    def _ai_choose_vote_target(self, session_id: str, ai_player: Dict, all_alive: List[int]) -> Optional[int]:
        """AI选择投票目标"""
        try:
            # 排除自己
            candidates = [p for p in all_alive if p != ai_player['player_number']]
            if not candidates:
                return None
            
            # 获取角色记忆和游戏历史
            character = self.character_manager.get_character(session_id, ai_player['character_id'])
            character_memory = character.get_recent_memory() if character else "无记忆"
            recent_messages = self.db.get_game_messages(session_id, limit=15)
            history = "\n".join([f"{msg['speaker_name']}: {msg['content']}" for msg in recent_messages[-10:]])
            
            candidates_str = "、".join([f"{c}号玩家" for c in candidates])
            
            prompt = f"""你是狼人杀游戏中的{ai_player['player_number']}号玩家，角色是{ai_player['role']}。

你的记忆：{character_memory}

最近的讨论：
{history}

现在需要投票，可选择的目标：{candidates_str}

请根据你的身份选择投票目标：
1. 如果你是狼人，优先投好人，保护狼人队友
2. 如果你是好人，投最可疑的玩家
3. 如果你是神职，保护自己和其他好人

请直接输出要投票的玩家号码（只需要数字）："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            try:
                target = int(response.strip())
                if target in candidates:
                    return target
            except ValueError:
                pass
            
            # 如果AI选择失败，根据角色随机选择
            if ai_player['role'] == 'werewolf':
                # 狼人优先投非狼人
                non_werewolves = []
                ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
                ai_players = json.loads(ai_players_str) if ai_players_str else []
                
                for candidate in candidates:
                    if candidate == 1:  # 真实玩家
                        non_werewolves.append(candidate)
                    else:
                        ai_player_info = next((p for p in ai_players if p['player_number'] == candidate), None)
                        if ai_player_info and ai_player_info['role'] != 'werewolf':
                            non_werewolves.append(candidate)
                
                return random.choice(non_werewolves) if non_werewolves else random.choice(candidates)
            else:
                return random.choice(candidates)
                
        except Exception as e:
            print(f"AI选择投票目标失败: {e}")
            return random.choice([p for p in all_alive if p != ai_player['player_number']])
    
    def _process_voting_results(self, session_id: str):
        """处理投票结果"""
        try:
            # 获取所有投票
            player_vote = int(self.db.get_game_state_value(session_id, 'player_vote') or 0)
            ai_votes_str = self.db.get_game_state_value(session_id, 'ai_votes')
            ai_votes = json.loads(ai_votes_str) if ai_votes_str else {}
            
            # 统计票数
            vote_counts = {}
            
            # 真实玩家投票
            if player_vote > 0:
                vote_counts[player_vote] = vote_counts.get(player_vote, 0) + 1
            
            # AI玩家投票
            for target in ai_votes.values():
                vote_counts[target] = vote_counts.get(target, 0) + 1
            
            # 找出得票最多的玩家
            if vote_counts:
                max_votes = max(vote_counts.values())
                winners = [player for player, votes in vote_counts.items() if votes == max_votes]
                
                # 如果平票，随机选择
                eliminated_player = random.choice(winners)
                
                # 更新玩家状态
                if eliminated_player != 1:  # 不是真实玩家
                    ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
                    ai_players = json.loads(ai_players_str) if ai_players_str else []
                    
                    for player in ai_players:
                        if player['player_number'] == eliminated_player:
                            player['alive'] = False
                            break
                    
                    self.db.set_game_state(session_id, 'ai_players', json.dumps(ai_players))
                else:
                    # 真实玩家被投出
                    self.db.set_game_state(session_id, 'player_alive', 'false')
                
                # 法官宣布结果
                judge_id = self.db.get_game_state_value(session_id, 'judge_id')
                result_message = f"📊 投票结果：{eliminated_player}号玩家被投票出局！"
                
                # 显示详细投票情况
                vote_details = "\n".join([f"{player}号: {votes}票" for player, votes in vote_counts.items()])
                result_message += f"\n\n票数统计：\n{vote_details}"
                
                self.db.add_game_message(
                    session_id, judge_id, "📊 法官", "judge", result_message
                )
                
                # 检查游戏是否结束
                if not self._check_game_over(session_id):
                    # 继续下一轮，增加天数
                    day_count = int(self.db.get_game_state_value(session_id, 'day_count') or 1)
                    self.db.set_game_state(session_id, 'day_count', str(day_count + 1))
                    
                    # 开始新的夜晚
                    self._start_night_phase(session_id)
            
        except Exception as e:
            print(f"处理投票结果失败: {e}")
    
    def _check_game_over(self, session_id: str) -> bool:
        """检查游戏是否结束"""
        try:
            # 获取存活玩家信息
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            player_alive = self.db.get_game_state_value(session_id, 'player_alive') != 'false'
            player_role = self.db.get_game_state_value(session_id, 'player_role')
            
            # 统计存活的狼人和好人
            alive_werewolves = [p for p in alive_ai_players if p['role'] == 'werewolf']
            alive_good_guys = [p for p in alive_ai_players if p['role'] != 'werewolf']
            
            # 如果真实玩家存活，加入对应阵营
            if player_alive:
                if player_role == 'werewolf':
                    alive_werewolves.append({'player_number': 1, 'role': player_role})
                else:
                    alive_good_guys.append({'player_number': 1, 'role': player_role})
            
            winner = None
            
            # 判断胜负
            if len(alive_werewolves) == 0:
                winner = "好人阵营"
            elif len(alive_werewolves) >= len(alive_good_guys):
                winner = "狼人阵营"
            
            if winner:
                # 游戏结束
                self.db.set_game_state(session_id, 'current_phase', 'game_over')
                self.db.set_game_state(session_id, 'winner', winner)
                
                # 生成游戏结束消息
                end_message = self._generate_game_end_message(session_id, winner)
                judge_id = self.db.get_game_state_value(session_id, 'judge_id')
                
                self.db.add_game_message(
                    session_id, judge_id, "🏆 法官", "judge", end_message
                )
                
                return True
            
            return False
            
        except Exception as e:
            print(f"检查游戏结束失败: {e}")
            return False
    
    def _generate_game_end_message(self, session_id: str, winner: str) -> str:
        """生成游戏结束消息"""
        try:
            # 获取所有角色信息
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            player_role = self.db.get_game_state_value(session_id, 'player_role')
            
            # 构建角色揭示信息
            all_roles = [f"1号玩家（您）: {player_role}"]
            all_roles.extend([f"{p['player_number']}号玩家: {p['role']}" for p in ai_players])
            
            roles_reveal = "\n".join(all_roles)
            
            prompt = f"""狼人杀游戏结束了！{winner}获得胜利！

所有玩家身份：
{roles_reveal}

请作为法官生成游戏结束的总结词：
1. 祝贺获胜阵营
2. 点评游戏过程中的精彩表现
3. 揭示关键转折点
4. 营造热烈的结束氛围
5. 控制在200字以内

请直接输出结束词："""
            
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            return f"🏆 游戏结束！{winner}获得胜利！\n\n{response.strip()}\n\n角色揭示：\n{roles_reveal}"
            
        except Exception as e:
            print(f"生成游戏结束消息失败: {e}")
            return f"🏆 游戏结束！{winner}获得胜利！\n\n感谢各位玩家的精彩表现，期待下次再战！"
    
    def load_game_state(self, session_id: str) -> Optional[Dict]:
        """加载游戏状态"""
        return self.db.get_game_session(session_id)
    
    def get_game_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取游戏消息"""
        return self.db.get_game_messages(session_id, limit)
    
    def get_current_phase(self, session_id: str) -> str:
        """获取当前游戏阶段"""
        return self.db.get_game_state_value(session_id, 'current_phase') or 'night'
    
    def get_player_role(self, session_id: str) -> str:
        """获取玩家角色"""
        return self.db.get_game_state_value(session_id, 'player_role') or 'villager'
    
    def get_alive_players(self, session_id: str) -> List[Dict]:
        """获取存活玩家列表"""
        try:
            ai_players_str = self.db.get_game_state_value(session_id, 'ai_players')
            ai_players = json.loads(ai_players_str) if ai_players_str else []
            alive_ai_players = [p for p in ai_players if p['alive']]
            
            # 添加真实玩家
            player_alive = self.db.get_game_state_value(session_id, 'player_alive') != 'false'
            result = []
            
            if player_alive:
                result.append({
                    'player_number': 1,
                    'name': '玩家1（您）',
                    'alive': True
                })
            
            for player in alive_ai_players:
                result.append({
                    'player_number': player['player_number'],
                    'name': f'玩家{player["player_number"]}',
                    'alive': True
                })
            
            return result
            
        except Exception as e:
            print(f"获取存活玩家失败: {e}")
            return []