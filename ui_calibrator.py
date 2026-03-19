#!/usr/bin/env python3
"""
UI 校准工具：首次校准时确认当前群名 + 当前聊天区。
"""
import json
from pathlib import Path

from ApplicationServices import AXUIElementCreateApplication, kAXFocusedWindowAttribute

from wecom_monitor import (
    ax_copy,
    find_wecom_app,
    get_primary_text,
    inspect_ui,
)

WS = Path(__file__).parent
DATA_DIR = WS / 'data'
DATA_DIR.mkdir(exist_ok=True)
UI_MAPPING_FILE = DATA_DIR / 'ui_mapping.json'


def collect_candidates(context):
    candidates = []
    seen = set()

    selected_chat_prefix = context['selected']['chat_prefix']
    if selected_chat_prefix and selected_chat_prefix in context['group_infos']:
        info = context['group_infos'][selected_chat_prefix]
        candidates.append({
            'prefix': selected_chat_prefix,
            'count': info['count'],
            'samples': info['samples'],
            'score': '推荐',
        })
        seen.add(selected_chat_prefix)

    for candidate in context['chat_candidates']:
        if candidate['prefix'] in seen:
            continue
        candidates.append(candidate)
        seen.add(candidate['prefix'])

    return candidates


def prompt_choice(candidates, label):
    print(f'\n请选择{label}：')
    for idx, candidate in enumerate(candidates, 1):
        score = candidate.get('score')
        score_label = f'，{score}' if isinstance(score, str) else ''
        print(f'  {idx}. {candidate["prefix"]} ({candidate["count"]} 个文本{score_label})')
        for sample in candidate['samples'][:3]:
            print(f'     - {sample}')

    while True:
        choice = input(f'输入 {label} 序号: ').strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return candidates[int(choice) - 1]['prefix']
        print('输入无效，请重试。')


def confirm_preview(focused, chat_prefix):
    context = inspect_ui(focused, chat_prefix_override=chat_prefix)
    mapping = context['selected']
    group_name = get_primary_text(context['group_infos'], mapping['group_name_prefix'])
    group_meta = get_primary_text(context['group_infos'], mapping['group_meta_prefix'])
    messages = context['messages']

    print('\n📌 首次校准确认结果')
    print(f'当前群名: {group_name or "(未识别)"}')
    print(f'群信息: {group_meta or "(未识别)"}')
    print(f'聊天区: {mapping["chat_prefix"] or "(未识别)"}')
    print(f'主消息链: {mapping["chat_main_thread_prefix"] or "(未识别)"}')
    print(f'解析消息数: {len(messages)}')
    print('最近消息预览:')
    if not messages:
        print('  (未解析到聊天内容)')
    else:
        for idx, msg in enumerate(messages[-8:], 1):
            body = (msg.get('body') or '').strip() or '(空)'
            print(f'  {idx}. {body[:160]}')

    print('\n请确认以上“群名 + 当前聊天区域”是否正确。')
    while True:
        choice = input('确认无误？(y/n): ').strip().lower()
        if choice in ('y', 'yes'):
            UI_MAPPING_FILE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding='utf-8')
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

    context = inspect_ui(focused)
    candidates = collect_candidates(context)
    if not candidates:
        print('❌ 未扫描到候选聊天区域。')
        return 1

    print('\n🧭 当前窗口结构识别：')
    print(f'  会话列表: {context["selected"]["session_list_prefix"] or "(未识别)"}')
    print(f'  群名区域: {context["selected"]["group_name_prefix"] or "(未识别)"}')
    print(f'  群信息区域: {context["selected"]["group_meta_prefix"] or "(未识别)"}')

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
