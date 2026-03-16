#!/usr/bin/env python3
"""
企业微信结束会话工具 - 使用 pyautogui
"""
import sys
import json
import os
import pyautogui

CONFIG_FILE = os.path.expanduser("~/.wework_session_config.json")

def end_session():
    """执行结束会话"""
    if not os.path.exists(CONFIG_FILE):
        print("❌ 未找到配置文件，请先运行: python3 wework_end_session.py --setup")
        sys.exit(1)
    
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    
    btn1 = config["end_session_button"]
    btn2 = config["confirm_button"]
    
    print(f"点击结束会话按钮 ({btn1[0]}, {btn1[1]})...")
    pyautogui.click(btn1[0], btn1[1])
    
    pyautogui.sleep(1.0)
    
    print(f"点击确认按钮 ({btn2[0]}, {btn2[1]})...")
    pyautogui.click(btn2[0], btn2[1])
    
    print("✅ 完成！")

def setup_coordinates():
    """设置坐标"""
    print("=" * 60)
    print("企业微信结束会话 - 坐标设置")
    print("=" * 60)
    
    input("\n1. 请将鼠标移到【结束会话】按钮上，然后按回车...")
    btn1 = pyautogui.position()
    print(f"   ✅ 已记录: ({btn1.x}, {btn1.y})")
    
    input("\n2. 请将鼠标移到确认弹窗的【结束】按钮上，然后按回车...")
    btn2 = pyautogui.position()
    print(f"   ✅ 已记录: ({btn2.x}, {btn2.y})")
    
    config = {
        "end_session_button": [btn1.x, btn1.y],
        "confirm_button": [btn2.x, btn2.y]
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ 配置已保存到: {CONFIG_FILE}")
    print("现在可以运行: python3 wework_end_session_v2.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        setup_coordinates()
    else:
        end_session()
