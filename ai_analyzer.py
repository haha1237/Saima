#!/usr/bin/env python
# -*- coding: utf-8 -*-

from openai import OpenAI
import json
from typing import List, Dict, Optional
import time

class AIAnalyzer:
    """
    AI日志分析器，使用传音智库API进行智能分析
    """
    
    def __init__(self, api_key: str):
        """
        初始化AI分析器
        
        Args:
            api_key: 传音智库API密钥
        """
        self.api_key = api_key
        self.base_url = "https://hk-intra-paas.transsion.com/tranai-proxy/v1"
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url
        )
    
    def analyze_log_content(self, log_content: str, log_type: str = "general") -> Dict:
        """
        使用AI分析日志内容
        
        Args:
            log_content: 日志内容
            log_type: 日志类型 (audio, display, general)
            
        Returns:
            分析结果字典
        """
        try:
            # 构建针对不同日志类型的分析提示
            system_prompt = self._get_system_prompt(log_type)
            user_prompt = self._build_analysis_prompt(log_content, log_type)
            
            # 调用API
            response = self._call_api(system_prompt, user_prompt)
            
            if response:
                return {
                    "success": True,
                    "analysis": response,
                    "log_type": log_type,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "API调用失败",
                    "log_type": log_type
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"分析过程出错: {str(e)}",
                "log_type": log_type
            }
    
    def analyze_error_patterns(self, log_content: str) -> Dict:
        """
        分析日志中的错误模式
        
        Args:
            log_content: 日志内容
            
        Returns:
            错误分析结果
        """
        try:
            system_prompt = "你是一个专业的日志分析专家，专门识别和分析系统错误模式。"
            user_prompt = f"""请分析以下日志内容中的错误模式：

{log_content}

请提供：
1. 发现的错误类型和严重程度
2. 错误发生的频率和模式
3. 可能的根本原因
4. 建议的解决方案"""
            
            response = self._call_api(system_prompt, user_prompt)
            
            if response:
                return {
                    "success": True,
                    "error_analysis": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "错误分析失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"错误分析过程出错: {str(e)}"
            }
    
    def summarize_log_issues(self, log_content: str) -> Dict:
        """
        总结日志中的问题
        
        Args:
            log_content: 日志内容
            
        Returns:
            问题总结结果
        """
        try:
            system_prompt = "你是一个系统运维专家，擅长总结和归纳日志中的关键问题。"
            user_prompt = f"""请总结以下日志内容中的关键问题：

{log_content}

请提供：
1. 主要问题列表（按优先级排序）
2. 每个问题的影响范围
3. 建议的处理优先级
4. 预防措施建议"""
            
            response = self._call_api(system_prompt, user_prompt)
            
            if response:
                return {
                    "success": True,
                    "summary": response,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "问题总结失败"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"问题总结过程出错: {str(e)}"
            }
    
    def _get_system_prompt(self, log_type: str) -> str:
        """
        根据日志类型获取系统提示
        
        Args:
            log_type: 日志类型
            
        Returns:
            系统提示文本
        """
        prompts = {
            "audio": "你是一个专业的音频系统分析专家，擅长分析音频相关的日志和问题。请专注于音频播放、录制、编解码、音效处理等方面的分析。",
            "display": "你是一个专业的显示系统分析专家，擅长分析显示相关的日志和问题。请专注于屏幕显示、图形渲染、分辨率、刷新率等方面的分析。",
            "general": "你是一个专业的系统日志分析专家，擅长分析各种类型的系统日志，识别问题并提供解决方案。"
        }
        
        return prompts.get(log_type, prompts["general"])
    
    def _build_analysis_prompt(self, log_content: str, log_type: str) -> str:
        """
        构建分析提示
        
        Args:
            log_content: 日志内容
            log_type: 日志类型
            
        Returns:
            分析提示文本
        """
        base_prompt = f"""请分析以下{log_type}日志内容：

{log_content}

请提供详细的分析报告，包括：
1. 日志概要和关键信息
2. 发现的问题和异常
3. 性能指标分析
4. 建议的优化措施
5. 潜在风险评估"""
        
        return base_prompt
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        调用传音智库API
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            
        Returns:
            API响应内容
        """
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            print(f"API调用出错: {str(e)}")
            return None
    
    def test_connection(self) -> Dict:
        """
        测试API连接
        
        Returns:
            包含连接状态和消息的字典
        """
        try:
            response = self._call_api(
                "You are a helpful assistant.",
                "Hello! Please respond with 'Connection test successful.'"
            )
            if response is not None and "Connection test successful" in response:
                return {
                    "status": "success",
                    "message": "API连接测试成功！"
                }
            else:
                return {
                    "status": "error",
                    "message": "API响应异常，请检查配置"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"API连接失败: {str(e)}"
            }