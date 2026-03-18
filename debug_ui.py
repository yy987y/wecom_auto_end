#!/usr/bin/env python3
"""
调试脚本：检查企微 UI 元素路径
"""
from wecom_monitor import find_wecom_app, walk_collect, role, ax_str
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    kAXFocusedWindowAttribute,
    kAXValueAttribute,
    kAXTitleAttribute
)

app = find_wecom_app()
if not app:
    print("❌ 未找到企微")
    exit(1)

print(f"✅ 找到企微: {app.localizedName()}")

app_el = AXUIElementCreateApplication(app.processIdentifier())
focused = AXUIElementCopyAttributeValue(app_el, kAXFocusedWindowAttribute, None)[1]

if not focused:
    print("❌ 未获取到焦点窗口")
    exit(1)

print("✅ 获取到焦点窗口")
print("\n🔍 查找所有文本元素...")

all_texts = walk_collect(focused, lambda el: role(el) in ['AXStaticText', 'AXTextField', 'AXTextArea'], max_depth=12)

print(f"\n📊 总共找到 {len(all_texts)} 个文本元素")

# 按路径前缀分组
path_groups = {}
for el, path in all_texts:
    prefix = '.'.join(path.split('.')[:4])  # 前4级
    if prefix not in path_groups:
        path_groups[prefix] = []
    text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
    if text:
        path_groups[prefix].append((path, text[:30]))

print("\n📋 按路径前缀分组:")
for prefix, items in sorted(path_groups.items()):
    print(f"\n{prefix} ({len(items)} 个)")
    for path, text in items[:5]:  # 只显示前5个
        print(f"  {path} | {text}")
    if len(items) > 5:
        print(f"  ... 还有 {len(items)-5} 个")

# 重点检查聊天区域
print("\n\n🎯 聊天区域 (window.0.31.9) 的文本:")
chat_count = 0
for el, path in all_texts:
    if 'window.0.31.9' in path and 'window.0.26' not in path and 'window.0.31.9.9' not in path:
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if text:
            chat_count += 1
            if chat_count <= 20:
                print(f"  [{path}] {text[:40]}")

print(f"\n✅ 聊天区域共 {chat_count} 个文本元素")
