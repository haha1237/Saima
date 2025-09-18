import os
from typing import Dict, Tuple

class CommandExecutor:
    def __init__(self):
        """
        初始化命令执行器
        """
        # 不再需要存储进程和停止标志
        pass
    
    # 删除set_pause_callback方法
    
    # 删除check_for_pause_command方法
    
    def execute_command(self, bat_path: str, gui_mode: bool = False) -> Tuple[int, str]:
        """
        执行指定的bat命令
        
        Args:
            bat_path: bat文件的路径
            gui_mode: 是否为GUI模式，默认为False（终端模式）
            
        Returns:
            返回码和输出信息的元组
        """
        if not os.path.exists(bat_path):
            return 1, f"错误: 找不到命令文件 {bat_path}"
        
        try:
            print(f"执行批处理文件: {bat_path}")
            
            if gui_mode:
                # GUI模式：使用start命令在新窗口中执行
                print("注意: 如果脚本包含pause命令，请在控制台窗口中按任意键继续")
                
                # 直接使用os.system执行命令，这样可以保留原始的控制台交互
                cmd = f'start cmd.exe /c "{bat_path} & pause"'
                os.system(cmd)
                
                # 由于我们使用了start命令，这里不需要等待进程结束
                # 创建一个虚拟的输出文本
                output_text = f"命令已在新窗口中启动: {bat_path}\n请在命令窗口中完成交互。"
                
                # 返回成功状态码和输出文本
                return 0, output_text
            else:
                # 终端模式：直接在当前终端执行命令
                # 使用os.system直接在当前终端执行，这样可以实时显示输出
                # 在Windows系统中，os.system会直接在当前控制台执行命令，并实时显示输出
                return_code = os.system(bat_path)
                
                # 由于os.system直接在终端显示输出，我们无法捕获输出内容
                # 但这样可以确保输出是实时显示的
                # 不显示额外的提示信息
                output_text = ""
                
                # 返回返回码和输出文本
                return return_code, output_text
        
        except Exception as e:
            return 1, f"执行命令时出错: {str(e)}"
            
    # 删除wait_for_keypress和continue_after_pause方法
    # 因为我们现在使用单独的命令窗口来处理交互
                
    def stop_execution(self):
        """
        停止命令执行
        """
        # 由于我们使用了os.system和start命令，无法直接停止进程
        # 用户需要在命令窗口中手动关闭
        print("请在命令窗口中手动关闭批处理脚本")
        return