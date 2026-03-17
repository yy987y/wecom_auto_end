#!/usr/bin/env python3
"""
企微消息监听 - 回调版本
使用 Accessibility Notification 而不是轮询
"""
import sys
from pathlib import Path
from AppKit import NSWorkspace
from ApplicationServices import (
    AXIsProcessTrustedWithOptions,
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXObserverCreate,
    AXObserverAddNotification,
    AXObserverRemoveNotification,
    CFRunLoopRun,
    CFRunLoopStop,
    CFRunLoopGetCurrent,
    kAXFocusedWindowAttribute,
    kAXValueChangedNotification,
    kAXUIElementCreatedNotification,
    kAXRowCountChangedNotification,
)

sys.path.insert(0, str(Path(__file__).parent))
from wecom_monitor import get_group_name, get_messages, find_wecom_app
from logger import logger


class WeChatMonitor:
    def __init__(self, on_message_change):
        """
        on_message_change: 回调函数 (group_name, messages) -> None
        """
        self.on_message_change = on_message_change
        self.observer = None
        self.app = None
        self.last_message_hash = None
        
    def notification_callback(self, observer, element, notification, refcon):
        """Accessibility 通知回调"""
        try:
            logger.debug(f'收到通知: {notification}')
            
            # 读取当前群名和消息
            app = find_wecom_app()
            if not app:
                return
            
            app_el = AXUIElementCreateApplication(app.processIdentifier())
            focused = AXUIElementCopyAttributeValue(app_el, kAXFocusedWindowAttribute, None)[1]
            if not focused:
                return
            
            group_name = get_group_name(focused)
            messages = get_messages(focused)
            
            if not group_name or len(messages) < 2:
                return
            
            # 计算消息哈希，避免重复触发
            msg_hash = hash(str(messages[-1]))
            if msg_hash == self.last_message_hash:
                return
            
            self.last_message_hash = msg_hash
            logger.info(f'💬 检测到消息变化: {group_name}')
            
            # 调用回调
            self.on_message_change(group_name, messages)
            
        except Exception as e:
            logger.error(f'通知回调异常: {e}', exc_info=True)
    
    def start(self):
        """启动监听"""
        if not AXIsProcessTrustedWithOptions({'AXTrustedCheckOptionPrompt': True}):
            logger.error('❌ 需要 Accessibility 权限')
            return False
        
        self.app = find_wecom_app()
        if not self.app:
            logger.error('❌ 未找到企微应用')
            return False
        
        pid = self.app.processIdentifier()
        app_el = AXUIElementCreateApplication(pid)
        
        # 创建观察者
        self.observer = AXObserverCreate(pid, self.notification_callback, None)[1]
        
        # 注册通知
        notifications = [
            kAXValueChangedNotification,
            kAXUIElementCreatedNotification,
            kAXRowCountChangedNotification,
        ]
        
        for notif in notifications:
            try:
                AXObserverAddNotification(self.observer, app_el, notif, None)
                logger.info(f'✅ 已注册通知: {notif}')
            except Exception as e:
                logger.warning(f'注册通知失败 {notif}: {e}')
        
        logger.info('🎯 开始监听企微消息（回调模式）...')
        
        # 进入事件循环
        try:
            CFRunLoopRun()
        except KeyboardInterrupt:
            logger.info('👋 已退出')
        
        return True
    
    def stop(self):
        """停止监听"""
        if self.observer:
            # 移除所有通知
            CFRunLoopStop(CFRunLoopGetCurrent())
            logger.info('✅ 已停止监听')


def main():
    """测试"""
    def on_message(group_name, messages):
        print(f'\n📍 群名: {group_name}')
        print(f'📝 消息数: {len(messages)}')
        if messages:
            last = messages[-1]
            print(f'📝 最后一条: [{last.get("sender")}] {last.get("content", "")[:50]}')
    
    monitor = WeChatMonitor(on_message)
    monitor.start()


if __name__ == '__main__':
    main()
