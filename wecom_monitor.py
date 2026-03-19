#!/usr/bin/env python3
"""
企微会话自动收口守护进程 v1
"""
import json
import re
import select
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from AppKit import NSWorkspace
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    AXUIElementCreateSystemWide,
    kAXChildrenAttribute,
    kAXDescriptionAttribute,
    kAXFocusedApplicationAttribute,
    kAXFocusedUIElementAttribute,
    kAXFocusedWindowAttribute,
    kAXRoleAttribute,
    kAXTitleAttribute,
    kAXValueAttribute,
)

from wecom_agent import call_brainmaker
from wecom_executor import execute_end_session
from wecom_judge import judge_end_status

WS = Path(__file__).parent
LOG_DIR = WS / 'logs'
LOG_DIR.mkdir(exist_ok=True)
UI_MAPPING_FILE = WS / 'data' / 'ui_mapping.json'

TEXT_ROLES = ('AXStaticText', 'AXTextField', 'AXTextArea')
EXCLUDED_PATH_PREFIXES = ('window.0.26',)
UI_MAPPING_KEYS = (
    'chat_prefix',
    'chat_main_thread_prefix',
    'group_name_prefix',
    'group_meta_prefix',
    'session_list_prefix',
)
SESSION_META_HINTS = {'外部', '未读', '@我', '单聊', '群聊'}
GROUP_META_HINTS = ('群主', '外部联系人', '由企业微信用户创建', '企业微信用户创建')
SYSTEM_MESSAGE_HINTS = ('撤回了一条消息', '加入了外部群聊', '邀请', '拍了拍', '已被移出群聊')
GROUP_NAME_HINTS = ('群', '项目', '客户', 'VIP', '云信')
TIME_PATTERNS = (
    re.compile(r'^\d{1,2}:\d{2}$'),
    re.compile(r'^\d{1,2}/\d{1,2}$'),
    re.compile(r'^\d{1,2}月\d{1,2}日(?: \d{1,2}:\d{2})?$'),
    re.compile(r'^(今天|昨天|前天)\s*\d{1,2}:\d{2}$'),
    re.compile(r'^\d+\s*(分钟前|小时前)$'),
)


def ax_copy(element, attr):
    err, value = AXUIElementCopyAttributeValue(element, attr, None)
    return value if err == 0 else None


def ax_str(element, attr):
    v = ax_copy(element, attr)
    if v is None:
        return None
    try:
        s = str(v)
        return s if s not in ('None', '') else None
    except Exception:
        return None


def ax_children(element):
    v = ax_copy(element, kAXChildrenAttribute)
    return list(v) if v else []


def role(el):
    return ax_str(el, kAXRoleAttribute) or '-'


def scroll_to_bottom():
    """模拟按下 Cmd+Down 滚动到底部 - 已禁用，会导致切换群"""
    pass


def find_wecom_app():
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        name = app.localizedName() or ''
        if any(n.lower() in name.lower() for n in ['企业微信', 'WeCom', 'WXWork']):
            return app
    return None


def get_fresh_focused_window():
    """每次重新获取当前聚焦的企微窗口，避免复用旧 AX 引用。"""
    app = find_wecom_app()
    if not app:
        return None, None, None

    app_el = AXUIElementCreateApplication(app.processIdentifier())
    focused = ax_copy(app_el, kAXFocusedWindowAttribute)

    system_wide = AXUIElementCreateSystemWide()
    focused_ui = ax_copy(system_wide, kAXFocusedUIElementAttribute)
    focused_app = ax_copy(system_wide, kAXFocusedApplicationAttribute)

    return app, focused, {
        'app_el': app_el,
        'system_focused_ui': focused_ui,
        'system_focused_app': focused_app,
    }


def walk_collect(el, predicate, depth=0, max_depth=9, out=None, path='window'):
    if out is None:
        out = []
    if predicate(el):
        out.append((el, path))
    if depth >= max_depth:
        return out
    children = ax_children(el)
    if len(children) > 220:
        return out
    for i, child in enumerate(children):
        walk_collect(child, predicate, depth + 1, max_depth, out, f'{path}.{i}')
    return out


