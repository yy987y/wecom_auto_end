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
    kAXChildrenAttribute, kAXRoleAttribute, kAXValueAttribute,
    kAXTitleAttribute, kAXDescriptionAttribute
)

# 导入本地模块
from wecom_judge import judge_end_status
from wecom_agent import call_brainmaker
from wecom_executor import execute_end_session

WS = Path(__file__).parent
LOG_DIR = WS / 'logs'
LOG_DIR.mkdir(exist_ok=True)

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

def get_messages(focused, debug=False):
    # 先滚动到底部，确保最新消息可见
    scroll_to_bottom()
    
    # 新策略：直接从聊天区域提取所有文本，不依赖 AXTable/AXRow
    # 查找路径包含 window.0.31.9 的文本元素（中间聊天区域）
    all_texts = walk_collect(focused, lambda el: role(el) in ['AXStaticText', 'AXTextField', 'AXTextArea'], max_depth=12)
    
    # 过滤出聊天区域的文本，并获取位置信息
    chat_texts = []
    seen_texts = set()  # 用于去重
    for el, path in all_texts:
        # 只要聊天区域的（window.0.31.9）
        if 'window.0.31.9' not in path:
            continue
        # 跳过侧边栏（window.0.26）
        if 'window.0.26' in path:
            continue
        
        text = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        if text and text not in seen_texts:  # 去重
            # 获取位置信息
            try:
                from ApplicationServices import AXUIElementCopyAttributeValue, kAXPositionAttribute
                pos_result = AXUIElementCopyAttributeValue(el, kAXPositionAttribute, None)
                if pos_result[0] == 0 and pos_result[1]:
                    x = pos_result[1].pointValue().x
                    chat_texts.append((path, text, x))
                else:
                    chat_texts.append((path, text, 0))
            except:
                chat_texts.append((path, text, 0))
            seen_texts.add(text)
    
    # 只取最新的30个
    chat_texts = chat_texts[-30:] if len(chat_texts) > 30 else chat_texts
    
    if debug:
        print(f'\n🔍 DEBUG: 聊天区域找到 {len(chat_texts)} 个文本元素（最后20个）')
        for i, (path, text, x) in enumerate(chat_texts[-20:], 1):
            print(f'  {i}. [x={x:.0f}] [{path}] {text[:80]}')
    
    # 按路径分组，并根据 x 坐标判断是否是我方消息
    messages = []
    current_group = []
    last_msg_id = None
    
    # 计算 x 坐标的中位数，用于判断左右
    x_coords = [x for _, _, x in chat_texts if x > 0]
    if x_coords:
        median_x = sorted(x_coords)[len(x_coords) // 2]
    else:
        median_x = 500  # 默认值
    
    for path, text, x in chat_texts:
        # 提取消息ID（第7级，索引6）
        parts = path.split('.')
        if len(parts) >= 7:
            msg_id = parts[6]
        else:
            msg_id = path
        
        # 如果消息ID变化，说明是新的消息
        if last_msg_id and msg_id != last_msg_id:
            if current_group:
                # 判断是否是我方消息（右侧，x 坐标较大）
                group_x = [x for _, x in current_group if x > 0]
                is_our_message = any(x > median_x for x in group_x) if group_x else False
                
                # 组合消息内容
                texts = [t for t, _ in current_group]
                sender = '我方' if is_our_message else texts[0] if texts else ''
                content = ' '.join(texts[1:]) if len(texts) > 1 and not is_our_message else ' '.join(texts)
                
                messages.append({
                    'sender': sender,
                    'content': content,
                    'body': ' '.join(texts),
                    'is_our': is_our_message
                })
            current_group = []
        
        current_group.append((text, x))
        last_msg_id = msg_id
    
    # 处理最后一组
    if current_group:
        group_x = [x for _, x in current_group if x > 0]
        is_our_message = any(x > median_x for x in group_x) if group_x else False
        
        texts = [t for t, _ in current_group]
        sender = '我方' if is_our_message else texts[0] if texts else ''
        content = ' '.join(texts[1:]) if len(texts) > 1 and not is_our_message else ' '.join(texts)
        
        messages.append({
            'sender': sender,
            'content': content,
            'body': ' '.join(texts),
            'is_our': is_our_message
        })
    
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
