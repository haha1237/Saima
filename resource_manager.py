"""
资源路径管理模块
解决PyInstaller打包后的资源文件读写问题
"""
import os
import sys
import shutil
from pathlib import Path


class ResourceManager:
    """资源路径管理器"""
    
    def __init__(self):
        self._init_paths()
        self._ensure_writable_dirs()
    
    def _init_paths(self):
        """初始化路径"""
        # 检测是否为PyInstaller打包的exe
        self.is_exe = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
        
        if self.is_exe:
            # exe环境：临时目录用于读取，exe同级目录用于写入
            self.read_base_path = sys._MEIPASS
            self.write_base_path = os.path.dirname(sys.executable)
        else:
            # 开发环境：使用项目根目录
            self.read_base_path = os.path.dirname(os.path.abspath(__file__))
            self.write_base_path = self.read_base_path
    
    def _ensure_writable_dirs(self):
        """确保可写目录存在"""
        dirs_to_create = ['keyword', 'batch_script', 'processed_log']
        
        for dir_name in dirs_to_create:
            write_dir = os.path.join(self.write_base_path, dir_name)
            if not os.path.exists(write_dir):
                os.makedirs(write_dir, exist_ok=True)
                
                # 如果是exe环境，从临时目录复制初始文件
                if self.is_exe:
                    read_dir = os.path.join(self.read_base_path, dir_name)
                    if os.path.exists(read_dir):
                        self._copy_directory_contents(read_dir, write_dir)
    
    def _copy_directory_contents(self, src_dir, dst_dir):
        """复制目录内容"""
        try:
            for root, dirs, files in os.walk(src_dir):
                # 计算相对路径
                rel_path = os.path.relpath(root, src_dir)
                dst_root = os.path.join(dst_dir, rel_path) if rel_path != '.' else dst_dir
                
                # 创建目录
                os.makedirs(dst_root, exist_ok=True)
                
                # 复制文件
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dst_root, file)
                    if not os.path.exists(dst_file):  # 只复制不存在的文件
                        shutil.copy2(src_file, dst_file)
        except Exception as e:
            print(f"复制目录内容时出错: {e}")
    
    def get_read_path(self, relative_path):
        """获取读取路径（优先从可写目录读取，如果不存在则从只读目录读取）"""
        # 首先尝试从可写目录读取
        write_path = os.path.join(self.write_base_path, relative_path)
        if os.path.exists(write_path):
            return write_path
        
        # 如果可写目录不存在，从只读目录读取
        read_path = os.path.join(self.read_base_path, relative_path)
        return read_path
    
    def get_write_path(self, relative_path):
        """获取写入路径（总是返回可写目录）"""
        write_path = os.path.join(self.write_base_path, relative_path)
        
        # 确保父目录存在
        parent_dir = os.path.dirname(write_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        return write_path
    
    def get_keyword_dir(self):
        """获取关键词目录（可写）"""
        return os.path.join(self.write_base_path, 'keyword')
    
    def get_batch_script_dir(self):
        """获取批处理脚本目录（可写）"""
        return os.path.join(self.write_base_path, 'batch_script')
    
    def get_processed_log_dir(self):
        """获取处理后日志目录（可写）"""
        return os.path.join(self.write_base_path, 'processed_log')
    
    def copy_file_to_writable(self, relative_path):
        """将文件从只读目录复制到可写目录"""
        read_path = os.path.join(self.read_base_path, relative_path)
        write_path = self.get_write_path(relative_path)
        
        if os.path.exists(read_path) and not os.path.exists(write_path):
            try:
                shutil.copy2(read_path, write_path)
                return True
            except Exception as e:
                print(f"复制文件失败: {e}")
                return False
        return False


# 全局资源管理器实例
resource_manager = ResourceManager()


def get_resource_path(relative_path):
    """获取资源读取路径（兼容旧代码）"""
    return resource_manager.get_read_path(relative_path)


def get_writable_path(relative_path):
    """获取资源写入路径"""
    return resource_manager.get_write_path(relative_path)