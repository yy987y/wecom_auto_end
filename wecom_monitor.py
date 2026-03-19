#!/usr/bin/env python3
"""
企微会话自动收口守护进程 v1
"""
import time
import json
import sys
import select
import subprocess
from pathlib import Path
from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
    AXIsProcessTrustedWithOptions, kAXFocusedWindowAttribute,
    kAXFocusedUIElementAttribute, kAXFocusedApplicationAttribute,
    kAXChildrenAttribute, kAXRoleAttribute, kAXValueAttribute,
    kAXTitleAttribute, kAXDescriptionAttribute,
    AXUIElementCreateSystemWide,
)

# 导入本地模块
from wecom_judge import judge_end_status
from wecom_agent import call_brainmaker
from wecom_executor import execute_end_session

WS = Path(__file__).parent
LOG_DIR = WS / 'logs'
LOG_DIR.mkdir(exist_ok=True)
UI_MAPPING_FILE = WS / 'data' / 'ui_mapping.json'

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
    except:
        return None

def ax_children(element):
    v = ax_copy(element, kAXChildrenAttribute)
    return list(v) if v else []

def role(el):
    return ax_str(el, kAXRoleAttribute) or '-'

def scroll_to_bottom():
    """模拟按下 Cmd+Down 滚动到底部 - 已禁用，会导致切换群"""
    # 禁用：Cmd+Down 会触发企微切换群的快捷键
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

def load_ui_mapping():
    if not UI_MAPPING_FILE.exists():
        return {}
    try:
        return json.loads(UI_MAPPING_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def get_group_name(focused):
    fields = walk_collect(focused, lambda el: role(el) in ('AXTextField', 'AXStaticText'), max_depth=8)
    scored = []
    for el, path in fields:
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute)
        if not text:
            continue
        score = 0
        if role(el) == 'AXTextField': score += 5
        if path.startswith('window.0.31'): score += 8
        if '.31.5' in path: score += 20
        if any(k in text for k in ['群', 'VIP', '项目', '客户']) or ('-' in text and len(text) >= 6): score += 10
        scored.append((score, text))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None

def _filter_main_chat_thread(chat_prefix, chat_texts):
    """尽量只保留聊天正文主链，排除群成员/资料卡/侧边说明等分支。"""
    if not chat_texts:
        return chat_texts

    # 先按 chat_prefix 下的第一级子分支聚类，例如 window.0.29.9.0 / .1 / .2
    branch_groups = {}
    for path, text in chat_texts:
        suffix = path[len(chat_prefix):].lstrip('.')
        first_seg = suffix.split('.', 1)[0] if suffix else '_root'
        branch_key = f'{chat_prefix}.{first_seg}' if first_seg != '_root' else chat_prefix
        branch_groups.setdefault(branch_key, []).append((path, text))

    def score_branch(items):
        score = 0
        unique_paths = len({p for p, _ in items})
        score += min(unique_paths, 80)

        texts = [t.strip() for _, t in items if t and t.strip()]
        long_texts = sum(1 for t in texts if len(t) >= 8)
        score += long_texts * 2

        # 会话列表/群成员区域常见特征，做降权
        penalty_keywords = ['刚刚', '分钟前', '昨天', '周一', '周二', '周三', '周四', '周五', '周六', '周日', '群主:', '外部联系人']
        penalty = sum(1 for t in texts if any(k in t for k in penalty_keywords))
        score -= penalty * 3

        # 大量纯人名/短 token 的分支通常不是正文
        short_texts = sum(1 for t in texts if len(t) <= 4)
        score -= short_texts
        return score

    best_branch_key = max(branch_groups.keys(), key=lambda k: score_branch(branch_groups[k]))
    best_items = branch_groups[best_branch_key]

    # 兼容旧版经验路径：如果能识别到 0.0.0 主链，则优先使用更深的主链
    preferred_prefix = f'{chat_prefix}.0.0.0.'
    preferred_items = [(p, t) for p, t in best_items if p.startswith(preferred_prefix)]
    if preferred_items:
        return preferred_items

    return best_items


