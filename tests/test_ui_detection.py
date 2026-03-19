import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wecom_monitor import analyze_ui_entries, normalize_ui_mapping, parse_message_block


def build_session_list_entries(prefix, total_rows):
    entries = []
    for idx in range(total_rows):
        row = f'{prefix}.0.{idx}'
        entries.extend([
            (f'{row}.0.1', f'会话{idx}'),
            (f'{row}.0.2', f'用户{idx}: 最近消息 {idx}'),
            (f'{row}.0.4', '昨天 18:31' if idx % 2 == 0 else '外部'),
        ])
    return entries


def build_current_layout_entries():
    entries = []
    entries.extend(build_session_list_entries('window.0.29.2', 12))
    entries.append(('window.0.29.5', '云信 -飞虎互动音视频项目沟通'))
    entries.append(('window.0.29.6', '由企业微信用户创建的外部群，含31位外部联系人 | 群主: 高超'))
    entries.extend([
        ('window.0.29.9.0.0.0.0.0.1', '3月9日 16:13'),
        ('window.0.29.9.0.0.0.0.0.2', '高超:'),
        ('window.0.29.9.0.0.0.0.0.3', '@杨帅旗 和同事确认了一下，目前小程序的媒体服务器没有做互踢的通知'),
        ('window.0.29.9.0.0.0.1.0.0', '3月9日 16:18'),
        ('window.0.29.9.0.0.0.1.0.1', '我确认一下'),
        ('window.0.29.9.0.0.0.2.0.0', '2月10日 17:57'),
        ('window.0.29.9.0.0.0.2.0.1', '来自飞虎互动的杨帅旗撤回了一条消息'),
    ])
    for idx, name in enumerate(['Abble', '常远', '冯江涛', '庆程', '网易-徐冬', '周梁伟']):
        entries.append((f'window.0.29.9.2.0.{idx}.0.1', name))
    return entries


def build_legacy_layout_entries():
    entries = []
    entries.extend(build_session_list_entries('window.0.31.2', 10))
    entries.append(('window.0.31.5', '好未来-云信重点问题沟通群'))
    entries.append(('window.0.31.6', '由企业微信用户创建的外部群，含42位外部联系人 | 群主: 高超'))
    entries.extend([
        ('window.0.31.9.0.0.0.0.0.1', '今天 10:11'),
        ('window.0.31.9.0.0.0.0.0.2', '薛鹏:'),
        ('window.0.31.9.0.0.0.0.0.3', '发你邮箱了'),
        ('window.0.31.9.0.0.0.1.0.0', '今天 10:15'),
        ('window.0.31.9.0.0.0.1.0.1', '收到'),
    ])
    for idx, name in enumerate(['成员A', '成员B', '成员C']):
        entries.append((f'window.0.31.9.9.0.{idx}.0.1', name))
    return entries


class UiDetectionTests(unittest.TestCase):
    def test_current_layout_prefers_real_chat_area(self):
        context = analyze_ui_entries(build_current_layout_entries())
        self.assertEqual(context['selected']['session_list_prefix'], 'window.0.29.2')
        self.assertEqual(context['selected']['group_name_prefix'], 'window.0.29.5')
        self.assertEqual(context['selected']['group_meta_prefix'], 'window.0.29.6')
        self.assertEqual(context['selected']['chat_prefix'], 'window.0.29.9')
        self.assertEqual(context['selected']['chat_main_thread_prefix'], 'window.0.29.9.0.0.0')
        self.assertEqual(len(context['messages']), 3)
        self.assertIn('媒体服务器没有做互踢的通知', context['messages'][0]['body'])

    def test_legacy_layout_still_works(self):
        context = analyze_ui_entries(build_legacy_layout_entries())
        self.assertEqual(context['selected']['session_list_prefix'], 'window.0.31.2')
        self.assertEqual(context['selected']['group_name_prefix'], 'window.0.31.5')
        self.assertEqual(context['selected']['chat_prefix'], 'window.0.31.9')
        self.assertEqual(context['selected']['chat_main_thread_prefix'], 'window.0.31.9.0.0.0')
        self.assertEqual(context['messages'][-1]['body'], '收到')

    def test_invalid_old_mapping_falls_back_to_detected_prefix(self):
        mapping = {
            'chat_prefix': 'window.0.24.0',
            'session_list_prefix': 'window.0.24.1',
        }
        context = analyze_ui_entries(build_current_layout_entries(), mapping)
        self.assertEqual(context['selected']['chat_prefix'], 'window.0.29.9')
        self.assertEqual(context['selected']['session_list_prefix'], 'window.0.29.2')

    def test_normalize_ui_mapping_keeps_new_fields_and_defaults(self):
        normalized = normalize_ui_mapping({'chat_prefix': 'window.0.29.9'})
        self.assertEqual(normalized['chat_prefix'], 'window.0.29.9')
        self.assertIsNone(normalized['chat_main_thread_prefix'])
        self.assertIsNone(normalized['group_name_prefix'])

    def test_parse_message_block_handles_system_message(self):
        parsed = parse_message_block([
            ('window.0.29.9.0.0.0.2.0.0', '2月10日 17:57'),
            ('window.0.29.9.0.0.0.2.0.1', '来自飞虎互动的杨帅旗撤回了一条消息'),
        ])
        self.assertEqual(parsed['sender'], '')
        self.assertEqual(parsed['body'], '来自飞虎互动的杨帅旗撤回了一条消息')


if __name__ == '__main__':
    unittest.main()
