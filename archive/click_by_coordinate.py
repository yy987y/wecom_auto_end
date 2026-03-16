#!/usr/bin/env python3
"""
使用 pyautogui 通过坐标点击结束会话按钮
"""
import pyautogui
import time

# 获取屏幕尺寸
screen_width, screen_height = pyautogui.size()
print(f"屏幕尺寸: {screen_width}x{screen_height}")

# 查找"结束会话"文字在屏幕上的位置
print("正在查找'结束会话'按钮...")
try:
    # 尝试定位按钮（需要截图）
    location = pyautogui.locateOnScreen('结束会话', confidence=0.8)
    if location:
        # 点击按钮中心
        center = pyautogui.center(location)
        print(f"找到按钮位置: {center}")
        pyautogui.click(center)
        print("✅ 已点击结束会话")
        
        # 等待确认对话框
        time.sleep(1)
        
        # 查找并点击确认按钮
        confirm_location = pyautogui.locateOnScreen('确定', confidence=0.8)
        if confirm_location:
            confirm_center = pyautogui.center(confirm_location)
            pyautogui.click(confirm_center)
            print("✅ 已点击确认")
    else:
        print("❌ 未找到按钮")
except Exception as e:
    print(f"❌ 错误: {e}")
    print("提示：pyautogui 的 locateOnScreen 需要安装 opencv-python")
    print("或者使用固定坐标点击")
