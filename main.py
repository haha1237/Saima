#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from command_manager import CommandManager
from command_executor import CommandExecutor
from interactive import Interactive
from log_analyzer import LogAnalyzer

def main():
    # 获取批处理脚本的基础路径
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'batch_script')
    
    # 检查基础路径是否存在
    if not os.path.exists(base_path):
        print(f"错误: 找不到批处理脚本目录: {base_path}")
        print("请确保批处理脚本目录存在并包含正确的文件结构")
        return 1
    
    try:
        # 初始化各个模块
        command_manager = CommandManager(base_path)
        command_executor = CommandExecutor()
        log_analyzer = LogAnalyzer()
        interactive = Interactive(command_manager, command_executor, log_analyzer)
        
        # 运行交互式界面
        interactive.run()
        
        return 0
    except Exception as e:
        print(f"程序运行时出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())