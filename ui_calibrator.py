#!/usr/bin/env python3
"""
UI 校准工具：扫描候选区域并让用户手动选择聊天区/会话列表。
"""
import json
from pathlib import Path

from ApplicationServices import (
    AXUIElementCreateApplication,
    kAXFocusedWindowAttribute,
    kAXValueAttribute,
    kAXTitleAttribute,
)

from wecom_monitor import ax_copy, ax_str, find_wecom_app, role, walk_collect

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


def prompt_choice(candidates, label, allow_skip=False):
    print(f'\n请选择{label}：')
    for idx, c in enumerate(candidates, 1):
        print(f'  {idx}. {c["prefix"]} ({c["count"]} 个文本)')
        for sample in c['samples'][:3]:
            print(f'     - {sample}')
    if allow_skip:
        print('  0. 跳过')

    while True:
        choice = input(f'输入 {label} 编号: ').strip()
        if allow_skip and choice == '0':
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1]['prefix']
        print('输入无效，请重试。')


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

    print('\n🔍 扫描到以下候选区域：')
    chat_prefix = prompt_choice(candidates, '聊天区')
    session_list_prefix = prompt_choice(candidates, '会话列表', allow_skip=True)

    mapping = {
        'chat_prefix': chat_prefix,
        'session_list_prefix': session_list_prefix,
    }
    UI_MAPPING_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\n✅ UI 映射已保存到: {UI_MAPPING_FILE}')
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
