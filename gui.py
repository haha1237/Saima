#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import time
import subprocess
import re
from datetime import datetime

from command_manager import CommandManager
from command_executor import CommandExecutor
from log_analyzer import LogAnalyzer
from resource_manager import resource_manager

# Markdown支持
try:
    from tkhtmlview import HTMLLabel
    from markdown2 import Markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("警告: 未安装tkhtmlview或markdown2库，将使用普通文本显示。")
    print("请运行: pip install tkhtmlview markdown2")

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.updating = True
        threading.Thread(target=self.update_text_widget, daemon=True).start()
    
    def write(self, string):
        self.queue.put(string)
    
    def flush(self):
        pass
    
    def update_text_widget(self):
        while self.updating:
            try:
                while True:
                    string = self.queue.get_nowait()
                    self.text_widget.configure(state="normal")
                    self.text_widget.insert(tk.END, string)
                    self.text_widget.see(tk.END)
                    self.text_widget.configure(state="disabled")
                    self.queue.task_done()
            except queue.Empty:
                pass
            time.sleep(0.1)
    
    def stop_updating(self):
        self.updating = False

class BatchCommandGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 使用资源管理器获取路径
        self.base_path = resource_manager.get_batch_script_dir()
        keyword_dir = resource_manager.get_keyword_dir()
        processed_dir = resource_manager.get_processed_log_dir()
        
        # 初始化各个模块
        self.command_manager = CommandManager(self.base_path)
        self.command_executor = CommandExecutor()
        
        # AI API密钥（可以从配置文件或环境变量读取）
        self.ai_api_key = "sk_bb948d4a08697edc789ccdf83743992b3ba455f9f56cf945f502975"
        
        self.log_analyzer = LogAnalyzer(keyword_dir=keyword_dir, processed_dir=processed_dir, ai_api_key=self.ai_api_key)
        
        # 性能优化配置
        self.performance_config = {
            'buffer_size': 50,          # 缓冲区大小（行数）
            'update_interval': 0.1,     # UI更新间隔（秒）
            'max_lines': 10000,         # 最大显示行数
            'enable_highlight': True    # 是否启用关键字高亮
        }
        
        # 设置窗口属性
        self.title("Audio/Display调试命令集一键执行平台 - 图形界面")
        self.geometry("1000x700")  # 增加窗口初始大小
        self.minsize(900, 600)  # 增加最小窗口大小
        
        # 创建主框架
        self.create_widgets()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # 创建顶部标题栏
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = ttk.Label(title_frame, text="Audio/Display调试命令集一键执行平台", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT, padx=10)
        
        # 创建选项卡控件
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建命令执行选项卡
        self.command_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.command_tab, text="命令执行")
        self.create_command_tab()
        
        # 创建日志分析选项卡
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="日志分析")
        self.create_log_tab()
        
        # 创建底部状态栏
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        # 创建版权信息
        version_label = ttk.Label(status_frame, text="v1.0")
        version_label.pack(side=tk.RIGHT)
    
    def create_command_tab(self):
        # 创建左侧选择区域和右侧输出区域的分隔窗格
        command_paned = ttk.PanedWindow(self.command_tab, orient=tk.HORIZONTAL)
        command_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧选择区域
        left_frame = ttk.Frame(command_paned)
        command_paned.add(left_frame, weight=1)
        
        # 右侧输出区域
        right_frame = ttk.Frame(command_paned)
        command_paned.add(right_frame, weight=2)
        
        # 在左侧框架中创建选择控件
        # 模块选择（Audio/Display）
        module_frame = ttk.LabelFrame(left_frame, text="模块选择")
        module_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.module_var = tk.StringVar()
        modules = self.command_manager.get_modules()
        if modules:
            self.module_var.set(modules[0])
        
        for module in modules:
            ttk.Radiobutton(module_frame, text=module, variable=self.module_var, 
                           value=module, command=self.on_module_change).pack(anchor=tk.W, padx=10, pady=2)
        
        # 命令类型选择（单条命令/组合命令）
        self.cmd_type_frame = ttk.LabelFrame(left_frame, text="命令类型")
        self.cmd_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cmd_type_var = tk.StringVar()
        self.update_command_types()
        
        # 命令选择
        self.cmd_frame = ttk.LabelFrame(left_frame, text="命令选择")
        self.cmd_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.cmd_listbox = tk.Listbox(self.cmd_frame)
        self.cmd_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.cmd_listbox.bind("<<ListboxSelect>>", self.on_command_select)
        
        # 当前选中命令显示区域
        self.selected_cmd_frame = ttk.LabelFrame(left_frame, text="当前选中命令")
        self.selected_cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.selected_cmd_var = tk.StringVar(value="未选择命令")
        self.selected_cmd_label = ttk.Label(self.selected_cmd_frame, textvariable=self.selected_cmd_var, wraplength=250)
        self.selected_cmd_label.pack(fill=tk.X, padx=5, pady=5)
        
        self.update_commands()
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # 执行按钮
        self.execute_button = ttk.Button(button_frame, text="执行命令", command=self.execute_command)
        self.execute_button.pack(fill=tk.X, pady=2)
        
        # 编辑命令按钮（整合显示、添加、删除功能）
        self.edit_command_button = ttk.Button(button_frame, text="编辑命令", command=self.show_edit_command_dialog)
        self.edit_command_button.pack(fill=tk.X, pady=2)
        
        # 在右侧框架中创建输出区域
        output_frame = ttk.Frame(right_frame)
        output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 执行结果（包含命令信息和执行结果）
        cmd_output_frame = ttk.LabelFrame(output_frame, text="执行结果")
        cmd_output_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建文本框容器以支持横向滚动条
        cmd_text_frame = ttk.Frame(cmd_output_frame)
        cmd_text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.cmd_output_text = tk.Text(cmd_text_frame, height=15, wrap=tk.NONE, state="disabled")
        
        # 添加垂直和横向滚动条
        cmd_v_scrollbar = ttk.Scrollbar(cmd_text_frame, orient=tk.VERTICAL, command=self.cmd_output_text.yview)
        cmd_h_scrollbar = ttk.Scrollbar(cmd_text_frame, orient=tk.HORIZONTAL, command=self.cmd_output_text.xview)
        
        self.cmd_output_text.configure(yscrollcommand=cmd_v_scrollbar.set, xscrollcommand=cmd_h_scrollbar.set)
        
        # 布局滚动条和文本框
        self.cmd_output_text.grid(row=0, column=0, sticky="nsew")
        cmd_v_scrollbar.grid(row=0, column=1, sticky="ns")
        cmd_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        cmd_text_frame.grid_rowconfigure(0, weight=1)
        cmd_text_frame.grid_columnconfigure(0, weight=1)
        
        # 配置实时日志的高亮标签样式（与日志分析页面一致）
        self.cmd_output_text.tag_configure("highlight_red", background="#ffcccc", foreground="#cc0000")
        self.cmd_output_text.tag_configure("highlight_blue", background="#ccccff", foreground="#0000cc")
        self.cmd_output_text.tag_configure("highlight_green", background="#ccffcc", foreground="#00cc00")
        self.cmd_output_text.tag_configure("highlight_yellow", background="#ffffcc", foreground="#cccc00")
        self.cmd_output_text.tag_configure("highlight_purple", background="#ffccff", foreground="#cc00cc")
        

        
        # 实时日志抓取功能区域
        realtime_log_frame = ttk.LabelFrame(output_frame, text="实时日志抓取")
        realtime_log_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 创建一行布局的控件容器
        realtime_controls_frame = ttk.Frame(realtime_log_frame)
        realtime_controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 日志类型选择
        ttk.Label(realtime_controls_frame, text="日志类型:").pack(side=tk.LEFT, padx=(0, 5))
        self.realtime_log_type_var = tk.StringVar(value="dmesg")
        log_type_combo = ttk.Combobox(realtime_controls_frame, textvariable=self.realtime_log_type_var, 
                                     values=["dmesg", "logcat"], state="readonly", width=8)
        log_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # 筛选方向选择
        ttk.Label(realtime_controls_frame, text="筛选方向:").pack(side=tk.LEFT, padx=(0, 5))
        self.realtime_direction_var = tk.StringVar(value="Audio")
        direction_combo = ttk.Combobox(realtime_controls_frame, textvariable=self.realtime_direction_var, 
                                      values=["Audio", "Display", "Both"], state="readonly", width=8)
        direction_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # 保存日志复选框
        self.save_log_var = tk.BooleanVar()
        self.save_log_checkbox = ttk.Checkbutton(realtime_controls_frame, text="保存", 
                                               variable=self.save_log_var)
        self.save_log_checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        # 操作按钮
        self.start_realtime_button = ttk.Button(realtime_controls_frame, text="开始实时日志抓取筛选", 
                                               command=self.start_realtime_log_capture)
        self.start_realtime_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_realtime_button = ttk.Button(realtime_controls_frame, text="停止抓取", 
                                              command=self.stop_realtime_log_capture, state="disabled")
        self.stop_realtime_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 性能设置按钮
        self.performance_settings_button = ttk.Button(realtime_controls_frame, text="性能设置", 
                                                     command=self.open_performance_settings_dialog)
        self.performance_settings_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_realtime_button = ttk.Button(realtime_controls_frame, text="清除输出", 
                                               command=self.clear_realtime_output)
        self.clear_realtime_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # 初始化实时日志抓取相关变量
        self.realtime_process = None
        self.realtime_stop_event = None
        self.realtime_thread = None
        self.log_file_handle = None  # 用于保存日志文件句柄
    
    def create_log_tab(self):
        # 创建左侧选择区域和右侧输出区域的分隔窗格
        log_paned = ttk.PanedWindow(self.log_tab, orient=tk.HORIZONTAL)
        log_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧选择区域
        left_frame = ttk.Frame(log_paned)
        log_paned.add(left_frame, weight=1)
        
        # 右侧输出区域
        right_frame = ttk.Frame(log_paned)
        log_paned.add(right_frame, weight=2)
        
        # 创建右侧的主要内容区域和底部按钮区域
        # 主要内容区域（用于显示结果）
        result_frame = ttk.Frame(right_frame)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        
        # 底部按钮区域（固定在底部）
        bottom_button_frame = ttk.Frame(right_frame)
        bottom_button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 在左侧框架中创建选择控件
        # 日志文件选择（放在最上面）
        log_file_frame = ttk.LabelFrame(left_frame, text="日志文件")
        log_file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.log_file_var = tk.StringVar()
        log_file_entry = ttk.Entry(log_file_frame, textvariable=self.log_file_var)
        log_file_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=5, pady=5)
        
        browse_button = ttk.Button(log_file_frame, text="浏览...", command=self.browse_log_file)
        browse_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 日志筛选框
        log_type_frame = ttk.LabelFrame(left_frame, text="日志筛选")
        log_type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.log_type_var = tk.StringVar(value="audio")
        ttk.Radiobutton(log_type_frame, text="Audio相关日志", variable=self.log_type_var, 
                       value="audio").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Radiobutton(log_type_frame, text="Display相关日志", variable=self.log_type_var, 
                       value="display").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Radiobutton(log_type_frame, text="所有关键词", variable=self.log_type_var, 
                       value="all").pack(anchor=tk.W, padx=10, pady=2)
        
        # 将按钮放入日志筛选框中
        self.analyze_button = ttk.Button(log_type_frame, text="开始筛选", command=self.analyze_log)
        self.analyze_button.pack(fill=tk.X, padx=5, pady=5)
        
        edit_keywords_button = ttk.Button(log_type_frame, text="编辑关键词", command=self.edit_keywords)
        edit_keywords_button.pack(fill=tk.X, padx=5, pady=2)
        
        # AI分析功能
        ai_frame = ttk.LabelFrame(left_frame, text="AI智能分析")
        ai_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # AI分析类型选择
        self.ai_analysis_type_var = tk.StringVar(value="comprehensive")
        ttk.Radiobutton(ai_frame, text="综合分析", variable=self.ai_analysis_type_var, 
                       value="comprehensive").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Radiobutton(ai_frame, text="错误分析", variable=self.ai_analysis_type_var, 
                       value="error_analysis").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Radiobutton(ai_frame, text="性能分析", variable=self.ai_analysis_type_var, 
                       value="performance").pack(anchor=tk.W, padx=10, pady=2)
        ttk.Radiobutton(ai_frame, text="问题总结", variable=self.ai_analysis_type_var, 
                       value="summary").pack(anchor=tk.W, padx=10, pady=2)
        
        # AI分析按钮
        self.ai_analyze_button = ttk.Button(ai_frame, text="AI分析日志", command=self.ai_analyze_log)
        self.ai_analyze_button.pack(fill=tk.X, padx=5, pady=5)
        
        # API连接测试按钮
        test_api_button = ttk.Button(ai_frame, text="测试API连接", command=self.test_ai_api)
        test_api_button.pack(fill=tk.X, padx=5, pady=2)
        

        
        # 在右侧框架中创建输出区域
        # 分析结果框（使用之前创建的result_frame）
        result_labelframe = ttk.LabelFrame(result_frame, text="分析结果")
        result_labelframe.pack(fill=tk.BOTH, expand=True)
        
        # 创建两个不同的输出组件
        # 1. 日志筛选结果的高亮文本组件（支持横向滚动）
        text_frame = ttk.Frame(result_labelframe)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_filter_text = tk.Text(text_frame, wrap=tk.NONE, state="disabled")
        
        # 添加滚动条
        v_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.log_filter_text.yview)
        h_scrollbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.log_filter_text.xview)
        
        self.log_filter_text.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # 布局滚动条和文本框
        self.log_filter_text.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # 配置高亮标签样式
        self.log_filter_text.tag_configure("highlight_red", background="#ffcccc", foreground="#cc0000")
        self.log_filter_text.tag_configure("highlight_blue", background="#ccccff", foreground="#0000cc")
        self.log_filter_text.tag_configure("highlight_green", background="#ccffcc", foreground="#00cc00")
        self.log_filter_text.tag_configure("highlight_yellow", background="#ffffcc", foreground="#cccc00")
        self.log_filter_text.tag_configure("highlight_purple", background="#ffccff", foreground="#cc00cc")
        
        # 2. AI分析结果的markdown组件
        if MARKDOWN_AVAILABLE:
            self.markdown_converter = Markdown()
            self.ai_analysis_text = HTMLLabel(result_labelframe, html="<p>准备显示AI分析结果...</p>")
        else:
            self.ai_analysis_text = scrolledtext.ScrolledText(result_labelframe, wrap=tk.WORD)
            self.ai_analysis_text.configure(state="disabled")
        
        # 默认显示日志筛选组件
        self.current_display_mode = "log_filter"  # "log_filter" 或 "ai_analysis"
        # text_frame已经通过pack显示，无需再次pack log_filter_text
        
        # 保存text_frame引用以便切换显示模式
        self.log_filter_frame = text_frame
        
        # 保持向后兼容性和原始引用
        self.log_output_text = self.log_filter_text
        self.original_log_output_text = self.ai_analysis_text
        
        # 在底部按钮区域创建按钮（固定在底部）
        save_button = ttk.Button(bottom_button_frame, text="保存日志筛选结果", command=self.save_log_results)
        save_button.pack(side=tk.LEFT, padx=5)
        
        save_ai_button = ttk.Button(bottom_button_frame, text="保存AI分析", command=self.save_ai_analysis)
        save_ai_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = ttk.Button(bottom_button_frame, text="清除输出", command=self.clear_log_output)
        clear_button.pack(side=tk.RIGHT, padx=5)
    
    def on_module_change(self):
        self.update_command_types()
        self.update_commands()
    
    def update_command_types(self):
        # 清除现有的命令类型选项
        for widget in self.cmd_type_frame.winfo_children():
            widget.destroy()
        
        # 获取当前模块的命令类型
        module = self.module_var.get()
        command_types = self.command_manager.get_command_types(module)
        
        if command_types:
            self.cmd_type_var.set(command_types[0])
        else:
            self.cmd_type_var.set("")
        
        # 添加命令类型选项
        type_names = {
            'single_command': '单条命令',
            'combination_command': '组合命令'
        }
        
        for cmd_type in command_types:
            ttk.Radiobutton(self.cmd_type_frame, text=type_names.get(cmd_type, cmd_type), 
                           variable=self.cmd_type_var, value=cmd_type, 
                           command=self.update_commands).pack(anchor=tk.W, padx=10, pady=2)
    
    def update_commands(self):
        # 清除命令列表
        self.cmd_listbox.delete(0, tk.END)
        
        # 获取当前模块和命令类型的命令
        module = self.module_var.get()
        cmd_type = self.cmd_type_var.get()
        
        if not module or not cmd_type:
            return
        
        commands = self.command_manager.get_commands(module, cmd_type)
        
        # 按命令ID排序
        sorted_commands = sorted(commands.items(), key=lambda x: int(x[0]))
        
        # 添加命令到列表框
        for cmd_id, cmd_info in sorted_commands:
            self.cmd_listbox.insert(tk.END, f"{cmd_id}. {cmd_info['help']}")
        
        # 如果有命令，选择第一个
        if self.cmd_listbox.size() > 0:
            self.cmd_listbox.selection_set(0)
            # 确保cmd_desc_text已经初始化后再调用
            if hasattr(self, 'cmd_desc_text'):
                self.on_command_select(None)
        else:
            # 如果没有命令，清空当前选中命令显示
            if hasattr(self, 'selected_cmd_var'):
                self.selected_cmd_var.set("未选择命令")
    
    def on_command_select(self, event):
        # 获取选中的命令
        selection = self.cmd_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        cmd_text = self.cmd_listbox.get(index)
        cmd_id = cmd_text.split(".")[0]
        
        # 获取命令信息
        module = self.module_var.get()
        cmd_type = self.cmd_type_var.get()
        commands = self.command_manager.get_commands(module, cmd_type)
        
        if cmd_id in commands:
            cmd_info = commands[cmd_id]
            
            # 更新当前选中命令显示
            self.selected_cmd_var.set(f"{cmd_id}. {cmd_info['help']}")
        else:
            # 如果没有选中命令或命令信息不存在
            self.selected_cmd_var.set("未选择命令")
    
    def execute_command(self):
        # 获取选中的命令
        selection = self.cmd_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个命令")
            return
        
        index = selection[0]
        cmd_text = self.cmd_listbox.get(index)
        cmd_id = cmd_text.split(".")[0]
        
        # 获取命令信息
        module = self.module_var.get()
        cmd_type = self.cmd_type_var.get()
        commands = self.command_manager.get_commands(module, cmd_type)
        
        if cmd_id in commands:
            cmd_info = commands[cmd_id]
            bat_path = cmd_info['bat_path']
            
            # 清除输出
            self.clear_output()
            
            # 更新状态
            self.status_label.config(text=f"正在执行: {cmd_info['help']}")
            
            # 在执行结果区域显示命令信息和执行结果
            self.cmd_output_text.configure(state="normal")
            self.cmd_output_text.delete(1.0, tk.END)
            self.cmd_output_text.insert(tk.END, f"正在执行: {cmd_info['help']}\n")
            self.cmd_output_text.insert(tk.END, f"命令文件: {bat_path}\n")
            self.cmd_output_text.insert(tk.END, "-" * 60 + "\n")
            self.cmd_output_text.configure(state="disabled")
            
            # 重定向标准输出到文本框
            redirect = RedirectText(self.cmd_output_text)
            old_stdout = sys.stdout
            sys.stdout = redirect
            
            # 执行命令
            
            # 在新线程中执行命令
            def run_command():
                try:
                    # 在GUI模式下执行命令，传入gui_mode=True
                    return_code, output = self.command_executor.execute_command(bat_path, gui_mode=True)
                    
                    # 恢复标准输出
                    sys.stdout = old_stdout
                    redirect.stop_updating()
                    
                    # 更新UI
                    self.after(100, lambda: self.update_command_output(return_code, output))
                except Exception as e:
                    sys.stdout = old_stdout
                    redirect.stop_updating()
                    self.after(100, lambda: self.update_command_output(1, f"执行命令时出错: {str(e)}"))
            
            threading.Thread(target=run_command, daemon=True).start()
    

    
    def update_command_output(self, return_code, output):
        self.cmd_output_text.configure(state="normal")
        self.cmd_output_text.insert(tk.END, "\n" + "-" * 60 + "\n")
        self.cmd_output_text.insert(tk.END, f"命令执行完成，返回码: {return_code}\n")
        self.cmd_output_text.configure(state="disabled")
        
        # 更新状态
        self.status_label.config(text="就绪")
    
    def _switch_to_log_filter_mode(self):
        """切换到日志筛选显示模式"""
        if self.current_display_mode != "log_filter":
            # 隐藏AI分析组件
            if hasattr(self, 'ai_analysis_text'):
                self.ai_analysis_text.pack_forget()
            
            # 显示日志筛选组件框架
            if hasattr(self, 'log_filter_frame'):
                self.log_filter_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.current_display_mode = "log_filter"
            
            # 更新向后兼容性引用
            self.log_output_text = self.log_filter_text
    
    def _switch_to_ai_analysis_mode(self):
        """切换到AI分析显示模式"""
        if self.current_display_mode != "ai_analysis":
            # 隐藏日志筛选组件框架
            if hasattr(self, 'log_filter_frame'):
                self.log_filter_frame.pack_forget()
            
            # 显示AI分析组件
            if hasattr(self, 'original_log_output_text'):
                self.original_log_output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.current_display_mode = "ai_analysis"
            
            # 恢复原始的log_output_text引用
            if hasattr(self, 'original_log_output_text'):
                self.log_output_text = self.original_log_output_text
    
    def _insert_highlighted_content(self, content_lines):
        """插入高亮内容到文本组件"""
        # 获取当前选择的日志类型对应的关键词
        keywords = self._get_current_keywords()
        
        # 定义高亮颜色循环
        highlight_colors = ["highlight_red", "highlight_blue", "highlight_green", "highlight_yellow", "highlight_purple"]
        
        for line in content_lines:
            # 获取插入前的文本末尾位置
            line_start = self.log_filter_text.index(tk.END + "-1c")
            self.log_filter_text.insert(tk.END, f"{line}\n")
            
            # 为每个关键词应用不同颜色的高亮
            for i, keyword in enumerate(keywords):
                color_tag = highlight_colors[i % len(highlight_colors)]
                self._highlight_keyword_in_line(line, keyword, line_start, color_tag)
    
    def _get_current_keywords(self):
        """获取当前选择的日志类型对应的关键词"""
        log_type = self.log_type_var.get()
        keywords = []
        
        try:
            if log_type == "audio":
                audio_path = resource_manager.get_read_path("keyword/audio.txt")
                with open(audio_path, "r", encoding="utf-8") as f:
                    keywords = [line.strip() for line in f if line.strip()]
            elif log_type == "display":
                display_path = resource_manager.get_read_path("keyword/display.txt")
                with open(display_path, "r", encoding="utf-8") as f:
                    keywords = [line.strip() for line in f if line.strip()]
            elif log_type == "all":
                # 合并所有关键词
                try:
                    audio_path = resource_manager.get_read_path("keyword/audio.txt")
                    with open(audio_path, "r", encoding="utf-8") as f:
                        keywords.extend([line.strip() for line in f if line.strip()])
                except:
                    pass
                try:
                    display_path = resource_manager.get_read_path("keyword/display.txt")
                    with open(display_path, "r", encoding="utf-8") as f:
                        keywords.extend([line.strip() for line in f if line.strip()])
                except:
                    pass
        except Exception as e:
            print(f"读取关键词文件出错: {e}")
        
        return keywords
    
    def _highlight_keyword_in_line(self, line, keyword, line_start, color_tag):
        """在指定行中高亮关键词"""
        line_lower = line.lower()
        keyword_lower = keyword.lower()
        
        start_pos = 0
        while True:
            pos = line_lower.find(keyword_lower, start_pos)
            if pos == -1:
                break
            
            # 计算在文本组件中的位置
            start_index = f"{line_start.split('.')[0]}.{int(line_start.split('.')[1]) + pos}"
            end_index = f"{line_start.split('.')[0]}.{int(line_start.split('.')[1]) + pos + len(keyword)}"
            
            # 应用高亮标签
            self.log_filter_text.tag_add(color_tag, start_index, end_index)
            
            start_pos = pos + 1
    
    def clear_output(self):
        # 清除执行结果
        self.cmd_output_text.configure(state="normal")
        self.cmd_output_text.delete(1.0, tk.END)
        self.cmd_output_text.configure(state="disabled")
    
    def browse_log_file(self):
        file_path = filedialog.askopenfilename(
            title="选择日志文件",
            filetypes=[("所有文件", "*.*"), ("日志文件", "*.log *.txt")]
        )
        if file_path:
            self.log_file_var.set(file_path)
    
    def analyze_log(self):
        log_path = self.log_file_var.get()
        if not log_path:
            messagebox.showwarning("警告", "请先选择日志文件")
            return
        
        if not os.path.exists(log_path):
            messagebox.showerror("错误", f"文件 {log_path} 不存在")
            return
        
        log_type = self.log_type_var.get()
        
        # 清除输出
        self.clear_log_output()
        
        # 更新状态
        self.status_label.config(text=f"正在分析{log_type}日志文件: {log_path}")
        
        # 清除分析结果区域
        self.log_output_text.configure(state="normal")
        self.log_output_text.delete(1.0, tk.END)
        
        # 显示分析开始信息
        self.log_output_text.insert(tk.END, f"正在分析{log_type}日志文件，请稍候...\n")
        self.log_output_text.configure(state="disabled")
        
        # 在新线程中分析日志（不重定向输出）
        def run_analysis():
            try:
                result = self.log_analyzer.analyze_log(log_path, log_type)
                
                # 更新UI
                self.after(100, lambda: self.update_log_output(result))
            except Exception as e:
                self.after(100, lambda: self.update_log_output({'files': 0, 'matched_lines': 0, 'error': str(e)}))
        
        threading.Thread(target=run_analysis, daemon=True).start()
    
    def update_log_output(self, result):
        # 清除分析进度信息
        self.log_output_text.configure(state="normal")
        self.log_output_text.delete(1.0, tk.END)
        self.log_output_text.configure(state="disabled")
        
        # 切换到日志筛选显示模式
        self._switch_to_log_filter_mode()
        
        # 使用高亮文本组件显示日志筛选结果
        self.log_filter_text.configure(state="normal")
        self.log_filter_text.delete(1.0, tk.END)  # 清除之前的内容
        
        # 添加分析完成信息
        if 'error' in result:
            self.log_filter_text.insert(tk.END, f"❌ 分析出错: {result['error']}\n\n")
        else:
            self.log_filter_text.insert(tk.END, f"✅ 日志筛选完成\n匹配结果: 匹配到 {result['matched_lines']} 行\n\n")
            
            # 显示匹配的行内容并高亮关键词
            if 'matched_content' in result and result['matched_content']:
                self.log_filter_text.insert(tk.END, "📋 匹配内容:\n")
                self._insert_highlighted_content(result['matched_content'])
            elif result['matched_lines'] > 0:
                self.log_filter_text.insert(tk.END, "💾 匹配的内容已保存到处理后的日志文件中\n")
        
        self.log_filter_text.configure(state="disabled")
        
        # 更新状态
        self.status_label.config(text="就绪")
    
    def clear_log_output(self):
        """清除日志输出"""
        # 检查当前显示模式并清除对应的组件
        if hasattr(self, 'current_display_mode'):
            if self.current_display_mode == 'log_filter':
                # 清除日志筛选文本组件
                self.log_filter_text.configure(state="normal")
                self.log_filter_text.delete(1.0, tk.END)
                self.log_filter_text.configure(state="disabled")
            else:
                # 清除AI分析结果组件
                if MARKDOWN_AVAILABLE and hasattr(self, 'markdown_converter'):
                    self.log_output_text.set_html("")
                else:
                    self.log_output_text.configure(state="normal")
                    self.log_output_text.delete(1.0, tk.END)
                    self.log_output_text.configure(state="disabled")
        else:
            # 默认清除AI分析结果组件（向后兼容）
            if MARKDOWN_AVAILABLE and hasattr(self, 'markdown_converter'):
                self.log_output_text.set_html("")
            else:
                self.log_output_text.configure(state="normal")
                self.log_output_text.delete(1.0, tk.END)
                self.log_output_text.configure(state="disabled")
    
    def ai_analyze_log(self):
        """使用AI分析日志，支持超长日志的智能分段处理"""
        log_file = self.log_file_var.get().strip()
        if not log_file:
            messagebox.showwarning("警告", "请先选择日志文件")
            return
        
        if not os.path.exists(log_file):
            messagebox.showerror("错误", f"日志文件不存在: {log_file}")
            return
        
        # 获取分析类型
        analysis_type = self.ai_analysis_type_var.get()
        
        # 清除输出
        self.clear_log_output()
        
        # 更新状态
        self.status_label.config(text="正在进行AI分析...")
        self.ai_analyze_button.config(state="disabled")
        
        # 在新线程中执行AI分析
        def ai_analysis_thread():
            try:
                # 显示开始分析的提示
                self.after(0, lambda: self._update_ai_progress("正在读取日志文件..."))
                
                # 读取日志文件内容
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                
                # 显示日志长度信息和处理策略
                content_length = len(log_content)
                if content_length > 10000:
                    progress_msg = f"检测到超长日志（{content_length:,} 字符）\n启用智能分段处理机制...\n正在进行AI分析，请耐心等待..."
                    self.after(0, lambda: self._update_ai_progress(progress_msg))
                else:
                    progress_msg = f"日志长度：{content_length:,} 字符\n正在进行AI分析..."
                    self.after(0, lambda: self._update_ai_progress(progress_msg))
                
                # 调用AI分析（现在支持自动分段处理）
                result = self.log_analyzer.analyze_with_ai(log_content, analysis_type)
                
                # 在主线程中更新UI
                self.after(0, lambda: self.update_ai_analysis_result(result, analysis_type))
                
            except FileNotFoundError:
                error_msg = "错误：日志文件不存在，请重新选择文件"
                self.after(0, lambda: self.update_ai_analysis_result(error_msg, analysis_type))
            except PermissionError:
                error_msg = "错误：没有权限读取日志文件"
                self.after(0, lambda: self.update_ai_analysis_result(error_msg, analysis_type))
            except UnicodeDecodeError:
                error_msg = "错误：日志文件编码格式不支持，请检查文件格式"
                self.after(0, lambda: self.update_ai_analysis_result(error_msg, analysis_type))
            except Exception as e:
                error_msg = f"AI分析失败: {str(e)}\n\n请检查：\n1. 网络连接是否正常\n2. API配置是否正确\n3. 日志文件是否完整"
                self.after(0, lambda: self.update_ai_analysis_result({"error": error_msg}, analysis_type))
        
        # 启动分析线程
        threading.Thread(target=ai_analysis_thread, daemon=True).start()
    
    def _update_ai_progress(self, message):
        """更新AI分析进度显示"""
        try:
            # 切换到AI分析模式以显示进度
            self._switch_to_ai_analysis_mode()
            
            # 在AI分析结果区域显示进度信息
            if hasattr(self, 'ai_result_text'):
                self.ai_result_text.delete(1.0, tk.END)
                self.ai_result_text.insert(tk.END, message)
                self.ai_result_text.see(tk.END)
                self.ai_result_text.update_idletasks()
        except Exception as e:
            print(f"更新进度显示失败: {e}")
    
    def update_ai_analysis_result(self, result, analysis_type):
        """更新AI分析结果"""
        # 切换到AI分析模式
        self._switch_to_ai_analysis_mode()
        
        if MARKDOWN_AVAILABLE and hasattr(self, 'markdown_converter'):
            # 使用markdown格式显示AI分析结果
            type_names = {
                "comprehensive": "综合分析",
                "error_analysis": "错误分析", 
                "performance": "性能分析",
                "summary": "问题总结"
            }
            
            markdown_content = ""
            
            # 添加分析类型标题
            analysis_name = type_names.get(analysis_type, analysis_type)
            markdown_content += f"\n## 🤖 AI {analysis_name} 结果\n\n"
            
            if isinstance(result, dict) and "error" in result:
                markdown_content += f"### ❌ 分析出错\n\n**错误信息:** {result['error']}\n\n"
            else:
                # 处理新的分析结果格式
                if isinstance(result, dict):
                    # 显示分析结果
                    if "analysis" in result:
                        markdown_content += f"### 📊 分析结果\n\n{result['analysis']}\n\n"
                    
                    if "suggestions" in result:
                        markdown_content += f"### 💡 建议\n\n{result['suggestions']}\n\n"
                    
                    if "summary" in result:
                        markdown_content += f"### 📝 总结\n\n{result['summary']}\n\n"
                    
                    # 处理分段分析结果
                    if "segment_count" in result:
                        markdown_content += f"### 📋 分析统计\n\n"
                        markdown_content += f"- **分段数量:** {result['segment_count']}\n"
                        if "total_length" in result:
                            markdown_content += f"- **总长度:** {result['total_length']} 字符\n"
                        markdown_content += "\n"
                    
                    # 显示详细分析内容
                    if "detailed_analysis" in result:
                        markdown_content += f"### 🔍 详细分析\n\n{result['detailed_analysis']}\n\n"
                    
                    # 显示关键发现
                    if "key_findings" in result:
                        markdown_content += f"### 🔑 关键发现\n\n{result['key_findings']}\n\n"
                    
                    # 显示处理信息
                    if "processing_info" in result:
                        markdown_content += f"### ℹ️ 处理信息\n\n{result['processing_info']}\n\n"
                
                # 如果结果是字符串格式，直接显示
                elif isinstance(result, str):
                    markdown_content += f"### 📋 分析内容\n\n```\n{result}\n```\n\n"
            
            # 获取当前内容并追加新内容
            try:
                current_html = self.log_output_text.get_html()
                if current_html and current_html.strip():
                    # 在现有内容后添加分隔线和新内容
                    markdown_content = "\n---\n" + markdown_content
                    new_html = self.markdown_converter.convert(markdown_content)
                    combined_html = current_html + new_html
                    self.log_output_text.set_html(combined_html)
                else:
                    # 没有现有内容，直接设置
                    html_content = self.markdown_converter.convert(markdown_content)
                    self.log_output_text.set_html(html_content)
            except:
                # 如果获取当前内容失败，直接设置新内容
                html_content = self.markdown_converter.convert(markdown_content)
                self.log_output_text.set_html(html_content)
        else:
            # 使用原来的ScrolledText方式
            self.log_output_text.configure(state="normal")
            
            # 添加分析类型标题
            type_names = {
                "comprehensive": "综合分析",
                "error_analysis": "错误分析", 
                "performance": "性能分析",
                "summary": "问题总结"
            }
            
            self.log_output_text.insert(tk.END, f"=== AI {type_names.get(analysis_type, analysis_type)} 结果 ===\n\n")
            
            if isinstance(result, dict) and "error" in result:
                self.log_output_text.insert(tk.END, f"错误: {result['error']}\n")
            else:
                # 处理新的分析结果格式
                if isinstance(result, dict):
                    # 显示分析结果
                    if "analysis" in result:
                        self.log_output_text.insert(tk.END, f"分析结果:\n{result['analysis']}\n\n")
                    
                    if "suggestions" in result:
                        self.log_output_text.insert(tk.END, f"建议:\n{result['suggestions']}\n\n")
                    
                    if "summary" in result:
                        self.log_output_text.insert(tk.END, f"总结:\n{result['summary']}\n\n")
                    
                    # 处理分段分析结果
                    if "segment_count" in result:
                        self.log_output_text.insert(tk.END, f"分析统计:\n")
                        self.log_output_text.insert(tk.END, f"- 分段数量: {result['segment_count']}\n")
                        if "total_length" in result:
                            self.log_output_text.insert(tk.END, f"- 总长度: {result['total_length']} 字符\n")
                        self.log_output_text.insert(tk.END, "\n")
                    
                    # 显示详细分析内容
                    if "detailed_analysis" in result:
                        self.log_output_text.insert(tk.END, f"详细分析:\n{result['detailed_analysis']}\n\n")
                    
                    # 显示关键发现
                    if "key_findings" in result:
                        self.log_output_text.insert(tk.END, f"关键发现:\n{result['key_findings']}\n\n")
                    
                    # 显示处理信息
                    if "processing_info" in result:
                        self.log_output_text.insert(tk.END, f"处理信息:\n{result['processing_info']}\n\n")
                
                # 如果结果是字符串格式，直接显示
                elif isinstance(result, str):
                    self.log_output_text.insert(tk.END, result)
            
            self.log_output_text.configure(state="disabled")
        
        # 恢复按钮状态
        self.ai_analyze_button.config(state="normal")
        self.status_label.config(text="AI分析完成")
    
    def test_ai_api(self):
        """测试AI API连接"""
        self.status_label.config(text="正在测试API连接...")
        
        def test_thread():
            result = self.log_analyzer.test_ai_connection()
            self.after(0, lambda: self.show_api_test_result(result))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def show_api_test_result(self, result):
        """显示API测试结果"""
        if result["status"] == "success":
            messagebox.showinfo("API测试", f"连接成功!\n{result['message']}")
            self.status_label.config(text="API连接正常")
        else:
            messagebox.showerror("API测试", f"连接失败!\n{result['message']}")
            self.status_label.config(text="API连接失败")
    
    def save_log_results(self):
        # 获取日志输出内容
        content = self.log_output_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("警告", "没有可保存的内容")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存分析结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", f"分析结果已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件时出错: {str(e)}")
    
    def save_ai_analysis(self):
        """保存AI分析结果"""
        # 获取日志输出内容
        content = self.log_output_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("警告", "没有可保存的AI分析内容")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="保存AI分析结果",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", f"AI分析结果已保存到 {file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存AI分析结果时出错: {str(e)}")
    
    def edit_keywords(self):
        # 创建关键词编辑对话框
        keyword_dialog = tk.Toplevel(self)
        keyword_dialog.title("编辑关键词")
        keyword_dialog.geometry("600x700")  # 增加弹窗大小
        keyword_dialog.minsize(600, 700)  # 设置最小大小
        keyword_dialog.transient(self)
        keyword_dialog.grab_set()
        
        # 创建选项卡控件
        keyword_notebook = ttk.Notebook(keyword_dialog)
        keyword_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 音频关键词选项卡
        audio_frame = ttk.Frame(keyword_notebook)
        keyword_notebook.add(audio_frame, text="音频关键词")
        
        # 添加说明标签
        audio_label = ttk.Label(audio_frame, text="每行一个关键词，可直接编辑、删除或添加")
        audio_label.pack(anchor=tk.W, padx=5, pady=5)
        
        audio_text = scrolledtext.ScrolledText(audio_frame)
        audio_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 显示关键词选项卡
        display_frame = ttk.Frame(keyword_notebook)
        keyword_notebook.add(display_frame, text="显示关键词")
        
        # 添加说明标签
        display_label = ttk.Label(display_frame, text="每行一个关键词，可直接编辑、删除或添加")
        display_label.pack(anchor=tk.W, padx=5, pady=5)
        
        display_text = scrolledtext.ScrolledText(display_frame)
        display_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加载关键词
        try:
            # 音频关键词
            audio_path = resource_manager.get_read_path('keyword/audio.txt')
            if os.path.exists(audio_path):
                with open(audio_path, 'r', encoding='utf-8') as f:
                    audio_text.insert(tk.END, f.read())
            
            # 显示关键词
            display_path = resource_manager.get_read_path('keyword/display.txt')
            if os.path.exists(display_path):
                with open(display_path, 'r', encoding='utf-8') as f:
                    display_text.insert(tk.END, f.read())
        except Exception as e:
            messagebox.showerror("错误", f"加载关键词时出错: {str(e)}")
        
        # 按钮区域
        button_frame = ttk.Frame(keyword_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_keywords():
            try:
                # 保存音频关键词到可写路径
                audio_content = audio_text.get(1.0, tk.END).strip()
                audio_path = resource_manager.get_write_path('keyword/audio.txt')
                with open(audio_path, 'w', encoding='utf-8') as f:
                    f.write(audio_content)
                
                # 保存显示关键词到可写路径
                display_content = display_text.get(1.0, tk.END).strip()
                display_path = resource_manager.get_write_path('keyword/display.txt')
                with open(display_path, 'w', encoding='utf-8') as f:
                    f.write(display_content)
                
                # 重新加载关键词
                self.log_analyzer._load_keywords()
                
                messagebox.showinfo("成功", "关键词已保存")
                keyword_dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"保存关键词时出错: {str(e)}")
        
        # 保存和取消按钮
        ttk.Button(button_frame, text="保存", command=save_keywords).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=keyword_dialog.destroy).pack(side=tk.RIGHT, padx=5)
    

    
    def show_edit_command_dialog(self):
        """显示整合的编辑命令对话框"""
        # 创建编辑命令对话框
        edit_dialog = tk.Toplevel(self)
        edit_dialog.title("编辑命令")
        edit_dialog.geometry("900x700")
        edit_dialog.minsize(900, 700)
        edit_dialog.transient(self)
        edit_dialog.grab_set()
        
        # 创建左右分隔的主框架
        main_frame = ttk.Frame(edit_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧选择区域
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 右侧编辑区域
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 模块选择
        module_frame = ttk.LabelFrame(left_frame, text="模块")
        module_frame.pack(fill=tk.X, pady=5)
        
        edit_module_var = tk.StringVar(value="Audio")
        ttk.Radiobutton(module_frame, text="Audio", variable=edit_module_var, 
                       value="Audio", command=lambda: update_command_types()).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(module_frame, text="Display", variable=edit_module_var, 
                       value="Display", command=lambda: update_command_types()).pack(anchor=tk.W, padx=5, pady=2)
        
        # 命令类型选择
        type_frame = ttk.LabelFrame(left_frame, text="命令类型")
        type_frame.pack(fill=tk.X, pady=5)
        
        edit_type_var = tk.StringVar(value="single_command")
        ttk.Radiobutton(type_frame, text="单条命令", variable=edit_type_var, 
                       value="single_command", command=lambda: update_commands()).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(type_frame, text="组合命令", variable=edit_type_var, 
                       value="combination_command", command=lambda: update_commands()).pack(anchor=tk.W, padx=5, pady=2)
        
        # 命令列表
        cmd_frame = ttk.LabelFrame(left_frame, text="命令列表")
        cmd_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        edit_cmd_listbox = tk.Listbox(cmd_frame, height=12)
        edit_cmd_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        edit_cmd_listbox.bind('<<ListboxSelect>>', lambda e: load_command_for_edit())
        
        # 左侧按钮区域
        left_button_frame = ttk.Frame(left_frame)
        left_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(left_button_frame, text="新增命令", command=lambda: show_add_command_dialog()).pack(fill=tk.X, pady=2)
        ttk.Button(left_button_frame, text="删除命令", command=lambda: delete_selected_command()).pack(fill=tk.X, pady=2)
        
        # 右侧编辑区域
        # 命令描述编辑
        desc_frame = ttk.LabelFrame(right_frame, text="命令描述")
        desc_frame.pack(fill=tk.X, pady=5)
        
        edit_desc_text = scrolledtext.ScrolledText(desc_frame, height=6, wrap=tk.WORD)
        edit_desc_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 脚本内容编辑
        content_frame = ttk.LabelFrame(right_frame, text="脚本内容")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        edit_content_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD)
        edit_content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧按钮区域
        right_button_frame = ttk.Frame(right_frame)
        right_button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(right_button_frame, text="保存修改", command=lambda: save_command_changes()).pack(side=tk.LEFT, padx=5)
        ttk.Button(right_button_frame, text="关闭", command=edit_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 存储当前编辑的命令信息
        current_edit_cmd = {"module": None, "cmd_type": None, "cmd_id": None}
        
        def update_command_types():
            """更新命令类型"""
            update_commands()
        
        def update_commands():
            """更新命令列表"""
            edit_cmd_listbox.delete(0, tk.END)
            module = edit_module_var.get()
            cmd_type = edit_type_var.get()
            
            commands = self.command_manager.get_commands(module, cmd_type)
            for cmd_id in sorted(commands.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                edit_cmd_listbox.insert(tk.END, f"{cmd_id}: {commands[cmd_id]['help'][:50]}...")
            
            # 清空编辑区域
            edit_desc_text.delete(1.0, tk.END)
            edit_content_text.delete(1.0, tk.END)
            current_edit_cmd.update({"module": None, "cmd_type": None, "cmd_id": None})
        
        def load_command_for_edit():
            """加载选中命令到编辑区域"""
            selection = edit_cmd_listbox.curselection()
            if not selection:
                return
            
            selected_text = edit_cmd_listbox.get(selection[0])
            cmd_id = selected_text.split(':')[0]
            
            module = edit_module_var.get()
            cmd_type = edit_type_var.get()
            
            cmd_info = self.command_manager.get_command_info(module, cmd_type, cmd_id)
            if cmd_info:
                # 更新当前编辑命令信息
                current_edit_cmd.update({"module": module, "cmd_type": cmd_type, "cmd_id": cmd_id})
                
                # 加载描述
                edit_desc_text.delete(1.0, tk.END)
                edit_desc_text.insert(1.0, cmd_info['help'])
                
                # 加载脚本内容
                edit_content_text.delete(1.0, tk.END)
                try:
                    with open(cmd_info['bat_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    edit_content_text.insert(1.0, content)
                except Exception as e:
                    edit_content_text.insert(1.0, f"无法读取脚本文件: {str(e)}")
        
        def save_command_changes():
            """保存命令修改"""
            if not current_edit_cmd["cmd_id"]:
                messagebox.showwarning("警告", "请先选择要修改的命令")
                return
            
            # 获取修改后的内容
            new_description = edit_desc_text.get(1.0, tk.END).strip()
            new_script = edit_content_text.get(1.0, tk.END).strip()
            
            if not new_description:
                messagebox.showwarning("警告", "命令描述不能为空")
                return
            
            if not new_script:
                messagebox.showwarning("警告", "脚本内容不能为空")
                return
            
            # 直接保存，无需确认
            try:
                # 获取命令目录
                cmd_dir = os.path.join(self.base_path, current_edit_cmd["module"], 
                                     current_edit_cmd["cmd_type"], current_edit_cmd["cmd_id"])
                
                # 保存描述文件
                with open(os.path.join(cmd_dir, "help.txt"), 'w', encoding='utf-8') as f:
                    f.write(new_description)
                
                # 保存脚本文件
                bat_files = [f for f in os.listdir(cmd_dir) if f.endswith('.bat')]
                if bat_files:
                    bat_path = os.path.join(cmd_dir, bat_files[0])
                    with open(bat_path, 'w', encoding='utf-8') as f:
                        f.write(new_script)
                
                messagebox.showinfo("成功", "命令修改已保存")
                
                # 手动更新列表中的当前项目，避免清空编辑区域
                current_selection = edit_cmd_listbox.curselection()
                if current_selection:
                    # 更新列表框中当前项的显示文本
                    cmd_id = current_edit_cmd["cmd_id"]
                    new_display_text = f"{cmd_id}: {new_description[:50]}..."
                    edit_cmd_listbox.delete(current_selection[0])
                    edit_cmd_listbox.insert(current_selection[0], new_display_text)
                    edit_cmd_listbox.selection_set(current_selection[0])
                
                # 如果当前主界面显示的是相同模块和类型，也更新主界面
                if (current_edit_cmd["module"] == self.module_var.get() and 
                    current_edit_cmd["cmd_type"] == self.cmd_type_var.get()):
                    self.update_commands()
                
            except Exception as e:
                messagebox.showerror("错误", f"保存命令时出错: {str(e)}")
        
        def delete_selected_command():
            """删除选中的命令"""
            selection = edit_cmd_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请先选择要删除的命令")
                return
            
            selected_text = edit_cmd_listbox.get(selection[0])
            cmd_id = selected_text.split(':')[0]
            
            module = edit_module_var.get()
            cmd_type = edit_type_var.get()
            
            # 确认删除
            if messagebox.askyesno("确认删除", f"确定要删除命令 {cmd_id} 吗？\n\n删除后，该命令后面的所有命令编号将自动减一。"):
                success = self.command_manager.delete_command(module, cmd_type, cmd_id)
                if success:
                    # 更新命令列表
                    update_commands()
                    
                    # 如果当前主界面显示的是相同模块和类型，也更新主界面
                    if module == self.module_var.get() and cmd_type == self.cmd_type_var.get():
                        self.update_commands()
                else:
                    messagebox.showerror("错误", "删除命令失败")
        
        def show_add_command_dialog():
            """显示添加命令对话框"""
            # 创建添加命令子对话框
            add_dialog = tk.Toplevel(edit_dialog)
            add_dialog.title("添加命令")
            add_dialog.geometry("600x600")
            add_dialog.minsize(600, 600)
            add_dialog.transient(edit_dialog)
            add_dialog.grab_set()
            
            # 命令信息框架
            info_frame = ttk.Frame(add_dialog)
            info_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 模块选择（默认使用当前选择的模块）
            module_frame = ttk.Frame(info_frame)
            module_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(module_frame, text="模块:").pack(side=tk.LEFT)
            
            add_module_var = tk.StringVar(value=edit_module_var.get())
            ttk.Radiobutton(module_frame, text="Audio", variable=add_module_var, 
                           value="Audio").pack(side=tk.LEFT, padx=10)
            ttk.Radiobutton(module_frame, text="Display", variable=add_module_var, 
                           value="Display").pack(side=tk.LEFT, padx=10)
            
            # 命令类型选择（默认使用当前选择的类型）
            type_frame = ttk.Frame(info_frame)
            type_frame.pack(fill=tk.X, pady=5)
            
            ttk.Label(type_frame, text="命令类型:").pack(side=tk.LEFT)
            
            add_type_var = tk.StringVar(value=edit_type_var.get())
            ttk.Radiobutton(type_frame, text="单条命令", variable=add_type_var, 
                           value="single_command").pack(side=tk.LEFT, padx=10)
            ttk.Radiobutton(type_frame, text="组合命令", variable=add_type_var, 
                           value="combination_command").pack(side=tk.LEFT, padx=10)
            
            # 命令描述
            desc_frame = ttk.LabelFrame(add_dialog, text="命令描述")
            desc_frame.pack(fill=tk.X, padx=10, pady=5)
            
            add_desc_text = scrolledtext.ScrolledText(desc_frame, height=5)
            add_desc_text.pack(fill=tk.X, padx=5, pady=5)
            
            # 批处理脚本
            script_frame = ttk.LabelFrame(add_dialog, text="批处理脚本")
            script_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            add_script_text = scrolledtext.ScrolledText(script_frame)
            add_script_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 按钮区域
            button_frame = ttk.Frame(add_dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def add_command():
                # 获取输入
                module = add_module_var.get()
                cmd_type = add_type_var.get()
                description = add_desc_text.get(1.0, tk.END).strip()
                script = add_script_text.get(1.0, tk.END).strip()
                
                # 验证输入
                if not description:
                    messagebox.showwarning("警告", "请输入命令描述")
                    return
                
                if not script:
                    messagebox.showwarning("警告", "请输入批处理脚本内容")
                    return
                
                # 自动生成命令ID
                cmd_path = os.path.join(self.base_path, module, cmd_type)
                if not os.path.exists(cmd_path):
                    os.makedirs(cmd_path, exist_ok=True)
                    cmd_id = "1"
                else:
                    # 获取现有目录中的最大ID值
                    existing_ids = [int(d) for d in os.listdir(cmd_path) if os.path.isdir(os.path.join(cmd_path, d)) and d.isdigit()]
                    cmd_id = str(max(existing_ids, default=0) + 1)
                
                # 创建命令目录
                cmd_dir = os.path.join(self.base_path, module, cmd_type, cmd_id)
                os.makedirs(cmd_dir, exist_ok=True)
                
                try:
                    # 保存help.txt
                    with open(os.path.join(cmd_dir, "help.txt"), 'w', encoding='utf-8') as f:
                        f.write(description)
                    
                    # 保存.bat文件
                    with open(os.path.join(cmd_dir, f"command_{cmd_id}.bat"), 'w', encoding='utf-8') as f:
                        f.write(script)
                    
                    messagebox.showinfo("成功", f"命令已添加到 {module}/{cmd_type}/{cmd_id}")
                    
                    # 更新编辑对话框的命令列表
                    if module == edit_module_var.get() and cmd_type == edit_type_var.get():
                        update_commands()
                    
                    # 更新主界面命令列表
                    if module == self.module_var.get() and cmd_type == self.cmd_type_var.get():
                        self.update_commands()
                    
                    add_dialog.destroy()
                except Exception as e:
                    messagebox.showerror("错误", f"添加命令时出错: {str(e)}")
            
            ttk.Button(button_frame, text="添加", command=add_command).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=add_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # 初始化
        update_commands()
    
    def show_delete_command_dialog(self):
        """显示删除命令对话框"""
        # 创建删除命令对话框
        delete_dialog = tk.Toplevel(self)
        delete_dialog.title("删除命令")
        delete_dialog.geometry("800x700")  # 拉长弹窗尺寸
        delete_dialog.minsize(800, 700)
        delete_dialog.transient(self)
        delete_dialog.grab_set()
        
        # 创建左右分隔的主框架
        main_frame = ttk.Frame(delete_dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧选择区域
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 右侧显示区域
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 模块选择
        module_frame = ttk.LabelFrame(left_frame, text="模块")
        module_frame.pack(fill=tk.X, pady=5)
        
        delete_module_var = tk.StringVar(value="Audio")
        ttk.Radiobutton(module_frame, text="Audio", variable=delete_module_var, 
                       value="Audio", command=lambda: update_command_types()).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(module_frame, text="Display", variable=delete_module_var, 
                       value="Display", command=lambda: update_command_types()).pack(anchor=tk.W, padx=5, pady=2)
        
        # 命令类型选择
        type_frame = ttk.LabelFrame(left_frame, text="命令类型")
        type_frame.pack(fill=tk.X, pady=5)
        
        delete_type_var = tk.StringVar(value="single_command")
        ttk.Radiobutton(type_frame, text="单条命令", variable=delete_type_var, 
                       value="single_command", command=lambda: update_commands()).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(type_frame, text="组合命令", variable=delete_type_var, 
                       value="combination_command", command=lambda: update_commands()).pack(anchor=tk.W, padx=5, pady=2)
        
        # 命令列表
        cmd_frame = ttk.LabelFrame(left_frame, text="命令列表")
        cmd_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        delete_cmd_listbox = tk.Listbox(cmd_frame, height=12)
        delete_cmd_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        delete_cmd_listbox.bind('<<ListboxSelect>>', lambda e: show_command_details())
        
        # 右侧命令详情显示区域
        details_frame = ttk.LabelFrame(right_frame, text="命令详情")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        delete_details_text = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD)
        delete_details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        delete_details_text.configure(state="disabled")
        
        def update_command_types():
            """更新命令类型"""
            update_commands()
        
        def update_commands():
            """更新命令列表"""
            delete_cmd_listbox.delete(0, tk.END)
            module = delete_module_var.get()
            cmd_type = delete_type_var.get()
            
            commands = self.command_manager.get_commands(module, cmd_type)
            for cmd_id in sorted(commands.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                delete_cmd_listbox.insert(tk.END, f"{cmd_id}: {commands[cmd_id]['help'][:50]}...")
        
        def show_command_details():
            """显示选中命令的详细信息"""
            selection = delete_cmd_listbox.curselection()
            if not selection:
                return
            
            selected_text = delete_cmd_listbox.get(selection[0])
            cmd_id = selected_text.split(':')[0]
            
            module = delete_module_var.get()
            cmd_type = delete_type_var.get()
            
            cmd_info = self.command_manager.get_command_info(module, cmd_type, cmd_id)
            if cmd_info:
                delete_details_text.configure(state="normal")
                delete_details_text.delete(1.0, tk.END)
                
                details = f"命令ID: {cmd_id}\n"
                details += f"模块: {module}\n"
                details += f"类型: {cmd_type}\n"
                details += f"脚本路径: {cmd_info['bat_path']}\n\n"
                details += f"命令描述:\n{cmd_info['help']}\n\n"
                
                # 显示脚本内容
                details += "脚本内容:\n"
                try:
                    with open(cmd_info['bat_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                    details += content
                except Exception as e:
                    details += f"无法读取脚本文件: {str(e)}"
                
                delete_details_text.insert(1.0, details)
                delete_details_text.configure(state="disabled")
        
        def delete_command():
            """删除选中的命令"""
            selection = delete_cmd_listbox.curselection()
            if not selection:
                messagebox.showwarning("警告", "请先选择要删除的命令")
                return
            
            selected_text = delete_cmd_listbox.get(selection[0])
            cmd_id = selected_text.split(':')[0]
            
            module = delete_module_var.get()
            cmd_type = delete_type_var.get()
            
            # 确认删除
            if messagebox.askyesno("确认删除", f"确定要删除命令 {cmd_id} 吗？\n\n删除后，该命令后面的所有命令编号将自动减一。"):
                success = self.command_manager.delete_command(module, cmd_type, cmd_id)
                if success:
                    messagebox.showinfo("成功", "命令已删除，编号已重新排列")
                    
                    # 更新命令列表
                    update_commands()
                    
                    # 如果当前主界面显示的是相同模块和类型，也更新主界面
                    if module == self.module_var.get() and cmd_type == self.cmd_type_var.get():
                        self.update_commands()
                    
                    # 清空详情显示
                    delete_details_text.configure(state="normal")
                    delete_details_text.delete(1.0, tk.END)
                    delete_details_text.configure(state="disabled")
                else:
                    messagebox.showerror("错误", "删除命令失败")
        
        # 初始化
        update_commands()
        
        # 按钮区域
        button_frame = ttk.Frame(delete_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="删除命令", command=delete_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=delete_dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_add_command_dialog(self):
        # 创建添加命令对话框
        add_dialog = tk.Toplevel(self)
        add_dialog.title("添加命令")
        add_dialog.geometry("600x700")  # 增加弹窗大小
        add_dialog.minsize(600, 700)  # 设置最小大小
        add_dialog.transient(self)
        add_dialog.grab_set()
        
        # 命令信息框架
        info_frame = ttk.Frame(add_dialog)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 模块选择
        module_frame = ttk.Frame(info_frame)
        module_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(module_frame, text="模块:").pack(side=tk.LEFT)
        
        add_module_var = tk.StringVar(value="Audio")
        ttk.Radiobutton(module_frame, text="Audio", variable=add_module_var, 
                       value="Audio").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(module_frame, text="Display", variable=add_module_var, 
                       value="Display").pack(side=tk.LEFT, padx=10)
        
        # 命令类型选择
        type_frame = ttk.Frame(info_frame)
        type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(type_frame, text="命令类型:").pack(side=tk.LEFT)
        
        add_type_var = tk.StringVar(value="single_command")
        ttk.Radiobutton(type_frame, text="单条命令", variable=add_type_var, 
                       value="single_command").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="组合命令", variable=add_type_var, 
                       value="combination_command").pack(side=tk.LEFT, padx=10)
        
        # 移除命令ID输入框，改为自动生成
        
        # 命令描述
        desc_frame = ttk.LabelFrame(add_dialog, text="命令描述 (help.txt)")
        desc_frame.pack(fill=tk.X, padx=10, pady=5)
        
        desc_text = scrolledtext.ScrolledText(desc_frame, height=5)
        desc_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 批处理脚本
        script_frame = ttk.LabelFrame(add_dialog, text="批处理脚本 (.bat)")
        script_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        script_text = scrolledtext.ScrolledText(script_frame)
        script_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 按钮区域
        button_frame = ttk.Frame(add_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_command():
            # 获取输入
            module = add_module_var.get()
            cmd_type = add_type_var.get()
            description = desc_text.get(1.0, tk.END).strip()
            script = script_text.get(1.0, tk.END).strip()
            
            # 验证输入
            if not description:
                messagebox.showwarning("警告", "请输入命令描述")
                return
            
            if not script:
                messagebox.showwarning("警告", "请输入批处理脚本内容")
                return
            
            # 自动生成命令ID
            cmd_path = os.path.join(self.base_path, module, cmd_type)
            if not os.path.exists(cmd_path):
                os.makedirs(cmd_path, exist_ok=True)
                cmd_id = "1"
            else:
                # 获取现有目录中的最大ID值
                existing_ids = [int(d) for d in os.listdir(cmd_path) if os.path.isdir(os.path.join(cmd_path, d)) and d.isdigit()]
                cmd_id = str(max(existing_ids, default=0) + 1)
            
            # 创建命令目录
            cmd_dir = os.path.join(self.base_path, module, cmd_type, cmd_id)
            os.makedirs(cmd_dir, exist_ok=True)
            
            try:
                # 保存help.txt
                with open(os.path.join(cmd_dir, "help.txt"), 'w', encoding='utf-8') as f:
                    f.write(description)
                
                # 保存.bat文件
                with open(os.path.join(cmd_dir, f"command_{cmd_id}.bat"), 'w', encoding='utf-8') as f:
                    f.write(script)
                
                messagebox.showinfo("成功", f"命令已添加到 {module}/{cmd_type}/{cmd_id}")
                
                # 更新命令列表
                if module == self.module_var.get() and cmd_type == self.cmd_type_var.get():
                    self.update_commands()
                
                add_dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"添加命令时出错: {str(e)}")
        
        ttk.Button(button_frame, text="添加", command=add_command).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=add_dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def start_realtime_log_capture(self):
        """开始实时日志抓取"""
        if self.realtime_process is not None:
            messagebox.showwarning("警告", "实时日志抓取已在运行中")
            return
        
        # 获取选择的日志类型和筛选方向
        log_type = self.realtime_log_type_var.get()
        direction = self.realtime_direction_var.get()
        
        # 根据下拉框选择确定筛选方向
        audio_enabled = direction in ["Audio", "Both"]
        display_enabled = direction in ["Display", "Both"]
        
        try:
            # 设置创建标志
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            # 检查设备连接状态
            self._append_to_output("检查设备连接状态...\n")
            devices_process = subprocess.Popen(
                ["adb", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=creation_flags
            )
            devices_stdout, devices_stderr = devices_process.communicate(timeout=10)
            
            # 解析设备列表
            connected_devices = []
            for line in devices_stdout.split('\n'):
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    connected_devices.append(device_id)
            
            if not connected_devices:
                messagebox.showerror("错误", "未检测到已连接的设备，请确保设备已连接并启用USB调试")
                return
            
            self._append_to_output(f"检测到设备: {', '.join(connected_devices)}\n")
            
            # 先执行adb root命令
            self._append_to_output("执行adb root...\n")
            root_process = subprocess.Popen(
                ["adb", "root"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=creation_flags
            )
            root_stdout, root_stderr = root_process.communicate(timeout=10)
            
            # 检查adb root是否成功
            if root_process.returncode != 0:
                self._append_to_output(f"警告: adb root执行失败: {root_stderr}\n")
            else:
                self._append_to_output(f"adb root执行成功\n")
            
            # 等待一下让root权限生效
            time.sleep(1)
            
            # 构建adb命令
            if log_type == "dmesg":
                cmd = ["adb", "shell", "dmesg", "-w"]
            elif log_type == "logcat":
                # 进入adb shell内执行logcat，结束后使用exit退出
                cmd = ["adb", "shell", "logcat"]
            else:
                messagebox.showerror("错误", "不支持的日志类型")
                return
            
            # 启动adb进程
            # 在Windows下添加creationflags参数以隐藏终端窗口
            self.realtime_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                creationflags=creation_flags
            )
            
            # 创建停止事件
            self.realtime_stop_event = threading.Event()
            
            # 启动日志读取线程
            self.realtime_thread = threading.Thread(
                target=self._realtime_log_reader,
                args=(audio_enabled, display_enabled),
                daemon=True
            )
            self.realtime_thread.start()
            
            # 如果勾选了保存日志，创建日志文件
            if self.save_log_var.get():
                self.log_file_handle, self.log_file_path = self._create_log_file()
                if self.log_file_handle:
                    self._append_to_output(f"日志将保存到: {self.log_file_path}\n")
                else:
                    self._append_to_output("警告: 日志文件创建失败，将不会保存日志\n")
                    self.log_file_path = None
            
            # 更新按钮状态
            self.start_realtime_button.config(state="disabled")
            self.stop_realtime_button.config(state="normal")
            
            # 在输出框中显示开始信息
            start_msg = f"开始实时抓取{log_type}日志，筛选方向: {direction}\n" + "="*50 + "\n"
            self._append_to_output(start_msg)
            
            # 如果启用了日志保存，也写入到文件
            if self.save_log_var.get():
                self._write_to_log_file(start_msg)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动实时日志抓取失败: {str(e)}")
            self.realtime_process = None
    
    def stop_realtime_log_capture(self):
        """停止实时日志抓取"""
        if self.realtime_stop_event:
            self.realtime_stop_event.set()
        
        if self.realtime_process:
            try:
                self.realtime_process.terminate()
                self.realtime_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.realtime_process.kill()
            except Exception as e:
                print(f"停止进程时出错: {e}")
            finally:
                self.realtime_process = None
        
        if self.realtime_thread and self.realtime_thread.is_alive():
            self.realtime_thread.join(timeout=2)
        
        # 更新按钮状态
        self.start_realtime_button.config(state="normal")
        self.stop_realtime_button.config(state="disabled")
        
        # 在输出框中显示停止信息
        stop_msg = "\n" + "="*50 + "\n实时日志抓取已停止\n"
        self._append_to_output(stop_msg)
        
        # 如果启用了日志保存，写入停止信息并关闭文件
        if self.save_log_var.get():
            self._write_to_log_file(stop_msg)
        
        # 关闭日志文件
        self._close_log_file()
    
    def clear_realtime_output(self):
        """清除实时日志输出"""
        self.cmd_output_text.configure(state="normal")
        self.cmd_output_text.delete(1.0, tk.END)
        self.cmd_output_text.configure(state="disabled")
    
    def _realtime_log_reader(self, audio_enabled, display_enabled):
        """实时日志读取线程（优化版本）"""
        import os
        
        try:
            # 获取关键字
            audio_keywords = set()
            display_keywords = set()
            
            if audio_enabled and hasattr(self.log_analyzer, 'keywords') and 'audio' in self.log_analyzer.keywords:
                audio_keywords = self.log_analyzer.keywords['audio']
            
            if display_enabled and hasattr(self.log_analyzer, 'keywords') and 'display' in self.log_analyzer.keywords:
                display_keywords = self.log_analyzer.keywords['display']
            
            all_keywords = audio_keywords.union(display_keywords)
            
            # 预编译正则表达式以提高性能
            compiled_patterns = {}
            for keyword in all_keywords:
                compiled_patterns[keyword] = re.compile(re.escape(keyword), re.IGNORECASE)
            
            # 缓冲区设置（使用配置选项）
            buffer_lines = []
            buffer_size = self.performance_config['buffer_size']
            last_update_time = time.time()
            update_interval = self.performance_config['update_interval']
            
            # 设置非阻塞读取（仅在非Windows系统）
            if sys.platform != "win32" and self.realtime_process:
                import fcntl
                fd = self.realtime_process.stdout.fileno()
                fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            
            consecutive_empty_reads = 0
            max_empty_reads = 100  # 连续空读取次数限制
            
            while not self.realtime_stop_event.is_set():
                try:
                    # 检查进程状态
                    if not self.realtime_process or self.realtime_process.poll() is not None:
                        # 进程已退出，获取退出信息
                        if self.realtime_process:
                            return_code = self.realtime_process.returncode
                            stderr_output = ""
                            try:
                                stderr_output = self.realtime_process.stderr.read() or ""
                            except:
                                pass
                            
                            error_msg = f"logcat进程意外退出，返回码: {return_code}"
                            if stderr_output:
                                error_msg += f"，错误信息: {stderr_output}"
                            
                            self.after(0, self._append_to_output, f"\n{error_msg}\n")
                            
                            # 检查是否是设备连接问题
                            if "device not found" in stderr_output.lower() or "no devices" in stderr_output.lower():
                                self.after(0, self._append_to_output, "\n检测到设备连接问题，尝试重新连接...\n")
                                # 可以在这里添加重连逻辑
                        break
                    
                    # 非阻塞读取（Windows使用不同的方法）
                    line = None
                    if sys.platform == "win32":
                        # Windows下使用线程池和超时机制
                        try:
                            import threading
                            import queue
                            
                            def read_line():
                                try:
                                    return self.realtime_process.stdout.readline()
                                except:
                                    return None
                            
                            # 使用线程读取，设置超时
                            result_queue = queue.Queue()
                            read_thread = threading.Thread(target=lambda: result_queue.put(read_line()))
                            read_thread.daemon = True
                            read_thread.start()
                            
                            try:
                                line = result_queue.get(timeout=0.1)
                            except queue.Empty:
                                line = None
                        except:
                            line = None
                    else:
                        # Unix/Linux系统使用select
                        try:
                            import select
                            ready, _, _ = select.select([self.realtime_process.stdout], [], [], 0.1)
                            if ready:
                                try:
                                    line = self.realtime_process.stdout.readline()
                                except IOError:
                                    line = None
                        except:
                            line = None
                    
                    if line:
                        consecutive_empty_reads = 0
                        line = line.strip()
                        if line:  # 只处理非空行
                            # 检查是否包含关键字（优化版本）
                            if self._line_contains_keywords_optimized(line, all_keywords, compiled_patterns):
                                buffer_lines.append((line, all_keywords))
                    else:
                        consecutive_empty_reads += 1
                        # 如果连续空读取太多次，可能进程有问题
                        if consecutive_empty_reads > max_empty_reads:
                            self.after(0, self._append_to_output, "\n警告: logcat进程可能无响应，尝试重启...\n")
                            break
                        
                        # 短暂休眠避免CPU占用过高
                        time.sleep(0.01)
                    
                    # 批量更新UI条件：缓冲区满了或者时间间隔到了
                    current_time = time.time()
                    if (len(buffer_lines) >= buffer_size or 
                        (buffer_lines and current_time - last_update_time >= update_interval)):
                        
                        # 批量更新UI
                        self.after(0, self._batch_append_to_output_with_highlight, buffer_lines.copy())
                        buffer_lines.clear()
                        last_update_time = current_time
                
                except Exception as e:
                    self.after(0, self._append_to_output, f"\n读取日志行时出错: {e}\n")
                    break
            
            # 处理剩余的缓冲区内容
            if buffer_lines:
                self.after(0, self._batch_append_to_output_with_highlight, buffer_lines)
        
        except Exception as e:
            self.after(0, self._append_to_output, f"\n实时日志读取线程出错: {e}\n")
        finally:
            # 确保进程被清理
            if self.realtime_process:
                try:
                    self.realtime_process.terminate()
                    self.realtime_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        self.realtime_process.kill()
                    except:
                        pass
                except:
                    pass
    
    def _line_contains_keywords(self, line, keywords):
        """检查行是否包含关键字"""
        if not keywords:
            return True  # 如果没有关键字，显示所有行
        
        for keyword in keywords:
            if keyword.lower() in line.lower():
                return True
        return False
    
    def _line_contains_keywords_optimized(self, line, keywords, compiled_patterns):
        """优化的关键字匹配方法"""
        if not keywords:
            return True  # 如果没有关键字，显示所有行
        
        # 使用预编译的正则表达式进行匹配，性能更好
        line_lower = line.lower()
        for keyword in keywords:
            if keyword.lower() in line_lower:
                return True
        return False
    
    def _highlight_keywords(self, line, keywords):
        """高亮关键字（保留用于简单文本替换）"""
        if not keywords:
            return line
        
        highlighted_line = line
        for keyword in keywords:
            # 使用正则表达式进行大小写不敏感的替换
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            highlighted_line = pattern.sub(f"**{keyword}**", highlighted_line)
        
        return highlighted_line
    
    def _check_device_connection(self):
        """检查设备连接状态"""
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            devices_process = subprocess.Popen(
                ["adb", "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=creation_flags
            )
            devices_stdout, devices_stderr = devices_process.communicate(timeout=5)
            
            # 解析设备列表
            connected_devices = []
            for line in devices_stdout.split('\n'):
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    connected_devices.append(device_id)
            
            return len(connected_devices) > 0, connected_devices
        except Exception as e:
            return False, []
    
    def _append_to_output(self, text):
        """线程安全地向输出框添加文本"""
        try:
            self.cmd_output_text.configure(state="normal")
            # 确保文本以换行符结尾
            if not text.endswith('\n'):
                text += '\n'
            self.cmd_output_text.insert(tk.END, text)
            
            # 如果启用了日志保存，写入到文件
            if self.save_log_var.get():
                self._write_to_log_file(text)
            
            # 强制滚动到底部
            self.cmd_output_text.see(tk.END)
            # 确保滚动条更新
            self.cmd_output_text.update_idletasks()
            self.cmd_output_text.configure(state="disabled")
        except Exception as e:
            print(f"添加输出文本时出错: {e}")
    
    def _append_to_output_with_highlight(self, line, keywords):
        """线程安全地向输出框添加带高亮的文本"""
        try:
            self.cmd_output_text.configure(state="normal")
            
            # 确保行以换行符结尾
            if not line.endswith('\n'):
                line += '\n'
            
            # 获取当前插入位置
            start_pos = self.cmd_output_text.index(tk.END + "-1c")
            
            # 插入原始文本
            self.cmd_output_text.insert(tk.END, line)
            
            # 如果启用了日志保存，写入到文件
            if self.save_log_var.get():
                self._write_to_log_file(line)
            
            # 为关键字添加高亮
            if keywords:
                # 定义高亮颜色循环
                highlight_colors = ["highlight_red", "highlight_blue", "highlight_green", 
                                  "highlight_yellow", "highlight_purple"]
                color_index = 0
                
                for keyword in keywords:
                    # 在插入的文本中查找关键字
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    for match in pattern.finditer(line):
                        # 计算在Text组件中的位置
                        start_idx = f"{start_pos}+{match.start()}c"
                        end_idx = f"{start_pos}+{match.end()}c"
                        
                        # 应用高亮标签
                        color_tag = highlight_colors[color_index % len(highlight_colors)]
                        self.cmd_output_text.tag_add(color_tag, start_idx, end_idx)
                    
                    color_index += 1
            
            # 强制滚动到底部
            self.cmd_output_text.see(tk.END)
            # 确保滚动条更新
            self.cmd_output_text.update_idletasks()
            self.cmd_output_text.configure(state="disabled")
        except Exception as e:
            print(f"添加高亮输出文本时出错: {e}")
    
    def _batch_append_to_output_with_highlight(self, buffer_lines):
        """批量向输出框添加带高亮的文本（优化版本）"""
        try:
            if not buffer_lines:
                return
            
            self.cmd_output_text.configure(state="normal")
            
            # 检查并限制最大行数
            current_lines = int(self.cmd_output_text.index('end-1c').split('.')[0])
            max_lines = self.performance_config['max_lines']
            
            if current_lines > max_lines:
                # 删除前面的行，保留最新的内容
                lines_to_delete = current_lines - max_lines + len(buffer_lines)
                self.cmd_output_text.delete('1.0', f'{lines_to_delete}.0')
            
            # 定义高亮颜色循环
            highlight_colors = ["highlight_red", "highlight_blue", "highlight_green", 
                              "highlight_yellow", "highlight_purple"]
            
            # 根据配置决定是否启用高亮
            enable_highlight = self.performance_config['enable_highlight']
            
            # 收集所有关键字并预编译正则表达式（仅在启用高亮时）
            compiled_patterns = {}
            if enable_highlight:
                all_keywords = set()
                for _, keywords in buffer_lines:
                    all_keywords.update(keywords)
                
                for keyword in all_keywords:
                    compiled_patterns[keyword] = re.compile(re.escape(keyword), re.IGNORECASE)
            
            # 批量处理所有行
            for line, keywords in buffer_lines:
                # 确保行以换行符结尾
                if not line.endswith('\n'):
                    line += '\n'
                
                # 获取当前插入位置
                start_pos = self.cmd_output_text.index(tk.END + "-1c")
                
                # 插入原始文本
                self.cmd_output_text.insert(tk.END, line)
                
                # 如果启用了日志保存，写入到文件
                if self.save_log_var.get():
                    self._write_to_log_file(line)
                
                # 为关键字添加高亮（仅在启用时）
                if enable_highlight and keywords:
                    color_index = 0
                    for keyword in keywords:
                        # 使用预编译的正则表达式
                        pattern = compiled_patterns.get(keyword)
                        if pattern:
                            for match in pattern.finditer(line):
                                # 计算在Text组件中的位置
                                start_idx = f"{start_pos}+{match.start()}c"
                                end_idx = f"{start_pos}+{match.end()}c"
                                
                                # 应用高亮标签
                                color_tag = highlight_colors[color_index % len(highlight_colors)]
                                self.cmd_output_text.tag_add(color_tag, start_idx, end_idx)
                        
                        color_index += 1
            
            # 只在最后滚动到底部和设置状态，减少UI操作
            self.cmd_output_text.see(tk.END)
            # 确保滚动条更新
            self.cmd_output_text.update_idletasks()
            self.cmd_output_text.configure(state="disabled")
            
        except Exception as e:
            print(f"批量添加高亮输出文本时出错: {e}")
    
    def open_performance_settings_dialog(self):
        """打开性能设置弹窗对话框"""
        # 创建弹窗窗口
        dialog = tk.Toplevel(self)
        dialog.title("性能设置")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        
        # 设置窗口居中
        dialog.transient(self)
        dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 标题
        title_label = ttk.Label(main_frame, text="实时日志抓取性能设置", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 缓冲区设置
        buffer_frame = ttk.LabelFrame(main_frame, text="缓冲区设置")
        buffer_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(buffer_frame, text="缓冲区大小（行数）:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        buffer_size_var = tk.IntVar(value=self.performance_config['buffer_size'])
        buffer_spinbox = ttk.Spinbox(buffer_frame, from_=10, to=200, textvariable=buffer_size_var, width=10)
        buffer_spinbox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(buffer_frame, text="(10-200，推荐50)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 更新频率设置
        update_frame = ttk.LabelFrame(main_frame, text="更新频率设置")
        update_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(update_frame, text="UI更新间隔（秒）:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        update_interval_var = tk.DoubleVar(value=self.performance_config['update_interval'])
        interval_spinbox = ttk.Spinbox(update_frame, from_=0.05, to=1.0, increment=0.05, textvariable=update_interval_var, width=10)
        interval_spinbox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(update_frame, text="(0.05-1.0秒，推荐0.1)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 显示限制设置
        display_frame = ttk.LabelFrame(main_frame, text="显示限制设置")
        display_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(display_frame, text="最大显示行数:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        max_lines_var = tk.IntVar(value=self.performance_config['max_lines'])
        lines_spinbox = ttk.Spinbox(display_frame, from_=1000, to=50000, increment=1000, textvariable=max_lines_var, width=10)
        lines_spinbox.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(display_frame, text="(1000-50000，推荐10000)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 高亮设置
        highlight_frame = ttk.LabelFrame(main_frame, text="高亮设置")
        highlight_frame.pack(fill=tk.X, pady=(0, 10))
        
        enable_highlight_var = tk.BooleanVar(value=self.performance_config['enable_highlight'])
        highlight_check = ttk.Checkbutton(highlight_frame, text="启用关键字高亮（关闭可提升性能）", variable=enable_highlight_var)
        highlight_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # 性能说明
        info_frame = ttk.LabelFrame(main_frame, text="性能优化说明")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, state="disabled")
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        info_content = """性能优化建议：

1. 缓冲区大小：增大可减少UI更新频率，但会增加延迟。推荐50行。
2. 更新间隔：增大可减少CPU占用，但会增加显示延迟。推荐0.1秒。
3. 最大显示行数：限制内存占用，超出时自动删除旧内容。推荐10000行。
4. 关键字高亮：关闭可显著提升性能，特别是在关键字较多时。

注意：修改设置后需要重新启动实时日志抓取才能生效。"""
        
        info_text.configure(state="normal")
        info_text.insert("1.0", info_content)
        info_text.configure(state="disabled")
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        def apply_settings():
            """应用设置并关闭对话框"""
            try:
                # 更新配置
                self.performance_config['buffer_size'] = buffer_size_var.get()
                self.performance_config['update_interval'] = update_interval_var.get()
                self.performance_config['max_lines'] = max_lines_var.get()
                self.performance_config['enable_highlight'] = enable_highlight_var.get()
                
                messagebox.showinfo("设置已应用", "性能设置已更新！\n重新启动实时日志抓取后生效。", parent=dialog)
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("设置失败", f"应用设置时出错：{e}", parent=dialog)
        
        def reset_settings():
            """重置设置为默认值"""
            buffer_size_var.set(50)
            update_interval_var.set(0.1)
            max_lines_var.set(10000)
            enable_highlight_var.set(True)
            
            messagebox.showinfo("设置已重置", "性能设置已重置为默认值！", parent=dialog)
        
        # 应用设置按钮
        apply_btn = ttk.Button(button_frame, text="应用设置", command=apply_settings)
        apply_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重置为默认值按钮
        reset_btn = ttk.Button(button_frame, text="重置为默认值", command=reset_settings)
        reset_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="取消", command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        
        # 设置窗口居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def _create_log_file(self):
        """创建日志文件，返回文件句柄"""
        try:
            # 创建日志保存目录
            if getattr(sys, 'frozen', False):
                # 如果是打包后的exe程序，使用exe文件所在目录（与keyword目录同级）
                base_dir = os.path.dirname(sys.executable)
                print(f"exe程序根目录：{base_dir}")
            else:
                # 如果是源码运行，使用脚本所在目录
                base_dir = os.path.dirname(os.path.abspath(__file__))
                print(f"源码运行目录：{base_dir}")
            
            log_dir = os.path.join(base_dir, "realtime_logs")
            
            # 确保日志目录存在
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                print(f"创建日志目录：{log_dir}")
            else:
                print(f"使用现有日志目录：{log_dir}")
            
            # 创建时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建日志文件名
            log_type = self.realtime_log_type_var.get()
            direction = self.realtime_direction_var.get()
            log_filename = f"realtime_{log_type}_{direction}_{timestamp}.txt"
            log_filepath = os.path.join(log_dir, log_filename)
            
            # 创建并打开文件
            log_file = open(log_filepath, 'w', encoding='utf-8', buffering=1)  # 行缓冲
            
            # 写入文件头信息
            header_info = [
                f"实时日志抓取 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"日志类型: {log_type}",
                f"筛选方向: {direction}",
                f"保存路径: {log_filepath}",
                "=" * 60,
                ""
            ]
            
            for line in header_info:
                log_file.write(line + "\n")
            log_file.flush()
            
            print(f"日志文件已创建：{log_filepath}")
            return log_file, log_filepath
            
        except PermissionError:
            error_msg = "权限不足，无法创建日志文件。请检查目录权限。"
            messagebox.showerror("权限错误", error_msg)
            print(f"权限错误：{error_msg}")
            return None, None
        except OSError as e:
            error_msg = f"文件系统错误：{e}"
            messagebox.showerror("文件系统错误", error_msg)
            print(f"文件系统错误：{error_msg}")
            return None, None
        except Exception as e:
            error_msg = f"创建日志文件失败：{e}"
            messagebox.showerror("错误", error_msg)
            print(f"创建日志文件失败：{error_msg}")
            return None, None
    
    def _close_log_file(self):
        """关闭日志文件"""
        if self.log_file_handle:
            try:
                # 写入结束信息
                end_info = [
                    "",
                    "=" * 60,
                    f"日志结束 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"文件路径: {getattr(self, 'log_file_path', '未知')}"
                ]
                
                for line in end_info:
                    self.log_file_handle.write(line + "\n")
                
                self.log_file_handle.flush()
                self.log_file_handle.close()
                
                print(f"日志文件已关闭：{getattr(self, 'log_file_path', '未知')}")
                
            except Exception as e:
                print(f"关闭日志文件时出错：{e}")
            finally:
                self.log_file_handle = None
                self.log_file_path = None
    
    def _write_to_log_file(self, text):
        """写入文本到日志文件"""
        if not self.log_file_handle or not self.save_log_var.get():
            return
            
        try:
            # 移除ANSI颜色代码和控制字符
            clean_text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
            clean_text = re.sub(r'\r', '', clean_text)  # 移除回车符
            
            # 确保文件句柄仍然有效
            if self.log_file_handle.closed:
                print("警告：日志文件句柄已关闭，无法写入")
                return
                
            self.log_file_handle.write(clean_text)
            self.log_file_handle.flush()
            
        except (OSError, IOError) as e:
            print(f"写入日志文件时发生I/O错误：{e}")
            # 尝试关闭文件句柄
            try:
                if self.log_file_handle and not self.log_file_handle.closed:
                    self.log_file_handle.close()
            except:
                pass
            self.log_file_handle = None
            
        except Exception as e:
            print(f"写入日志文件时出错：{e}")

    
    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗?"):
            # 停止实时日志抓取
            if hasattr(self, 'realtime_process') and self.realtime_process:
                self.stop_realtime_log_capture()
            
            # 确保日志文件被关闭
            if hasattr(self, 'log_file_handle') and self.log_file_handle:
                self._close_log_file()
                
            self.destroy()

def main():
    app = BatchCommandGUI()
    app.mainloop()

if __name__ == "__main__":
    main()