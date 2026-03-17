#!/usr/bin/env python3
"""
企微自动结束会话 v1.2
状态机版本：
1. 启动 Whistle
2. 检查企微 UI 状态
3. 确保侧边栏 / 网易智企 / 登录状态就绪
4. 读取真实群名 + 消息
5. 本地三态判断 + Brainmaker 兜底
6. 通过 Whistle HTTP 拉取 session/token
7. 调用 HTTP API 结束会话
"""
import base64
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import requests
from AppKit import NSWorkspace
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    AXUIElementCopyAttributeValue,
    AXUIElementCreateApplication,
    kAXFocusedWindowAttribute,
)

sys.path.insert(0, str(Path(__file__).parent))
from logger import setup_logger
from wecom_judge import judge_end_status
from wecom_monitor import ax_copy, find_wecom_app, get_group_name, get_messages
from wecom_executor import run_swift, open_sidebar_and_qiyu, ensure_login_state, reset_sidebar

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
logger = setup_logger('wecom_auto', Path(__file__).parent / 'logs')


class WeChatAutoFlow:
    def __init__(self):
        self.whistle_port = 8899
        self.group_manage_id = 6275817
        self.current_group = None
        self.script_dir = Path(__file__).parent
        self.last_whistle_id = None
        self.token = None
        self.session_cookie = None
        self.cached_sessions = []  # 缓存会话列表
        self.session_mapping_file = self.script_dir / 'data' / 'session_mapping.txt'
        self.session_mapping = self.load_session_mapping()
        self.code = None  # 企业代码
        self.full_cookies = {}  # 完整的 Cookie

    def start_whistle(self):
        logger.info('🚀 启动 Whistle...')
        try:
            subprocess.run(['w2', 'start'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            time.sleep(2)
            logger.info('✅ Whistle 已启动')
        except Exception as e:
            logger.warning(f'⚠️ Whistle 启动异常/可能已运行: {e}')

    def load_session_mapping(self):
        """加载群名->sessionId映射"""
        mapping = {}
        if not self.session_mapping_file.exists():
            return mapping
        try:
            with open(self.session_mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        group_name, session_id = line.split(':', 1)
                        mapping[group_name.strip()] = session_id.strip()
            logger.info(f'📖 加载了 {len(mapping)} 条会话映射')
        except Exception as e:
            logger.error(f'加载会话映射失败: {e}')
        return mapping

    def save_session_mapping(self):
        """保存群名->sessionId映射"""
        try:
            self.session_mapping_file.parent.mkdir(exist_ok=True)
            with open(self.session_mapping_file, 'w', encoding='utf-8') as f:
                f.write('# 群名 -> sessionId 映射\n')
                f.write('# 自动生成，请勿手动编辑\n\n')
                for group_name, session_id in sorted(self.session_mapping.items()):
                    f.write(f'{group_name}: {session_id}\n')
            logger.debug(f'💾 已保存 {len(self.session_mapping)} 条会话映射')
        except Exception as e:
            logger.error(f'保存会话映射失败: {e}')

    def get_focused_window(self):
        app = find_wecom_app()
        if not app:
            logger.warning('未找到企业微信进程')
            return None, None
        app_el = AXUIElementCreateApplication(app.processIdentifier())
        focused = ax_copy(app_el, kAXFocusedWindowAttribute)
        if not focused:
            logger.warning('未获取到企微焦点窗口')
            return app, None
        return app, focused

    def get_current_context(self):
        app, focused = self.get_focused_window()
        if not focused:
            return None, []
        group_name = get_group_name(focused)
        messages = get_messages(focused)
        logger.debug(f'当前群名: {group_name}')
        logger.debug(f'当前消息数: {len(messages)}')
        return group_name, messages

    def ensure_sidebar_chain(self, max_retries=2):
        """确保 UI 进入网易智企就绪态；若卡住则关闭侧边栏重试"""
        for attempt in range(1, max_retries + 1):
            logger.info(f'🧪 UI 就绪尝试 #{attempt}')
            ok, msg = open_sidebar_and_qiyu(wait_seconds=5)
            if not ok:
                logger.error(f'打开侧边栏/切网易智企失败: {msg}')
                continue

            login_ok, login_msg = ensure_login_state()
            if login_ok:
                logger.info('✅ 登录状态已处理完成或已处于登录成功状态')
            else:
                logger.warning('⚠️ 当前未明确判定为已登录，继续结合 Whistle 结果判断')

            logger.info('⏳ 等待 qiyukf 请求产生...')
            time.sleep(3)
            sessions = self.extract_qiyu_context_from_whistle()
            if sessions or self.token or self.session_cookie:
                logger.info(f'✅ UI 就绪成功：token={bool(self.token)}, cookie={bool(self.session_cookie)}, sessions={len(sessions)}')
                return True

            logger.warning('本轮未检测到 qiyukf 请求或关键参数，尝试重置侧边栏后重试')
            reset_sidebar()
            time.sleep(1)

        return False

    def fetch_whistle_data(self, count=100):
        url = f'http://127.0.0.1:{self.whistle_port}/cgi-bin/get-data?count={count}'
        try:
            r = requests.get(url, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f'拉取 Whistle 数据失败: {e}')
            return None

    def extract_qiyu_context_from_whistle(self):
        """通过 HTTP 拉取最近请求，提取 token/session/sessionId 列表"""
        data = self.fetch_whistle_data(150)
        if not data:
            return []

        items = data.get('data', {}).get('data', {})
        logger.debug(f'Whistle 最近请求数: {len(items)}')

        qiyu_count = 0
        sessions = []
        for _, item in items.items():
            req_url = item.get('url', '') or ''
            if 'qiyukf.com' not in req_url:
                continue
            qiyu_count += 1

            # token
            if 'token=' in req_url and not self.token:
                try:
                    self.token = req_url.split('token=')[1].split('&')[0]
                    logger.info(f'🔑 获取到 token: {self.token[:20]}...')
                except Exception:
                    pass

            # cookie
            req_headers = item.get('req', {}).get('headers', {}) or {}
            cookie_str = req_headers.get('cookie', '') or req_headers.get('Cookie', '') or ''
            if cookie_str:
                # 解析所有 Cookie
                for part in cookie_str.split(';'):
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=', 1)
                        self.full_cookies[key] = value
                
                # 提取关键 Cookie
                if 'QIYUFIXED_SESSIONID_QW=' in cookie_str and not self.session_cookie:
                    try:
                        for part in cookie_str.split(';'):
                            part = part.strip()
                            if part.startswith('QIYUFIXED_SESSIONID_QW='):
                                self.session_cookie = part.split('=', 1)[1]
                                logger.info(f'🍪 获取到 session cookie: {self.session_cookie[:12]}...')
                                break
                    except Exception:
                        pass
            
            # 提取 code 参数
            if 'code=' in req_url and not self.code:
                try:
                    self.code = req_url.split('code=')[1].split('&')[0]
                    logger.info(f'🏢 获取到 code: {self.code}')
                except Exception:
                    pass

            # 会话列表接口
            if 'session/chat/service/record' in req_url:
                logger.info('📋 发现会话列表请求')
                res = item.get('res', {}) or {}
                base64_body = res.get('base64')
                if not base64_body:
                    logger.warning('会话列表响应中无 base64 内容')
                    continue
                try:
                    decoded = base64.b64decode(base64_body).decode('utf-8')
                    payload = json.loads(decoded)
                    result = payload.get('result', [])
                    logger.info(f'📋 解析出 {len(result)} 条会话记录')
                    for row in result:
                        if row.get('status') == 1:
                            sessions.append({
                                'id': row.get('id'),
                                'name': ((row.get('user') or {}).get('realname') or 'unknown'),
                                'timestamp': item.get('startTime', 0)  # 记录请求时间
                            })
                except Exception as e:
                    logger.error(f'解析 Whistle 会话响应失败: {e}')
            
            # 会话详情接口（更准确，包含当前查看的会话）
            if 'session/chat/detail' in req_url or 'sessionId=' in req_url:
                try:
                    if 'sessionId=' in req_url:
                        session_id = req_url.split('sessionId=')[1].split('&')[0]
                        timestamp = item.get('startTime', 0)
                        logger.debug(f'🎯 从请求 URL 提取到 sessionId: {session_id} (时间: {timestamp})')
                        # 将当前会话放在列表最前面，并记录时间戳
                        sessions.insert(0, {
                            'id': session_id,
                            'name': 'current',
                            'timestamp': timestamp,
                            'is_current': True
                        })
                except Exception as e:
                    logger.debug(f'提取 sessionId 失败: {e}')

        logger.info(f'Whistle qiyukf 请求数: {qiyu_count}')
        if qiyu_count == 0:
            logger.warning('最近请求中未发现 qiyukf.com')
        
        # 按时间戳排序，最新的在前面
        if sessions:
            sessions.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            logger.info(f'📋 提取到 {len(sessions)} 个会话，已按时间排序')
            if sessions[0].get('is_current'):
                logger.info(f'🎯 最新会话 ID: {sessions[0]["id"]}')
        
        logger.debug(f'提取结果: sessions={len(sessions)}, token={bool(self.token)}, cookie={bool(self.session_cookie)}')
        
        # 如果提取到会话列表，更新缓存和映射
        if sessions:
            self.cached_sessions = sessions
            logger.info(f'📦 已缓存 {len(sessions)} 个会话')
            # 更新映射（假设会话名称就是群名）
            for session in sessions:
                session_name = session.get('name', '')
                session_id = session.get('id', '')
                if session_name and session_id:
                    self.session_mapping[session_name] = session_id
            self.save_session_mapping()
        
        return sessions

    def judge_current_chat(self, group_name, messages):
        status, confidence, reason = judge_end_status(messages)
        logger.info(f'本地判断: {status} / {confidence:.2f} / {reason}')

        if status == 'uncertain':
            logger.info('本地判断不确定，调用 Brainmaker 兜底...')
            try:
                from wecom_agent import call_brainmaker
                ai_result = call_brainmaker(group_name, messages)
                logger.info(f'AI 结果: {ai_result}')
                if ai_result and ai_result.get('ended') and ai_result.get('confidence', 0) >= 0.7:
                    return 'strong_end_candidate', ai_result.get('confidence', 0.8), ai_result.get('reason', 'AI判断结束')
                return 'not_end', ai_result.get('confidence', 0.5) if ai_result else 0.0, ai_result.get('reason', 'AI判断未结束') if ai_result else 'AI失败'
            except Exception as e:
                logger.error(f'Brainmaker 调用失败: {e}', exc_info=True)
                return 'not_end', 0.0, f'Brainmaker 异常: {e}'
        return status, confidence, reason

    def close_sessions(self, sessions):
        if not sessions:
            logger.warning('没有可关闭的 session 列表')
            return 0
        if not self.token:
            logger.warning('没有 token，无法关闭')
            return 0

        success = 0
        base_url = 'https://qw.qiyukf.com/chat/api/session/closeWXCSSession'
        
        for session in sessions:
            # 构造 URL 参数
            url = base_url
            params = []
            if self.code:
                params.append(f'code={self.code}')
            if self.token:
                params.append(f'token={self.token}')
            if params:
                url = f'{base_url}?{"&".join(params)}'
            
            body = {
                'sessionId': session['id'],
                'groupManageId': self.group_manage_id
            }
            
            # 使用完整的 Cookie
            cookies = self.full_cookies.copy() if self.full_cookies else {}
            if not cookies.get('___csrfToken') and self.token:
                cookies['___csrfToken'] = self.token
            
            try:
                logger.info(f'🔄 关闭会话: {session.get("name", "unknown")} / {session["id"]}')
                logger.debug(f'URL: {url}')
                logger.debug(f'Cookies: {len(cookies)} 个')
                r = requests.post(url, data=body, cookies=cookies, verify=False, timeout=8)
                logger.debug(f'响应: {r.status_code} - {r.text[:200]}')
                
                if r.status_code == 200:
                    resp_data = r.json()
                    if resp_data.get('code') == 200:
                        success += 1
                        logger.info('  ✅ 成功')
                    else:
                        logger.warning(f'  ❌ 失败: {resp_data.get("message", "unknown")}')
                else:
                    logger.warning(f'  ❌ 失败 HTTP {r.status_code}: {r.text[:200]}')
            except Exception as e:
                logger.error(f'  ❌ 异常: {e}')
        return success

    def ensure_qiyu_ready(self):
        logger.info('🧭 启动阶段：强制将 UI 调整到“网易智企就绪态”...')
        chain_ok = self.ensure_sidebar_chain()
        if not chain_ok:
            logger.error('❌ UI 就绪链路失败：侧边栏 / 网易智企 / 登录 未完成')
            return False
        logger.info('⏳ UI 链路已执行，等待 qiyukf 请求产生...')
        time.sleep(3)
        sessions = self.extract_qiyu_context_from_whistle()
        qiyu_ok = bool(sessions) or bool(self.token) or bool(self.session_cookie)
        if qiyu_ok:
            logger.info(f'✅ 网易智企就绪：token={bool(self.token)}, cookie={bool(self.session_cookie)}, sessions={len(sessions)}')
            return True
        logger.warning('⚠️ 未检测到 qiyukf 请求 / token / cookie / session，网易智企可能未真正就绪')
        return False

    def run_once(self):
        group_name, messages = self.get_current_context()
        if not group_name:
            logger.warning('未读到当前群名，跳过本轮')
            return
        if len(messages) < 3:
            logger.info(f'当前会话消息过少({len(messages)})，跳过: {group_name}')
            return

        logger.info(f'📍 当前群/会话: {group_name}')
        status, confidence, reason = self.judge_current_chat(group_name, messages)
        logger.info(f'最终判断: {status} / {confidence:.2f} / {reason}')

        if status != 'strong_end_candidate':
            logger.info('当前不需要结束，继续监听')
            return

        logger.info('进入结束会话链路...')
        
        # 企微切换会话后侧边栏内容会重置，需要重新点击网易智企
        logger.info('🔄 重新切换到网易智企以刷新数据...')
        refresh_ok, _ = run_swift('wecom_click_netease.swift')
        if refresh_ok:
            logger.info('✅ 已切换到网易智企')
            time.sleep(3)  # 等待请求产生
        else:
            logger.warning('⚠️ 切换网易智企失败，尝试完整刷新侧边栏')
            refresh_ok, _ = open_sidebar_and_qiyu(wait_seconds=3)
            if not refresh_ok:
                logger.error('刷新侧边栏失败')
                return
            time.sleep(2)
        
        sessions = self.extract_qiyu_context_from_whistle()
        if not sessions:
            logger.warning('刷新后仍未提取到会话列表，尝试使用缓存')
            sessions = self.cached_sessions
        if not sessions:
            logger.warning('缓存也为空，尝试从映射文件查找当前群的 sessionId')
            if group_name in self.session_mapping:
                session_id = self.session_mapping[group_name]
                sessions = [{'id': session_id, 'name': group_name}]
                logger.info(f'✅ 从映射找到会话: {group_name} -> {session_id}')
            else:
                logger.error(f'未找到群 "{group_name}" 的 sessionId 映射')
                return

        # 只关闭当前会话（优先使用标记为 is_current 的）
        target_session = None
        for session in sessions:
            if session.get('is_current'):
                target_session = session
                logger.info(f'🎯 找到当前会话: {session["id"]}')
                break
        
        if not target_session and sessions:
            # 如果没有明确标记，使用最新的（第一个）
            target_session = sessions[0]
            logger.warning(f'⚠️ 未找到明确的当前会话，使用第一个: {target_session["id"]}')
        
        if not target_session:
            logger.error('未找到可关闭的会话')
            return

        success = self.close_sessions([target_session])
        logger.info(f'✅ 本轮关闭完成: {success}/1')

    def run(self):
        if not AXIsProcessTrustedWithOptions({'AXTrustedCheckOptionPrompt': True}):
            logger.error('❌ 需要 Accessibility 权限')
            return

        logger.info('🎯 企微自动结束会话 v1.2 启动')
        self.start_whistle()

        # 先强制把 UI 调整到“网易智企就绪态”
        ready = self.ensure_qiyu_ready()
        logger.info(f'🎛️ 网易智企就绪检查结果: {ready}')

        logger.info('👀 开始监听当前企微会话...')
        while True:
            try:
                group_name, _ = self.get_current_context()
                if group_name and group_name != self.current_group:
                    logger.info(f'🔄 检测到会话切换: {self.current_group} -> {group_name}')
                    self.current_group = group_name
                    self.run_once()
                time.sleep(2)
            except KeyboardInterrupt:
                logger.info('👋 已退出')
                break
            except Exception as e:
                logger.error(f'主循环异常: {e}', exc_info=True)
                time.sleep(3)


if __name__ == '__main__':
    WeChatAutoFlow().run()
