#!/usr/bin/env python3
"""
测试：通过 Cookie 访问七鱼页面，提取会话信息
"""
import requests
import json
from pathlib import Path
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载 Cookie
cookie_file = Path(__file__).parent / 'data' / '.qiyu_cookies.json'
with open(cookie_file) as f:
    cookies = json.load(f)

# 创建 session
session = requests.Session()
for name, value in cookies.items():
    session.cookies.set(name, value)

# 访问首页（禁用 SSL 验证）
url = 'https://qw.qiyukf.com/wxwork/index?code=wyzqkj'
response = session.get(url, verify=False)

print(f"状态码: {response.status_code}")
print(f"响应长度: {len(response.text)}")

# 查找可能包含会话信息的内容
if 'sessionId' in response.text:
    print("✅ 找到 sessionId")
if 'chatGroupId' in response.text:
    print("✅ 找到 chatGroupId")

# 保存响应用于分析
with open('/tmp/qiyu_index.html', 'w') as f:
    f.write(response.text)
print("响应已保存到: /tmp/qiyu_index.html")
