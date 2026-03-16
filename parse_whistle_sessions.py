#!/usr/bin/env python3
"""
解析 Whistle 捕获的七鱼会话数据
从 /chat/api/session/chat/service/record 响应中提取会话信息
"""

import json
import base64
from typing import Dict, List

def parse_whistle_response(base64_data: str) -> List[Dict]:
    """解析 Whistle 捕获的 base64 编码响应"""
    # 解码 base64
    json_str = base64.b64decode(base64_data).decode('utf-8')
    data = json.loads(json_str)
    
    sessions = []
    for session in data.get('result', []):
        # 提取关键字段
        session_info = {
            'sessionId': session.get('id'),
            'userId': session.get('user', {}).get('id'),
            'userName': session.get('user', {}).get('realname'),
            'foreignId': session.get('foreignId'),
            'status': session.get('status'),
            'kefu': session.get('kefu', {}).get('realname'),
            'kefuId': session.get('kefu', {}).get('id'),
        }
        sessions.append(session_info)
    
    return sessions

def main():
    # 示例：从文件读取 Whistle 捕获的数据
    with open('/Users/yanchao/Downloads/1.txt', 'r') as f:
        content = f.read()
    
    # 提取 base64 数据（在 "base64": "..." 中）
    import re
    match = re.search(r'"base64":\s*"([^"]+)"', content)
    if not match:
        print("未找到 base64 数据")
        return
    
    base64_data = match.group(1)
    sessions = parse_whistle_response(base64_data)
    
    print(f"共找到 {len(sessions)} 个会话")
    print("\n前 5 个会话示例：")
    for i, session in enumerate(sessions[:5], 1):
        print(f"\n{i}. {session['userName']}")
        print(f"   sessionId: {session['sessionId']}")
        print(f"   userId: {session['userId']}")
        print(f"   foreignId: {session['foreignId']}")
        print(f"   客服: {session['kefu']}")

if __name__ == '__main__':
    main()
