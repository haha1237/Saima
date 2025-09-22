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
        使用AI分析日志内容，支持超长日志的分段处理
        
        Args:
            log_content: 日志内容
            log_type: 日志类型 (audio, display, general)
            
        Returns:
            分析结果字典
        """
        try:
            # 检测日志长度，决定是否使用分段处理
            if len(log_content) > 10000:
                return self._analyze_long_log_content(log_content, log_type)
            else:
                return self._analyze_single_log_content(log_content, log_type)
        except Exception as e:
            return {
                "success": False,
                "error": f"分析过程出错: {str(e)}",
                "log_type": log_type
            }
    
    def _analyze_long_log_content(self, log_content: str, log_type: str = "general") -> Dict:
        """
        分析超长日志内容，使用分段处理机制
        
        Args:
            log_content: 超长日志内容
            log_type: 日志类型
            
        Returns:
            整合后的分析结果字典
        """
        try:
            # 智能分段
            segments = self._smart_segment_log(log_content)
            
            # 分段分析
            segment_results = []
            context_summary = ""
            
            for i, segment in enumerate(segments):
                # 构建包含上下文的分析提示
                segment_result = self._analyze_segment_with_context(
                    segment, log_type, i + 1, len(segments), context_summary
                )
                
                if segment_result["success"]:
                    segment_results.append(segment_result)
                    # 更新上下文摘要
                    context_summary = self._extract_context_summary(segment_result["analysis"])
                else:
                    # 如果某段分析失败，记录错误但继续处理其他段
                    segment_results.append({
                        "success": False,
                        "error": f"第{i+1}段分析失败: {segment_result.get('error', '未知错误')}",
                        "segment_index": i + 1
                    })
            
            # 整合所有分段结果
            final_result = self._integrate_segment_results(segment_results, log_type)
            
            return final_result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"超长日志分析过程出错: {str(e)}",
                "log_type": log_type
            }
    
    def _smart_segment_log(self, log_content: str, max_segment_size: int = 8000) -> List[str]:
        """
        智能分段日志内容，保持上下文关联性
        
        Args:
            log_content: 日志内容
            max_segment_size: 每段最大字符数
            
        Returns:
            分段后的日志列表
        """
        segments = []
        lines = log_content.split('\n')
        current_segment = ""
        overlap_lines = 5  # 段间重叠行数，保持上下文
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 检查添加当前行是否会超出限制
            if len(current_segment) + len(line) + 1 > max_segment_size and current_segment:
                # 保存当前段
                segments.append(current_segment.strip())
                
                # 开始新段，包含重叠内容
                overlap_start = max(0, i - overlap_lines)
                current_segment = '\n'.join(lines[overlap_start:i]) + '\n'
            
            current_segment += line + '\n'
            i += 1
        
        # 添加最后一段
        if current_segment.strip():
            segments.append(current_segment.strip())
        
        return segments
    
    def _analyze_segment_with_context(self, segment: str, log_type: str, 
                                    segment_index: int, total_segments: int, 
                                    context_summary: str) -> Dict:
        """
        分析单个段落，结合上下文信息
        
        Args:
            segment: 当前段落内容
            log_type: 日志类型
            segment_index: 当前段落索引
            total_segments: 总段落数
            context_summary: 前文上下文摘要
            
        Returns:
            段落分析结果
        """
        try:
            # 构建系统提示
            system_prompt = self._get_system_prompt(log_type)
            
            # 构建包含上下文的用户提示
            context_info = ""
            if context_summary:
                context_info = f"\n\n【前文上下文摘要】:\n{context_summary}\n"
            
            user_prompt = f"""这是一个超长日志的第{segment_index}段（共{total_segments}段）。
{context_info}
请分析以下日志段落，并注意与前文的关联性：

{segment}

请提供详细的分析，包括：
1. 本段的主要问题和错误
2. 与前文的关联性分析
3. 关键信息提取
4. 本段小结"""
            
            # 调用API
            response = self._call_api(system_prompt, user_prompt)
            
            if response:
                return {
                    "success": True,
                    "analysis": response,
                    "segment_index": segment_index,
                    "total_segments": total_segments,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "API调用失败",
                    "segment_index": segment_index
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"段落分析出错: {str(e)}",
                "segment_index": segment_index
            }
    
    def _extract_context_summary(self, analysis_text: str) -> str:
        """
        从分析结果中提取上下文摘要
        
        Args:
            analysis_text: 分析结果文本
            
        Returns:
            上下文摘要
        """
        # 简单提取关键信息作为上下文
        lines = analysis_text.split('\n')
        summary_lines = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['错误', '异常', '失败', '问题', '关键', '重要']):
                summary_lines.append(line)
                if len(summary_lines) >= 3:  # 限制摘要长度
                    break
        
        return '\n'.join(summary_lines) if summary_lines else "无明显关键信息"
    
    def _integrate_segment_results(self, segment_results: List[Dict], log_type: str) -> Dict:
        """
        整合所有分段分析结果
        
        Args:
            segment_results: 分段分析结果列表
            log_type: 日志类型
            
        Returns:
            整合后的最终分析结果
        """
        try:
            successful_results = [r for r in segment_results if r.get("success", False)]
            failed_results = [r for r in segment_results if not r.get("success", False)]
            
            if not successful_results:
                return {
                    "success": False,
                    "error": "所有分段分析都失败了",
                    "log_type": log_type,
                    "failed_segments": len(failed_results)
                }
            
            # 构建整合分析的提示
            integration_prompt = f"""请整合以下{len(successful_results)}个日志分段的分析结果，生成完整的智能分析总结报告：

"""
            
            for i, result in enumerate(successful_results):
                integration_prompt += f"=== 第{result['segment_index']}段分析结果 ===\n"
                integration_prompt += result['analysis'] + "\n\n"
            
            integration_prompt += """
请基于以上分段分析，提供：
1. 整体问题总结
2. 关键错误和异常汇总
3. 问题的关联性分析
4. 解决建议
5. 完整的诊断报告

确保不遗漏任何重要信息，保持分析的连贯性和完整性。"""
            
            # 调用API进行结果整合
            system_prompt = self._get_system_prompt(log_type)
            integrated_response = self._call_api(system_prompt, integration_prompt)
            
            if integrated_response:
                # 构建最终结果
                final_analysis = f"""=== 超长日志智能分析报告 ===
处理信息：
- 总段数：{len(segment_results)}
- 成功分析段数：{len(successful_results)}
- 失败段数：{len(failed_results)}
- 分析时间：{time.strftime("%Y-%m-%d %H:%M:%S")}

{integrated_response}
"""
                
                if failed_results:
                    final_analysis += f"\n\n=== 处理异常信息 ===\n"
                    for failed in failed_results:
                        final_analysis += f"第{failed.get('segment_index', '?')}段: {failed.get('error', '未知错误')}\n"
                
                return {
                    "success": True,
                    "analysis": final_analysis,
                    "log_type": log_type,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "segment_info": {
                        "total_segments": len(segment_results),
                        "successful_segments": len(successful_results),
                        "failed_segments": len(failed_results)
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "结果整合失败",
                    "log_type": log_type,
                    "partial_results": successful_results
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"结果整合过程出错: {str(e)}",
                "log_type": log_type
            }
    
    def _analyze_single_log_content(self, log_content: str, log_type: str = "general") -> Dict:
        """
        分析单段日志内容（原有逻辑）
        
        Args:
            log_content: 日志内容
            log_type: 日志类型
            
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