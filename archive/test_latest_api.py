#!/usr/bin/env python3
"""测试 /chat/api/session/latest 端点"""
import requests
import json
import urllib3
urllib3.disable_warnings()

cookies = {
    'QIYUFIXED_SESSIONID_QW': '66195E3CC9944763BB5FDF002D8D1143',
    '___csrfToken': 'IPHH3224Q9Q2826FXCUXXLD4TGMTTFSI'
}

# 测试几个 userId
user_ids = [42010212677, 40577490390, 40577490399]

for user_id in user_ids:
    print(f"\n测试 userId: {user_id}")
    resp = requests.get(
        'https://qw.qiyukf.com/chat/api/session/latest',
        params={
            'code': 'wyzqkj',
            'userId': user_id,
            'token': 'IPHH3224Q9Q2826FXCUXXLD4TGMTTFSI'
        },
        cookies=cookies,
        verify=False,
        timeout=5
    )
    print(f"状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
