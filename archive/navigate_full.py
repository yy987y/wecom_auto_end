#!/usr/bin/env python3
"""
完整导航：打开侧边栏 → 点击网易智企 → 处理重新登录
"""
import time
from Cocoa import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    kAXFocusedWindowAttribute,
    kAXChildrenAttribute,
    kAXParentAttribute,
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
    return None

def find_element(element, matcher, depth=0, max_depth=8):
    """递归查找元素"""
    if depth > max_depth:
        return None
    if matcher(element):
        return element
    children = ax_copy(element, kAXChildrenAttribute)
    if children and len(children) < 150:
        for child in children:
            result = find_element(child, matcher, depth + 1, max_depth)
            if result:
                return result
    return None

def click_sidebar_button(focused):
    """点击侧边栏按钮（Quick Meeting 右侧第13个兄弟节点）"""
    # 查找 Quick Meeting 按钮
    qm = find_element(focused, lambda e: (
        ax_copy(e, kAXRoleAttribute) == 'AXButton' and
        ('Quick Meeting' in str(ax_copy(e, kAXTitleAttribute) or '') or
         '快速会议' in str(ax_copy(e, kAXTitleAttribute) or ''))
    ))
    
    if not qm:
        print("⚠️  未找到 Quick Meeting")
        return False
    
    # 获取父节点
    parent = ax_copy(qm, kAXParentAttribute)
    if not parent:
        return False
    
    # 获取所有兄弟节点
    siblings = ax_copy(parent, kAXChildrenAttribute)
    if not siblings or len(siblings) < 14:
        return False
    
    # 点击第13个兄弟节点（索引13）
    btn = siblings[13]
    if ax_copy(btn, kAXRoleAttribute) == 'AXButton':
        print("✅ 找到侧边栏按钮")
        AXUIElementPerformAction(btn, kAXPressAction)
        return True
    
    return False

def navigate_to_qiyu():
    """完整导航流程"""
    app = find_wecom()
    if not app:
        print("❌ 未找到企业微信")
        return False
    
    app.activateWithOptions_(1 << 1)
    time.sleep(0.5)
    
    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)
    
    if not focused:
        print("❌ 未找到焦点窗口")
        return False
    
    # 1. 打开侧边栏
    print("🔍 打开侧边栏...")
    if click_sidebar_button(focused):
        print("✅ 侧边栏已打开")
        time.sleep(2)  # 增加等待时间
    else:
        print("⚠️  侧边栏可能已打开")
        time.sleep(1)
    
    # 2. 点击网易智企
    print("🔍 查找网易智企...")
    qiyu = find_element(focused, lambda e: (
        '网易' in str(ax_copy(e, kAXTitleAttribute) or '') or
        '智企' in str(ax_copy(e, kAXTitleAttribute) or '')
    ))
    
    if not qiyu:
        print("❌ 未找到网易智企")
        return False
    
    print("✅ 找到网易智企，点击...")
    AXUIElementPerformAction(qiyu, kAXPressAction)
    time.sleep(2)
    
    # 3. 检查是否需要重新登录
    print("🔍 检查是否需要登录...")
    login_btn = find_element(focused, lambda e: (
        '登录' in str(ax_copy(e, kAXTitleAttribute) or '') or
        'login' in str(ax_copy(e, kAXTitleAttribute) or '').lower()
    ))
    
    if login_btn:
        print("✅ 找到登录按钮，点击...")
        AXUIElementPerformAction(login_btn, kAXPressAction)
        time.sleep(2)
    
    print("✅ 导航完成")
    return True

if __name__ == '__main__':
    navigate_to_qiyu()
