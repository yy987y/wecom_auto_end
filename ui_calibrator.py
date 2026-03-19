#!/usr/bin/env python3
"""
UI 校准工具：首次校准时确认当前群名 + 当前聊天区预览。
"""
import json
from datetime import datetime
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
    role,
    walk_collect,
    get_group_name,
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
            'items': items,
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
            return candidates[int(choice) - 1]
        print('输入无效，请重试。')


def build_chat_preview(candidate):
    chat_prefix = candidate['prefix']
    chat_texts = candidate['items']

    if chat_prefix == 'window.0.31.9':
        main_thread_prefix = 'window.0.31.9.0.0.0.'
        filtered_chat_texts = [(path, text) for path, text in chat_texts if path.startswith(main_thread_prefix)]
        if filtered_chat_texts:
            chat_texts = filtered_chat_texts

    preview = chat_texts[-12:] if len(chat_texts) > 12 else chat_texts
    return chat_texts, preview


def confirm_current_context(group_name, candidate):
    chat_texts, preview = build_chat_preview(candidate)

    print('\n📌 首次校准确认')
    print(f'  群名识别结果: {group_name or "(未识别到)"}')
    print(f'  聊天区路径: {candidate["prefix"]}')
    print(f'  聊天区文本数: {len(chat_texts)}')
    print('\n🧾 当前聊天区预览（末尾样本）:')
    if preview:
        for path, text in preview:
            print(f'  - [{path}] {text[:120]}')
    else:
        print('  (无可预览文本)')

    while True:
        answer = input('\n上述“群名 + 当前聊天区”是否正确？(y/n): ').strip().lower()
        if answer in ('y', 'yes'):
            return True, chat_texts
        if answer in ('n', 'no'):
            return False, chat_texts
        print('请输入 y 或 n。')


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

    current_group = get_group_name(focused)

    print('\n🔍 扫描到以下候选聊天区域：')
    chat_candidate = prompt_choice(candidates, '聊天区')
    ok, chat_texts = confirm_current_context(current_group, chat_candidate)
    if not ok:
        print('\n⚠️ 请切到正确会话后重新运行校准，或重新选择更合适的聊天区。')
        return 1

    mapping = {
        'chat_prefix': chat_candidate['prefix'],
        'session_list_prefix': None,
        'calibration_group_name': current_group,
        'calibration_chat_preview': [text for _, text in chat_texts[-8:]],
        'calibrated_at': datetime.now().isoformat(timespec='seconds'),
    }
    UI_MAPPING_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n✅ UI 映射已保存到: {UI_MAPPING_FILE}')
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
