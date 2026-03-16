#!/usr/bin/env python3
"""
企微自动结束会话 - 简化版
手动触发：切换群后运行此脚本，自动完成所有操作
"""
import subprocess
import time
import json
import requests
import warnings
from pathlib import Path

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def click_sidebar():
    """点击侧边栏打开网易智企"""
    print("📱 打开侧边栏...")
    subprocess.run(['swift', 'wecom_click_sidebar_candidate.swift'], 
                   cwd=Path(__file__).parent, check=True)
    time.sleep(3)

def get_latest_whistle_data():
    """从 Whistle 最新捕获的文件获取会话数据"""
    import re
    import base64
    
    # 假设 Whistle 数据保存在固定位置
    whistle_file = Path.home() / 'Downloads' / '1.txt'
    
    with open(whistle_file) as f:
        content = f.read()
    
    match = re.search(r'"base64":\s*"([^"]+)"', content)
    if not match:
        return [], None
    
    json_str = base64.b64decode(match.group(1)).decode('utf-8')
    data = json.loads(json_str)
    
    # 提取 token
    match_token = re.search(r'token=([A-Z0-9]+)', content)
    token = match_token.group(1) if match_token else None
    
    sessions = []
    for item in data.get('result', []):
        if item.get('status') == 1:
            sessions.append({
                'id': item['id'],
                'name': item['user']['realname']
            })
    
    return sessions, token

def close_session(session_id, token):
    """关闭会话"""
    url = 'https://qw.qiyukf.com/chat/api/session/closeWXCSSession'
    data = {
        'sessionId': session_id,
        'groupManageId': 6275817
    }
    cookies = {'___csrfToken': token}
    
    response = requests.post(url, data=data, cookies=cookies, verify=False, timeout=5)
    return response.status_code == 200

def main():
    print("🎯 企微自动结束会话\n")
    
    # 1. 打开侧边栏
    click_sidebar()
    
    # 2. 获取会话数据
    print("📋 获取会话列表...")
    sessions, token = get_latest_whistle_data()
    
    if not sessions:
        print("❌ 未找到会话数据")
        return
    
    print(f"✅ 找到 {len(sessions)} 个会话\n")
    
    # 3. 批量关闭
    for i, session in enumerate(sessions[:10], 1):  # 限制前10个
        print(f"[{i}] {session['name'][:30]}")
        if close_session(session['id'], token):
            print("  ✅ 已关闭")
        else:
            print("  ❌ 失败")

if __name__ == '__main__':
    main()
