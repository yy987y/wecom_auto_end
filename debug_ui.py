#!/usr/bin/env python3
"""
调试脚本：与主逻辑保持一致，检查企微 UI 元素路径 / 群名 / 聊天区域 / 解析结果
"""
from wecom_monitor import (
    find_wecom_app,
    walk_collect,
    role,
    ax_str,
    get_group_name,
    get_messages,
)
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    kAXFocusedWindowAttribute,
    kAXValueAttribute,
    kAXTitleAttribute,
)


def build_path_groups(focused):
    all_texts = walk_collect(
        focused,
        lambda el: role(el) in ['AXStaticText', 'AXTextField', 'AXTextArea'],
        max_depth=12,
    )

    is_chinese = False
    for el, path in all_texts[:50]:
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if '群聊' in text or '单聊' in text or '外部' in text:
            is_chinese = True
            break

    path_groups = {}
    for el, path in all_texts:
        if 'window.0.26' in path:
            continue
        parts = path.split('.')
        prefix = '.'.join(parts[:4]) if len(parts) >= 4 else path

        if is_chinese and prefix == 'window.0.31.2':
            continue

        if prefix not in path_groups:
            path_groups[prefix] = []

        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if text:
            path_groups[prefix].append((path, text))

    return all_texts, path_groups, is_chinese


app = find_wecom_app()
if not app:
    print('❌ 未找到企微')
    exit(1)

print(f'✅ 找到企微: {app.localizedName()}')

# 每次运行都重新创建 app/focused 对象，避免复用旧引用
app_el = AXUIElementCreateApplication(app.processIdentifier())
focused = AXUIElementCopyAttributeValue(app_el, kAXFocusedWindowAttribute, None)[1]

if not focused:
    print('❌ 未获取到焦点窗口')
    exit(1)

print('✅ 获取到焦点窗口')

window_title = ax_str(focused, kAXTitleAttribute) or ax_str(focused, kAXValueAttribute) or '(无标题)'
print(f'🪟 当前窗口标题: {window_title}')

current_group = get_group_name(focused)
print(f'👥 主逻辑识别群名: {current_group}')

print('\n🔍 查找所有文本元素...')
all_texts, path_groups, is_chinese = build_path_groups(focused)
print(f'📊 总共找到 {len(all_texts)} 个文本元素')
print(f"🌐 检测语言: {'中文' if is_chinese else '英文'}")

print('\n📋 按路径前缀分组:')
for prefix, items in sorted(path_groups.items()):
    print(f'\n{prefix} ({len(items)} 个)')
    for path, text in items[:5]:
        print(f'  {path} | {text[:60]}')
    if len(items) > 5:
        print(f'  ... 还有 {len(items)-5} 个')

if path_groups:
    chat_prefix = max(path_groups.keys(), key=lambda k: len(path_groups[k]))
    chat_texts = path_groups[chat_prefix]

    print(f'\n\n🎯 主逻辑将选择聊天区域: {chat_prefix}')
    print(f'📦 该区域原始文本数: {len(chat_texts)}')

    preview = chat_texts[-30:] if len(chat_texts) > 30 else chat_texts
    print('\n🧾 主逻辑实际使用的原始文本（末尾样本）:')
    for path, text in preview[-20:]:
        print(f'  [{path}] {text[:100]}')
else:
    print('\n❌ 未找到任何可用路径分组')

print('\n\n🧠 主逻辑 get_messages(debug=True) 输出:')
messages = get_messages(focused, debug=True)

print(f'\n✅ 主逻辑最终解析出 {len(messages)} 条消息')
print('\n📝 最后 10 条解析结果:')
for i, msg in enumerate(messages[-10:], 1):
    sender = (msg.get('sender') or '')[:40]
    content = (msg.get('content') or '')[:100]
    print(f'  {i}. sender=[{sender}] content=[{content}]')
