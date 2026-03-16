#!/usr/bin/env python3
"""
Whistle WebSocket 实时监听
捕获七鱼会话数据并自动关闭
"""
import websocket
import json
import threading
import time
import requests
import warnings
from collections import deque

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class QiyuAutoClose:
    def __init__(self):
        self.whistle_ws = "ws://127.0.0.1:8899/cgi-bin/socket.io/?transport=websocket"
        self.sessions = deque(maxlen=200)  # 缓存最近的会话
        self.token = None
        self.group_manage_id = 6275817
        
    def on_message(self, ws, message):
        """处理 Whistle 消息"""
        try:
            # Whistle 可能发送多种格式，尝试解析
            if message.startswith('42'):  # Socket.IO 消息格式
                data = json.loads(message[2:])
                if isinstance(data, list) and len(data) > 1:
                    event_data = data[1]
                    self._process_request(event_data)
            
        except Exception as e:
            pass  # 忽略解析错误
    
    def _process_request(self, data):
        """处理请求数据"""
        url = data.get('url', '')
        
        # 捕获会话列表请求
        if 'session/chat/service/record' in url:
            print(f"\n✅ 捕获到会话列表请求")
            self._extract_sessions(data)
        
        # 捕获 token
        if 'token=' in url and not self.token:
            self.token = url.split('token=')[1].split('&')[0]
            print(f"🔑 获取到 Token: {self.token[:20]}...")
    
    def _extract_sessions(self, data):
        """从响应中提取会话"""
        import base64
        
        res = data.get('res', {})
        if 'base64' in res:
            try:
                json_str = base64.b64decode(res['base64']).decode('utf-8')
                result = json.loads(json_str)
                
                for item in result.get('result', []):
                    if item.get('status') == 1:
                        session = {
                            'id': item['id'],
                            'name': item['user']['realname']
                        }
                        self.sessions.append(session)
                
                print(f"📋 发现 {len(self.sessions)} 个进行中的会话")
            except:
                pass
    
    def close_session(self, session_id):
        """关闭会话"""
        url = 'https://qw.qiyukf.com/chat/api/session/closeWXCSSession'
        data = {
            'sessionId': session_id,
            'groupManageId': self.group_manage_id
        }
        cookies = {'___csrfToken': self.token}
        
        try:
            response = requests.post(url, data=data, cookies=cookies, verify=False, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def on_open(self, ws):
        print("🔗 已连接 Whistle WebSocket")
        print("👀 等待捕获七鱼请求...\n")
    
    def on_error(self, ws, error):
        print(f"❌ WebSocket 错误: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print("🔌 连接已关闭")
    
    def run(self):
        """启动监听"""
        ws = websocket.WebSocketApp(
            self.whistle_ws,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # 在后台线程运行
        threading.Thread(target=ws.run_forever, daemon=True).start()
        
        print("🎯 企微自动结束会话 - 实时监听模式")
        print("💡 提示：切换企微群并打开侧边栏，脚本会自动捕获并关闭会话\n")
        
        try:
            while True:
                time.sleep(1)
                
                # 如果有会话且有 token，提示用户
                if self.sessions and self.token and len(self.sessions) > 0:
                    print(f"\n⚡ 按 Enter 关闭 {len(self.sessions)} 个会话，或 Ctrl+C 退出")
                    input()
                    
                    success = 0
                    for session in list(self.sessions):
                        if self.close_session(session['id']):
                            print(f"✅ 已关闭: {session['name'][:30]}")
                            success += 1
                        else:
                            print(f"❌ 失败: {session['name'][:30]}")
                    
                    print(f"\n✨ 完成！成功关闭 {success}/{len(self.sessions)} 个会话")
                    self.sessions.clear()
                    
        except KeyboardInterrupt:
            print("\n\n👋 已退出")

if __name__ == '__main__':
    app = QiyuAutoClose()
    app.run()
