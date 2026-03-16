#!/usr/bin/env python3
"""
网易七鱼 API 封装
通过 HTTP API 直接结束会话，不依赖 UI 自动化
"""
import requests
import json
import re
from pathlib import Path

class QiyuAPI:
    def __init__(self, code='wyzqkj', cookie_file=None):
        self.code = code
        self.base_url = 'https://qw.qiyukf.com'
        self.session = requests.Session()
        self.token = None
        self.cookie_file = cookie_file or Path(__file__).parent / 'data' / '.qiyu_cookies.json'
        
    def extract_cookies_from_charles(self, meta_file):
        """从 Charles 抓包文件提取 Cookie"""
        with open(meta_file) as f:
            data = json.load(f)
        
        cookies = {}
        headers = data.get('request', {}).get('header', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'cookie':
                # 解析 cookie 字符串
                parts = header['value'].split('=', 1)
                if len(parts) == 2:
                    cookies[parts[0]] = parts[1]
        
        return cookies
    
    def load_cookies_from_file(self):
        """从文件加载 Cookie"""
        if self.cookie_file.exists():
            with open(self.cookie_file) as f:
                cookies = json.load(f)
                for name, value in cookies.items():
                    self.session.cookies.set(name, value)
                # 提取 token
                self.token = cookies.get('___csrfToken')
                return True
        return False
    
    def save_cookies(self, cookies):
        """保存 Cookie 到文件"""
        self.cookie_file.parent.mkdir(exist_ok=True)
        with open(self.cookie_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f'✅ Cookie 已保存到: {self.cookie_file}')
    
    def get_latest_session(self, user_id):
        """
        获取最新会话信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            dict: 会话信息 {sessionId, groupManageId} 或 None
        """
        if not self.token:
            print('❌ 缺少 CSRF Token')
            return None
            
        url = f'{self.base_url}/chat/api/session/latest'
        params = {
            'code': self.code,
            'userId': user_id,
            'token': self.token
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # 解析响应获取 sessionId 和 groupManageId
                if data and isinstance(data, dict):
                    session_id = data.get('sessionId') or data.get('id')
                    group_manage_id = data.get('groupManageId') or data.get('groupId')
                    if session_id and group_manage_id:
                        return {
                            'sessionId': session_id,
                            'groupManageId': group_manage_id
                        }
                print(f'⚠️  响应中未找到会话信息: {data}')
                return None
            else:
                print(f'❌ 获取会话失败: {response.status_code}')
                return None
        except Exception as e:
            print(f'❌ 请求异常: {e}')
            return None

    
    def get_active_sessions_by_chatgroup(self, chat_group_id):
        """通过 chatGroupId 查询活跃会话"""
        # TODO: 需要查询接口的 URL
        # 可能的接口：/chat/api/session/list 或 /wxwork/group/sessions
        print(f"⚠️  需要实现：通过 chatGroupId {chat_group_id} 查询活跃会话")
        return []
    
    def get_sessions_by_group_name(self, group_name):
        """通过群名查询活跃会话"""
        # TODO: 需要你提供管理后台查询接口的 URL
        # 从 info.log 看，应该有一个接口可以通过群名查询会话列表
        print(f"⚠️  需要实现：通过群名 '{group_name}' 查询会话的接口")
        return []
    
    def close_session(self, session_id, group_manage_id, token=None):
        """
        结束会话
        
        Args:
            session_id: 会话ID
            group_manage_id: 群管理ID
            token: CSRF Token (可选，如果不提供则使用已加载的)
        
        Returns:
            bool: 是否成功
        """
        token = token or self.token
        if not token:
            print('❌ 缺少 CSRF Token')
            return False
            
        url = f'{self.base_url}/chat/api/session/closeWXCSSession'
        params = {
            'code': self.code,
            'token': token
        }
        data = {
            'sessionId': session_id,
            'groupManageId': group_manage_id
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Origin': 'https://qw.qiyukf.com',
            'Referer': 'https://qw.qiyukf.com/wxwork/group/list'
        }
        
        try:
            response = self.session.post(url, params=params, data=data, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f'✅ 成功结束会话: {session_id}')
                return True
            else:
                print(f'❌ 结束会话失败: {response.status_code} - {response.text}')
                return False
        except Exception as e:
            print(f'❌ 请求异常: {e}')
            return False
    
    def close_current_session(self, user_id):
        """
        获取并结束当前会话
        
        Args:
            user_id: 用户ID
        
        Returns:
            bool: 是否成功
        """
        print(f'获取用户 {user_id} 的最新会话...')
        session_info = self.get_latest_session(user_id)
        if not session_info:
            print('❌ 无法获取会话信息')
            return False
        
        session_id = session_info['sessionId']
        group_manage_id = session_info['groupManageId']
        print(f'会话信息: sessionId={session_id}, groupManageId={group_manage_id}')
        
        return self.close_session(session_id, group_manage_id)

if __name__ == '__main__':
    # 测试
    api = QiyuAPI()
    if api.load_cookies_from_file():
        print('✅ Cookie 已加载')
        print(f'Token: {api.token}')
        # 测试获取会话（需要提供 userId）
        # api.close_current_session('40605777273')
    else:
        print('⚠️  未找到 Cookie 文件')

