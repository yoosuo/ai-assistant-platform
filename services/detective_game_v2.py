#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI推理侦探游戏服务 - 按照开发文档实现
"""

import uuid
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.database import DatabaseManager
from services.ai_service import AIService

class DetectiveGameV2:
    """AI推理侦探游戏服务"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.ai_service = AIService()
        
        # 案件类型配置
        self.case_types = {
            "murder": {
                "name": "城市谋杀案",
                "description": "在繁华都市中发生的神秘谋杀案件",
                "complexity": "高"
            },
            "campus": {
                "name": "校园事件", 
                "description": "发生在大学校园内的离奇案件",
                "complexity": "中"
            },
            "castle": {
                "name": "古堡奇案",
                "description": "古老城堡中的神秘失踪案",
                "complexity": "高"
            }
        }
        
        # 游戏阶段
        self.game_phases = [
            "case_setup",      # 案件设定
            "scene_display",   # 场景展示
            "free_exploration", # 自由探索
            "conclusion",      # 推理结论
            "game_end"         # 游戏结束
        ]
    
    def create_new_game(self, user_id: int = 1) -> str:
        """创建新的侦探游戏"""
        session_id = str(uuid.uuid4())
        
        # 初始化游戏状态
        initial_state = {
            "session_id": session_id,
            "user_id": user_id,
            "game_type": "detective",
            "phase": "case_setup",
            "case_type": None,
            "case_data": {},
            "discovered_clues": [],
            "questioned_suspects": [],
            "analyzed_evidence": [],
            "notebook": [],
            "score": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到数据库
        try:
            self.db.create_game_session(session_id, "detective", user_id, initial_state)
            return session_id
        except Exception as e:
            print(f"创建侦探游戏失败: {e}")
            return None
    
    def start_case(self, session_id: str, case_type: str) -> Dict[str, Any]:
        """开始案件 - 生成完整案件设定"""
        try:
            # 生成案件背景
            case_prompt = self._build_case_generation_prompt(case_type)
            
            # 调用AI生成案件
            ai_result = self.ai_service.chat([{
                "role": "system", 
                "content": case_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "案件生成失败"}
            
            # 解析案件数据
            case_data = self._parse_case_data(ai_result['content'])
            
            # 更新游戏状态
            game_state = self.load_game_state(session_id)
            game_state.update({
                "phase": "scene_display",
                "case_type": case_type,
                "case_data": case_data,
                "current_scene": "crime_scene"
            })
            
            self._save_game_state(session_id, game_state)
            
            # 记录游戏消息
            self._add_game_message(session_id, "system", 
                f"📋 **案件概况**\n\n{case_data.get('case_overview', '')}")
            
            self._add_game_message(session_id, "system",
                f"👥 **嫌疑人名单**\n\n" + 
                "\n".join([f"• **{s['name']}** - {s['role']} - {s['basic_info']}" 
                          for s in case_data.get('suspects', [])]))
            
            self._add_game_message(session_id, "system",
                f"🏠 **案发现场**\n\n{case_data.get('crime_scene_description', '')}")
            
            return {
                "success": True,
                "message": "案件已生成，开始您的推理之旅！",
                "case_data": case_data,
                "available_actions": ["investigate", "interrogate", "analyze", "notebook"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"开始案件失败: {str(e)}"}
    
    def investigate_scene(self, session_id: str, investigation_target: str) -> Dict[str, Any]:
        """调查场景 - 自由探索阶段"""
        try:
            game_state = self.load_game_state(session_id)
            case_data = game_state.get('case_data', {})
            
            # 构建调查提示词
            investigation_prompt = self._build_investigation_prompt(case_data, investigation_target)
            
            # AI生成调查结果
            ai_result = self.ai_service.chat([{
                "role": "system",
                "content": investigation_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "调查失败"}
            
            # 解析调查结果
            investigation_result = ai_result['content']
            
            # 检查是否发现新线索
            new_clue = self._extract_clue_from_result(investigation_result)
            if new_clue:
                game_state['discovered_clues'].append({
                    "clue": new_clue,
                    "source": f"调查: {investigation_target}",
                    "timestamp": datetime.now().isoformat()
                })
                self._save_game_state(session_id, game_state)
            
            # 记录调查消息
            self._add_game_message(session_id, "user", f"🔍 调查: {investigation_target}")
            self._add_game_message(session_id, "assistant", investigation_result)
            
            return {
                "success": True,
                "investigation_result": investigation_result,
                "new_clue_found": bool(new_clue),
                "clue": new_clue if new_clue else None
            }
            
        except Exception as e:
            return {"success": False, "error": f"调查失败: {str(e)}"}
    
    def interrogate_suspect(self, session_id: str, suspect_name: str, question: str) -> Dict[str, Any]:
        """审讯嫌疑人"""
        try:
            game_state = self.load_game_state(session_id)
            case_data = game_state.get('case_data', {})
            
            # 查找嫌疑人信息
            suspect = None
            for s in case_data.get('suspects', []):
                if s['name'] == suspect_name:
                    suspect = s
                    break
            
            if not suspect:
                return {"success": False, "error": "找不到该嫌疑人"}
            
            # 构建审讯提示词
            interrogation_prompt = self._build_interrogation_prompt(case_data, suspect, question)
            
            # AI生成回应
            ai_result = self.ai_service.chat([{
                "role": "system",
                "content": interrogation_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "审讯失败"}
            
            response = ai_result['content']
            
            # 记录审讯历史
            interrogation_record = {
                "suspect": suspect_name,
                "question": question,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            
            game_state['questioned_suspects'].append(interrogation_record)
            self._save_game_state(session_id, game_state)
            
            # 记录消息
            self._add_game_message(session_id, "user", f"💬 质问 {suspect_name}: {question}")
            self._add_game_message(session_id, "suspect", f"**{suspect_name}**: {response}")
            
            return {
                "success": True,
                "suspect_response": response,
                "suspect_info": suspect
            }
            
        except Exception as e:
            return {"success": False, "error": f"审讯失败: {str(e)}"}
    
    def analyze_evidence(self, session_id: str, evidence_name: str) -> Dict[str, Any]:
        """分析证据"""
        try:
            game_state = self.load_game_state(session_id)
            case_data = game_state.get('case_data', {})
            
            # 构建证据分析提示词
            analysis_prompt = self._build_evidence_analysis_prompt(case_data, evidence_name)
            
            # AI分析
            ai_result = self.ai_service.chat([{
                "role": "system",
                "content": analysis_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "分析失败"}
            
            analysis_result = ai_result['content']
            
            # 记录分析历史
            analysis_record = {
                "evidence": evidence_name,
                "analysis": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            
            game_state['analyzed_evidence'].append(analysis_record)
            self._save_game_state(session_id, game_state)
            
            # 记录消息
            self._add_game_message(session_id, "user", f"🔬 分析证据: {evidence_name}")
            self._add_game_message(session_id, "assistant", analysis_result)
            
            return {
                "success": True,
                "analysis_result": analysis_result
            }
            
        except Exception as e:
            return {"success": False, "error": f"分析失败: {str(e)}"}
    
    def submit_conclusion(self, session_id: str, suspect: str, reasoning: str) -> Dict[str, Any]:
        """提交推理结论"""
        try:
            game_state = self.load_game_state(session_id)
            case_data = game_state.get('case_data', {})
            
            # 构建评估提示词
            evaluation_prompt = self._build_evaluation_prompt(case_data, suspect, reasoning)
            
            # AI评估
            ai_result = self.ai_service.chat([{
                "role": "system",
                "content": evaluation_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "评估失败"}
            
            evaluation = self._parse_evaluation_result(ai_result['content'])
            
            # 更新游戏状态
            game_state.update({
                "phase": "game_end",
                "final_conclusion": {
                    "suspect": suspect,
                    "reasoning": reasoning,
                    "evaluation": evaluation,
                    "submitted_at": datetime.now().isoformat()
                },
                "score": evaluation.get('score', 0)
            })
            
            self._save_game_state(session_id, game_state)
            
            # 记录结论消息
            self._add_game_message(session_id, "user", f"📝 **推理结论**\n\n凶手: {suspect}\n\n推理过程: {reasoning}")
            self._add_game_message(session_id, "system", f"🎯 **案件评估**\n\n{evaluation.get('feedback', '')}")
            
            return {
                "success": True,
                "evaluation": evaluation,
                "case_solved": evaluation.get('correct', False),
                "score": evaluation.get('score', 0),
                "grade": evaluation.get('grade', 'C')
            }
            
        except Exception as e:
            return {"success": False, "error": f"提交结论失败: {str(e)}"}
    
    def get_notebook(self, session_id: str) -> Dict[str, Any]:
        """获取推理笔记"""
        try:
            game_state = self.load_game_state(session_id)
            
            notebook = {
                "discovered_clues": game_state.get('discovered_clues', []),
                "questioned_suspects": game_state.get('questioned_suspects', []),
                "analyzed_evidence": game_state.get('analyzed_evidence', []),
                "progress_summary": self._generate_progress_summary(game_state)
            }
            
            return {"success": True, "notebook": notebook}
            
        except Exception as e:
            return {"success": False, "error": f"获取笔记失败: {str(e)}"}
    
    def get_hint(self, session_id: str) -> Dict[str, Any]:
        """获取提示 - 不直接给出答案"""
        try:
            game_state = self.load_game_state(session_id)
            case_data = game_state.get('case_data', {})
            
            # 构建提示生成提示词
            hint_prompt = self._build_hint_prompt(case_data, game_state)
            
            ai_result = self.ai_service.chat([{
                "role": "system",
                "content": hint_prompt
            }])
            
            if not ai_result['success']:
                return {"success": False, "error": "获取提示失败"}
            
            hint = ai_result['content']
            
            # 记录提示消息
            self._add_game_message(session_id, "user", "💡 请求提示")
            self._add_game_message(session_id, "assistant", f"💡 **提示**: {hint}")
            
            return {"success": True, "hint": hint}
            
        except Exception as e:
            return {"success": False, "error": f"获取提示失败: {str(e)}"}
    
    # ===== 辅助方法 =====
    
    def _build_case_generation_prompt(self, case_type: str) -> str:
        """构建案件生成提示词"""
        case_info = self.case_types.get(case_type, self.case_types["murder"])
        
        return f"""你是一个专业的推理小说作家，需要创建一个{case_info['name']}的完整案件。

要求：
1. 创建一个逻辑完整的{case_info['description']}
2. 设计5个嫌疑人，每人都有动机、机会和不在场证明
3. 其中只有1个是真凶，其他人有合理的误导性线索
4. 提供详细的案发现场描述
5. 设计关键证据和线索

请按以下JSON格式回复：
{{
    "case_overview": "案件概述",
    "victim": {{
        "name": "受害者姓名",
        "background": "背景信息",
        "death_time": "死亡时间",
        "death_method": "死亡方式"
    }},
    "crime_scene_description": "详细的案发现场描述",
    "suspects": [
        {{
            "name": "嫌疑人姓名",
            "role": "身份/职业", 
            "basic_info": "基本信息",
            "motive": "作案动机",
            "alibi": "不在场证明",
            "personality": "性格特点",
            "is_culprit": false
        }}
    ],
    "key_evidence": [
        {{
            "name": "证据名称",
            "description": "证据描述",
            "location": "发现位置",
            "significance": "重要性"
        }}
    ],
    "truth": {{
        "real_culprit": "真凶姓名",
        "real_motive": "真实动机", 
        "method": "作案手法",
        "timeline": "作案时间线"
    }}
}}"""
    
    def _build_investigation_prompt(self, case_data: Dict, target: str) -> str:
        """构建调查提示词"""
        return f"""你是案件现场的调查专家。

案件背景：
{case_data.get('case_overview', '')}

现场描述：
{case_data.get('crime_scene_description', '')}

玩家要调查：{target}

请模拟调查结果，要求：
1. 描述调查发现的具体细节
2. 如果发现重要线索，在回复最后用"[线索发现：具体线索内容]"格式标注
3. 保持神秘感，不要直接透露真相
4. 描述要生动具体，增强沉浸感

调查结果："""
    
    def _build_interrogation_prompt(self, case_data: Dict, suspect: Dict, question: str) -> str:
        """构建审讯提示词"""
        return f"""你正在扮演嫌疑人：{suspect['name']}

角色信息：
- 身份：{suspect['role']}
- 性格：{suspect['personality']}
- 动机：{suspect['motive']}
- 不在场证明：{suspect['alibi']}

案件背景：{case_data.get('case_overview', '')}

现在侦探质问你：{question}

要求：
1. 以第一人称回答，符合角色性格
2. 如果是真凶，要巧妙撒谎或转移话题
3. 如果不是真凶，可以提供一些有用信息，但也可能有误导性
4. 保持角色一致性，记住之前的对话
5. 适当表现紧张、愤怒或其他情绪

回答："""
    
    def _build_evidence_analysis_prompt(self, case_data: Dict, evidence: str) -> str:
        """构建证据分析提示词"""
        return f"""你是专业的法医和证据分析专家。

案件背景：{case_data.get('case_overview', '')}

需要分析的证据：{evidence}

案件中的关键证据：
{json.dumps(case_data.get('key_evidence', []), indent=2, ensure_ascii=False)}

请提供专业的分析结果：
1. 证据的基本信息
2. 可能的来源和形成过程
3. 与案件的关联性分析
4. 可能指向的嫌疑人或线索方向
5. 需要进一步调查的方向

分析报告："""
    
    def _build_evaluation_prompt(self, case_data: Dict, suspect: str, reasoning: str) -> str:
        """构建评估提示词"""
        truth = case_data.get('truth', {})
        real_culprit = truth.get('real_culprit', '')
        
        return f"""你是推理案件的评判专家，需要评估玩家的推理结论。

真实答案：
- 真凶：{real_culprit}
- 真实动机：{truth.get('real_motive', '')}
- 作案手法：{truth.get('method', '')}

玩家的结论：
- 嫌疑人：{suspect}
- 推理过程：{reasoning}

请评估并以JSON格式回复：
{{
    "correct": true/false,
    "score": 0-100,
    "grade": "S/A/B/C",
    "feedback": "详细的评价和正确答案解释",
    "logic_score": 0-30,
    "evidence_score": 0-30,
    "reasoning_score": 0-40
}}"""
    
    def _build_hint_prompt(self, case_data: Dict, game_state: Dict) -> str:
        """构建提示生成提示词"""
        discovered_clues = game_state.get('discovered_clues', [])
        questioned_suspects = game_state.get('questioned_suspects', [])
        
        return f"""你是推理游戏的助手，需要给玩家一个不直接透露答案的提示。

玩家当前进度：
- 已发现线索：{len(discovered_clues)}个
- 已质问嫌疑人：{len(questioned_suspects)}次

请给出一个指导性提示：
1. 不要直接说出真凶名字
2. 可以提示调查方向或关注点
3. 可以提示某些线索的重要性
4. 鼓励玩家继续探索

提示内容："""
    
    def _parse_case_data(self, ai_response: str) -> Dict:
        """解析AI生成的案件数据"""
        try:
            # 尝试解析JSON
            case_data = json.loads(ai_response)
            return case_data
        except:
            # 如果解析失败，返回默认案件
            return self._get_default_case()
    
    def _parse_evaluation_result(self, ai_response: str) -> Dict:
        """解析评估结果"""
        try:
            return json.loads(ai_response)
        except:
            return {
                "correct": False,
                "score": 50,
                "grade": "C",
                "feedback": "评估解析失败，但您的推理过程值得肯定！",
                "logic_score": 15,
                "evidence_score": 15,
                "reasoning_score": 20
            }
    
    def _extract_clue_from_result(self, investigation_result: str) -> Optional[str]:
        """从调查结果中提取线索"""
        import re
        match = re.search(r'\[线索发现：([^\]]+)\]', investigation_result)
        return match.group(1) if match else None
    
    def _generate_progress_summary(self, game_state: Dict) -> str:
        """生成进度总结"""
        clues_count = len(game_state.get('discovered_clues', []))
        suspects_count = len(game_state.get('questioned_suspects', []))
        evidence_count = len(game_state.get('analyzed_evidence', []))
        
        return f"已发现线索: {clues_count}个 | 已质问嫌疑人: {suspects_count}次 | 已分析证据: {evidence_count}个"
    
    def _get_default_case(self) -> Dict:
        """获取默认案件数据"""
        return {
            "case_overview": "图书馆深夜发生神秘谋杀案，馆长被发现死在办公室中。",
            "victim": {
                "name": "张馆长",
                "background": "图书馆馆长，工作认真负责",
                "death_time": "晚上10点左右",
                "death_method": "头部重击"
            },
            "crime_scene_description": "馆长办公室内一片狼藉，桌上散落着文件，地上有打斗痕迹。",
            "suspects": [
                {
                    "name": "李助理",
                    "role": "图书馆助理",
                    "basic_info": "工作勤奋的年轻人",
                    "motive": "升职竞争",
                    "alibi": "声称在家看电视",
                    "personality": "内向谨慎",
                    "is_culprit": True
                }
            ],
            "key_evidence": [
                {
                    "name": "血迹书档",
                    "description": "沾有血迹的厚重书档",
                    "location": "办公桌旁",
                    "significance": "疑似凶器"
                }
            ],
            "truth": {
                "real_culprit": "李助理",
                "real_motive": "因升职被拒而怀恨在心",
                "method": "用书档击打头部",
                "timeline": "晚上9:30趁无人时进入办公室"
            }
        }
    
    def load_game_state(self, session_id: str) -> Dict:
        """加载游戏状态"""
        try:
            game_session = self.db.get_game_session(session_id)
            if game_session and game_session.get('game_state'):
                return json.loads(game_session['game_state'])
            return {}
        except Exception as e:
            print(f"加载游戏状态失败: {e}")
            return {}
    
    def _save_game_state(self, session_id: str, game_state: Dict):
        """保存游戏状态"""
        try:
            game_state_json = json.dumps(game_state, ensure_ascii=False)
            self.db.update_game_state(session_id, game_state_json)
        except Exception as e:
            print(f"保存游戏状态失败: {e}")
    
    def get_game_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取游戏消息"""
        try:
            return self.db.get_game_messages(session_id, limit)
        except Exception as e:
            print(f"获取游戏消息失败: {e}")
            return []
    
    def _add_game_message(self, session_id: str, role: str, content: str):
        """添加游戏消息"""
        try:
            self.db.add_game_message(session_id, role, content)
        except Exception as e:
            print(f"添加游戏消息失败: {e}")