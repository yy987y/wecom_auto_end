#!/usr/bin/env python3
"""
企微会话收口判断模块
本地三态判断：not_end / strong_end_candidate / uncertain
"""
import re

# 关键词词典
THANK_WORDS = ['谢谢', '感谢', '辛苦', '多谢', '谢了']
CONFIRM_WORDS = ['好的', 'ok', 'OK', '可以', '明白', '收到', '行', '好']
PROMISE_WORDS = ['确认后答复', '稍后答复', '稍后回复', '明天回复', '下周一', '周五我们会提供', 
                 '会提供', '安排研发处理', '让研发处理', '跟进后同步', '确认后回你',
                 '有结论随时同步', '有结论同步', '随时同步', '确认后同步', '处理后同步',
                 '稍后联系', '明天联系', '后续跟进', '持续跟进']
SOLVED_WORDS = ['已修复', '已经修复', '解决了', '已处理', '可以了', '恢复正常', '已经解决']
NEW_QUESTION_WORDS = ['还有个问题', '另外问', '再问一下', '顺便问', '还有一个']

def normalize_text(text):
    """文本归一化"""
    if not text:
        return ''
    text = text.lower()
    text = text.replace('ＯＫ', 'ok').replace('ｏｋ', 'ok')
    return text.strip()

def contains_keywords(text, keywords):
    """检查是否包含关键词"""
    text = normalize_text(text)
    return any(k.lower() in text for k in keywords)

def is_my_side(sender):
    """判断是否是我方发言（简化版，后续可根据实际调整）"""
    # 当前简化判断：不含 @WeChat 的认为是我方
    return '@WeChat' not in sender if sender else False

def calculate_end_score(messages):
    """计算收口评分"""
    if not messages or len(messages) < 2:
        return 0, '消息太少'
    
    score = 0
    reasons = []
    
    # 最近4条
    recent = messages[-4:]
    last_msg = messages[-1]
    last_text = last_msg.get('content') or last_msg.get('body') or ''
    last_sender = last_msg.get('sender') or ''
    
    # 检查最后一条是否是客户确认
    if not is_my_side(last_sender):
        if contains_keywords(last_text, CONFIRM_WORDS):
            score += 3
            reasons.append('客户确认词')
        if contains_keywords(last_text, THANK_WORDS):
            score += 2
            reasons.append('客户感谢词')
    
    # 检查最近是否有我方承诺/解决
    for msg in recent[:-1]:
        sender = msg.get('sender') or ''
        text = msg.get('content') or msg.get('body') or ''
        if is_my_side(sender):
            if contains_keywords(text, PROMISE_WORDS):
                score += 4  # 提高权重，直接触发关闭
                reasons.append('我方明确承诺')
            if contains_keywords(text, SOLVED_WORDS):
                score += 2
                reasons.append('我方已解决')
    
    # 检查是否有新问题信号
    for msg in recent:
        text = msg.get('content') or msg.get('body') or ''
        if contains_keywords(text, NEW_QUESTION_WORDS):
            score -= 5
            reasons.append('检测到新问题')
            break
    
    return score, ' + '.join(reasons) if reasons else '无明显信号'

def judge_end_status(messages):
    """
    三态判断
    返回: (status, confidence, reason)
    status: 'not_end' | 'strong_end_candidate' | 'uncertain'
    """
    if not messages or len(messages) < 3:
        return 'not_end', 0.0, '消息数不足'
    
    score, score_reason = calculate_end_score(messages)
    
    # 强未结束
    if score < 0:
        return 'not_end', 0.9, f'评分{score}: {score_reason}'
    
    # 强收口候选
    if score >= 4:
        return 'strong_end_candidate', 0.8, f'评分{score}: {score_reason}'
    
    # 不确定
    return 'uncertain', 0.5, f'评分{score}: {score_reason}'
