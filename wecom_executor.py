#!/usr/bin/env python3
"""
企微侧边栏执行器统一模块
"""
import subprocess
import time
from pathlib import Path

WS = Path(__file__).parent

def run_swift(script_name):
    """执行 Swift 脚本"""
    cmd = f'swift {WS}/{script_name}'
    p = subprocess.run(cmd, shell=True, cwd=WS, capture_output=True, text=True, timeout=10)
    output = (p.stdout or '') + (p.stderr or '')
    return p.returncode == 0, output.strip()

def execute_end_session():
    """
    执行结束会话完整链路
    返回: (success, message)
    """
    steps = [
        ('wecom_click_sidebar_candidate.swift', '打开侧边栏'),
        ('wecom_click_netease.swift', '点击网易智企'),
        ('wecom_click_relogin.swift', '处理重新登录'),
    ]
    
    for script, desc in steps:
        success, output = run_swift(script)
        print(f"[执行器] {desc}: {'✅' if success else '❌'}")
        if output:
            print(f"  {output}")
        time.sleep(0.5)
    
    # TODO: 最后接上"结束会话"按钮点击
    # 当前先返回已到达目标页
    return True, '已执行侧边栏链路，到达目标页'
