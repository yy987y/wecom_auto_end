#!/usr/bin/env python3
"""
尝试从企微 WebView 中提取会话信息
"""
import subprocess

# 尝试通过 AppleScript 获取 WebView 内容
script = '''
tell application "System Events"
    tell process "企业微信"
        -- 获取窗口信息
        set windowCount to count of windows
        return windowCount
    end tell
end tell
'''

result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
print(f"窗口数量: {result.stdout.strip()}")
print(f"错误: {result.stderr.strip()}")
