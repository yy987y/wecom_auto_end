#!/usr/bin/env python3
"""企微侧边栏执行器统一模块"""
import subprocess
import time
from pathlib import Path

WS = Path(__file__).parent


def run_swift(script_name, timeout=10):
    cmd = f'swift {WS}/{script_name}'
    p = subprocess.run(cmd, shell=True, cwd=WS, capture_output=True, text=True, timeout=timeout)
    output = (p.stdout or '') + (p.stderr or '')
    return p.returncode == 0, output.strip()


def open_sidebar_and_qiyu(wait_seconds=5):
    steps = [
        ('wecom_click_sidebar_candidate.swift', '打开侧边栏'),
        ('wecom_click_netease.swift', '点击网易智企'),
    ]
    for script, desc in steps:
        success, output = run_swift(script)
        print(f"[执行器] {desc}: {'✅' if success else '❌'}")
        if output:
            print(f"  {output}")
        if not success:
            return False, f'{desc}失败'
        time.sleep(0.8)

    print(f"[执行器] 等待网易智企页面加载 {wait_seconds}s...")
    time.sleep(wait_seconds)
    return True, '已打开侧边栏并切到网易智企'


def ensure_login_state():
    success, output = run_swift('wecom_click_relogin.swift')
    print(f"[执行器] 检查并处理登录状态: {'✅' if success else '⚠️'}")
    if output:
        print(f"  {output}")
    return success, output


def reset_sidebar():
    success, output = run_swift('wecom_toggle_sidebar.swift')
    print(f"[执行器] 重置侧边栏: {'✅' if success else '❌'}")
    if output:
        print(f"  {output}")
    time.sleep(1)
    return success, output


def execute_end_session():
    success, msg = open_sidebar_and_qiyu(wait_seconds=5)
    if not success:
        return False, msg

    ensure_login_state()
    return True, '已执行侧边栏链路，到达目标页'
