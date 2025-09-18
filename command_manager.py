import os
import json
from typing import Dict, List, Tuple, Optional

class CommandManager:
    def __init__(self, base_path: str):
        """
        初始化命令管理器
        
        Args:
            base_path: 命令脚本的基础路径
        """
        self.base_path = base_path
        self.modules = ['Audio', 'Display']
        self.command_types = ['single_command', 'combination_command']
    
    def get_modules(self) -> List[str]:
        """
        获取所有可用的模块（Audio/Display）
        
        Returns:
            模块列表
        """
        return [module for module in self.modules if os.path.exists(os.path.join(self.base_path, module))]
    
    def get_command_types(self, module: str) -> List[str]:
        """
        获取指定模块下的命令类型（单条命令/组合命令）
        
        Args:
            module: 模块名称
            
        Returns:
            命令类型列表
        """
        module_path = os.path.join(self.base_path, module)
        return [cmd_type for cmd_type in self.command_types 
                if os.path.exists(os.path.join(module_path, cmd_type))]
    
    def get_commands(self, module: str, command_type: str) -> Dict[str, Dict[str, str]]:
        """
        获取指定模块和命令类型下的所有命令
        
        Args:
            module: 模块名称
            command_type: 命令类型
            
        Returns:
            命令字典，键为命令ID，值为命令信息（包含bat路径和帮助信息）
        """
        commands = {}
        command_path = os.path.join(self.base_path, module, command_type)
        
        if not os.path.exists(command_path):
            return commands
        
        # 遍历命令目录（以数字命名的文件夹）
        for cmd_id in os.listdir(command_path):
            cmd_dir = os.path.join(command_path, cmd_id)
            if os.path.isdir(cmd_dir):
                bat_file = None
                help_file = None
                
                # 查找bat文件和help.txt文件
                for file in os.listdir(cmd_dir):
                    file_path = os.path.join(cmd_dir, file)
                    if file.endswith('.bat'):
                        bat_file = file_path
                    elif file == 'help.txt':
                        help_file = file_path
                
                # 如果同时存在bat文件和help文件，则添加到命令列表
                if bat_file and help_file:
                    help_content = ''
                    try:
                        with open(help_file, 'r', encoding='utf-8') as f:
                            help_content = f.read().strip()
                    except Exception as e:
                        help_content = f'无法读取帮助信息: {str(e)}'
                    
                    commands[cmd_id] = {
                        'bat_path': bat_file,
                        'help': help_content
                    }
        
        return commands
    
    def get_command_info(self, module: str, command_type: str, command_id: str) -> Optional[Dict[str, str]]:
        """
        获取特定命令的信息
        
        Args:
            module: 模块名称
            command_type: 命令类型
            command_id: 命令ID
            
        Returns:
            命令信息字典，如果命令不存在则返回None
        """
        commands = self.get_commands(module, command_type)
        return commands.get(command_id)
    
    def delete_command(self, module: str, command_type: str, command_id: str) -> bool:
        """
        删除指定的命令
        
        Args:
            module: 模块名称
            command_type: 命令类型
            command_id: 命令ID
            
        Returns:
            删除是否成功
        """
        import shutil
        
        command_path = os.path.join(self.base_path, module, command_type)
        cmd_dir = os.path.join(command_path, command_id)
        
        if not os.path.exists(cmd_dir):
            return False
        
        try:
            # 删除命令目录
            shutil.rmtree(cmd_dir)
            
            # 重新编号后续目录
            self._renumber_commands(module, command_type, int(command_id))
            
            return True
        except Exception as e:
            print(f"删除命令失败: {str(e)}")
            return False
    
    def _renumber_commands(self, module: str, command_type: str, deleted_id: int):
        """
        重新编号命令目录，将删除ID后的所有目录数字依次减一
        
        Args:
            module: 模块名称
            command_type: 命令类型
            deleted_id: 被删除的命令ID
        """
        command_path = os.path.join(self.base_path, module, command_type)
        
        if not os.path.exists(command_path):
            return
        
        # 获取所有数字目录并排序
        numeric_dirs = []
        for item in os.listdir(command_path):
            item_path = os.path.join(command_path, item)
            if os.path.isdir(item_path) and item.isdigit():
                numeric_dirs.append(int(item))
        
        numeric_dirs.sort()
        
        # 重命名大于deleted_id的目录
        for dir_id in reversed(numeric_dirs):  # 从大到小处理，避免冲突
            if dir_id > deleted_id:
                old_path = os.path.join(command_path, str(dir_id))
                new_path = os.path.join(command_path, str(dir_id - 1))
                
                try:
                    os.rename(old_path, new_path)
                except Exception as e:
                    print(f"重命名目录失败 {old_path} -> {new_path}: {str(e)}")
