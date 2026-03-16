#!/usr/bin/env python3
"""
Brainmaker 兜底判断模块
"""
import sys
import os
import time
import json
import yaml
from pathlib import Path

from cookie_manager import get_cookies
from brainmaker_api import BrainmakerAPI

# 加载配置
config_file = Path(__file__).parent / "config.yaml"
if config_file.exists():
    with open(config_file) as f:
        config = yaml.safe_load(f)
else:
    config = {"brainmaker": {"request_interval": 3, "models": ["claude-sonnet-4-5-20250514"]}}

# 请求间隔控制
last_request_time = 0
request_interval = config.get("brainmaker", {}).get("request_interval", 3)

# 简单缓存
cache = {}
cache_ttl = config.get("brainmaker", {}).get("cache", {}).get("ttl", 300)

# 调用统计
from datetime import datetime
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
    print(f"  📊 今日已调用: {stats['count']} 次")

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

def call_brainmaker(group_name, messages):
    """调用 Brainmaker 判断，支持模型自动降级、请求间隔和缓存"""
    global last_request_time
    
    # 检查缓存
    cache_key = f"{group_name}_{len(messages)}"
    if cache_key in cache:
        cached_time, cached_result = cache[cache_key]
        if time.time() - cached_time < cache_ttl:
            print(f"  → 使用缓存结果")
            return cached_result
    
    # 请求间隔控制
    elapsed = time.time() - last_request_time
    if elapsed < request_interval:
        wait_time = request_interval - elapsed
        print(f"  → 等待 {wait_time:.1f}s 避免频控...")
        time.sleep(wait_time)
    
    # 模型优先级列表
    models = config.get("brainmaker", {}).get("models", [
        "claude-sonnet-4-5-20250514",
        "claude-sonnet-3-5-20241022", 
        "gpt-4o-mini",
        "deepseek-chat"
    ])
    
    try:
        cookies = get_cookies()
        api = BrainmakerAPI(cookies)
        
        prompt = build_agent_prompt(group_name, messages)
        
        agent_messages = [{
            "role": "user",
            "content": [{"type": "text", "text": prompt}]
        }]
        
        # 尝试每个模型
        for model in models:
            try:
                print(f"  → 尝试模型: {model}")
                last_request_time = time.time()
                
                response = api.chat(
                    messages=agent_messages,
                    model=model,
                    temperature=0.1,
                    max_tokens=800,
                    stream=False
                )
                
                # 检查是否额度不足
                if response.status_code == 200:
                    result = api.parse_response(response)
                    if result and "额度已达上限" not in result:
                        # 成功获取结果
                        if '{' in result and '}' in result:
                            start = result.index('{')
                            end = result.rindex('}') + 1
                            json_str = result[start:end]
                            data = json.loads(json_str)
                            print(f"  ✓ 使用模型 {model} 成功")
                            
                            # 记录调用统计
                            record_call(model)
                            
                            # 缓存结果
                            cache[cache_key] = (time.time(), data)
                            return data
                    elif result and "额度已达上限" in result:
                        print(f"  ✗ {model} 额度不足，尝试下一个...")
                        continue
                        
            except Exception as e:
                print(f"  ✗ {model} 调用失败: {e}")
                continue
        
        print("  → 所有模型都不可用")
        return None
        
    except Exception as e:
        print(f"Brainmaker 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None
