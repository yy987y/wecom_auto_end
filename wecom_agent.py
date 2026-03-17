#!/usr/bin/env python3
"""Brainmaker 兜底判断模块"""
import time
import json
import yaml
from pathlib import Path
from datetime import datetime

from cookie_manager import get_cookies
from brainmaker_api import BrainmakerAPI
from logger import setup_logger

logger = setup_logger('wecom_auto', Path(__file__).parent / 'logs')

config_file = Path(__file__).parent / "config.yaml"
if config_file.exists():
    with open(config_file) as f:
        config = yaml.safe_load(f)
else:
    config = {"brainmaker": {"request_interval": 3, "model": "claude-opus-4-5-20251101"}}

last_request_time = 0
request_interval = config.get("brainmaker", {}).get("request_interval", 3)
cache = {}
cache_ttl = config.get("brainmaker", {}).get("cache", {}).get("ttl", 300)
stats_file = Path(__file__).parent / "data" / "agent_stats.json"

def load_stats():
    if stats_file.exists():
        data = json.loads(stats_file.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        if data.get("date") == today:
            return data
    return {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0, "models": {}}

def save_stats(stats):
    stats_file.parent.mkdir(exist_ok=True)
    stats_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2))

def record_call(model):
    stats = load_stats()
    stats["count"] += 1
    stats["models"][model] = stats["models"].get(model, 0) + 1
    save_stats(stats)
    logger.info(f"📊 今日已调用 Brainmaker: {stats['count']} 次")
    return stats['count']

def build_agent_prompt(group_name, messages):
    """构建 agent 判断 prompt"""
    msg_lines = []
    for i, msg in enumerate(messages[-10:], 1):
        sender = msg.get('sender', 'unknown')
        content = msg.get('content') or msg.get('body', '')
        msg_lines.append(f"{i}. {sender}: {content}")
    
    context = '\n'.join(msg_lines)
    
    prompt = f"""你是技术支持助手。判断该聊天问题是否已经结束。

群名：{group_name}

最近消息：
{context}

结束标准：
1. 问题已解决或给出明确承诺
2. 客户已确认
3. 没有新的悬空问题
4. 对话自然收口

返回 JSON：
{{
  "ended": true/false,
  "confidence": 0.0-1.0,
  "reason": "简要原因"
}}"""
    
    return prompt

def _extract_json_block(text: str):
    if not text:
        return None
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
    return None


def call_brainmaker(group_name, messages):
    """调用 Brainmaker 判断：固定单模型，带频控、缓存、统计和详细日志"""
    global last_request_time

    cache_key = f"{group_name}_{len(messages)}"
    if cache_key in cache:
        cached_time, cached_result = cache[cache_key]
        if time.time() - cached_time < cache_ttl:
            logger.info('→ 使用 Brainmaker 缓存结果')
            return cached_result

    elapsed = time.time() - last_request_time
    if elapsed < request_interval:
        wait_time = request_interval - elapsed
        logger.info(f'→ 等待 {wait_time:.1f}s 避免频控...')
        time.sleep(wait_time)

    model = config.get("brainmaker", {}).get("model", "claude-opus-4-5-20251101")

    try:
        logger.info('→ 获取 Brainmaker cookies...')
        cookies = get_cookies()
        if not cookies:
            logger.error('→ 未获取到 Brainmaker cookies')
            return None
        logger.info(f'→ 已获取 Brainmaker cookies，数量: {len(cookies)}')

        api = BrainmakerAPI(cookies)
        prompt = build_agent_prompt(group_name, messages)
        agent_messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }]

        logger.info(f'→ 调用 Brainmaker 模型: {model}')
        last_request_time = time.time()
        response = api.chat(
            messages=agent_messages,
            model=model,
            temperature=0.1,
            max_tokens=800,
            stream=False
        )
        logger.info(f'→ Brainmaker HTTP 状态: {response.status_code}')

        if response.status_code != 200:
            logger.error(f'→ Brainmaker 请求失败: {response.text[:300]}')
            return None

        result = api.parse_response(response)
        logger.debug(f'→ Brainmaker 原始解析结果: {result}')
        if not result:
            logger.error('→ Brainmaker 返回空结果')
            return None

        json_str = _extract_json_block(result)
        if not json_str:
            logger.error(f'→ Brainmaker 返回中未提取到 JSON: {result[:300]}')
            return None

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f'→ Brainmaker JSON 解析失败: {e}')
            logger.error(f'→ JSON 原文: {repr(json_str)}')
            # 尝试修复常见问题：替换中文引号、清理特殊字符
            try:
                fixed_json = json_str.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
                data = json.loads(fixed_json)
                logger.info('✓ JSON 修复后解析成功')
            except Exception as e2:
                logger.error(f'→ JSON 修复后仍失败: {e2}')
                return None

        logger.info(f'✓ Brainmaker 判断成功: {data}')
        record_call(model)
        cache[cache_key] = (time.time(), data)
        return data

    except Exception as e:
        logger.error(f'Brainmaker 调用失败: {e}', exc_info=True)
        return None
