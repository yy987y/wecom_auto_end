#!/usr/bin/env python3
"""
企微会话收口判断模块
本地三态判断：not_end / strong_end_candidate / uncertain
"""
import re
import yaml
from pathlib import Path

# 加载关键词配置
def load_keywords():
    config_file = Path(__file__).parent / 'keywords.yaml'
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    # 默认配置
    return {
        'customer_confirm': {'score': 3, 'keywords': ['好的', 'OK', 'ok', '可以', '明白', '收到']},
        'customer_thanks': {'score': 2, 'keywords': ['谢谢', '感谢', '多谢']},
        'our_promise': {'score': 2, 'keywords': ['稍后', '明天', '下周']},
        'problem_solved': {'score': 2, 'keywords': ['已解决', '已修复']},
        'new_problem': {'score': -5, 'keywords': ['还有个问题', '另外', '再问一下']},
        'thresholds': {'strong_end': 4, 'keep': 0}
    }

KEYWORDS_CONFIG = load_keywords()

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
        if contains_keywords(last_text, KEYWORDS_CONFIG['customer_confirm']['keywords']):
            score += KEYWORDS_CONFIG['customer_confirm']['score']
            reasons.append('客户确认词')
        if contains_keywords(last_text, KEYWORDS_CONFIG['customer_thanks']['keywords']):
            score += KEYWORDS_CONFIG['customer_thanks']['score']
            reasons.append('客户感谢词')
    
    # 检查最近是否有我方承诺/解决
    for msg in recent[:-1]:
        sender = msg.get('sender') or ''
        text = msg.get('content') or msg.get('body') or ''
        if is_my_side(sender):
            if contains_keywords(text, KEYWORDS_CONFIG['our_promise']['keywords']):
                score += KEYWORDS_CONFIG['our_promise']['score']
                reasons.append('我方承诺')
            if contains_keywords(text, KEYWORDS_CONFIG['problem_solved']['keywords']):
                score += KEYWORDS_CONFIG['problem_solved']['score']
                reasons.append('问题已解决')
    
    # 检查是否有新问题信号
    for msg in recent:
        text = msg.get('content') or msg.get('body') or ''
        if contains_keywords(text, KEYWORDS_CONFIG['new_problem']['keywords']):
            score += KEYWORDS_CONFIG['new_problem']['score']
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
    thresholds = KEYWORDS_CONFIG.get('thresholds', {'strong_end': 4, 'keep': 0})
    
    # 强未结束
    if score < thresholds['keep']:
        return 'not_end', 0.9, f'评分{score}: {score_reason}'
    
    # 强收口候选
    if score >= thresholds['strong_end']:
        return 'strong_end_candidate', 0.8, f'评分{score}: {score_reason}'
    
    # 不确定
    return 'uncertain', 0.5, f'评分{score}: {score_reason}'
