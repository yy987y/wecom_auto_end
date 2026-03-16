import requests
import json

class BrainmakerAPI:
    def __init__(self, cookies):
        self.base_url = "https://brainmaker.netease.com"
        self.cookies = cookies
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'content-type': 'application/json',
            'origin': 'https://brainmaker.netease.com',
            'referer': 'https://brainmaker.netease.com/v3',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def chat(self, messages, model="claude-opus-4-5-20251101", temperature=0.7, max_tokens=2048, stream=False):
        """
        发送聊天请求

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": [{"type": "text", "text": "..."}]}, ...]
            model: 模型名称
            temperature: 温度参数 (0-1)
            max_tokens: 最大token数
            stream: 是否流式返回

        Returns:
            requests.Response 对象
        """
        url = f"{self.base_url}/api/chat-bm-stream"

        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "presence_penalty": 0,
            "stream": stream,
            "web_search": False,
            "thinking": False
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            cookies=self.cookies,
            stream=stream
        )

        return response

    def parse_response(self, response):
        """解析非流式响应"""
        try:
            if response.status_code != 200:
                print(f"API 返回错误状态码: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                return None
            
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content']
            
            print(f"响应格式异常: {data}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"原始响应: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"解析响应时出错: {e}")
            return None


