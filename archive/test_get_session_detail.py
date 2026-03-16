#!/usr/bin/env python3
"""
测试获取会话详情 API
尝试找到包含 groupManageId 的端点
"""
import requests
import json

# 从 Whistle 捕获的 Cookie
cookies = {
    'QIYUFIXED_SESSIONID_QW': '66195E3CC9944763BB5FDF002D8D1143',
    '___csrfToken': 'IPHH3224Q9Q2826FXCUXXLD4TGMTTFSI'
}

# 测试会话 ID（从 Whistle 响应中获取）
session_id = 14993798865
user_id = 42010212677

# 尝试几个可能的 API 端点
endpoints = [
    f'/chat/api/session/{session_id}',
    f'/chat/api/session/detail?sessionId={session_id}',
    f'/chat/api/session/info?id={session_id}',
    f'/api/session/chat/group?userId={user_id}',
]

base_url = 'https://qw.qiyukf.com'

for endpoint in endpoints:
    print(f"\n尝试: {endpoint}")
    try:
        resp = requests.get(
            base_url + endpoint,
            cookies=cookies,
            params={'code': 'wyzqkj', 'token': 'IPHH3224Q9Q2826FXCUXXLD4TGMTTFSI'},
            timeout=5,
            verify=False
        )
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    except Exception as e:
        print(f"错误: {e}")
