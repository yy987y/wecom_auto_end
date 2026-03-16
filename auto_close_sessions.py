#!/usr/bin/env python3
"""
自动结束七鱼会话
基于 Whistle 捕获的数据 + HTTP API
"""
import json
import requests
import warnings
from pathlib import Path

# 禁用 SSL 警告
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def load_config():
    """加载配置"""
    config_file = Path(__file__).parent / 'config.json'
    with open(config_file) as f:
        return json.load(f)

def parse_whistle_data(file_path):
    """解析 Whistle 捕获的会话列表"""
    import re
    import base64
    
    with open(file_path) as f:
        content = f.read()
    
    match = re.search(r'"base64":\s*"([^"]+)"', content)
    if not match:
        return []
    
    json_str = base64.b64decode(match.group(1)).decode('utf-8')
    data = json.loads(json_str)
    
    sessions = []
    for item in data.get('result', []):
        if item.get('status') == 1:  # 只处理进行中的会话
            sessions.append({
                'sessionId': item['id'],
                'userId': item['user']['id'],
                'userName': item['user']['realname']
            })
    return sessions

def close_session(session_id, config):
    """关闭单个会话"""
    url = f"{config['baseUrl']}/chat/api/session/closeWXCSSession"
    
    data = {
        'sessionId': session_id,
        'groupManageId': config['groupManageId']
    }
    
    cookies = config['cookies']
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(url, data=data, cookies=cookies, headers=headers, verify=False, timeout=5)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def main():
    import sys
    
    config = load_config()
    
    # 从 Whistle 数据文件读取
    whistle_file = Path.home() / 'Downloads' / '1.txt'
    sessions = parse_whistle_data(whistle_file)
    
    # 限制处理数量（避免一次处理太多）
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sessions = sessions[:limit]
    
    print(f'准备关闭 {len(sessions)} 个会话\n')
    
    success = 0
    failed = 0
    
    for i, session in enumerate(sessions, 1):
        print(f"[{i}/{len(sessions)}] {session['userName'][:30]}")
        print(f"  sessionId: {session['sessionId']}")
        
        ok, msg = close_session(session['sessionId'], config)
        if ok:
            print(f'  ✅ 成功')
            success += 1
        else:
            print(f'  ❌ 失败: {msg[:50]}')
            failed += 1
    
    print(f'\n总结: 成功 {success}, 失败 {failed}')

if __name__ == '__main__':
    main()
