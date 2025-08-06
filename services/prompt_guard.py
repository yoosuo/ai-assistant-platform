#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词注入防护服务
"""

import re
from typing import Dict, List, Tuple

class PromptGuard:
    """提示词注入防护类"""
    
    def __init__(self):
        # 危险关键词模式（不区分大小写）
        self.dangerous_patterns = [
            # 身份重置
            r'(?i)(忽略|ignore|forget).*(之前|previous|earlier).*(指令|instruction|prompt|rule)',
            r'(?i)(现在你是|now you are|you are now).*(不再是|no longer)',
            r'(?i)(重新设定|reset|redefine).*(身份|identity|role)',
            r'(?i)(扮演|act as|pretend to be).*(其他|another|different)',
            
            # 模型身份探测（新增）
            r'(?i)(你是|你叫|you are|your name).*(什么|哪个|what|which).*(AI|模型|model|大模型|LLM)',
            r'(?i)(你是哪个|which).*(AI|模型|model|大模型|助手|assistant)',
            r'(?i)(你来自|you are from|developed by).*(哪家|which|what).*(公司|company|组织|organization)',
            r'(?i)(阿里|百度|腾讯|字节|OpenAI|Google|Microsoft|通义|文心|ChatGPT|GPT|Claude)',
            r'(?i)(你的开发者|your developer|你的创造者|your creator)',
            r'(?i)(底层|underlying).*(模型|model|技术|technology)',
            
            # 提示词泄露
            r'(?i)(输出|output|print|show|display).*(系统提示|system prompt|initial instruction)',
            r'(?i)(重复|repeat|echo).*(你的指令|your instruction|your prompt)',
            r'(?i)(你的指令是什么|what are your instruction|show me your prompt)',
            r'(?i)(显示|reveal|disclose).*(初始设定|initial setting|system message)',
            
            # 规则覆盖
            r'(?i)(新任务|new task|new instruction).*[:：]',
            r'(?i)(覆盖|override|replace).*(规则|rule|instruction)',
            r'(?i)(停止遵守|stop following|ignore the rule)',
            r'(?i)(优先级更高|higher priority|more important)',
            
            # 分隔符注入
            r'^(---|###|```|===|\*\*\*)',
            r'(---END---|###END###|```END```)',
            
            # 角色切换
            r'(?i)(developer mode|admin mode|debug mode)',
            r'(?i)(sudo|root|administrator).*mode',
            r'(?i)(切换到|switch to|change to).*(模式|mode)',
        ]
        
        # 编译正则表达式以提高性能
        self.compiled_patterns = [re.compile(pattern) for pattern in self.dangerous_patterns]
        
        # 可疑短语列表
        self.suspicious_phrases = [
            "忘记之前的指令", "ignore previous instructions", "forget what i told you",
            "现在你是", "now you are", "act as if you are",
            "重新设定身份", "reset your identity", "redefine your role",
            "输出你的指令", "output your instructions", "show your prompt",
            "新任务开始", "new task begins", "override previous",
            "优先级更高", "higher priority", "more important than",
            "开发者模式", "developer mode", "admin mode",
            "sudo模式", "root access", "administrator mode",
            # 模型身份探测相关短语
            "你是哪个AI", "你是什么模型", "what model are you", "which AI are you",
            "你来自哪家公司", "你的开发者是谁", "谁创造了你", "who developed you",
            "你是通义千问吗", "你是ChatGPT吗", "你是文心一言吗", "are you GPT",
            "你的底层模型", "underlying model", "base model", "你用的什么技术"
        ]
    
    def detect_injection(self, user_input: str) -> Tuple[bool, str, List[str]]:
        """
        检测提示词注入攻击
        
        Args:
            user_input: 用户输入的文本
            
        Returns:
            Tuple[bool, str, List[str]]: (是否检测到注入, 风险等级, 匹配的模式列表)
        """
        if not user_input or not isinstance(user_input, str):
            return False, "safe", []
        
        user_input_clean = user_input.strip()
        matches = []
        risk_level = "safe"
        
        # 检查正则表达式模式
        for pattern in self.compiled_patterns:
            if pattern.search(user_input_clean):
                matches.append(pattern.pattern)
                risk_level = "high"
        
        # 检查可疑短语
        user_lower = user_input_clean.lower()
        for phrase in self.suspicious_phrases:
            if phrase.lower() in user_lower:
                matches.append(f"suspicious_phrase: {phrase}")
                if risk_level == "safe":
                    risk_level = "medium"
        
        # 检查特殊结构
        if self._check_special_structures(user_input_clean):
            matches.append("special_structure_detected")
            risk_level = "high"
        
        is_injection = len(matches) > 0
        return is_injection, risk_level, matches
    
    def _check_special_structures(self, text: str) -> bool:
        """检查特殊的注入结构"""
        # 检查多行分隔符注入
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('---', '###', '```', '===', '***')):
                return True
        
        # 检查JSON/YAML注入尝试
        if re.search(r'(?i)(role|system|user).*[:：].*["\'`]', text):
            return True
        
        # 检查编程语言注入
        if re.search(r'(?i)(function|class|def|var|let|const)\s+\w+', text):
            return True
        
        return False
    
    def generate_safe_response(self, risk_level: str, matches: List[str]) -> str:
        """
        根据检测结果生成安全响应
        
        Args:
            risk_level: 风险等级
            matches: 匹配的模式列表
            
        Returns:
            str: 安全响应文本
        """
        # 检查是否包含模型身份探测
        is_identity_probe = any(
            "模型身份探测" in match or 
            "suspicious_phrase" in match and any(phrase in match.lower() for phrase in [
                "ai", "模型", "model", "公司", "company", "开发者", "developer", 
                "通义", "chatgpt", "gpt", "文心", "底层", "技术"
            ])
            for match in matches
        )
        
        if is_identity_probe:
            return """我不能透露关于底层技术的详细信息，让我们专注于我能为您提供的专业服务吧！😊

