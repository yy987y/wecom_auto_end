#!/usr/bin/env python3
"""
自动导航到网易智企侧边栏（简化版）
"""
import time
import subprocess
from Cocoa import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    kAXFocusedWindowAttribute,
    kAXChildrenAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
    kAXPressAction
)

def ax_copy(element, attr):
    try:
        err, val = AXUIElementCopyAttributeValue(element, attr, None)
        return val if err == 0 else None
    except:
        return None

def find_wecom():
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        bundle_id = app.bundleIdentifier()
        if bundle_id and 'WeWorkMac' in bundle_id:
            return app
        name = app.localizedName()
        if name and ('WeChat' in name or '企业微信' in name or 'WeWork' in name):
            return app
    return None

def find_qiyu_tab(element, depth=0, max_depth=15):
    """递归查找网易智企标签"""
    if depth > max_depth:
        return None
    
    role = ax_copy(element, kAXRoleAttribute)
    title = ax_copy(element, kAXTitleAttribute)
    
    # 查找包含"网易"或"智企"的按钮/标签
    if title and isinstance(title, str):
        if '网易' in title or '智企' in title or 'qiyu' in title.lower():
            return element
    
    children = ax_copy(element, kAXChildrenAttribute)
    if children:
        for child in children:
            result = find_qiyu_tab(child, depth + 1, max_depth)
            if result:
                return result
    
    return None

def navigate_to_qiyu():
    """导航到网易智企侧边栏"""
    app = find_wecom()
    if not app:
        print("❌ 未找到企业微信")
        return False
    
    # 激活企微窗口
    app.activateWithOptions_(1 << 1)
    time.sleep(0.5)
    
    # 使用 AppleScript 打开侧边栏（如果有快捷键的话）
    # 或者直接查找标签
    
    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)
    
    if not focused:
        print("❌ 未找到焦点窗口")
        return False
    
    print("🔍 查找网易智企标签...")
    qiyu_tab = find_qiyu_tab(focused)
    
    if not qiyu_tab:
        print("❌ 未找到网易智企标签")
        return False
    
    title = ax_copy(qiyu_tab, kAXTitleAttribute)
    print(f"✅ 找到标签: {title}")
    print("🖱️  点击标签...")
    
    # 点击标签
    AXUIElementPerformAction(qiyu_tab, kAXPressAction)
    time.sleep(2)
    
    print("✅ 导航完成")
    return True

if __name__ == '__main__':
    navigate_to_qiyu()