def flatten_texts(el, depth=0, max_depth=7, out=None):
    if out is None:
        out = []
    for attr in (kAXTitleAttribute, kAXDescriptionAttribute, kAXValueAttribute):
        val = ax_str(el, attr)
        if val and val not in out:
            out.append(val)
    if depth >= max_depth:
        return out
    children = ax_children(el)
    if len(children) > 120:
        return out
    for child in children:
        flatten_texts(child, depth + 1, max_depth, out)
    return out


def sanitize_text(text):
    if text is None:
        return ''
    cleaned = str(text).replace('\u2060', '').replace('\ufeff', '')
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def path_sort_key(path):
    key = []
    for part in path.split('.'):
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part))
    return tuple(key)


def get_relative_parts(path, base_prefix):
    path_parts = path.split('.')
    prefix_parts = base_prefix.split('.')
    return path_parts[len(prefix_parts):]


def is_excluded_path(path):
    return any(path.startswith(prefix) for prefix in EXCLUDED_PATH_PREFIXES)


def is_time_like(text):
    text = sanitize_text(text)
    if not text:
        return False
    return any(pattern.match(text) for pattern in TIME_PATTERNS)


def is_sender_like(text):
    text = sanitize_text(text)
    if not text:
        return False
    return text.endswith(':') or text.endswith('：')


def is_system_message(text):
    text = sanitize_text(text)
    return any(hint in text for hint in SYSTEM_MESSAGE_HINTS)


def looks_like_short_name(text):
    text = sanitize_text(text)
    if not text or is_time_like(text):
        return False
    if is_sender_like(text):
        return False
    if any(token in text for token in SESSION_META_HINTS):
        return False
    if any(token in text for token in GROUP_META_HINTS):
        return False
    if '\n' in text:
        return False
    return len(text) <= 10 and ' ' not in text


def looks_like_group_name(text):
    text = sanitize_text(text)
    if not text or is_time_like(text):
        return False
    if any(token in text for token in GROUP_META_HINTS):
        return False
    if any(token in text for token in GROUP_NAME_HINTS):
        return True
    return '-' in text and len(text) >= 6


def collect_text_entries(focused, max_depth=12):
    all_texts = walk_collect(
        focused,
        lambda el: role(el) in TEXT_ROLES,
        max_depth=max_depth,
    )

    entries = []
    for el, path in all_texts:
        if is_excluded_path(path):
            continue
        text = sanitize_text(ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or '')
        if text:
            entries.append((path, text))
    entries.sort(key=lambda item: path_sort_key(item[0]))
    return entries


def detect_language(entries):
    for _, text in entries[:50]:
        if any(token in text for token in ['群聊', '单聊', '外部']):
            return '中文'
    return '英文'


def build_path_groups(entries, prefix_depth=4):
    path_groups = defaultdict(list)
    for path, text in entries:
        parts = path.split('.')
        prefix = '.'.join(parts[:prefix_depth]) if len(parts) >= prefix_depth else path
        path_groups[prefix].append((path, text))

    normalized = {}
    for prefix, items in path_groups.items():
        items.sort(key=lambda item: path_sort_key(item[0]))
        normalized[prefix] = items
    return normalized


def build_group_info(prefix, items):
    items = sorted(items, key=lambda item: path_sort_key(item[0]))
    texts = [text for _, text in items]
    relative_parts = [get_relative_parts(path, prefix) for path, _ in items]
    top_branches = [parts[0] for parts in relative_parts if parts]
    row_roots = ['.'.join(parts[:2]) if len(parts) >= 2 else parts[0] for parts in relative_parts if parts]

    time_like_count = sum(1 for text in texts if is_time_like(text))
    session_meta_count = sum(1 for text in texts if text in SESSION_META_HINTS)
    sender_like_count = sum(1 for text in texts if is_sender_like(text))
    long_text_count = sum(1 for text in texts if len(text) >= 20)
    short_name_count = sum(1 for text in texts if looks_like_short_name(text))
    group_meta_count = sum(1 for text in texts if any(token in text for token in GROUP_META_HINTS))
    system_message_count = sum(1 for text in texts if is_system_message(text))

    return {
        'prefix': prefix,
        'items': items,
        'texts': texts,
        'count': len(items),
        'samples': texts[:3],
        'primary_text': texts[0] if texts else '',
        'unique_row_count': len(set(row_roots)),
        'top_branch_counts': Counter(top_branches),
        'time_like_count': time_like_count,
        'session_meta_count': session_meta_count,
        'sender_like_count': sender_like_count,
        'long_text_count': long_text_count,
        'short_name_count': short_name_count,
        'group_meta_count': group_meta_count,
        'system_message_count': system_message_count,
    }


