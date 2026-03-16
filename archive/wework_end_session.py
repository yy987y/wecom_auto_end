#!/usr/bin/env python3
"""
企业微信结束会话工具 - 支持不同分辨率
使用方法：
1. 首次运行：python3 wework_end_session.py --setup
2. 正常使用：python3 wework_end_session.py
"""
import sys
import json
import os
import time
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventGetLocation,
    CGEventCreate,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGHIDEventTap
)
from AppKit import NSWorkspace

CONFIG_FILE = os.path.expanduser("~/.wework_session_config.json")

def activate_wework():
    """激活企业微信窗口"""
    workspace = NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        if "企业微信" in app.localizedName() or "WeCom" in app.localizedName():
            app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
            time.sleep(0.2)
            return True
    return False

def get_mouse_position():
    """获取当前鼠标位置"""
    event = CGEventCreate(None)
    pos = CGEventGetLocation(event)
    return (pos.x, pos.y)

def virtual_click(x, y):
    """虚拟点击（不移动鼠标）"""
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), 0)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), 0)
    
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    CGEventPost(kCGHIDEventTap, up)

def setup_coordinates():
    """设置坐标"""
    print("=" * 60)
    print("企业微信结束会话 - 坐标设置")
    print("=" * 60)
    
    input("\n1. 请将鼠标移到【结束会话】按钮上，然后按回车...")
    btn1 = get_mouse_position()
    print(f"   ✅ 已记录: ({btn1[0]}, {btn1[1]})")
    
    input("\n2. 请将鼠标移到确认弹窗的【结束】按钮上，然后按回车...")
    btn2 = get_mouse_position()
    print(f"   ✅ 已记录: ({btn2[0]}, {btn2[1]})")
    
    config = {
        "end_session_button": btn1,
        "confirm_button": btn2
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ 配置已保存到: {CONFIG_FILE}")
    print("现在可以运行: python3 wework_end_session.py")

def end_session():
    """执行结束会话"""
    if not os.path.exists(CONFIG_FILE):
        print("❌ 未找到配置文件，请先运行: python3 wework_end_session.py --setup")
        sys.exit(1)
    
    # 激活企业微信
    print("激活企业微信窗口...")
    if not activate_wework():
        print("⚠️  未找到企业微信进程")
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    btn1 = config["end_session_button"]
    btn2 = config["confirm_button"]
    
    print("点击结束会话按钮...")
    virtual_click(btn1[0], btn1[1])
    
    time.sleep(0.3)
    
    print("点击确认按钮...")
    virtual_click(btn2[0], btn2[1])
    
    print("✅ 完成！")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_coordinates()
    else:
        end_session()
