#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI推理侦探游戏 - 完整实现
"""

import json
import uuid
import random
from datetime import datetime
from typing import Dict, List, Optional
from services.ai_service import AIService
from services.ai_character_manager import AICharacterManager
from utils.database import DatabaseManager


class DetectiveGame:
    """AI推理侦探游戏"""
    
    def __init__(self):
        # 从配置文件加载AI服务设置
        self.ai_service = self._load_ai_service()
        self.character_manager = AICharacterManager()
        self.db = DatabaseManager()
        
        # 案件类型
        self.case_types = [
            'murder', 'theft', 'fraud', 'kidnapping', 'corporate_crime'
        ]
        
        # 线索类型
        self.evidence_types = [
            'physical', 'testimony', 'financial', 'digital', 'forensic'
        ]
    
    def _load_ai_service(self):
        """从配置文件加载AI服务"""
        import json
        import os
        
        config_path = 'config/settings.json'
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                platform = config.get('current_platform', 'dashscope')
                
                if platform == 'dashscope':
                    api_key = config.get('dashscope_api_key')
                    model = config.get('current_model', 'qwen-plus')
                elif platform == 'openrouter':
                    api_key = config.get('openrouter_api_key')
                    model = config.get('current_model', 'gemini-flash')
                else:
                    # 默认使用百炼
                    platform = 'dashscope'
                    api_key = config.get('dashscope_api_key')
                    model = config.get('current_model', 'qwen-plus')
                
                if api_key:
                    print(f"🔧 使用{platform}平台，模型: {model}")
                    ai_service = AIService(api_key=api_key, platform=platform)
                    ai_service.set_model(model)
                    return ai_service
            
            # 如果配置文件不存在或没有API密钥，使用默认设置
            print("⚠️ 使用默认AI配置")
            return AIService()
            
        except Exception as e:
            print(f"❌ 加载AI配置失败: {e}")
            return AIService()
    
    def _safe_ai_call(self, prompt: str, fallback_message: str = "暂时无法提供AI分析，请稍后重试。") -> str:
        """安全的AI调用，有备用方案"""
        try:
            response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            if response.get('success') and response.get('content'):
                return response['content']
            else:
                print(f"AI调用失败: {response.get('error', '未知错误')}")
                return fallback_message
        except Exception as e:
            print(f"AI调用异常: {e}")
            return fallback_message
    
    def create_new_game(self, user_id: int = 1) -> str:
        """创建新的侦探游戏"""
        session_id = str(uuid.uuid4())
        
        config = {
            'game_type': 'ai_detective_game',
            'case_type': random.choice(self.case_types),
            'current_phase': 'investigation'
        }
        
        self.db.create_game_session(session_id, 'ai_detective_game', user_id, config)
        
        # 立即生成案件
        self._initialize_case(session_id, config['case_type'])
        
        return session_id
    
    def _initialize_case(self, session_id: str, case_type: str):
        """初始化案件"""
        # 1. 生成案件背景
        case_data = self._generate_case(case_type)
        
        # 2. 保存案件数据
        self.db.set_game_state(session_id, 'case_data', json.dumps(case_data))
        self.db.set_game_state(session_id, 'truth', json.dumps(case_data.get('truth', {})))
        
        # 3. 创建嫌疑人
        self._create_suspects(session_id, case_data)
        
        # 4. 初始化证据
        self._initialize_evidence(session_id, case_data)
        
        # 5. 发送开场消息
        self._send_case_intro(session_id, case_data)
    
    def _generate_case(self, case_type: str) -> Dict:
        """使用AI生成案件"""
        prompt = f"""
        生成一个{case_type}类型的推理案件，包含以下信息：
        
        案件信息：
        - 案件标题
        - 案件简介
        - 案发地点
        - 案发时间
        - 受害者信息
        
        嫌疑人信息（3-5个）：
        - 姓名、年龄、职业
        - 与受害者关系
        - 动机
        - 不在场证明
        - 性格特点
        
        证据线索（5-8个）：
        - 物理证据
        - 证人证言
        - 财务记录等
        
        真相：
        - 真正凶手
        - 作案动机
        - 作案过程
        
        请以JSON格式回复，确保逻辑严密。
        """
        
        try:
            api_response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            
            print(f"🔍 API响应结构: {api_response}")
            
            if not api_response.get('success'):
                print(f"❌ API调用失败: {api_response.get('error', '未知错误')}")
                return self._generate_simple_case(case_type)
            
            response = api_response['content']
            print(f"🤖 AI案件生成响应: {response[:100] if response else '空响应'}...")
            
            if not response or not response.strip():
                print("❌ AI返回空响应")
                return self._generate_simple_case(case_type)
            
            # 尝试解析JSON
            case_data = json.loads(response)
            return case_data
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {response[:200] if 'response' in locals() else '无响应'}")
            # 使用AI生成简化案件而不是固定模板
            return self._generate_simple_case(case_type)
        except Exception as e:
            print(f"AI生成案件失败: {e}")
            # 使用AI生成简化案件而不是固定模板
            return self._generate_simple_case(case_type)
    
    def _generate_simple_case(self, case_type: str) -> Dict:
        """生成简化案件（无需AI）"""
        print(f"🔄 使用本地生成的{case_type}案件")
        
        # 直接返回完整的备用案件，不依赖AI
        return self._get_fallback_case(case_type)
    
    def _get_fallback_case(self, case_type: str) -> Dict:
        """备用案件数据"""
        return {
            "title": "豪宅谋杀案",
            "description": "商业大亨李总在家中被发现死亡，死因为中毒。现场发现多个可疑线索。",
            "location": "市郊豪宅书房",
            "time": "昨晚11点左右",
            "victim": {
                "name": "李志强",
                "age": 52,
                "occupation": "房地产公司董事长"
            },
            "suspects": [
                {
                    "name": "李夫人",
                    "age": 45,
                    "occupation": "家庭主妇",
                    "relationship": "妻子",
                    "motive": "巨额保险金",
                    "alibi": "声称在卧室看电视",
                    "personality": "表面温和，内心城府很深"
                },
                {
                    "name": "张助理",
                    "age": 28,
                    "occupation": "私人助理",
                    "relationship": "工作伙伴",
                    "motive": "公司内幕交易被发现",
                    "alibi": "声称已回家",
                    "personality": "紧张焦虑，说话闪烁其词"
                },
                {
                    "name": "王律师",
                    "age": 55,
                    "occupation": "律师",
                    "relationship": "法律顾问",
                    "motive": "遗嘱修改纠纷",
                    "alibi": "在律师楼加班",
                    "personality": "老谋深算，措辞严谨"
                }
            ],
            "evidence": [
                {
                    "type": "physical",
                    "item": "茶杯",
                    "description": "书桌上有半杯茶，检测出氰化物残留"
                },
                {
                    "type": "testimony",
                    "item": "管家证言",
                    "description": "管家听到书房有争吵声"
                },
                {
                    "type": "financial",
                    "item": "保险单",
                    "description": "发现高额人寿保险，受益人为妻子"
                }
            ],
            "truth": {
                "killer": "李夫人",
                "method": "在茶中下毒",
                "motive": "为了获得保险金和遗产",
                "process": "趁李总专心工作时在茶中投毒"
            }
        }
    
    def _create_suspects(self, session_id: str, case_data: Dict):
        """创建嫌疑人角色"""
        suspects = case_data.get('suspects', [])
        
        for suspect in suspects:
            # 使用AI角色管理器创建角色
            character_id = self.character_manager.create_character(
                session_id=session_id,
                name=suspect['name'],
                character_type='suspect',
                personality=suspect.get('personality', ''),
                background=f"年龄：{suspect['age']}，职业：{suspect['occupation']}，关系：{suspect['relationship']}",
                secrets=f"动机：{suspect['motive']}，不在场证明：{suspect['alibi']}"
            )
            
            # 保存角色ID映射，方便后续查找
            self.db.set_game_state(session_id, f'suspect_{suspect["name"]}_id', character_id)
    
    def _initialize_evidence(self, session_id: str, case_data: Dict):
        """初始化证据"""
        evidence_list = case_data.get('evidence', [])
        
        discovered_evidence = []
        for evidence in evidence_list:
            discovered_evidence.append({
                'id': str(uuid.uuid4()),
                'type': evidence['type'],
                'name': evidence['item'],
                'description': evidence['description'],
                'discovered': False,
                'analyzed': False
            })
        
        self.db.set_game_state(session_id, 'evidence_list', json.dumps(discovered_evidence))
        self.db.set_game_state(session_id, 'discovered_clues', '0')
        self.db.set_game_state(session_id, 'interrogations_count', '0')
    
    def _send_case_intro(self, session_id: str, case_data: Dict):
        """发送案件介绍"""
        intro_message = f"""
