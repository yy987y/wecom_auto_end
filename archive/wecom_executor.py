#!/usr/bin/env python3
"""
企微侧边栏执行器统一模块
"""
from qiyu_api import QiyuAPI
from navigate_full import navigate_to_qiyu
import json
import time
import subprocess
from pathlib import Path

def enable_proxy():
    """临时启用系统代理"""
    subprocess.run(['/usr/sbin/networksetup', '-setwebproxy', 'Wi-Fi', '127.0.0.1', '8080'], check=False)
    subprocess.run(['/usr/sbin/networksetup', '-setsecurewebproxy', 'Wi-Fi', '127.0.0.1', '8080'], check=False)

def disable_proxy():
    """禁用系统代理"""
    subprocess.run(['/usr/sbin/networksetup', '-setwebproxystate', 'Wi-Fi', 'off'], check=False)
    subprocess.run(['/usr/sbin/networksetup', '-setsecurewebproxystate', 'Wi-Fi', 'off'], check=False)

def get_session_from_mitm():
    """从 mitmproxy 捕获的文件读取会话信息"""
    session_file = Path('/tmp/qiyu_session.json')
    if session_file.exists():
        with open(session_file) as f:
            return json.load(f)
    return None

def execute_end_session(group_name=None):
    """
    执行结束会话
    
    Args:
        group_name: 群名（用于日志）
    
    Returns:
        (success, message)
    """
    try:
        api = QiyuAPI()
        if not api.load_cookies_from_file():
            return False, 'Cookie 未配置'
        
        print(f"[执行器] 临时启用代理...")
        enable_proxy()
        time.sleep(1)
        
        print(f"[执行器] 导航到网易智企...")
        if not navigate_to_qiyu():
            disable_proxy()
            return False, '导航失败'
        
        # 等待页面加载和 mitmproxy 捕获
        print(f"[执行器] 等待会话信息...")
        time.sleep(3)
        
        print(f"[执行器] 禁用代理...")
        disable_proxy()
        
        session_info = get_session_from_mitm()
        if not session_info:
            return False, '未捕获到会话信息'
        
        session_id = session_info.get('sessionId')
        chat_group_id = session_info.get('chatGroupId')
        
        if not session_id or not chat_group_id:
            return False, f'会话信息不完整: {session_info}'
        
        print(f"  sessionId: {session_id}")
        print(f"  chatGroupId: {chat_group_id}")
        
        if api.close_session(session_id, chat_group_id):
            return True, '✅ 已成功结束会话'
        else:
            return False, 'API 调用失败'
            
    except Exception as e:
        disable_proxy()  # 确保异常时也关闭代理
        return False, f'异常: {e}'
