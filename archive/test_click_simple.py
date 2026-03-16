#!/usr/bin/env python3
import json
import time
from pathlib import Path
from wework_end_session import virtual_click, get_mouse_position

config_file = Path.home() / ".wework_session_config.json"

with open(config_file) as f:
    config = json.load(f)

btn1 = config["end_session_button"]
btn2 = config["confirm_button"]

print(f"当前鼠标: {get_mouse_position()}")
print(f"点击 {btn1}...")
virtual_click(btn1[0], btn1[1])
print(f"鼠标位置: {get_mouse_position()}")

time.sleep(1)

print(f"点击 {btn2}...")
virtual_click(btn2[0], btn2[1])
print(f"鼠标位置: {get_mouse_position()}")
print("完成")
