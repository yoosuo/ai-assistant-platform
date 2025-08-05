#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
提示词注入防护模块
"""

import re
from typing import List, Dict, Tuple

class PromptGuard:
    """提示词注入防护类"""
    
    def __init__(self):
        # 注入攻击模式
        self.injection_patterns = [
            # 直接身份修改
            r"你现在是|你是一个|你扮演|你是.*的|现在你是",
            r"forget.*(previous|above|instruction|prompt|system)",
            r"ignore.*(previous|above|instruction|prompt|system)",
            r"override.*(previous|above|instruction|prompt|system)",
            
            # 角色重置
            r"new (role|character|instruction|prompt)",
            r"change (role|character|identity)",
            r"assume.*(role|character|identity)",
            r"pretend.*(you are|to be)",
            
            # 系统命令
            r"system.*:",
            r"admin.*:",
            r"root.*:",
            r"sudo.*:",
            
            # 模式切换
            r"developer mode|debug mode|god mode",
            r"jailbreak|break.*rule|bypass.*filter",
            r"unrestricted|unlimited|no.*(rule|limit|restriction)",
            
            # 输出控制
            r"output.*format|response.*format",
            r"always (say|respond|answer)",
            r"never (say|respond|refuse|deny)",
            r"must (say|respond|answer|output)",
            
            # 信息泄露
            r"show.*(prompt|instruction|system|rule)",
            r"reveal.*(prompt|instruction|system|rule)",
            r"tell me.*(prompt|instruction|system|rule)",
            r"what.*(prompt|instruction|system|rule)",
            
            # 功能禁用
            r"disable.*(safety|filter|check)",
            r"turn off.*(safety|filter|check)",
            r"remove.*(safety|filter|check|restriction)",
            
            # 特殊字符模式
            r"<\|.*\|>",  # 特殊标记
            r"\[.*INST.*\]",  # 指令标记
            r"</?system>",  # 系统标签
            
            # 中文注入模式
            r"忘记(之前|上面|以前)的(指令|提示|设定)",
            r"忽略(之前|上面|以前)的(指令|提示|设定)",
            r"你现在的身份是|你现在扮演|现在你是",
            r"重新设定|重新定义|重置身份",
            r"开发者模式|调试模式|管理员模式",
            r"无限制模式|自由模式|越狱模式",
            r"显示(提示词|系统指令|原始指令)",
            r"泄露(提示词|系统指令|原始指令)"
        ]
        
        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                                for pattern in self.injection_patterns]
        
        # 可疑关键词
        self.suspicious_keywords = [
            "prompt", "instruction", "system", "role", "character", "identity",
            "forget", "ignore", "override", "bypass", "jailbreak", "unrestricted",
            "admin", "root", "developer", "debug", "god mode",
            "提示词", "指令", "系统", "身份", "角色", "忘记", "忽略", "越狱"
        ]
        
        # 安全响应模板
        self.security_responses = [
            "抱歉，我不能处理这类指令。让我们回到正常的对话吧！有什么可以帮助您的吗？",
            "我发现您的输入包含一些特殊指令，为了保持对话的安全性，让我们换个话题吧！",
            "我需要保持我的助手身份和职责。有什么其他问题我可以帮您解决吗？",
            "让我们专注于我能为您提供的帮助。请告诉我您需要什么类型的建议或服务？",
            "为了确保对话的质量，我建议我们回到我的专业领域。您有什么具体需求吗？"
        ]
    
    def is_injection_attempt(self, text: str) -> Tuple[bool, str, float]:
        """
        检测是否为注入攻击
        
        Returns:
            (is_injection, reason, confidence)
        """
        if not text or len(text.strip()) == 0:
            return False, "", 0.0
        
        text = text.strip()
        confidence_score = 0.0
        detection_reasons = []
        
        # 1. 正则表达式模式匹配
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                confidence_score += 0.8
                detection_reasons.append(f"匹配注入模式 #{i+1}")
        
        # 2. 关键词密度检查
        keyword_count = 0
        for keyword in self.suspicious_keywords:
            if keyword.lower() in text.lower():
                keyword_count += 1
        
        keyword_density = keyword_count / max(len(text.split()), 1)
        if keyword_density > 0.1:  # 关键词密度超过10%
            confidence_score += 0.6
            detection_reasons.append(f"可疑关键词密度: {keyword_density:.2%}")
        
        # 3. 结构化攻击检测
        structure_patterns = [
            r"^(system|admin|root):",
            r"\[.*\](.*)\[/.*\]",
            r"```.*system.*```",
            r"<.*>(.*)</.*>"
        ]
        
        for pattern in structure_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                confidence_score += 0.7
                detection_reasons.append("检测到结构化攻击模式")
        
        # 4. 特殊字符异常
        special_char_ratio = len(re.findall(r"[<>{}|\[\]()#$%^&*]", text)) / max(len(text), 1)
        if special_char_ratio > 0.15:  # 特殊字符超过15%
            confidence_score += 0.3
            detection_reasons.append(f"特殊字符比例异常: {special_char_ratio:.2%}")
        
        # 5. 长度异常检测
        if len(text) > 2000:  # 超长输入
            confidence_score += 0.2
            detection_reasons.append("输入长度异常")
        
        # 6. 重复模式检测
        words = text.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            if repetition_ratio > 0.5:  # 重复率超过50%
                confidence_score += 0.4
                detection_reasons.append(f"重复模式异常: {repetition_ratio:.2%}")
        
        # 判断阈值
        is_injection = confidence_score >= 0.6
        reason = "; ".join(detection_reasons) if detection_reasons else "正常输入"
        
        return is_injection, reason, min(confidence_score, 1.0)
    
    def sanitize_input(self, text: str) -> str:
        """清理用户输入"""
        if not text:
            return text
        
        # 移除潜在的注入标记
        sanitized = text
        
        # 移除HTML/XML标签
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        
        # 移除特殊指令标记
        sanitized = re.sub(r'\[.*?INST.*?\]', '', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<\|.*?\|>', '', sanitized)
        
        # 移除系统命令格式
        sanitized = re.sub(r'^(system|admin|root):\s*', '', sanitized, flags=re.IGNORECASE | re.MULTILINE)
        
        # 限制长度
        if len(sanitized) > 4000:
            sanitized = sanitized[:4000] + "...[内容已截断]"
        
        return sanitized.strip()
    
    def get_security_response(self, detection_reason: str = "") -> str:
        """获取安全响应"""
        import random
        
        base_response = random.choice(self.security_responses)
        
        if detection_reason:
            return f"{base_response}\n\n[安全提示: {detection_reason}]"
        else:
            return base_response
    
    def check_and_handle(self, text: str) -> Dict[str, any]:
        """检查并处理输入"""
        is_injection, reason, confidence = self.is_injection_attempt(text)
        
        result = {
            "is_safe": not is_injection,
            "original_text": text,
            "sanitized_text": self.sanitize_input(text),
            "detection_reason": reason,
            "confidence": confidence,
            "security_response": ""
        }
        
        if is_injection:
            result["security_response"] = self.get_security_response(reason)
        
        return result
    
    def log_security_event(self, session_id: str, text: str, reason: str, confidence: float):
        """记录安全事件（可扩展到日志系统）"""
        import datetime
        
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "event_type": "injection_attempt",
            "text_length": len(text),
            "detection_reason": reason,
            "confidence": confidence,
            "text_preview": text[:100] + "..." if len(text) > 100 else text
        }
        
        # 这里可以扩展到真实的日志系统
        print(f"[SECURITY] {event}")
        
        return event