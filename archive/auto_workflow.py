#!/usr/bin/env python3
"""
企微自动结束会话 - 完整流程
监控企微群切换 -> 自动打开侧边栏 -> 捕获会话数据 -> 判断并关闭会话
"""
import subprocess
import time
import json
import requests
import warnings
from pathlib import Path

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class WeChatAutoClose:
    def __init__(self):
        self.config_file = Path(__file__).parent / 'config.json'
        self.whistle_port = 8899
        self.group_manage_id = 6275817
        
    def start_whistle(self):
        """启动 Whistle 代理"""
        print("🚀 启动 Whistle...")
        subprocess.Popen(['w2', 'start'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        print("✅ Whistle 已启动")
    
    def monitor_group_switch(self):
        """监控企微群切换（通过 AppleScript）"""
        script = '''
        tell application "System Events"
            tell process "企业微信"
                set frontmost to true
                -- 检测当前窗口标题变化
                return name of front window
            end tell
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        return result.stdout.strip()
    
    def click_sidebar_and_open_qiyu(self):
        """点击侧边栏并打开网易智企"""
        print("  📱 打开侧边栏...")
        subprocess.run([
            'swift',
            str(Path(__file__).parent / 'wecom_click_sidebar_candidate.swift')
        ], check=True)
        time.sleep(2)
        print("  ✅ 已打开网易智企")
    
    def get_whistle_sessions(self):
        """从 Whistle 获取会话数据"""
        url = f'http://127.0.0.1:{self.whistle_port}/cgi-bin/get-data'
        try:
            response = requests.get(url, timeout=5)
            # 解析 Whistle 数据，提取 sessionId 和 token
            # 这里需要根据实际 Whistle API 调整
            return []
        except:
            return []
    
    def close_session(self, session_id, token):
        """关闭单个会话"""
        url = 'https://qw.qiyukf.com/chat/api/session/closeWXCSSession'
        data = {
            'sessionId': session_id,
            'groupManageId': self.group_manage_id
        }
        cookies = {'___csrfToken': token}
        
        try:
            response = requests.post(url, data=data, cookies=cookies, verify=False, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        """主流程"""
        print("🎯 企微自动结束会话启动\n")
        
        # 1. 启动 Whistle
        self.start_whistle()
        
        # 2. 监控群切换
        print("\n👀 监控企微群切换...")
        last_group = None
        
        while True:
            current_group = self.monitor_group_switch()
            
            if current_group != last_group and current_group:
                print(f"\n🔄 检测到群切换: {current_group}")
                last_group = current_group
                
                # 3. 打开侧边栏
                self.click_sidebar_and_open_qiyu()
                
                # 4. 等待 Whistle 捕获数据
                time.sleep(3)
                
                # 5. 获取会话并关闭
                sessions = self.get_whistle_sessions()
                if sessions:
                    print(f"  📋 发现 {len(sessions)} 个会话")
                    for session in sessions:
                        if self.close_session(session['id'], session['token']):
                            print(f"  ✅ 已关闭会话 {session['id']}")
                
            time.sleep(1)

if __name__ == '__main__':
    app = WeChatAutoClose()
    app.run()
