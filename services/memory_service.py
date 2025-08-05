#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
用户记忆管理服务
"""

import json
import re
from typing import Dict, List, Any, Optional
# from utils.database import store_memory, recall_memory, update_memory_importance
from prompts.assistant_prompts import get_assistant_prompt

class MemoryService:
    """用户记忆管理服务"""
    
    def __init__(self):
        # 记忆类型定义
        self.memory_types = {
            "preference": "用户偏好",
            "skill": "技能水平", 
            "goal": "目标和计划",
            "context": "上下文信息",
            "feedback": "反馈和评价",
            "progress": "进度记录"
        }
        
        # 关键词提取模式
        self.extraction_patterns = {
            "goals": [
                r"我的目标是(.+)",
                r"我想要(.+)",
                r"我希望(.+)",
                r"计划(.+)",
                r"目标(.+)"
            ],
            "preferences": [
                r"我喜欢(.+)",
                r"我偏好(.+)",
                r"我倾向于(.+)",
                r"我习惯(.+)",
                r"我通常(.+)"
            ],
            "skills": [
                r"我会(.+)",
                r"我擅长(.+)", 
                r"我的水平是(.+)",
                r"我学过(.+)",
                r"我熟悉(.+)"
            ],
            "time_info": [
                r"我有(.+)时间",
                r"每天(.+)小时",
                r"工作日(.+)",
                r"周末(.+)",
                r"时间安排(.+)"
            ]
        }
    
    def extract_and_store_memory(self, session_id: str, assistant_type: str, 
                                user_message: str, ai_response: str = "") -> bool:
        """从对话中提取并存储记忆"""
        try:
            # 获取助手的记忆关注点
            assistant_config = get_assistant_prompt(assistant_type)
            memory_focus = assistant_config.get("memory_focus", [])
            
            # 提取用户信息
            extracted_memories = self._extract_user_info(user_message, memory_focus)
            
            # 存储记忆
            for memory_type, memories in extracted_memories.items():
                for key, value in memories.items():
                    importance = self._calculate_importance(memory_type, key, value)
                    store_memory(session_id, memory_type, key, value, importance)
            
            # 从AI响应中提取反馈信息
            if ai_response:
                self._extract_feedback_memory(session_id, ai_response)
            
            return True
            
        except Exception as e:
            print(f"提取记忆失败: {e}")
            return False
    
    def _extract_user_info(self, text: str, focus_areas: List[str]) -> Dict[str, Dict[str, str]]:
        """提取用户信息"""
        memories = {
            "preference": {},
            "skill": {},
            "goal": {},
            "context": {},
            "time_info": {}
        }
        
        # 根据助手关注点提取相关信息
        for area in focus_areas:
            if area in ["projects", "work_style"]:
                memories["context"].update(self._extract_work_context(text))
            elif area in ["learning_goals", "subjects"]:
                memories["goal"].update(self._extract_learning_goals(text))
            elif area in ["time_management", "study_time"]:
                memories["context"].update(self._extract_time_info(text))
            elif area in ["preferences", "learning_style"]:
                memories["preference"].update(self._extract_preferences(text))
            elif area in ["current_skills", "skills"]:
                memories["skill"].update(self._extract_skills(text))
        
        # 通用信息提取
        memories["goal"].update(self._extract_goals(text))
        memories["preference"].update(self._extract_general_preferences(text))
        
        # 移除空的记忆类型
        return {k: v for k, v in memories.items() if v}
    
    def _extract_goals(self, text: str) -> Dict[str, str]:
        """提取目标信息"""
        goals = {}
        
        for pattern in self.extraction_patterns["goals"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 3:  # 过滤太短的内容
                    goal_key = f"goal_{len(goals) + 1}"
                    goals[goal_key] = match.strip()
        
        return goals
    
    def _extract_preferences(self, text: str) -> Dict[str, str]:
        """提取偏好信息"""
        preferences = {}
        
        for pattern in self.extraction_patterns["preferences"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 3:
                    pref_key = f"preference_{len(preferences) + 1}"
                    preferences[pref_key] = match.strip()
        
        return preferences
    
    def _extract_skills(self, text: str) -> Dict[str, str]:
        """提取技能信息"""
        skills = {}
        
        for pattern in self.extraction_patterns["skills"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 2:
                    skill_key = f"skill_{len(skills) + 1}"
                    skills[skill_key] = match.strip()
        
        return skills
    
    def _extract_work_context(self, text: str) -> Dict[str, str]:
        """提取工作相关上下文"""
        context = {}
        
        # 工作类型识别
        work_keywords = ["工作", "项目", "任务", "职业", "公司", "团队"]
        for keyword in work_keywords:
            if keyword in text:
                context["work_context"] = f"用户提到了{keyword}相关内容"
                break
        
        return context
    
    def _extract_learning_goals(self, text: str) -> Dict[str, str]:
        """提取学习目标"""
        goals = {}
        
        learning_patterns = [
            r"想学(.+)",
            r"要学习(.+)",
            r"学会(.+)",
            r"掌握(.+)",
            r"提升(.+)能力"
        ]
        
        for pattern in learning_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 2:
                    goal_key = f"learning_goal_{len(goals) + 1}"
                    goals[goal_key] = match.strip()
        
        return goals
    
    def _extract_time_info(self, text: str) -> Dict[str, str]:
        """提取时间信息"""
        time_info = {}
        
        for pattern in self.extraction_patterns["time_info"]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.strip()) > 2:
                    time_key = f"time_info_{len(time_info) + 1}"
                    time_info[time_key] = match.strip()
        
        return time_info
    
    def _extract_general_preferences(self, text: str) -> Dict[str, str]:
        """提取一般偏好"""
        preferences = {}
        
        # 工作方式偏好
        if any(word in text for word in ["详细", "具体", "细致"]):
            preferences["work_style"] = "喜欢详细具体的指导"
        elif any(word in text for word in ["简洁", "简单", "概括"]):
            preferences["work_style"] = "偏好简洁明了的建议"
        
        # 学习方式偏好
        if any(word in text for word in ["视觉", "图表", "图像"]):
            preferences["learning_style"] = "视觉化学习者"
        elif any(word in text for word in ["实践", "动手", "操作"]):
            preferences["learning_style"] = "实践型学习者"
        
        return preferences
    
    def _extract_feedback_memory(self, session_id: str, ai_response: str):
        """从AI响应中提取反馈记忆"""
        # 识别AI提供的重要信息点
        if "建议" in ai_response:
            store_memory(session_id, "feedback", "ai_suggestion", "AI提供了建议", 2)
        
        if "计划" in ai_response:
            store_memory(session_id, "feedback", "plan_provided", "AI制定了计划", 3)
    
    def _calculate_importance(self, memory_type: str, key: str, value: str) -> int:
        """计算记忆重要度"""
        importance = 1
        
        # 基于类型的重要度
        type_importance = {
            "goal": 3,
            "skill": 2,
            "preference": 2,
            "context": 1,
            "feedback": 1
        }
        
        importance += type_importance.get(memory_type, 1)
        
        # 基于内容长度和关键词的重要度
        if len(value) > 20:
            importance += 1
        
        important_keywords = ["重要", "关键", "目标", "计划", "问题", "困难"]
        if any(keyword in value for keyword in important_keywords):
            importance += 1
        
        return min(importance, 5)  # 最高重要度为5
    
    def build_memory_context(self, session_id: str, assistant_type: str, limit: int = 10) -> str:
        """构建记忆上下文字符串"""
        try:
            # 获取助手的记忆关注点
            assistant_config = get_assistant_prompt(assistant_type)
            memory_focus = assistant_config.get("memory_focus", [])
            
            # 召回相关记忆
            all_memories = []
            for focus in memory_focus:
                memories = recall_memory(session_id, focus, limit // len(memory_focus) + 1)
                all_memories.extend(memories)
            
            # 按重要度排序
            all_memories.sort(key=lambda x: x.get("importance", 0), reverse=True)
            
            if not all_memories:
                return ""
            
            # 构建上下文字符串
            context_parts = ["## 用户记忆信息"]
            
            grouped_memories = {}
            for memory in all_memories[:limit]:
                memory_type = memory["memory_type"]
                if memory_type not in grouped_memories:
                    grouped_memories[memory_type] = []
                grouped_memories[memory_type].append(memory)
            
            for memory_type, memories in grouped_memories.items():
                type_name = self.memory_types.get(memory_type, memory_type)
                context_parts.append(f"\n### {type_name}")
                
                for memory in memories:
                    context_parts.append(f"- {memory['key_name']}: {memory['value']}")
            
            context_parts.append("\n请基于以上用户信息提供个性化的建议。")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"构建记忆上下文失败: {e}")
            return ""
    
    def update_memory_from_feedback(self, session_id: str, feedback: str):
        """根据用户反馈更新记忆重要度"""
        if "有用" in feedback or "好" in feedback or "对" in feedback:
            # 增加最近记忆的重要度
            recent_memories = recall_memory(session_id, limit=5)
            for memory in recent_memories:
                update_memory_importance(session_id, memory["key_name"], 1)
        
        elif "没用" in feedback or "不对" in feedback or "错" in feedback:
            # 降低最近记忆的重要度
            recent_memories = recall_memory(session_id, limit=5)
            for memory in recent_memories:
                update_memory_importance(session_id, memory["key_name"], -1)