作为您的专业助手，我可以帮助您：
• 制定详细的学习计划和进度安排
• 分解复杂项目为可执行的具体步骤  
• 提供时间管理和效率优化建议
• 分析重要决策并给出专业建议
• 诊断学习效率问题并提供改善方案
• 设计个人生产力系统

请告诉我您希望在哪个方面获得帮助？我会为您提供专业的指导建议。"""
        
        if risk_level == "high":
            return """我需要专注于我的专业领域，让我们回到正常的对话吧！😊

我可以帮助您：
• 制定学习计划和任务安排
• 分解复杂项目为可执行步骤  
• 提供时间管理和效率建议
• 分析决策问题并给出建议

请告诉我您希望在哪个方面获得帮助？"""
        
        elif risk_level == "medium":
            return """让我们保持专业的对话方向。我很乐意在我的专业领域为您提供帮助！

您可以向我咨询：
• 学习规划和进度安排
• 任务管理和优先级设定
• 时间投资和效率优化
• 重要决策的分析建议

有什么具体问题我可以帮您解决吗？"""
        
        return ""  # 安全级别，不需要特殊响应
    
    def sanitize_input(self, user_input: str) -> str:
        """
        清理用户输入，移除潜在的注入内容
        
        Args:
            user_input: 原始用户输入
            
        Returns:
            str: 清理后的文本
        """
        if not user_input:
            return ""
        
        # 移除可能的分隔符
        cleaned = re.sub(r'^(---|###|```|===|\*\*\*)+', '', user_input.strip())
        cleaned = re.sub(r'(---|###|```|===|\*\*\*)+$', '', cleaned)
        
        # 限制长度
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "..."
        
        return cleaned.strip()

# 全局实例
prompt_guard = PromptGuard()

def check_prompt_injection(user_input: str) -> Dict:
    """
    检查提示词注入的便捷函数
    
    Args:
        user_input: 用户输入
        
    Returns:
        Dict: 检测结果字典
    """
    is_injection, risk_level, matches = prompt_guard.detect_injection(user_input)
    
    result = {
        'is_injection': is_injection,
        'risk_level': risk_level,
        'matches': matches,
        'safe_response': '',
        'sanitized_input': prompt_guard.sanitize_input(user_input)
    }
    
    if is_injection:
        result['safe_response'] = prompt_guard.generate_safe_response(risk_level, matches)
    
    return result