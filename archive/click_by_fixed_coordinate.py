#!/usr/bin/env python3
"""
使用 pyautogui 点击结束会话按钮
先激活企微窗口，确保点击有效
"""
import pyautogui
import time
import subprocess

# 先激活企微窗口
print("激活企业微信窗口...")
subprocess.run(['osascript', '-e', 'tell application "企业微信" to activate'], check=False)
time.sleep(0.5)

# 实际测量的坐标
END_SESSION_X = 1527
END_SESSION_Y = 847

print(f"🖱️  移动鼠标到: ({END_SESSION_X}, {END_SESSION_Y})")
pyautogui.moveTo(END_SESSION_X, END_SESSION_Y, duration=0.3)
time.sleep(0.2)

print(f"🖱️  点击结束会话按钮")
pyautogui.click()
print("✅ 已点击结束会话")

# 等待确认对话框
time.sleep(1.5)

# 点击确认按钮（通常在下方）
CONFIRM_X = END_SESSION_X
CONFIRM_Y = END_SESSION_Y + 100

print(f"🖱️  移动到确认按钮: ({CONFIRM_X}, {CONFIRM_Y})")
pyautogui.moveTo(CONFIRM_X, CONFIRM_Y, duration=0.3)
time.sleep(0.2)

print(f"🖱️  点击确认")
pyautogui.click()
print("✅ 已点击确认")
