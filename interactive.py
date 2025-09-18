import os
import sys
from typing import Dict, List, Optional, Tuple

from command_manager import CommandManager
from command_executor import CommandExecutor

class Interactive:
    def __init__(self, command_manager: CommandManager, command_executor: CommandExecutor, log_analyzer=None):
        """
        初始化交互模块
        
        Args:
            command_manager: 命令管理器实例
            command_executor: 命令执行器实例
            log_analyzer: 日志分析器实例
        """
        self.command_manager = command_manager
        self.command_executor = command_executor
        self.log_analyzer = log_analyzer
        self.current_module = None
        self.current_command_type = None
    
    def clear_screen(self):
        """
        清除屏幕
        """
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """
        打印程序头部信息
        """
        self.clear_screen()
        print("="*60)
        print("Audio/Display调试命令集一键执行平台 - 交互式执行器")
        print("="*60)
        print()
    
    def print_navigation(self):
        """
        打印导航信息
        """
        path = []
        if self.current_module:
            path.append(self.current_module)
        if self.current_command_type:
            path.append(self.current_command_type)
        
        if path:
            print(f"当前位置: {' > '.join(path)}")
        print()
    
    def select_module(self) -> Optional[str]:
        """
        选择模块（Audio/Display）
        
        Returns:
            选择的模块名称，如果用户选择退出则返回None
        """
        self.print_header()
        print("请选择模块:")
        print()
        
        modules = self.command_manager.get_modules()
        if not modules:
            print("错误: 未找到可用模块")
            input("按Enter键继续...")
            return None
        
        for i, module in enumerate(modules, 1):
            print(f"{i}. {module}")
        
        print("0. 返回上一级")
        print("q. 退出程序")
        print()
        
        while True:
            try:
                choice = input("请输入选项编号: ")
                if choice == '0':
                    return None
                elif choice.lower() == 'q':
                    sys.exit(0)
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(modules):
                    return modules[choice_idx]
                else:
                    print("无效的选项，请重新输入")
            except ValueError:
                print("请输入有效的数字")
    
    def select_command_type(self, module: str) -> Optional[str]:
        """
        选择命令类型（单条命令/组合命令）
        
        Args:
            module: 模块名称
            
        Returns:
            选择的命令类型，如果用户选择返回则返回None
        """
        self.print_header()
        self.current_module = module
        self.print_navigation()
        
        print(f"请选择{module}模块的命令类型:")
        print()
        
        command_types = self.command_manager.get_command_types(module)
        if not command_types:
            print(f"错误: 在{module}模块中未找到可用的命令类型")
            input("按Enter键继续...")
            return None
        
        # 显示中文名称
        type_names = {
            'single_command': '单条命令',
            'combination_command': '组合命令'
        }
        
        for i, cmd_type in enumerate(command_types, 1):
            print(f"{i}. {type_names.get(cmd_type, cmd_type)}")
        
        print("0. 返回上一级")
        print("q. 退出程序")
        print()
        
        while True:
            try:
                choice = input("请输入选项编号: ")
                if choice == '0':
                    self.current_module = None
                    return None
                elif choice.lower() == 'q':
                    sys.exit(0)
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(command_types):
                    return command_types[choice_idx]
                else:
                    print("无效的选项，请重新输入")
            except ValueError:
                print("请输入有效的数字")
    
    def select_command(self, module: str, command_type: str) -> Optional[Dict[str, str]]:
        """
        选择具体的命令
        
        Args:
            module: 模块名称
            command_type: 命令类型
            
        Returns:
            选择的命令信息，如果用户选择返回则返回None
        """
        self.print_header()
        self.current_module = module
        self.current_command_type = command_type
        self.print_navigation()
        
        print(f"请选择命令:")
        print()
        
        commands = self.command_manager.get_commands(module, command_type)
        if not commands:
            print(f"错误: 未找到可用的命令")
            input("按Enter键继续...")
            self.current_command_type = None
            return None
        
        # 按命令ID排序
        sorted_commands = sorted(commands.items(), key=lambda x: int(x[0]))
        
        for cmd_id, cmd_info in sorted_commands:
            print(f"{cmd_id}. {cmd_info['help']}")
        
        print("0. 返回上一级")
        print("q. 退出程序")
        print()
        
        while True:
            choice = input("请输入命令编号: ")
            if choice == '0':
                self.current_command_type = None
                return None
            elif choice.lower() == 'q':
                sys.exit(0)
            
            if choice in commands:
                return commands[choice]
            else:
                print("无效的命令编号，请重新输入")
    
    def execute_selected_command(self, command_info: Dict[str, str]):
        """
        执行选定的命令
        
        Args:
            command_info: 命令信息字典
        """
        self.print_header()
        self.print_navigation()
        
        bat_path = command_info['bat_path']
        help_text = command_info['help']
        
        print(f"正在执行: {help_text}")
        print(f"命令文件: {bat_path}")
        print("\n执行结果:")
        print("-" * 60)
        
        return_code, output = self.command_executor.execute_command(bat_path)
        
        print(output)
        print("-" * 60)
        print(f"命令执行完成，返回码: {return_code}")
        
        input("\n按Enter键继续...")
    
    def select_main_function(self):
        """
        选择主功能：分析日志或执行命令
        
        Returns:
            选择的功能，如果退出则返回None
        """
        self.clear_screen()
        self.print_header()
        
        print("请选择功能:")
        print()
        print("1. 执行命令")
        print("2. 分析日志")
        print("q. 退出程序")
        print()
        
        while True:
            choice = input("请输入选项: ").strip().lower()
            if choice == 'q':
                return None
            elif choice == '1':
                return 'execute_command'
            elif choice == '2':
                return 'analyze_log'
            else:
                print("无效的选项，请重新输入")
    
    def analyze_log_interface(self):
        """
        日志分析界面
        """
        if self.log_analyzer is None:
            print("错误: 日志分析器未初始化")
            input("\n按Enter键继续...")
            return
        
        while True:  # 外层循环用于日志类型选择
            self.clear_screen()
            self.print_header()
            
            # 选择日志类型
            print("请选择要分析的日志类型:")
            print()
            print("1. Audio相关日志")
            print("2. Display相关日志")
            print("0. 返回上级菜单")
            print("q. 退出程序")
            print()
            
            log_type_choice = input("请输入选项: ").strip().lower()
            if log_type_choice == 'q':
                sys.exit(0)
            elif log_type_choice == '0':
                return  # 返回主菜单
            elif log_type_choice in ['1', '2']:
                log_type = 'audio' if log_type_choice == '1' else 'display'
                
                # 日志文件路径输入循环
                while True:
                    # 清屏并重新显示界面
                    self.clear_screen()
                    self.print_header()
                    
                    # 获取日志文件路径
                    print(f"请输入要分析的{log_type}日志文件路径:")
                    print()
                    print("0. 返回上级菜单")
                    print("q. 退出程序")
                    print()
                    
                    log_path = input("请输入日志文件路径: ").strip()
                    if log_path.lower() == 'q':
                        sys.exit(0)
                    elif log_path == '0':
                        break  # 返回到日志类型选择界面
                    elif not log_path:
                        print("错误: 未提供文件路径，请重新输入")
                        input("\n按Enter键继续...")
                        continue
                    
                    if not os.path.exists(log_path) or not os.path.isfile(log_path):
                        print(f"错误: 文件 {log_path} 不存在或不是文件")
                        input("\n按Enter键继续...")
                        continue
                    
                    print(f"\n开始分析{log_type}日志文件: {log_path}")
                    
                    print("-" * 60)
                    
                    # 分析日志
                    result = self.log_analyzer.analyze_log(log_path, log_type)
                    
                    print("-" * 60)
                    print(f"分析完成: 处理了 {result['files']} 个文件，匹配了 {result['matched_lines']} 行")
                    print(f"处理后的日志保存在: {os.path.abspath(self.log_analyzer.processed_dir)}")
                    
                    input("\n按Enter键继续...")
                    # 继续循环，显示日志文件路径输入界面
    
    def run(self):
        """
        运行交互式界面
        """
        while True:
            # 选择主功能
            main_function = self.select_main_function()
            if main_function is None:
                break
            elif main_function == 'back':
                continue
            
            if main_function == 'analyze_log':
                self.analyze_log_interface()
            elif main_function == 'execute_command':
                # 执行命令功能
                while True:
                    # 选择模块
                    module = self.select_module()
                    if module is None:
                        break
                    
                    while True:
                        # 选择命令类型
                        command_type = self.select_command_type(module)
                        if command_type is None:
                            break
                        
                        while True:
                            # 选择具体命令
                            command_info = self.select_command(module, command_type)
                            if command_info is None:
                                break
                            
                            # 执行命令
                            self.execute_selected_command(command_info)
        
        self.print_header()
        print("感谢使用Audio/Display调试命令集一键执行平台，再见！")
        print()