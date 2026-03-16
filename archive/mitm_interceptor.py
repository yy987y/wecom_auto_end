#!/usr/bin/env python3
"""
使用 mitmproxy 监听企微侧边栏的网络请求
捕获七鱼的会话信息
"""
from mitmproxy import http
import json
import re

class QiyuInterceptor:
    def __init__(self):
        self.session_info = None
    
    def request(self, flow: http.HTTPFlow) -> None:
        """拦截请求"""
        # 只关注七鱼的请求
        if 'qiyukf.com' not in flow.request.pretty_url:
            return
        
        print(f"[请求] {flow.request.method} {flow.request.pretty_url}")
    
    def response(self, flow: http.HTTPFlow) -> None:
        """拦截响应"""
        if 'qiyukf.com' not in flow.request.pretty_url:
            return
        
        url = flow.request.pretty_url
        
        # 捕获 session/latest 响应
        if 'session/latest' in url:
            try:
                data = json.loads(flow.response.text)
                session_id = data.get('id') or data.get('sessionId')
                chat_group_id = data.get('chatGroupId')
                
                if session_id and chat_group_id:
                    self.session_info = {
                        'sessionId': session_id,
                        'chatGroupId': chat_group_id
                    }
                    print(f"✅ 捕获会话信息: {self.session_info}")
                    
                    # 保存到文件
                    with open('/tmp/qiyu_session.json', 'w') as f:
                        json.dump(self.session_info, f)
            except:
                pass
        
        # 捕获其他可能包含会话信息的接口
        if any(x in url for x in ['group/list', 'session/list', 'wxwork/group']):
            print(f"[响应] {url}")
            print(f"  状态: {flow.response.status_code}")
            if flow.response.text:
                print(f"  内容: {flow.response.text[:200]}...")

addons = [QiyuInterceptor()]
