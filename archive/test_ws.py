#!/usr/bin/env python3
"""测试 Whistle WebSocket 连接"""
import websocket
import time

def on_message(ws, message):
    print(f"收到消息: {message[:100]}")

def on_open(ws):
    print("✅ WebSocket 已连接")

def on_error(ws, error):
    print(f"❌ 错误: {error}")

ws = websocket.WebSocketApp(
    "ws://127.0.0.1:8899/cgi-bin/socket.io/?transport=websocket",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error
)

print("🔗 连接 Whistle WebSocket...")
ws.run_forever()
