#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试超长日志智能分析功能
"""

import os
import sys
from ai_analyzer import AIAnalyzer

def test_long_log_analysis():
    """测试超长日志分析功能"""
    print("=== 超长日志智能分析功能测试 ===\n")
    
    # 读取测试日志文件
    test_log_path = "test_long_log.txt"
    if not os.path.exists(test_log_path):
        print(f"错误: 测试日志文件 {test_log_path} 不存在")
        return
    
    try:
        with open(test_log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print(f"测试日志文件大小: {len(log_content)} 字符")
        print(f"是否超过10000字符阈值: {'是' if len(log_content) > 10000 else '否'}")
        print()
        
        # 创建AI分析器实例
        api_key = "sk_bb948d4a08697edc789ccdf83743992b3ba455f9f56cf945f502975"
        analyzer = AIAnalyzer(api_key)
        
        # 测试连接
        print("测试AI API连接...")
        connection_result = analyzer.test_connection()
        print(f"连接状态: {connection_result}")
        print()
        
        if not connection_result.get('success', False):
            print("AI API连接失败，无法进行分析测试")
            print("请检查API配置和网络连接")
            return
        
        # 执行分析
        print("开始执行超长日志分析...")
        print("=" * 50)
        
        result = analyzer.analyze_log_content(log_content)
        
        print("\n=== 分析结果 ===")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"{key}: {value}")
        else:
            print(result)
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def test_segment_algorithm():
    """测试分段算法"""
    print("\n=== 分段算法测试 ===\n")
    
    # 创建AI分析器实例
    api_key = "sk_bb948d4a08697edc789ccdf83743992b3ba455f9f56cf945f502975"
    analyzer = AIAnalyzer(api_key)
    
    # 读取测试日志
    test_log_path = "test_long_log.txt"
    try:
        with open(test_log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print(f"原始日志长度: {len(log_content)} 字符")
        
        # 测试分段功能
        segments = analyzer._smart_segment_log(log_content)
        
        print(f"分段数量: {len(segments)}")
        print()
        
        for i, segment in enumerate(segments, 1):
            print(f"段 {i}:")
            print(f"  长度: {len(segment)} 字符")
            print(f"  开头: {segment[:100]}...")
            print(f"  结尾: ...{segment[-100:]}")
            print()
        
    except Exception as e:
        print(f"分段测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行测试
    test_long_log_analysis()
    test_segment_algorithm()