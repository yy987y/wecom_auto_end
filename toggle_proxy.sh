#!/bin/bash
# 快速启用/禁用系统代理

INTERFACE="Wi-Fi"  # 或 "Ethernet"

if [ "$1" == "on" ]; then
    echo "🔛 启用系统代理..."
    networksetup -setwebproxy "$INTERFACE" 127.0.0.1 8080
    networksetup -setsecurewebproxy "$INTERFACE" 127.0.0.1 8080
    echo "✅ 代理已启用"
elif [ "$1" == "off" ]; then
    echo "🔴 禁用系统代理..."
    networksetup -setwebproxystate "$INTERFACE" off
    networksetup -setsecurewebproxystate "$INTERFACE" off
    echo "✅ 代理已禁用"
else
    echo "用法: $0 [on|off]"
fi