def session_list_score(info):
    score = 0
    if info['count'] >= 30:
        score += 25
    if info['unique_row_count'] >= 8:
        score += 20
    if info['session_meta_count'] >= 3:
        score += 18
    if info['time_like_count'] >= 3:
        score += 12
    if info['sender_like_count'] >= 3:
        score += 6
    if info['long_text_count'] > info['count'] * 0.55:
        score -= 8
    if info['count'] <= 5:
        score -= 30
    return score


def chat_container_score(info):
    score = 0
    if info['count'] >= 10:
        score += 10
    if info['time_like_count'] >= 2:
        score += 14
    if info['long_text_count'] >= 2:
        score += 14
    if info['sender_like_count'] >= 1:
        score += 6
    if info['system_message_count'] >= 1:
        score += 6
    if info['session_meta_count'] >= 4:
        score -= 28
    if info['short_name_count'] > info['count'] * 0.7:
        score -= 20
    if info['count'] <= 3:
        score -= 25
    return score


def chat_branch_score(info):
    score = 0
    if info['time_like_count'] >= 1:
        score += 14
    if info['long_text_count'] >= 1:
        score += 14
    if info['sender_like_count'] >= 1:
        score += 8
    if info['system_message_count'] >= 1:
        score += 5
    if info['short_name_count'] > info['count'] * 0.6:
        score -= 24
    if info['session_meta_count'] >= 2:
        score -= 12
    return score


def group_name_score(info, chat_prefix=None):
    text = info['primary_text']
    score = 0
    if info['count'] <= 3:
        score += 18
    else:
        score -= 20
    if looks_like_group_name(text):
        score += 18
    if 4 <= len(text) <= 60:
        score += 8
    if info['group_meta_count'] >= 1 or info['session_meta_count'] >= 1 or is_time_like(text):
        score -= 20
    if chat_prefix and '.'.join(info['prefix'].split('.')[:3]) == '.'.join(chat_prefix.split('.')[:3]):
        score += 6
    return score


def group_meta_score(info, chat_prefix=None):
    text = info['primary_text']
    score = 0
    if info['count'] <= 3:
        score += 12
    else:
        score -= 15
    if any(token in text for token in GROUP_META_HINTS):
        score += 22
    if chat_prefix and '.'.join(info['prefix'].split('.')[:3]) == '.'.join(chat_prefix.split('.')[:3]):
        score += 5
    return score


def normalize_ui_mapping(mapping):
    normalized = {key: None for key in UI_MAPPING_KEYS}
    if not isinstance(mapping, dict):
        return normalized
    for key in UI_MAPPING_KEYS:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = value.strip()
    return normalized


def load_ui_mapping():
    if not UI_MAPPING_FILE.exists():
        return normalize_ui_mapping({})
    try:
        raw = json.loads(UI_MAPPING_FILE.read_text(encoding='utf-8'))
    except Exception:
        raw = {}
    return normalize_ui_mapping(raw)


def pick_saved_or_best(group_infos, saved_prefix, scorer, min_score, excluded=None):
    excluded = excluded or set()
    if saved_prefix in group_infos and saved_prefix not in excluded:
        saved_score = scorer(group_infos[saved_prefix])
        if saved_score >= min_score:
            return saved_prefix

    candidates = [
        (scorer(info), info['count'], prefix)
        for prefix, info in group_infos.items()
        if prefix not in excluded
    ]
    if not candidates:
        return None
    best_score, _, best_prefix = max(candidates)
    if best_score >= min_score:
        return best_prefix
    return None