def get_messages(focused, debug=False):
    # 先滚动到底部，确保最新消息可见
    scroll_to_bottom()
    
    ui_mapping = load_ui_mapping()
    mapped_chat_prefix = ui_mapping.get('chat_prefix')
    mapped_session_list_prefix = ui_mapping.get('session_list_prefix')
    
    # 新策略：自动识别聊天区域
    all_texts = walk_collect(focused, lambda el: role(el) in ['AXStaticText', 'AXTextField', 'AXTextArea'], max_depth=12)
    
    # 检测语言版本（通过查找特征文本）
    is_chinese = False
    for el, path in all_texts[:50]:  # 只检查前50个
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if '群聊' in text or '单聊' in text or '外部' in text:
            is_chinese = True
            break
    
    # 按路径前4级分组
    path_groups = {}
    for el, path in all_texts:
        if 'window.0.26' in path:  # 排除侧边栏
            continue
        parts = path.split('.')
        prefix = '.'.join(parts[:4]) if len(parts) >= 4 else path
        
        # 用户手动校准的会话列表优先排除；否则回退到当前经验规则
        if mapped_session_list_prefix and prefix == mapped_session_list_prefix:
            continue
        if prefix == 'window.0.31.2':
            continue
        
        if prefix not in path_groups:
            path_groups[prefix] = []
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if text:
            path_groups[prefix].append((path, text))
    
    if not path_groups:
        return []

    # 优先使用用户手动校准的聊天区；否则回退到当前经验规则
    if mapped_chat_prefix and mapped_chat_prefix in path_groups and path_groups[mapped_chat_prefix]:
        chat_prefix = mapped_chat_prefix
    elif 'window.0.31.9' in path_groups and path_groups['window.0.31.9']:
        chat_prefix = 'window.0.31.9'
    else:
        chat_prefix = max(path_groups.keys(), key=lambda k: len(path_groups[k]))

    chat_texts = path_groups[chat_prefix]

    # 在主聊天容器内，仅保留消息主链，排除右侧群公告/名片/资料卡等分支
    if chat_prefix == 'window.0.31.9':
        main_thread_prefix = 'window.0.31.9.0.0.0.'
        filtered_chat_texts = [(path, text) for path, text in chat_texts if path.startswith(main_thread_prefix)]
        if filtered_chat_texts:
            chat_texts = filtered_chat_texts
    
    if debug:
        lang = '中文' if is_chinese else '英文'
        print(f'🔍 DEBUG: 检测到{lang}版本')
        print(f'🔍 DEBUG: 聊天区域 {chat_prefix}，{len(chat_texts)} 个文本')
    
    # 只取最新的30个
    chat_texts = chat_texts[-30:] if len(chat_texts) > 30 else chat_texts
    
    if debug:
        print(f'\n🔍 DEBUG: 聊天区域找到 {len(chat_texts)} 个文本元素（最后20个）')
        for i, (path, text) in enumerate(chat_texts[-20:], 1):
            print(f'  {i}. [{path}] {text[:80]}')
    
    # 简单解析：相邻的文本组合成消息
    # 假设：发送者 + 时间/内容
    messages = []
    i = 0
    while i < len(chat_texts):
        path1, text1 = chat_texts[i]
        
        # 如果下一个文本存在，尝试组合
        if i + 1 < len(chat_texts):
            path2, text2 = chat_texts[i + 1]
            messages.append({
                'sender': text1,
                'content': text2,
                'body': f'{text1} {text2}'
            })
            i += 2
        else:
            messages.append({
                'sender': '',
                'content': text1,
                'body': text1
            })
            i += 1
    
    # 只返回最后 20 条
    return messages[-20:] if len(messages) > 20 else messages

def main():
    if not AXIsProcessTrustedWithOptions({'AXTrustedCheckOptionPrompt': True}):
        print('❌ 需要 Accessibility 权限')
        return
    
    print('🚀 企微会话收口守护进程启动')
    print('💡 输入 "end" 或 "e" 手动触发结束当前会话')
    print('按 Ctrl+C 停止\n')
    
    # 记录上次处理的群和消息
    last_processed = {}  # {group_name: (msg_hash, timestamp)}
    cooldown_seconds = 60  # 同一个群判断后的冷却时间（秒）
    
    while True:
        try:
            # 检查是否有键盘输入（非阻塞）
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
            
            # 检查消息是否有变化 + 冷却时间
            # 使用群名+消息内容一起做哈希，避免群名识别误差
            msg_content = json.dumps([m.get('body', '') for m in messages[-5:]], ensure_ascii=False)
            cache_key = f"{group_name}:{msg_content}"
            msg_hash = hash(cache_key)
            current_time = time.time()
            
            if group_name in last_processed:
                last_hash, last_time = last_processed[group_name]
                # 如果消息没变化，或者在冷却时间内，跳过
                if last_hash == msg_hash:
                    time.sleep(10)
                    continue
                # 冷却时间检查（即使消息变了，也要等待）
                if (current_time - last_time) < cooldown_seconds:
                    print(f'  ⏳ 冷却中，剩余 {int(cooldown_seconds - (current_time - last_time))}s')
                    time.sleep(10)
                    continue
            
            last_processed[group_name] = (msg_hash, current_time)
            
            # 本地三态判断
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
