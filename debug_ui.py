#!/usr/bin/env python3
"""
调试脚本：与主逻辑保持一致，检查企微 UI 元素路径 / 群名 / 聊天区域 / 解析结果
"""
from ApplicationServices import kAXChildrenAttribute, kAXTitleAttribute, kAXValueAttribute

from wecom_monitor import (
    ax_copy,
    ax_str,
    get_group_name,
    get_messages,
    get_primary_text,
    get_fresh_focused_window,
    inspect_ui,
    role,
)


app, focused, ctx = get_fresh_focused_window()
if not app:
    print('❌ 未找到企微')
    raise SystemExit(1)

print(f'✅ 找到企微: {app.localizedName()}')

if not focused:
    print('❌ 未获取到焦点窗口')
    raise SystemExit(1)

print('✅ 获取到焦点窗口')

window_title = ax_str(focused, kAXTitleAttribute) or ax_str(focused, kAXValueAttribute) or '(无标题)'
print(f'🪟 当前窗口标题: {window_title}')

system_focused_ui = ctx.get('system_focused_ui')
system_focused_app = ctx.get('system_focused_app')
print(f"🧭 system-wide focused ui role: {role(system_focused_ui) if system_focused_ui else '(none)'}")
print(f"🧭 system-wide focused app title: {ax_str(system_focused_app, kAXTitleAttribute) or ax_str(system_focused_app, kAXValueAttribute) or '(none)'}")
print(f"🧭 focused window role: {role(focused)}")
print(f"🧭 focused window children: {len(ax_copy(focused, kAXChildrenAttribute) or [])}")

context = inspect_ui(focused)
group_name = get_primary_text(context['group_infos'], context['selected']['group_name_prefix'])
print(f'👥 主逻辑识别群名: {group_name}')

print('\n🔍 查找所有文本元素...')
print(f'📊 总共找到 {len(context["entries"])} 个文本元素')
print(f'🌐 检测语言: {context["language"]}')

print('\n📋 按路径前缀分组:')
for prefix, info in sorted(context['group_infos'].items()):
    print(f'\n{prefix} ({info["count"]} 个)')
    for path, text in info['items'][:5]:
        print(f'  {path} | {text[:80]}')
    if info['count'] > 5:
        print(f'  ... 还有 {info["count"] - 5} 个')

print('\n🎯 自动识别结果:')
print(f'  会话列表: {context["selected"]["session_list_prefix"] or "(未识别)"}')
print(f'  群名区域: {context["selected"]["group_name_prefix"] or "(未识别)"}')
print(f'  群信息区域: {context["selected"]["group_meta_prefix"] or "(未识别)"}')
print(f'  聊天区: {context["selected"]["chat_prefix"] or "(未识别)"}')
print(f'  主消息链: {context["selected"]["chat_main_thread_prefix"] or "(未识别)"}')

print('\n🧾 主消息链原始文本（末尾样本）:')
for path, text in context['chat_items'][-20:]:
    print(f'  [{path}] {text[:120]}')

print('\n📈 聊天区候选排行:')
for candidate in context['chat_candidates']:
    print(f'  - {candidate["prefix"]} | score={candidate["score"]} | count={candidate["count"]}')
    for sample in candidate['samples']:
        print(f'      {sample}')

print('\n🧠 主逻辑 get_messages(debug=True) 输出:')
messages = get_messages(focused, debug=True)

print(f'\n✅ 主逻辑最终解析出 {len(messages)} 条消息')
print('\n📝 最后 10 条解析结果:')
for idx, msg in enumerate(messages[-10:], 1):
    sender = (msg.get('sender') or '')[:40]
    content = (msg.get('content') or '')[:120]
    body = (msg.get('body') or '')[:120]
    print(f'  {idx}. sender=[{sender}] content=[{content}] body=[{body}]')

print('\n📌 get_group_name() 直接调用结果:')
print(f'  {get_group_name(focused) or "(未识别)"}')
