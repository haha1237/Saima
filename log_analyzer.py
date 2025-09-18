import os
import re
import shutil
from typing import List, Dict, Set, Optional
import colorama
from colorama import Fore, Style
from ai_analyzer import AIAnalyzer

# 初始化colorama
colorama.init(autoreset=True)

class LogAnalyzer:
    def __init__(self, keyword_dir: str = 'keyword', processed_dir: str = 'processed_log', ai_api_key: str = None):
        """
        初始化日志分析器
        
        Args:
            keyword_dir: 关键字文件夹路径
            processed_dir: 处理后的日志保存路径
            ai_api_key: AI分析API密钥
        """
        self.keyword_dir = keyword_dir
        self.processed_dir = processed_dir
        self.keywords = self._load_keywords()
        
        # 初始化AI分析器
        self.ai_analyzer = None
        if ai_api_key:
            try:
                self.ai_analyzer = AIAnalyzer(ai_api_key)
            except Exception as e:
                print(f"AI分析器初始化失败: {str(e)}")
        
        # 确保processed_log目录存在
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # 日志级别颜色映射
        self.log_level_colors = {
            'ERROR': Fore.RED,
            'WARN': Fore.YELLOW,
            'WARNING': Fore.YELLOW,
            'INFO': Fore.GREEN,
            'DEBUG': Fore.CYAN,
            'TRACE': Fore.BLUE
        }
    
    def _load_keywords(self) -> Dict[str, Set[str]]:
        """
        加载关键字文件
        
        Returns:
            关键字字典，键为类型（audio/display），值为关键字集合
        """
        import sys
        
        # 获取正确的资源路径（支持打包后的路径）
        def get_resource_path(relative_path):
            try:
                # PyInstaller打包后的临时目录
                base_path = sys._MEIPASS
            except AttributeError:
                # 开发环境下的当前目录
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
        
        keywords = {}
        
        # 使用资源路径获取关键字文件
        try:
            # 加载audio关键字
            audio_path = get_resource_path('keyword/audio.txt')
            if os.path.exists(audio_path):
                with open(audio_path, 'r', encoding='utf-8') as f:
                    keywords['audio'] = {line.strip() for line in f if line.strip()}
            else:
                keywords['audio'] = set()
                print(f"警告: 音频关键字文件 {audio_path} 不存在")
            
            # 加载display关键字
            display_path = get_resource_path('keyword/display.txt')
            if os.path.exists(display_path):
                with open(display_path, 'r', encoding='utf-8') as f:
                    keywords['display'] = {line.strip() for line in f if line.strip()}
            else:
                keywords['display'] = set()
                print(f"警告: 显示关键字文件 {display_path} 不存在")
                
        except Exception as e:
            print(f"加载关键字文件时出错: {e}")
            keywords = {'audio': set(), 'display': set()}
        
        return keywords
    
    def analyze_log_file(self, log_file: str, log_type: str = None) -> Dict:
        """
        分析单个日志文件
        
        Args:
            log_file: 日志文件路径
            log_type: 日志类型，'audio'或'display'
            
        Returns:
            处理结果统计，包含匹配的行数和匹配的行内容
        """
        if not os.path.exists(log_file) or not os.path.isfile(log_file):
            print(f"错误: 日志文件 {log_file} 不存在或不是文件")
            return {'files': 0, 'matched_lines': 0, 'matched_content': []}
        
        # 清空processed_log目录
        if os.path.exists(self.processed_dir):
            for file in os.listdir(self.processed_dir):
                file_path = os.path.join(self.processed_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        file_result = self._process_log_file(log_file, log_type)
        
        matched_content = []
        if isinstance(file_result, dict) and file_result['count'] > 0:
            files_count = 1
            matched_lines_count = file_result['count']
            
            # 添加文件名作为标题
            base_name = os.path.basename(log_file)
            matched_content.append(f"文件: {base_name}")
            matched_content.append("-" * 40)
            
            # 添加匹配的行内容
            for line in file_result['content']:
                matched_content.append(line.rstrip())
        else:
            files_count = 0
            matched_lines_count = 0
        
        return {'files': files_count, 'matched_lines': matched_lines_count, 'matched_content': matched_content}
    
    def analyze_log(self, log_path: str, log_type: str = None) -> Dict:
        """
        分析日志文件或目录
        
        Args:
            log_path: 日志文件或目录路径
            log_type: 日志类型，'audio'或'display'
            
        Returns:
            处理结果统计，包含处理的文件数、匹配的行数和匹配的行内容
        """
        if not os.path.exists(log_path):
            print(f"错误: 路径 {log_path} 不存在")
            return {'files': 0, 'matched_lines': 0, 'matched_content': []}
        
        # 如果是文件，直接处理单个文件
        if os.path.isfile(log_path):
            return self.analyze_log_file(log_path, log_type)
        
        # 如果是目录，处理目录中的所有文件
        # 清空processed_log目录
        if os.path.exists(self.processed_dir):
            for file in os.listdir(self.processed_dir):
                file_path = os.path.join(self.processed_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        
        files_count = 0
        matched_lines_count = 0
        matched_content = []
        
        # 遍历日志目录中的所有文件
        for root, _, files in os.walk(log_path):
            for file in files:
                if file.endswith('.log') or file.endswith('.txt'):
                    file_path = os.path.join(root, file)
                    file_result = self._process_log_file(file_path, log_type)
                    if isinstance(file_result, dict):
                        if file_result['count'] > 0:
                            files_count += 1
                            matched_lines_count += file_result['count']
                            # 收集匹配的行内容
                            # 添加文件名作为标题
                            base_name = os.path.basename(file_path)
                            if matched_content and matched_content[-1] != "":
                                matched_content.append("")
                            matched_content.append(f"文件: {base_name}")
                            matched_content.append("-" * 40)
                            # 添加匹配的行内容
                            for line in file_result['content']:
                                matched_content.append(line.rstrip())
        
        return {'files': files_count, 'matched_lines': matched_lines_count, 'matched_content': matched_content}
    
    def _process_log_file(self, file_path: str, log_type: str = None) -> Dict:
        """
        处理单个日志文件
        
        Args:
            file_path: 日志文件路径
            log_type: 日志类型，'audio'或'display'
            
        Returns:
            包含匹配行数和匹配行内容的字典
        """
        try:
            # 确定关键字类型（audio或display）
            if log_type and log_type in ['audio', 'display']:
                keyword_type = log_type
            else:
                # 如果未指定类型，则根据文件路径判断
                keyword_type = 'audio' if 'audio' in file_path.lower() else 'display'
            
            keywords = self.keywords[keyword_type]
            
            # 如果没有关键字，则跳过处理
            if not keywords:
                print(f"跳过 {file_path}: 没有{keyword_type}关键字")
                return {'count': 0, 'content': []}
            
            matched_lines = []
            total_lines = 0
            
            # 读取日志文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_lines += 1
                    # 检查行是否包含任何关键字（作为完整单词）
                    if self._line_contains_keywords(line, keywords):
                        matched_lines.append(line)
                        # 在控制台显示带颜色的行
                        colored_line = self._colorize_log_line(line)
                        print(colored_line, end='')
            
            # 如果有匹配的行，保存到processed_log目录
            if matched_lines:
                base_name = os.path.basename(file_path)
                processed_path = os.path.join(self.processed_dir, f"processed_{base_name}")
                
                with open(processed_path, 'w', encoding='utf-8') as f:
                    f.writelines(matched_lines)
                
                # 不再显示详细的处理路径信息
                print(f"匹配到 {len(matched_lines)}/{total_lines} 行")
                return {'count': len(matched_lines), 'content': matched_lines}
            else:
                print(f"跳过 {file_path}: 没有匹配的行")
                return {'count': 0, 'content': []}
                
        except Exception as e:
            print(f"处理 {file_path} 时出错: {str(e)}")
            return {'count': 0, 'content': [], 'error': str(e)}
    
    def _line_contains_keywords(self, line: str, keywords: Set[str]) -> bool:
        """
        检查行是否包含任何关键字（作为部分单词也可以匹配）
        
        Args:
            line: 日志行
            keywords: 关键字集合
            
        Returns:
            如果行包含任何关键字，则返回True
        """
        for keyword in keywords:
            # 直接匹配关键字，不要求是完整单词
            if keyword.lower() in line.lower():
                return True
        return False
    
    def _colorize_log_line(self, line: str) -> str:
        """
        根据日志级别为行添加颜色
        
        Args:
            line: 日志行
            
        Returns:
            带颜色的日志行
        """
        for level, color in self.log_level_colors.items():
            if f"[{level}]" in line or f" {level} " in line or f":{level}:" in line:
                return color + line
        
        # 默认颜色
        return line
    
    def analyze_with_ai(self, log_content: str, analysis_type: str = "comprehensive") -> Optional[Dict]:
        """
        使用AI分析日志内容
        
        Args:
            log_content: 日志内容
            analysis_type: 分析类型 (comprehensive, error_analysis, performance, summary)
            
        Returns:
            AI分析结果字典，包含分析内容和建议
        """
        if not self.ai_analyzer:
            return {"error": "AI分析器未初始化，请检查API密钥"}
        
        try:
            if analysis_type == "comprehensive":
                return self.ai_analyzer.analyze_log_content(log_content)
            elif analysis_type == "error_analysis":
                return self.ai_analyzer.analyze_error_patterns(log_content)
            elif analysis_type == "performance":
                return self.ai_analyzer.analyze_performance_issues(log_content)
            elif analysis_type == "summary":
                return self.ai_analyzer.summarize_issues(log_content)
            else:
                return self.ai_analyzer.analyze_log_content(log_content)
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}"}
    
    def test_ai_connection(self) -> Dict[str, str]:
        """
        测试AI API连接
        
        Returns:
            连接测试结果
        """
        if not self.ai_analyzer:
            return {"status": "error", "message": "AI分析器未初始化"}
        
        return self.ai_analyzer.test_connection()
    
    def get_analysis_summary(self) -> str:
        """
        获取分析摘要
        
        Returns:
            分析摘要字符串
        """
        if not hasattr(self, 'analysis_results'):
            return "尚未进行分析"
        
        summary = []
        summary.append("=== 日志分析摘要 ===")
        
        for file_path, result in self.analysis_results.items():
            summary.append(f"\n文件: {file_path}")
            summary.append(f"总行数: {result['total_lines']}")
            summary.append(f"匹配行数: {result['matched_lines']}")
            
            if result['keyword_matches']:
                summary.append("关键字匹配统计:")
                for keyword_type, matches in result['keyword_matches'].items():
                    if matches:
                        summary.append(f"  {keyword_type}: {len(matches)}次")
        
        return "\n".join(summary)