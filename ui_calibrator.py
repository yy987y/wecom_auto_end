#!/usr/bin/env python3
"""
UI 校准工具：首次校准时确认当前群名 + 当前聊天区。
"""
import json
from pathlib import Path

from ApplicationServices import (
    AXUIElementCreateApplication,
    kAXFocusedWindowAttribute,
    kAXValueAttribute,
    kAXTitleAttribute,
)

from wecom_monitor import (
    ax_copy,
    ax_str,
    find_wecom_app,
    get_group_name,
    get_messages,
    role,
    walk_collect,
)

WS = Path(__file__).parent
DATA_DIR = WS / 'data'
DATA_DIR.mkdir(exist_ok=True)
UI_MAPPING_FILE = DATA_DIR / 'ui_mapping.json'


def collect_candidates(focused):
    all_texts = walk_collect(
        focused,
        lambda el: role(el) in ['AXStaticText', 'AXTextField', 'AXTextArea'],
        max_depth=12,
    )

    path_groups = {}
    for el, path in all_texts:
        if 'window.0.26' in path:
            continue
        parts = path.split('.')
        prefix = '.'.join(parts[:4]) if len(parts) >= 4 else path
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if prefix not in path_groups:
            path_groups[prefix] = []
        if text:
            path_groups[prefix].append((path, text))

    candidates = []
    for prefix, items in sorted(path_groups.items()):
        if not items:
            continue
        samples = [text[:80] for _, text in items[:5]]
        candidates.append({
            'prefix': prefix,
            'count': len(items),
            'samples': samples,
        })
    return candidates


def prompt_choice(candidates, label):
    print(f'\n请选择{label}：')
    for idx, c in enumerate(candidates, 1):
        print(f'  {idx}. {c["prefix"]} ({c["count"]} 个文本)')
        for sample in c['samples'][:3]:
            print(f'     - {sample}')

    while True:
        choice = input(f'输入 {label} 编号: ').strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1]['prefix']
        print('输入无效，请重试。')


def confirm_preview(focused, chat_prefix):
    mapping = {
        'chat_prefix': chat_prefix,
        'session_list_prefix': None,
    }
    UI_MAPPING_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')

    group_name = get_group_name(focused)
    messages = get_messages(focused, debug=False)

    print('\n📌 首次校准确认结果')
    print(f'当前群名: {group_name or "(未识别)"}')
    print(f'解析消息数: {len(messages)}')
    print('最近消息预览:')
    if not messages:
        print('  (未解析到聊天内容)')
    else:
        for idx, msg in enumerate(messages[-8:], 1):
            sender = (msg.get('sender') or '').strip()
            content = (msg.get('content') or '').strip()
            body = (msg.get('body') or '').strip()
            line = body or f'{sender} {content}'.strip() or '(空)'
            print(f'  {idx}. {line[:160]}')

    print('\n请确认以上“群名 + 当前聊天区域”是否正确。')
    while True:
        choice = input('确认无误？(y/n): ').strip().lower()
        if choice in ('y', 'yes'):
            return mapping, group_name, messages
        if choice in ('n', 'no'):
            return None, group_name, messages
        print('输入无效，请输入 y 或 n。')


def main():
    app = find_wecom_app()
    if not app:
        print('❌ 未找到企业微信/WeCom，请先打开并聚焦到目标会话窗口。')
        return 1

    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)
    if not focused:
        print('❌ 未获取到焦点窗口。')
        return 1

    candidates = collect_candidates(focused)
    if not candidates:
        print('❌ 未扫描到候选区域。')
        return 1

    while True:
        print('\n🔍 扫描到以下候选聊天区域：')
        chat_prefix = prompt_choice(candidates, '聊天区')
        confirmed, group_name, messages = confirm_preview(focused, chat_prefix)
        if confirmed:
            print(f'\n✅ UI 映射已保存到: {UI_MAPPING_FILE}')
            print(json.dumps({
                **confirmed,
                'calibrated_group_name': group_name,
                'preview_message_count': len(messages),
            }, ensure_ascii=False, indent=2))
            return 0
        print('\n↩️ 预览不对，重新选择聊天区。')


if __name__ == '__main__':
    raise SystemExit(main())