def pick_chat_prefix(group_infos, ui_mapping, session_list_prefix, chat_prefix_override=None):
    excluded = {session_list_prefix} if session_list_prefix else set()
    if chat_prefix_override in group_infos and chat_prefix_override not in excluded:
        return chat_prefix_override

    saved_prefix = ui_mapping.get('chat_prefix')
    if saved_prefix in excluded:
        saved_prefix = None

    best_prefix = pick_saved_or_best(
        group_infos,
        saved_prefix,
        chat_container_score,
        min_score=10,
        excluded=excluded,
    )
    if best_prefix:
        return best_prefix

    remaining = [
        (info['count'], prefix)
        for prefix, info in group_infos.items()
        if prefix not in excluded
    ]
    if not remaining:
        return None
    return max(remaining)[1]


def pick_group_name_prefix(group_infos, ui_mapping, chat_prefix, session_list_prefix):
    excluded = {chat_prefix, session_list_prefix}
    return pick_saved_or_best(
        group_infos,
        ui_mapping.get('group_name_prefix'),
        lambda info: group_name_score(info, chat_prefix),
        min_score=8,
        excluded=excluded,
    )


def pick_group_meta_prefix(group_infos, ui_mapping, chat_prefix, session_list_prefix, group_name_prefix):
    excluded = {chat_prefix, session_list_prefix, group_name_prefix}
    return pick_saved_or_best(
        group_infos,
        ui_mapping.get('group_meta_prefix'),
        lambda info: group_meta_score(info, chat_prefix),
        min_score=8,
        excluded=excluded,
    )


def build_direct_child_groups(items, base_prefix):
    child_groups = defaultdict(list)
    base_len = len(base_prefix.split('.'))
    for path, text in items:
        parts = path.split('.')
        if len(parts) <= base_len:
            continue
        child_prefix = '.'.join(parts[:base_len + 1])
        child_groups[child_prefix].append((path, text))
    return {
        prefix: sorted(group_items, key=lambda item: path_sort_key(item[0]))
        for prefix, group_items in child_groups.items()
    }


def infer_chat_main_thread_prefix(chat_prefix, chat_items, saved_prefix=None):
    if not chat_prefix or not chat_items:
        return chat_prefix, chat_items

    saved_items = [
        (path, text)
        for path, text in chat_items
        if saved_prefix and path.startswith(f'{saved_prefix}.')
    ]
    if saved_prefix and saved_items:
        saved_info = build_group_info(saved_prefix, saved_items)
        if chat_branch_score(saved_info) >= 10:
            return saved_prefix, saved_items

    current_prefix = chat_prefix
    current_items = sorted(chat_items, key=lambda item: path_sort_key(item[0]))

    for _ in range(4):
        child_groups = build_direct_child_groups(current_items, current_prefix)
        if not child_groups:
            break

        scored_children = []
        for child_prefix, items in child_groups.items():
            info = build_group_info(child_prefix, items)
            scored_children.append((chat_branch_score(info), len(items), child_prefix, items))
        scored_children.sort(reverse=True)

        # 如果已经出现多个“像消息块”的兄弟节点，说明当前层就是主消息链，
        # 再往下走会误把某一条消息当成整条消息链。
        positive_children = [item for item in scored_children if item[0] >= 6]
        if len(child_groups) >= 2 and len(positive_children) >= 2:
            break

        best_score, best_count, best_prefix, best_items = scored_children[0]
        second_score = scored_children[1][0] if len(scored_children) > 1 else -999
        if best_score < 8:
            break

        is_single_chain = len(child_groups) == 1
        is_clear_winner = best_score - second_score >= 6
        is_dominant = best_count >= max(3, int(len(current_items) * 0.55))
        if not (is_single_chain or is_clear_winner or is_dominant):
            break

        current_prefix = best_prefix
        current_items = best_items

    return current_prefix, current_items


def group_message_blocks(chat_items, main_thread_prefix):
    message_groups = defaultdict(list)
    base_len = len(main_thread_prefix.split('.'))
    for path, text in chat_items:
        parts = path.split('.')
        if len(parts) > base_len:
            message_prefix = '.'.join(parts[:base_len + 1])
        else:
            message_prefix = main_thread_prefix
        message_groups[message_prefix].append((path, text))

    normalized = []
    for prefix, items in sorted(message_groups.items(), key=lambda item: path_sort_key(item[0])):
        items.sort(key=lambda item: path_sort_key(item[0]))
        normalized.append((prefix, items))
    return normalized


