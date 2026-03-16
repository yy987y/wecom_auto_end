#!/usr/bin/env python3
"""
通过 JavaScript 调用网易智企的 closeSession 接口
使用 osascript 执行 JavaScript
"""
import subprocess
import sys

# 会话 ID（需要从实际会话中获取）
session_id = 100000626355  # 这是示例 ID，需要替换为实际的会话 ID

# JavaScript 代码
js_code = f"""
var iframe = document.querySelector('iframe');
if (iframe && iframe.contentWindow) {{
    iframe.contentWindow.postMessage({{
        method: 'closeSession',
        params: {{
            type: 'close',
            id: {session_id}
        }}
    }}, '*');
    console.log('✅ 已发送结束会话消息');
}} else {{
    console.log('❌ 未找到 iframe');
}}
"""

print(f"尝试结束会话 ID: {session_id}")
print("注意：这需要在企微的 WebView 中执行")
print(f"JavaScript 代码:\n{js_code}")

# 注意：企微可能不支持直接执行 JavaScript
# 这个方案需要进一步研究如何注入 JavaScript 到企微的 WebView
print("\n⚠️  企微可能不支持直接执行 JavaScript")
print("需要研究如何注入代码到 CEF WebView")
