#!/usr/bin/env python3
"""
测试：监控企微侧边栏 WebView 的内容
"""
import time
from Cocoa import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    kAXFocusedWindowAttribute,
    kAXChildrenAttribute,
    kAXRoleAttribute,
    kAXValueAttribute,
    kAXTitleAttribute,
    kAXURLAttribute
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
        if 'WeChat' in app.localizedName() or '企业微信' in app.localizedName():
            return app
    return None

def explore_element(element, depth=0, max_depth=10):
    """递归探索元素树"""
    if depth > max_depth:
        return
    
    role = ax_copy(element, kAXRoleAttribute)
    title = ax_copy(element, kAXTitleAttribute)
    value = ax_copy(element, kAXValueAttribute)
    url = ax_copy(element, kAXURLAttribute)
    
    indent = "  " * depth
    
    # 打印有价值的信息
    if role:
        print(f"{indent}[{role}]", end="")
        if title:
            print(f" title={title[:50]}", end="")
        if url:
            print(f" url={url[:80]}", end="")
        if value and isinstance(value, str) and len(value) < 100:
            print(f" value={value[:50]}", end="")
        print()
    
    # 递归子元素
    children = ax_copy(element, kAXChildrenAttribute)
    if children:
        for child in children:
            explore_element(child, depth + 1, max_depth)

def main():
    app = find_wecom()
    if not app:
        print("❌ 未找到企业微信")
        return
    
    print(f"✅ 找到企业微信: {app.localizedName()}")
    
    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)
    
    if not focused:
        print("❌ 未找到焦点窗口")
        return
    
    print("\n🔍 探索窗口结构...")
    explore_element(focused, max_depth=8)

if __name__ == '__main__':
    main()
