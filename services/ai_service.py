#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI服务统一封装 - 支持OpenRouter多模型切换
"""

import requests
import json
import time
from typing import Dict, List, Optional, Generator
try:
    import dashscope
    from dashscope import Generation
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

class OpenRouterService:
    """OpenRouter API服务封装"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI-Assistant-Platform'
        })
        
        # 支持的模型映射 (包含免费模型)
        self.models = {
            # 免费模型 (推荐)
            'qwen3-14b-free': 'qwen/qwen3-14b:free',
            'qwen3-4b-free': 'qwen/qwen3-4b:free', 
            'qwen3-0.6b-free': 'qwen/qwen3-0.6b-04-28:free',
            'llama-3.2-3b-free': 'meta-llama/llama-3.2-3b-instruct:free',
            'llama-3.2-1b-free': 'meta-llama/llama-3.2-1b-instruct:free',
            'mistral-7b-free': 'mistralai/mistral-7b-instruct:free',
            'phi-3-mini-free': 'microsoft/phi-3-mini-128k-instruct:free',
            
            # 高级模型
            'gemini-pro': 'google/gemini-2.5-pro',
            'gemini-flash': 'google/gemini-2.5-flash',
            'claude-3.5-sonnet': 'anthropic/claude-3.5-sonnet',
            'claude-3.5-haiku': 'anthropic/claude-3.5-haiku',
            'gpt-4o': 'openai/gpt-4o',
            'gpt-4o-mini': 'openai/gpt-4o-mini',
            
            # Qwen系列
            'qwen3-32b': 'qwen/qwen3-32b',
            'qwen3-30b-a3b': 'qwen/qwen3-30b-a3b',
            'qwen-2.5-72b': 'qwen/qwen-2.5-72b-instruct',
            
            # 其他开源模型
            'llama-3.3-70b': 'meta-llama/llama-3.3-70b-instruct',
            'deepseek-v3': 'deepseek/deepseek-chat'
        }
    
    def chat_completion(self, model: str, messages: List[Dict], stream: bool = False, **kwargs) -> Dict:
        """聊天完成API调用"""
        model_name = self.models.get(model, model)
        
        data = {
            'model': model_name,
            'messages': messages,
            'stream': stream,
            'temperature': kwargs.get('temperature', 0.7),
            'max_tokens': kwargs.get('max_tokens', 2000),
            'top_p': kwargs.get('top_p', 0.9)
        }
        
        try:
            if stream:
                return self._stream_completion(data)
            else:
                return self._sync_completion(data)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content': ''
            }
    
    def _sync_completion(self, data: Dict) -> Dict:
        """同步聊天完成"""
        response = self.session.post(
            f'{self.base_url}/chat/completions',
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                'success': True,
                'content': result['choices'][0]['message']['content'],
                'usage': result.get('usage', {}),
                'model': result.get('model', data['model'])
            }
        else:
            return {
                'success': False,
                'error': f"API调用失败: {response.status_code}",
                'content': ''
            }
    
    def _stream_completion(self, data: Dict) -> Generator[str, None, None]:
        """流式聊天完成"""
        data['stream'] = True
        
        response = self.session.post(
            f'{self.base_url}/chat/completions',
            json=data,
            stream=True,
            timeout=60
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        chunk_data = json.loads(data_str)
                        if 'choices' in chunk_data and chunk_data['choices']:
                            delta = chunk_data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
    
    def get_available_models(self) -> List[Dict]:
        """获取可用模型列表"""
        try:
            response = self.session.get(f'{self.base_url}/models', timeout=30)
            if response.status_code == 200:
                models_data = response.json()
                return models_data.get('data', [])
            return []
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            return []

class DashScopeService:
    """百炼DashScope API服务封装"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        if DASHSCOPE_AVAILABLE:
            dashscope.api_key = api_key
        
        # 百炼支持的模型 (2024最新)
        self.models = {
            # 主力模型
            'qwen-max': 'qwen-max',
            'qwen-max-latest': 'qwen-max-latest', 
            'qwen-plus': 'qwen-plus',
            'qwen-plus-latest': 'qwen-plus-latest',
            'qwen-turbo': 'qwen-turbo',
            'qwen-turbo-latest': 'qwen-turbo-latest',
            'qwen-long': 'qwen-long',
            
            # 开源系列 (免费)
            'qwen3-32b': 'qwen3-32b',
            'qwen3-14b': 'qwen3-14b', 
            'qwen3-8b': 'qwen3-8b',
            'qwen3-4b': 'qwen3-4b',
            'qwen3-1.7b': 'qwen3-1.7b',
            'qwen3-0.6b': 'qwen3-0.6b',
            
            # 视觉模型
            'qwen-vl-max': 'qwen-vl-max',
            'qwen-vl-plus': 'qwen-vl-plus',
            
            # 代码模型
            'qwen-coder-plus': 'qwen-coder-plus',
            'qwen-coder-turbo': 'qwen-coder-turbo'
        }
    
    def chat_completion(self, model: str, messages: List[Dict], stream: bool = False, **kwargs) -> Dict:
        """DashScope聊天完成"""
        if not DASHSCOPE_AVAILABLE:
            return {
                'success': False,
                'error': '请安装dashscope: pip install dashscope',
                'content': ''
            }
        
        try:
            # 转换消息格式
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # 调用DashScope API
            response = Generation.call(
                model=model,
                messages=formatted_messages,
                stream=stream,
                **kwargs
            )
            
            if response.status_code == 200:
                if stream:
                    return {
                        'success': True,
                        'stream': response,
                        'content': ''
                    }
                else:
                    # 改进的响应内容解析
                    try:
                        # 方法1: 尝试标准路径
                        if hasattr(response, 'output') and response.output and \
                           hasattr(response.output, 'choices') and response.output.choices and \
                           len(response.output.choices) > 0:
                            content = response.output.choices[0].message.content
                        # 方法2: 尝试直接访问text字段
                        elif hasattr(response, 'output') and response.output and \
                             hasattr(response.output, 'text'):
                            content = response.output.text
                        # 方法3: 尝试message字段
                        elif hasattr(response, 'message'):
                            content = response.message
                        # 方法4: 尝试content字段
                        elif hasattr(response, 'content'):
                            content = response.content
                        else:
                            # 调试：输出响应结构
                            print(f"🔍 DashScope响应结构: {dir(response)}")
                            if hasattr(response, 'output'):
                                print(f"🔍 output结构: {dir(response.output)}")
                            content = f"API调用成功，响应结构: {str(response)[:200]}"
                        
                        return {
                            'success': True,
                            'content': content,
                            'usage': getattr(response, 'usage', {})
                        }
                    except Exception as e:
                        return {
                            'success': False,
                            'error': f'解析响应内容失败: {str(e)}',
                            'content': ''
                        }
            else:
                error_msg = getattr(response, 'message', f'HTTP {response.status_code}')
                return {
                    'success': False,
                    'error': f'DashScope API错误: {error_msg}',
                    'content': ''
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'DashScope调用异常: {str(e)}',
                'content': ''
            }
    
    def get_models(self) -> List[str]:
        """获取支持的模型列表"""
        return list(self.models.keys())

class AIService:
    """AI服务管理类 - 支持多平台"""
    
    def __init__(self, api_key: str = "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", platform: str = "openrouter"):
        self.platform = platform
        self.api_key = api_key
        
        if platform == "openrouter":
            self.service = OpenRouterService(api_key)
            self.current_model = 'gemini-flash'  # 默认使用快速模型
        elif platform == "dashscope":
            self.service = DashScopeService(api_key)
            self.current_model = 'qwen-turbo'  # 默认使用百炼快速模型
        else:
            raise ValueError(f"不支持的平台: {platform}")
        
        # 为了向后兼容，保留openrouter属性
        if platform == "openrouter":
            self.openrouter = self.service
    
    def set_model(self, model: str) -> bool:
        """设置当前使用的模型"""
        available_models = self.service.get_models() if hasattr(self.service, 'get_models') else list(self.service.models.keys())
        if model in available_models:
            self.current_model = model
            return True
        return False
    
    def chat(self, messages: List[Dict], stream: bool = False, **kwargs) -> Dict:
        """统一的聊天接口"""
        return self.service.chat_completion(
            model=self.current_model,
            messages=messages,
            stream=stream,
            **kwargs
        )
    
    def generate_content(self, prompt: str, model: str = None, **kwargs) -> str:
        """生成内容（用于游戏剧本生成等）"""
        use_model = model or self.current_model
        messages = [{'role': 'user', 'content': prompt}]
        
        result = self.service.chat_completion(
            model=use_model,
            messages=messages,
            stream=False,
            **kwargs
        )
        
        return result.get('content', '') if result.get('success') else ''
    
    def get_available_models(self) -> List[str]:
        """获取支持的模型列表"""
        if hasattr(self.service, 'get_models'):
            return self.service.get_models()
        else:
            return list(self.service.models.keys())
    
    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            if self.platform == "openrouter":
                return self._validate_openrouter_key()
            elif self.platform == "dashscope":
                return self._validate_dashscope_key()
            else:
                return False
                
        except Exception as e:
            print(f"❌ API密钥验证异常: {e}")
            return False
    
    def _validate_openrouter_key(self) -> bool:
        """验证OpenRouter API密钥"""
        import requests
        
        # 调试信息：显示输入的密钥
        masked_key = f"{self.api_key[:10]}...{self.api_key[-4:]}" if len(self.api_key) > 14 else "***"
        print(f"🔍 OpenRouter验证密钥: {masked_key}")
        print(f"🔍 密钥长度: {len(self.api_key)}")
        print(f"🔍 密钥前缀: {self.api_key[:15]}...")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'http://localhost:5000',
            'X-Title': 'AI-Assistant-Platform'
        }
        
        try:
            # 先尝试获取用户信息，这是验证API密钥最直接的方法
            print("🔍 正在验证OpenRouter API密钥权限...")
            
            # 方法1：尝试获取用户账户信息
            response = requests.get(
                'https://openrouter.ai/api/v1/auth/key',
                headers=headers,
                timeout=10
            )
            
            print(f"🔍 收到响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ OpenRouter API密钥验证成功")
                try:
                    data = response.json()
                    print(f"✅ 密钥信息: {data.get('data', {}).get('label', 'Valid key')}")
                    return True
                except Exception as e:
                    print(f"🔍 解析响应JSON失败，但密钥可能有效: {e}")
                    return True  # 即使JSON解析失败，200状态码表示密钥有效
            elif response.status_code == 401:
                print("❌ OpenRouter API密钥无效或已过期")
                return False
            elif response.status_code == 403:
                print("❌ OpenRouter API密钥权限不足")
                return False
            else:
                print(f"❌ OpenRouter API密钥验证失败，状态码: {response.status_code}")
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', response.text[:200])
                    print(f"错误详情: {error_msg}")
                except:
                    print(f"错误响应: {response.text[:200]}...")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ OpenRouter请求异常: {e}")
            return False
        except Exception as e:
            print(f"❌ OpenRouter验证未知错误: {e}")
            return False
    
    def _validate_dashscope_key(self) -> bool:
        """验证DashScope API密钥"""
        if not DASHSCOPE_AVAILABLE:
            print("❌ DashScope库未安装")
            return False
        
        try:
            # 直接设置API密钥并调用DashScope
            import dashscope
            from dashscope import Generation
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            # 使用简单的聊天请求验证密钥
            response = Generation.call(
                model='qwen-turbo',
                messages=[{'role': 'user', 'content': 'Hello'}],
                max_tokens=5
            )
            
            if response.status_code == 200:
                print("✅ DashScope API密钥验证成功")
                return True
            else:
                print(f"❌ DashScope API密钥验证失败: 状态码 {response.status_code}")
                print(f"错误信息: {getattr(response, 'message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ DashScope API密钥验证异常: {e}")
            return False