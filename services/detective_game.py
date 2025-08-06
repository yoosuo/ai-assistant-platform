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
            
            # 清理响应内容，移除markdown代码块
            cleaned_response = response.strip()
            
            # 查找JSON开始位置
            json_start = -1
            for marker in ['```json\n', '```json', '```\n', '```']:
                idx = cleaned_response.find(marker)
                if idx != -1:
                    json_start = idx + len(marker)
                    break
            
            if json_start == -1:
                # 没有找到代码块标记，直接查找JSON开始符号
                json_start = cleaned_response.find('{')
                if json_start == -1:
                    raise ValueError("无法找到JSON开始位置")
            
            # 查找JSON结束位置
            json_end = cleaned_response.rfind('```')
            if json_end == -1 or json_end <= json_start:
                # 没有找到结束标记，查找最后一个}
                json_end = cleaned_response.rfind('}') + 1
                if json_end <= json_start:
                    raise ValueError("无法找到JSON结束位置")
            
            # 提取JSON内容
            json_content = cleaned_response[json_start:json_end].strip()
            print(f"🧹 提取的JSON内容: {json_content[:200]}...")
            
            # 尝试解析JSON
            case_data = json.loads(json_content)
            print(f"✅ JSON解析成功，案件标题: {case_data.get('案件信息', {}).get('案件标题', 'Unknown')}")
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
            "案件信息": {
                "案件标题": "豪宅谋杀案",
                "案件简介": "商业大亨李总在家中被发现死亡，死因为中毒。现场发现多个可疑线索，多名亲近人员都有作案动机和机会。",
                "案发地点": "市郊豪宅书房",
                "案发时间": "昨晚11点左右",
                "受害者信息": {
                    "姓名": "李志强",
                    "年龄": "52岁",
                    "职业": "房地产公司董事长",
                    "其他信息": "生前身体健康，无疾病史"
                }
            },
            "嫌疑人信息": [
                {
                    "姓名": "李夫人",
                    "年龄": 45,
                    "职业": "家庭主妇",
                    "与受害者关系": "妻子",
                    "动机": "巨额保险金和遗产继承",
                    "不在场证明": "声称在卧室看电视",
                    "性格特点": "表面温和，内心城府很深"
                },
                {
                    "姓名": "张助理",
                    "年龄": 28,
                    "职业": "私人助理",
                    "与受害者关系": "工作伙伴",
                    "动机": "内幕交易被发现，担心被起诉",
                    "不在场证明": "声称在公司加班",
                    "性格特点": "紧张焦虑，说话闪烁其词"
                },
                {
                    "姓名": "王律师",
                    "年龄": 55,
                    "职业": "律师",
                    "与受害者关系": "法律顾问",
                    "动机": "遗嘱修改纠纷，经济损失",
                    "不在场证明": "声称在律师楼加班",
                    "性格特点": "老谋深算，措辞严谨"
                }
            ],
            "证据线索": [
                {
                    "类型": "物理证据",
                    "内容": "在书房发现一只红酒杯，杯中残留毒物"
                },
                {
                    "类型": "文件证据",
                    "内容": "桌上发现一份未签名的遗嘱草稿，内容有重大变更"
                },
                {
                    "类型": "电子证据",
                    "内容": "死者手机显示当晚有多通电话记录"
                },
                {
                    "类型": "财务证据",
                    "内容": "发现一份高额人寿保险合同，受益人为李夫人"
                },
                {
                    "类型": "银行记录",
                    "内容": "近期有大额现金转账记录，目的地不明"
                }
            ],
            "真相": {
                "真正凶手": "李夫人",
                "作案动机": "为了获得巨额保险金和遗产继承权",
                "作案过程": "李夫人趁李总在书房工作时，送去一杯红酒。红酒中事先投入了无色无味的剧毒物质，李总饮用后中毒身亡。"
            }
        }
    
    def _create_suspects(self, session_id: str, case_data: Dict):
        """创建嫌疑人角色"""
        print(f"🔧 开始创建嫌疑人，案件数据键名: {list(case_data.keys())}")
        
        # 处理新的中文数据结构
        if '嫌疑人信息' in case_data:
            suspects = case_data.get('嫌疑人信息', [])
            print(f"🔧 使用中文结构，嫌疑人数量: {len(suspects)}")
        else:
            suspects = case_data.get('suspects', [])
            print(f"🔧 使用英文结构，嫌疑人数量: {len(suspects)}")
        
        for suspect in suspects:
            print(f"🔧 处理嫌疑人: {suspect}")
            print(f"🔧 嫌疑人键名: {list(suspect.keys())}")
            # 支持中文和英文键名
            name = suspect.get('姓名', suspect.get('name', ''))
            age = suspect.get('年龄', suspect.get('age', ''))
            occupation = suspect.get('职业', suspect.get('occupation', ''))
            relationship = suspect.get('与受害者关系', suspect.get('relationship', ''))
            motive = suspect.get('动机', suspect.get('motive', ''))
            alibi = suspect.get('不在场证明', suspect.get('alibi', ''))
            personality = suspect.get('性格特点', suspect.get('personality', ''))
            
            print(f"🔧 创建角色: 姓名={name}, 年龄={age}, 职业={occupation}")
            
            # 使用AI角色管理器创建角色
            character_id = self.character_manager.create_character(
                session_id=session_id,
                name=name,
                character_type='suspect',
                personality=personality,
                background=f"年龄：{age}，职业：{occupation}，关系：{relationship}",
                secrets=f"动机：{motive}，不在场证明：{alibi}"
            )
            
            print(f"🔧 角色创建成功: {name} -> {character_id}")
            
            # 保存角色ID映射，方便后续查找
            self.db.set_game_state(session_id, f'suspect_{name}_id', character_id)
            print(f"🔧 保存角色映射: suspect_{name}_id -> {character_id}")
    
    def _initialize_evidence(self, session_id: str, case_data: Dict):
        """初始化证据"""
        # 处理新的中文数据结构
        if '证据线索' in case_data:
            evidence_list = case_data.get('证据线索', [])
        else:
            evidence_list = case_data.get('evidence', [])
        
        discovered_evidence = []
        for evidence in evidence_list:
            # 支持中文和英文键名
            evidence_type = evidence.get('类型', evidence.get('type', ''))
            evidence_content = evidence.get('内容', evidence.get('item', ''))
            evidence_desc = evidence.get('内容', evidence.get('description', ''))
            
            # 使用与key_evidence相同的命名格式
            evidence_name = evidence_type + ' - ' + evidence_content[:20] + "..."
            
            discovered_evidence.append({
                'id': str(uuid.uuid4()),
                'type': evidence_type,
                'name': evidence_name,
                'description': evidence_desc,
                'discovered': False,
                'analyzed': False
            })
        
        self.db.set_game_state(session_id, 'evidence_list', json.dumps(discovered_evidence))
        self.db.set_game_state(session_id, 'discovered_clues', '0')
        self.db.set_game_state(session_id, 'interrogations_count', '0')
    
    def _send_case_intro(self, session_id: str, case_data: Dict):
        """发送案件介绍"""
        # 处理新的中文数据结构
        if '案件信息' in case_data:
            case_info = case_data.get('案件信息', {})
            victim_info = case_info.get('受害者信息', {})
            
            case_title = case_info.get('案件标题', '')
            case_location = case_info.get('案发地点', '')
            case_time = case_info.get('案发时间', '')
            case_description = case_info.get('案件简介', '')
            victim_name = victim_info.get('姓名', '')
            victim_age = victim_info.get('年龄', '')
            victim_occupation = victim_info.get('职业', '')
        else:
            # 备用英文结构
            case_title = case_data.get('title', '')
            case_location = case_data.get('location', '')
            case_time = case_data.get('time', '')
            case_description = case_data.get('description', '')
            victim_info = case_data.get('victim', {})
            victim_name = victim_info.get('name', '')
            victim_age = victim_info.get('age', '')
            victim_occupation = victim_info.get('occupation', '')
        
        intro_message = f"""
🔍 **案件档案**

**案件：** {case_title}
**地点：** {case_location}
**时间：** {case_time}

**案情简介：**
{case_description}

**受害者：** {victim_name}（{victim_age}岁）
**职业：** {victim_occupation}

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
        try:
            # 获取基础游戏会话信息
            game_session = self.db.get_game_session(session_id)
            if not game_session:
                return None
            
            # 获取案件数据
            case_data_str = self.db.get_game_state_value(session_id, 'case_data')
            case_data = {}
            if case_data_str:
                try:
                    case_data = json.loads(case_data_str)
                    print(f"📂 从数据库加载的案件数据: {json.dumps(case_data, ensure_ascii=False)[:300]}...")
                except json.JSONDecodeError:
                    print(f"案件数据解析失败: {case_data_str[:100]}...")
            
            # 处理AI生成的中文键名数据结构
            suspects = []
            key_evidence = []
            case_overview = ""
            victim_name = ""
            crime_scene_description = ""
            
            # 检查是否是AI生成的中文结构
            if '案件信息' in case_data:
                # AI生成的中文结构
                case_info = case_data.get('案件信息', {})
                suspects_info = case_data.get('嫌疑人信息', [])
                evidence_info = case_data.get('证据线索', [])
                
                case_overview = case_info.get('案件标题', '') + ' - ' + case_info.get('案件简介', '')
                victim_info = case_info.get('受害者信息', {})
                if isinstance(victim_info, dict):
                    victim_name = victim_info.get('公司名称', '') or victim_info.get('姓名', '')
                else:
                    victim_name = str(victim_info)
                crime_scene_description = case_info.get('案发地点', '') + '，' + case_info.get('案发时间', '')
                
                # 转换嫌疑人信息
                for suspect in suspects_info:
                    suspects.append({
                        'name': suspect.get('姓名', ''),
                        'occupation': suspect.get('职业', ''),
                        'motive': suspect.get('动机', ''),
                        'basic_info': f"{suspect.get('年龄', '')}岁，{suspect.get('职业', '')}，{suspect.get('与受害者关系', '')}"
                    })
                
                # 转换证据信息
                for evidence in evidence_info:
                    key_evidence.append({
                        'name': evidence.get('类型', '') + ' - ' + evidence.get('内容', '')[:20] + "...",
                        'description': evidence.get('内容', '')
                    })
            else:
                # 备用数据结构
                case_overview = case_data.get('title', '') + ' - ' + case_data.get('summary', '')
                victim_name = case_data.get('victim', {}).get('name', '') if isinstance(case_data.get('victim'), dict) else case_data.get('victim', '')
                crime_scene_description = case_data.get('scene', '')
                
                # 获取游戏角色中的嫌疑人数据
                characters = self.db.get_game_characters(session_id)
                for char in characters:
                    if char.get('character_type') == 'suspect':
                        suspects.append({
                            'name': char.get('character_name', ''),
                            'occupation': char.get('background', '').split(',')[0] if char.get('background') else '',
                            'motive': char.get('personality', ''),
                            'basic_info': char.get('background', '')
                        })
                
                key_evidence = [{'name': ev, 'description': ev} for ev in case_data.get('initial_evidence', [])]
            
            # 构建完整的游戏状态
            game_state = {
                'session_id': session_id,
                'phase': 'investigation',
                'case_type': game_session.get('game_type', 'detective'),
                'case_data': {
                    'case_overview': case_overview,
                    'victim': {
                        'name': victim_name
                    },
                    'crime_scene_description': crime_scene_description,
                    'suspects': suspects,
                    'key_evidence': key_evidence
                }
            }
            
            print(f"🔍 组装的游戏状态: {json.dumps(game_state, ensure_ascii=False)[:200]}...")
            return game_state
            
        except Exception as e:
            print(f"加载游戏状态失败: {e}")
            return None
    
    def get_game_messages(self, session_id: str, limit: int = 20) -> List[Dict]:
        """获取游戏消息"""
        return self.db.get_game_messages(session_id, phase=None, limit=limit)
    
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
            print(f"🔍 开始审讯嫌疑人: {suspect_name}, 问题: {question}")
            
            # 获取嫌疑人角色ID
            character_id = self.db.get_game_state_value(session_id, f'suspect_{suspect_name}_id')
            print(f"🔍 从数据库获取角色ID: {character_id}")
            
            # 如果找不到，尝试查找所有角色ID进行模糊匹配
            if not character_id:
                print(f"🔍 尝试模糊匹配嫌疑人: {suspect_name}")
                # 获取所有嫌疑人角色
                all_characters = self.character_manager.get_all_characters(session_id)
                print(f"🔍 所有角色数量: {len(all_characters)}")
                for character in all_characters:
                    print(f"🔍 检查角色: {character.name}, 类型: {character.character_type}")
                    if character.character_type == 'suspect' and suspect_name in character.name:
                        character_id = character.character_id
                        print(f"✅ 找到匹配的嫌疑人: {character.name} -> {character_id}")
                        break
                
                if not character_id:
                    available_suspects = [char.name for char in all_characters if char.character_type == 'suspect']
                    print(f"❌ 没有找到嫌疑人, 可用嫌疑人: {available_suspects}")
                    return {
                        'success': False,
                        'error': f'找不到嫌疑人：{suspect_name}。可用嫌疑人：{", ".join(available_suspects)}'
                    }
            
            # 获取嫌疑人信息
            print(f"🔍 获取角色信息: session_id={session_id}, character_id={character_id}")
            character = self.character_manager.get_character(session_id, character_id)
            print(f"🔍 获取到的角色: {character}")
            
            if not character:
                print(f"❌ 角色不存在: {character_id}")
                return {
                    'success': False,
                    'error': f'找不到嫌疑人：{suspect_name}'
                }
            
            print(f"✅ 角色信息: 姓名={character.name}, 背景={character.background[:50]}...")
            
            # 构造审讯提示词
            prompt = f"""
            你现在扮演嫌疑人{suspect_name}，背景：{character.background}
            性格：{character.personality}
            秘密信息：{character.secrets}
            
            侦探问你：{question}
            
            请根据角色设定回答，要：
            1. 保持角色一致性
            2. 可以隐瞒部分真相但不能完全撒谎
            3. 在压力下可能露出破绽
            4. 回答要自然，符合人物性格
            
            直接回答问题，不要说"作为XXX"。
            """
            
            # AI生成回答
            print(f"🤖 调用AI生成回答...")
            ai_response = self.ai_service.chat(
                messages=[{"role": "user", "content": prompt}]
            )
            print(f"🤖 AI响应: {ai_response}")
            
            if not ai_response.get('success', False):
                print(f"❌ AI调用失败: {ai_response.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': f'AI回应生成失败：{ai_response.get("error", "未知错误")}'
                }
            
            answer = ai_response.get('content', '对不起，我现在无法回答这个问题。')
            print(f"🤖 AI生成的回答: {answer[:100]}...")
            
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
            print(f"💥 审讯过程中发生异常: {e}")
            import traceback
            traceback.print_exc()
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
            
            # 查找指定证据 - 支持模糊匹配
            print(f"🔍 寻找证据: {evidence_name}")
            print(f"🔍 可用证据列表: {[e['name'] for e in evidence_list]}")
            
            target_evidence = None
            for evidence in evidence_list:
                # 精确匹配
                if evidence['name'] == evidence_name:
                    target_evidence = evidence
                    break
                # 模糊匹配：如果存储的名称是描述的前缀
                elif evidence_name.startswith(evidence['name'].replace('...', '')):
                    target_evidence = evidence
                    break
                # 反向模糊匹配：如果传入的名称包含存储的名称（去掉省略号）
                elif evidence['name'].replace('...', '') in evidence_name:
                    target_evidence = evidence
                    break
            
            if not target_evidence:
                available_names = [e['name'] for e in evidence_list]
                return {
                    'success': False,
                    'error': f'没有找到证据：{evidence_name}。可用证据：{", ".join(available_names)}'
                }
            
            print(f"✅ 找到匹配证据: {target_evidence['name']}")
            
            # 标记为已发现和已分析
            target_evidence['discovered'] = True
            target_evidence['analyzed'] = True
            
            print(f"🔬 开始生成证据分析...")
            
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
            
            print(f"🤖 准备调用AI分析证据...")
            analysis_result = self._safe_ai_call(analysis_prompt, fallback_analysis)
            print(f"🤖 AI分析完成: {analysis_result[:100]}...")
            
            # 保存更新的证据列表
            self.db.set_game_state(session_id, 'evidence_list', json.dumps(evidence_list))
            
            # 更新发现线索数
            discovered_count = sum(1 for e in evidence_list if e['discovered'])
            self.db.set_game_state(session_id, 'discovered_clues', str(discovered_count))
            
            # 记录分析
            self.db.add_game_message(session_id, 'user', '🕵️ 侦探', 'user', f"分析证据：{evidence_name}")
            self.db.add_game_message(session_id, 'system', '🔬 法医分析', 'system', analysis_result)
            
            result = {
                'success': True,
                'evidence_name': evidence_name,
                'analysis': analysis_result,
                'discovered_clues': discovered_count
            }
            
            print(f"✅ 证据分析成功完成，返回结果: {result}")
            return result
            
        except Exception as e:
            import traceback
            print(f"💥 证据分析异常: {str(e)}")
            print(f"💥 异常堆栈: {traceback.format_exc()}")
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