def parse_message_block(items):
    texts = [sanitize_text(text) for _, text in items if sanitize_text(text)]
    if not texts:
        return None

    time_parts = [text for text in texts if is_time_like(text)]
    sender = ''
    content_parts = []

    for text in texts:
        if is_time_like(text):
            continue
        if not sender and is_sender_like(text):
            sender = text.rstrip(':：').strip()
            continue
        content_parts.append(text)

    if not content_parts and sender:
        content_parts = [sender]

    content = '\n'.join(content_parts).strip()
    if not content and time_parts:
        content = time_parts[-1]

    if sender and content and content != sender:
        body = f'{sender}: {content}'
    else:
        body = content or sender

    if not sender and len(content_parts) == 1 and is_system_message(content_parts[0]):
        body = content_parts[0]

    return {
        'sender': sender,
        'content': content,
        'body': body,
        'time': time_parts[-1] if time_parts else '',
    }


def parse_messages_from_thread(chat_items, main_thread_prefix):
    messages = []
    for _, block_items in group_message_blocks(chat_items, main_thread_prefix):
        parsed = parse_message_block(block_items)
        if parsed and parsed.get('body'):
            messages.append(parsed)
    return messages


def build_ranked_candidates(group_infos, scorer, excluded=None, top_n=5):
    excluded = excluded or set()
    ranked = []
    for prefix, info in group_infos.items():
        if prefix in excluded:
            continue
        ranked.append((scorer(info), prefix))
    ranked.sort(reverse=True)

    candidates = []
    for score, prefix in ranked[:top_n]:
        info = group_infos[prefix]
        candidates.append({
            'prefix': prefix,
            'count': info['count'],
            'samples': info['samples'],
            'score': score,
        })
    return candidates


def analyze_ui_entries(entries, ui_mapping=None, chat_prefix_override=None):
    ui_mapping = normalize_ui_mapping(ui_mapping or {})
    path_groups = build_path_groups(entries)
    group_infos = {
        prefix: build_group_info(prefix, items)
        for prefix, items in path_groups.items()
        if items
    }

    session_list_prefix = pick_saved_or_best(
        group_infos,
        ui_mapping.get('session_list_prefix'),
        session_list_score,
        min_score=20,
    )
    chat_prefix = pick_chat_prefix(group_infos, ui_mapping, session_list_prefix, chat_prefix_override)
    chat_info = group_infos.get(chat_prefix)
    chat_items = chat_info['items'] if chat_info else []
    chat_main_thread_prefix, main_thread_items = infer_chat_main_thread_prefix(
        chat_prefix,
        chat_items,
        ui_mapping.get('chat_main_thread_prefix'),
    )
    group_name_prefix = pick_group_name_prefix(group_infos, ui_mapping, chat_prefix, session_list_prefix)
    group_meta_prefix = pick_group_meta_prefix(
        group_infos,
        ui_mapping,
        chat_prefix,
        session_list_prefix,
        group_name_prefix,
    )

    messages = parse_messages_from_thread(main_thread_items, chat_main_thread_prefix) if main_thread_items else []
    selected = {
        'chat_prefix': chat_prefix,
        'chat_main_thread_prefix': chat_main_thread_prefix,
        'group_name_prefix': group_name_prefix,
        'group_meta_prefix': group_meta_prefix,
        'session_list_prefix': session_list_prefix,
    }

    excluded = {session_list_prefix, group_name_prefix, group_meta_prefix}
    return {
        'language': detect_language(entries),
        'entries': entries,
        'path_groups': path_groups,
        'group_infos': group_infos,
        'selected': selected,
        'chat_items': main_thread_items,
        'messages': messages,
        'chat_candidates': build_ranked_candidates(group_infos, chat_container_score, excluded=excluded),
        'session_candidates': build_ranked_candidates(group_infos, session_list_score),
    }


def inspect_ui(focused, ui_mapping=None, chat_prefix_override=None):
    entries = collect_text_entries(focused, max_depth=12)
    merged_mapping = normalize_ui_mapping(ui_mapping or load_ui_mapping())
    return analyze_ui_entries(entries, merged_mapping, chat_prefix_override=chat_prefix_override)


def get_primary_text(group_infos, prefix):
    if not prefix:
        return None
    info = group_infos.get(prefix)
    if not info or not info['texts']:
        return None
    return info['texts'][0]


