#!/usr/bin/env python3
"""
调试虚拟点击 - 显示详细信息
"""
import json
import time
from pathlib import Path
from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    CGEventGetLocation,
    CGEventCreate,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGHIDEventTap
)

def get_mouse_position():
    event = CGEventCreate(None)
    pos = CGEventGetLocation(event)
    return (pos.x, pos.y)

def click_at(x, y):
    """简单的点击，不恢复位置"""
    print(f"  创建点击事件在 ({x}, {y})")
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), 0)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), 0)
    
    print(f"  发送 MouseDown")
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.1)
    
    print(f"  发送 MouseUp")
    CGEventPost(kCGHIDEventTap, up)
    print(f"  点击完成")

config_file = Path.home() / ".wework_session_config.json"

with open(config_file) as f:
    config = json.load(f)

btn1 = config["end_session_button"]
btn2 = config["confirm_button"]

print("=" * 60)
print("调试虚拟点击")
print("=" * 60)
print(f"配置的结束会话按钮: {btn1}")
print(f"配置的确认按钮: {btn2}")
print(f"当前鼠标位置: {get_mouse_position()}")
print("")

input("按回车点击结束会话按钮...")
click_at(btn1[0], btn1[1])
print(f"点击后鼠标位置: {get_mouse_position()}")
print("")

input("按回车点击确认按钮...")
click_at(btn2[0], btn2[1])
print(f"点击后鼠标位置: {get_mouse_position()}")
print("")
print("测试完成")
