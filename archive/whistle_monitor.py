#!/usr/bin/env python3
"""
Whistle 实时监听 - 捕获七鱼会话数据
"""
import requests
import json
import time
import base64

class WhistleMonitor:
    def __init__(self, port=8899):
        self.base_url = f'http://127.0.0.1:{port}'
    
    def get_latest_sessions(self):
        """获取最新的会话列表和 token"""
        url = f'{self.base_url}/cgi-bin/get-data?count=100'
        
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            
            # Whistle 数据结构: data.data[id] = request
            items = data.get('data', {}).get('data', {})
            
            for req_id, item in items.items():
                req_url = item.get('url', '')
                if 'session/chat/service/record' in req_url:
                    return self._parse_session_data(item)
            
            return None, None
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            return None, None
    
    def _parse_session_data(self, item):
        """解析会话数据"""
        # 提取 token
        req_url = item.get('url', '')
        token = None
        if 'token=' in req_url:
            token = req_url.split('token=')[1].split('&')[0]
        
        # 解析响应
        res = item.get('res', {})
        if 'base64' in res:
            json_str = base64.b64decode(res['base64']).decode('utf-8')
            data = json.loads(json_str)
            
            sessions = []
            for session in data.get('result', []):
                if session.get('status') == 1:
                    sessions.append({
                        'sessionId': session['id'],
                        'userId': session['user']['id'],
                        'userName': session['user']['realname']
                    })
            
            return sessions, token
        
        return None, None

def main():
    """测试监听"""
    monitor = WhistleMonitor()
    
    print("🔍 监听 Whistle 数据...\n")
    sessions, token = monitor.get_latest_sessions()
    
    if sessions:
        print(f"✅ 找到 {len(sessions)} 个会话")
        print(f"🔑 Token: {token[:20]}...")
        print("\n前 3 个会话:")
        for s in sessions[:3]:
            print(f"  - {s['userName'][:30]} (ID: {s['sessionId']})")
    else:
        print("❌ 未找到会话数据")

if __name__ == '__main__':
    main()
