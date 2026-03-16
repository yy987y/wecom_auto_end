#!/usr/bin/env python3
"""
测试虚拟点击是否有效
会在配置的坐标位置进行虚拟点击，但不会移动鼠标
"""
import json
import time
from pathlib import Path
from wework_end_session import virtual_click, get_mouse_position

config_file = Path.home() / ".wework_session_config.json"

if not config_file.exists():
    print("❌ 配置文件不存在")
    exit(1)

with open(config_file) as f:
    config = json.load(f)

btn1 = config["end_session_button"]
btn2 = config["confirm_button"]

print("测试虚拟点击...")
print(f"当前鼠标位置: {get_mouse_position()}")
print(f"将虚拟点击: {btn1}")
print("注意：鼠标不会移动，但会在该位置产生点击事件")
print("")
input("按回车开始测试...")

print("虚拟点击结束会话按钮...")
virtual_click(btn1[0], btn1[1])
print(f"当前鼠标位置: {get_mouse_position()} (应该没变)")

time.sleep(1)

print("虚拟点击确认按钮...")
virtual_click(btn2[0], btn2[1])
print(f"当前鼠标位置: {get_mouse_position()} (应该没变)")

print("\n✅ 测试完成")
print("请检查企微是否成功结束了会话")