🔍 **案件档案**

**案件：** {case_data['title']}
**地点：** {case_data['location']}
**时间：** {case_data['time']}

**案情简介：**
{case_data['description']}

**受害者：** {case_data['victim']['name']}（{case_data['victim']['age']}岁）
**职业：** {case_data['victim']['occupation']}

---

作为资深侦探，您需要通过审讯嫌疑人、分析证据来找出真凶。

🎯 **调查提示：**
• 仔细审讯每个嫌疑人
• 寻找并分析所有证据
• 注意前后矛盾的供词
• 最终提交您的推理结论

开始您的调查吧！
        """
        
        self.db.add_game_message(session_id, 'system', '🕵️ 系统', 'system', intro_message)
    
    def load_game_state(self, session_id: str) -> Optional[Dict]:
        """加载游戏状态"""
        return self.db.get_game_session(session_id)
    
    def get_game_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取游戏消息"""
        return self.db.get_game_messages(session_id, limit)
    
    def start_case(self, session_id: str, case_type: str = 'murder') -> Dict:
        """开始新案件"""
        try:
            # 重新初始化案件
            self._initialize_case(session_id, case_type)
            
            return {
                'success': True,
                'message': '新案件已生成！开始您的调查。',
                'case_started': True
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'案件生成失败：{str(e)}'
            }
    
    def interrogate_suspect(self, session_id: str, suspect_name: str, question: str) -> Dict:
        """审讯嫌疑人"""
        try:
            # 获取嫌疑人角色ID
            character_id = self.db.get_game_state_value(session_id, f'suspect_{suspect_name}_id')
            
            # 如果找不到，尝试查找所有角色ID进行模糊匹配
            if not character_id:
                print(f"🔍 尝试模糊匹配嫌疑人: {suspect_name}")
                # 获取所有嫌疑人角色
                all_characters = self.character_manager.get_all_characters(session_id)
                for character in all_characters:
                    if character.character_type == 'suspect' and suspect_name in character.name:
                        character_id = character.id
                        print(f"✅ 找到匹配的嫌疑人: {character.name} -> {character_id}")
                        break
                
                if not character_id:
                    available_suspects = [char.name for char in all_characters if char.character_type == 'suspect']
                    return {
                        'success': False,
                        'error': f'找不到嫌疑人：{suspect_name}。可用嫌疑人：{", ".join(available_suspects)}'
                    }
            
            # 获取嫌疑人信息
            character = self.character_manager.get_character(session_id, character_id)
            
            if not character:
                return {
                    'success': False,
                    'error': f'找不到嫌疑人：{suspect_name}'
                }
            
            # 构造审讯提示词
            prompt = f"""
            你现在扮演嫌疑人{suspect_name}，背景：{character.get('background', '')}
            性格：{character.get('personality', '')}
            秘密信息：{character.get('secrets', '')}
            
            侦探问你：{question}
            
            请根据角色设定回答，要：
            1. 保持角色一致性
            2. 可以隐瞒部分真相但不能完全撒谎
            3. 在压力下可能露出破绽
            4. 回答要自然，符合人物性格
            
            直接回答问题，不要说"作为XXX"。
            """
            
            # AI生成回答
            answer = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )['content']
            
            # 记录对话
            self.db.add_game_message(session_id, 'user', '🕵️ 侦探', 'user', f"审讯{suspect_name}：{question}")
            self.db.add_game_message(session_id, character_id, f"👤 {suspect_name}", 'npc', answer)
            
            # 更新审讯次数
            count = int(self.db.get_game_state_value(session_id, 'interrogations_count') or '0')
            self.db.set_game_state(session_id, 'interrogations_count', str(count + 1))
            
            # 更新角色记忆
            self.character_manager.update_character_memory(session_id, character_id, f"被问：{question}，回答：{answer}")
            
            return {
                'success': True,
                'suspect_name': suspect_name,
                'question': question,
                'answer': answer,
                'interrogation_count': count + 1
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'审讯失败：{str(e)}'
            }
    
    def analyze_evidence(self, session_id: str, evidence_name: str) -> Dict:
        """分析证据"""
        try:
            # 获取证据列表
            evidence_list_str = self.db.get_game_state_value(session_id, 'evidence_list')
            if not evidence_list_str:
                return {
                    'success': False,
                    'error': '没有找到证据列表'
                }
            
            evidence_list = json.loads(evidence_list_str)
            
            # 查找指定证据
            target_evidence = None
            for evidence in evidence_list:
                if evidence['name'] == evidence_name:
                    target_evidence = evidence
                    break
            
            if not target_evidence:
                return {
                    'success': False,
                    'error': f'没有找到证据：{evidence_name}'
                }
            
            # 标记为已发现和已分析
            target_evidence['discovered'] = True
            target_evidence['analyzed'] = True
            
            # 生成分析结果
            analysis_prompt = f"""
            作为资深法医，分析以下证据：
            
            证据名称：{target_evidence['name']}
            证据类型：{target_evidence['type']}
            基本描述：{target_evidence['description']}
            
            请提供专业的分析结果，包括：
            1. 证据的重要性
            2. 可能的推理方向
            3. 与案件的关联性
            4. 需要进一步调查的线索
            
            分析要专业但易懂。
            """
            
            # 使用安全AI调用，带备用方案
            fallback_analysis = f"""
            【证据分析报告】
            
            证据名称：{target_evidence['name']}
            证据类型：{target_evidence['type']}
            
            初步分析：
            • 这是一个重要的{target_evidence['type']}类证据
            • 需要结合其他证据进行综合分析
            • 建议继续收集相关线索
            • 可能与案件核心有直接关联
            
            【建议】继续收集更多证据，进行交叉验证分析。
            """
            
            analysis_result = self._safe_ai_call(analysis_prompt, fallback_analysis)
            
            # 保存更新的证据列表
            self.db.set_game_state(session_id, 'evidence_list', json.dumps(evidence_list))
            
            # 更新发现线索数
            discovered_count = sum(1 for e in evidence_list if e['discovered'])
            self.db.set_game_state(session_id, 'discovered_clues', str(discovered_count))
            
            # 记录分析
            self.db.add_game_message(session_id, 'user', '🕵️ 侦探', 'user', f"分析证据：{evidence_name}")
            self.db.add_game_message(session_id, 'system', '🔬 法医分析', 'system', analysis_result)
            
            return {
                'success': True,
                'evidence_name': evidence_name,
                'analysis': analysis_result,
                'discovered_clues': discovered_count
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'证据分析失败：{str(e)}'
            }
    
    def get_evidence_list(self, session_id: str) -> Dict:
        """获取证据列表"""
        try:
            evidence_list_str = self.db.get_game_state_value(session_id, 'evidence_list')
            if not evidence_list_str:
                return {
                    'success': False,
                    'error': '没有找到证据列表'
                }
            
            evidence_list = json.loads(evidence_list_str)
            return {
                'success': True,
                'evidence_list': evidence_list
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'获取证据列表失败：{str(e)}'
            }
    
    def submit_conclusion(self, session_id: str, suspect: str, reasoning: str) -> Dict:
        """提交推理结论"""
        try:
            # 获取真相
            truth_str = self.db.get_game_state_value(session_id, 'truth')
            if not truth_str:
                return {
                    'success': False,
                    'error': '无法获取案件真相'
                }
            
            truth = json.loads(truth_str)
            correct_killer = truth.get('killer', '')
            
            # 判断是否正确
            is_correct = suspect == correct_killer
            
            # 计算得分
            interrogation_count = int(self.db.get_game_state_value(session_id, 'interrogations_count') or '0')
            discovered_clues = int(self.db.get_game_state_value(session_id, 'discovered_clues') or '0')
            
            base_score = 100 if is_correct else 0
            efficiency_bonus = max(0, 50 - interrogation_count * 5)  # 审讯效率奖励
            clue_bonus = discovered_clues * 10  # 线索发现奖励
            
            total_score = base_score + efficiency_bonus + clue_bonus
            
            # 生成评价
            evaluation_prompt = f"""
            作为资深警官，评价侦探的推理：
            
            指控嫌疑人：{suspect}
            推理过程：{reasoning}
            
            真实情况：
            真凶：{correct_killer}
            作案动机：{truth.get('motive', '')}
            作案手法：{truth.get('method', '')}
            
            请给出评价，包括：
            1. 推理是否正确
            2. 推理过程的优缺点
            3. 遗漏的关键线索
            4. 专业建议
            
            评价要客观公正。
            """
            
            evaluation = self.ai_service.chat(
                messages=[{"role": "user", "content": evaluation_prompt}]
            )['content']
            
            # 记录结论
            self.db.add_game_message(session_id, 'user', '🕵️ 侦探', 'user', f"最终结论：指控{suspect}。推理：{reasoning}")
            self.db.add_game_message(session_id, 'system', '⚖️ 结案评价', 'system', evaluation)
            
            # 保存得分
            self.db.save_game_score(session_id, 1, 'ai_detective_game', total_score, {
                'correct': is_correct,
                'accused': suspect,
                'actual_killer': correct_killer,
                'interrogations': interrogation_count,
                'clues_found': discovered_clues
            })
            
            return {
                'success': True,
                'correct': is_correct,
                'score': total_score,
                'accused': suspect,
                'actual_killer': correct_killer,
                'evaluation': evaluation,
                'case_closed': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'结案失败：{str(e)}'
            }