def get_group_name(focused):
    context = inspect_ui(focused)
    return get_primary_text(context['group_infos'], context['selected']['group_name_prefix'])


def get_messages(focused, debug=False):
    scroll_to_bottom()
    context = inspect_ui(focused)
    chat_prefix = context['selected']['chat_prefix']
    main_thread_prefix = context['selected']['chat_main_thread_prefix']
    chat_items = context['chat_items']

    if debug:
        print(f'🔍 DEBUG: 检测到{context["language"]}版本')
        print(
            f'🔍 DEBUG: 会话列表={context["selected"]["session_list_prefix"] or "(未识别)"} '
            f'群名={context["selected"]["group_name_prefix"] or "(未识别)"} '
            f'聊天区={chat_prefix or "(未识别)"} '
            f'主消息链={main_thread_prefix or "(未识别)"}'
        )
        print(f'🔍 DEBUG: 主消息链共 {len(chat_items)} 个文本')
        preview = chat_items[-20:]
        for idx, (path, text) in enumerate(preview, 1):
            print(f'  {idx}. [{path}] {text[:100]}')

    messages = context['messages']
    return messages[-20:] if len(messages) > 20 else messages


def main():
    if not AXIsProcessTrustedWithOptions({'AXTrustedCheckOptionPrompt': True}):
        print('❌ 需要 Accessibility 权限')
        return

    print('🚀 企微会话收口守护进程启动')
    print('💡 输入 "end" 或 "e" 手动触发结束当前会话')
    print('按 Ctrl+C 停止\n')

    last_processed = {}
    cooldown_seconds = 60

    while True:
        try:
            if select.select([sys.stdin], [], [], 0)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd in ['end', 'e']:
                    print('🔧 手动触发结束会话...')
                    success, msg = execute_end_session()
                    print(f'  → {msg}')
                    time.sleep(2)
                    continue

            app = find_wecom_app()
            if not app:
                time.sleep(10)
                continue

            app_el = AXUIElementCreateApplication(app.processIdentifier())
            focused = ax_copy(app_el, kAXFocusedWindowAttribute)
            if not focused:
                time.sleep(10)
                continue

            group_name = get_group_name(focused)
            if not group_name:
                time.sleep(10)
                continue

            messages = get_messages(focused)
            if len(messages) < 3:
                time.sleep(10)
                continue

            msg_content = json.dumps([m.get('body', '') for m in messages[-5:]], ensure_ascii=False)
            cache_key = f"{group_name}:{msg_content}"
            msg_hash = hash(cache_key)
            current_time = time.time()

            if group_name in last_processed:
                last_hash, last_time = last_processed[group_name]
                if last_hash == msg_hash:
                    time.sleep(10)
                    continue
                if (current_time - last_time) < cooldown_seconds:
                    print(f'  ⏳ 冷却中，剩余 {int(cooldown_seconds - (current_time - last_time))}s')
                    time.sleep(10)
                    continue

            last_processed[group_name] = (msg_hash, current_time)

            status, confidence, reason = judge_end_status(messages)

            print(f'[{time.strftime("%H:%M:%S")}] 群: {group_name[:30]}')
            print(f'  状态: {status} (置信度: {confidence:.2f})')
            print(f'  原因: {reason}')

            if status == 'not_end':
                time.sleep(10)
                continue

            if status == 'uncertain':
                print('  → 调用 Brainmaker 兜底判断...')
                agent_result = call_brainmaker(group_name, messages)
                if agent_result and agent_result.get('ended') and agent_result.get('confidence', 0) >= 0.7:
                    print(f'  → Agent 判定: 已结束 (置信度: {agent_result.get("confidence")})')
                    print(f'  → 原因: {agent_result.get("reason")}')
                    status = 'strong_end_candidate'
                else:
                    print('  → Agent 判定: 未结束或置信度不足')
                    time.sleep(10)
                    continue

            if status == 'strong_end_candidate':
                print('  → 执行结束会话链路...')
                success, msg = execute_end_session(group_name)
                print(f'  → 执行结果: {msg}')
                time.sleep(60)

        except KeyboardInterrupt:
            print('\n👋 守护进程已停止')
            break
        except Exception as e:
            print(f'❌ 错误: {e}')
            time.sleep(10)


if __name__ == '__main__':
    main()
