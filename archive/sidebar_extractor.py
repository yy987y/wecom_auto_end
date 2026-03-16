#!/usr/bin/env python3
"""
从企微侧边栏提取会话信息
"""
import re
from Cocoa import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    kAXFocusedWindowAttribute,
    kAXChildrenAttribute,
    kAXRoleAttribute,
    kAXValueAttribute,
    kAXURLAttribute,
    kAXTitleAttribute
)

def ax_copy(element, attr):
    """安全获取 AX 属性"""
    try:
        err, val = AXUIElementCopyAttributeValue(element, attr, None)
        return val if err == 0 else None
    except:
        return None

def find_wecom():
    """查找企微进程"""
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        name = app.localizedName()
        if name and ('WeChat' in name or '企业微信' in name):
            return app
    return None

def find_webview_url(element, depth=0, max_depth=15):
    """递归查找 WebView 的 URL"""
    if depth > max_depth:
        return None
    
    # 尝试获取 URL
    url = ax_copy(element, kAXURLAttribute)
    if url and 'qiyukf.com' in str(url):
        return str(url)
    
    # 尝试获取 value（有些 WebView 把 URL 放在 value 里）
    value = ax_copy(element, kAXValueAttribute)
    if value and isinstance(value, str) and 'qiyukf.com' in value:
        return value
    
    # 递归子元素
    children = ax_copy(element, kAXChildrenAttribute)
    if children:
        for child in children:
            result = find_webview_url(child, depth + 1, max_depth)
            if result:
                return result
    
    return None

def extract_session_from_url(url):
    """从 URL 中提取会话信息"""
    if not url:
        return None
    
    # 尝试提取常见参数
    params = {}
    
    # sessionId
    match = re.search(r'sessionId[=:](\d+)', url)
    if match:
        params['sessionId'] = match.group(1)
    
    # chatGroupId
    match = re.search(r'chatGroupId[=:](\d+)', url)
    if match:
        params['chatGroupId'] = match.group(1)
    
    # groupManageId
    match = re.search(r'groupManageId[=:](\d+)', url)
    if match:
        params['groupManageId'] = match.group(1)
    
    return params if params else None

def get_sidebar_session_info():
    """从企微侧边栏获取会话信息"""
    app = find_wecom()
    if not app:
        print("❌ 未找到企业微信")
        return None
    
    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)
    
    if not focused:
        print("❌ 未找到焦点窗口")
        return None
    
    # 查找 WebView URL
    url = find_webview_url(focused)
    if not url:
        print("⚠️  未找到七鱼 WebView URL")
        return None
    
    print(f"✅ 找到 URL: {url[:100]}...")
    
    # 从 URL 提取会话信息
    session_info = extract_session_from_url(url)
    if session_info:
        print(f"✅ 提取到会话信息: {session_info}")
    else:
        print("⚠️  URL 中未找到会话参数")
    
    return session_info

if __name__ == '__main__':
    info = get_sidebar_session_info()
    if info:
        print(f"\n会话信息: {info}")
