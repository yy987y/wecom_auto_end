#!/usr/bin/env python3
"""
企微消息读取 - OCR 版本
使用 macOS Vision Framework 识别屏幕文本
"""
import subprocess
import tempfile
from pathlib import Path
from AppKit import NSWorkspace
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    CGWindowListCreateImage,
    CGRectMake,
    kCGWindowImageDefault,
)
from Cocoa import NSBitmapImageRep, NSPNGFileType


def find_wecom_window():
    """查找企微窗口"""
    window_list = CGWindowListCopyWindowInfo(
        kCGWindowListOptionOnScreenOnly, kCGNullWindowID
    )
    
    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName', '')
        window_name = window.get('kCGWindowName', '')
        
        if any(n in owner_name for n in ['企业微信', 'WeCom', 'WXWork']):
            if window_name:  # 有标题的窗口才是聊天窗口
                return window
    
    return None


def capture_window_bottom(window, height=500):
    """截取窗口底部区域"""
    bounds = window['kCGWindowBounds']
    x = bounds['X']
    y = bounds['Y']
    w = bounds['Width']
    h = bounds['Height']
    
    # 只截取底部 height 像素
    capture_y = y + h - height
    capture_rect = CGRectMake(x, capture_y, w, height)
    
    # 截图
    window_id = window['kCGWindowNumber']
    image = CGWindowListCreateImage(
        capture_rect,
        kCGWindowListOptionOnScreenOnly,
        window_id,
        kCGWindowImageDefault
    )
    
    return image


def save_image_to_file(cg_image, filepath):
    """保存 CGImage 到文件"""
    bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)
    data = bitmap.representationUsingType_properties_(NSPNGFileType, None)
    data.writeToFile_atomically_(str(filepath), True)


def ocr_image_with_vision(image_path):
    """使用 Vision Framework 进行 OCR"""
    script = f'''
import Vision
import CoreImage

let url = URL(fileURLWithPath: "{image_path}")
let ciImage = CIImage(contentsOf: url)!

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(ciImage: ciImage, options: [:])
try? handler.perform([request])

if let results = request.results as? [VNRecognizedTextObservation] {{
    for observation in results {{
        if let text = observation.topCandidates(1).first?.string {{
            print(text)
        }}
    }}
}}
'''
    
    # 保存 Swift 脚本
    script_file = Path(tempfile.gettempdir()) / 'ocr_vision.swift'
    script_file.write_text(script)
    
    # 执行
    result = subprocess.run(
        ['swift', str(script_file)],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        lines = result.stdout.strip().split('\n')
        return [line for line in lines if line.strip()]
    
    return []


def parse_messages_from_ocr(lines):
    """从 OCR 结果解析消息"""
    messages = []
    current_sender = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 简单启发式：如果行尾有 @ 或包含时间，可能是发送者
        # 这里需要根据实际 OCR 结果调整
        if '@' in line or ':' in line[:10]:
            # 保存上一条消息
            if current_sender and current_content:
                messages.append({
                    'sender': current_sender,
                    'content': ' '.join(current_content),
                    'body': f'{current_sender}: {" ".join(current_content)}'
                })
            
            # 开始新消息
            current_sender = line
            current_content = []
        else:
            # 消息内容
            current_content.append(line)
    
    # 保存最后一条
    if current_sender and current_content:
        messages.append({
            'sender': current_sender,
            'content': ' '.join(current_content),
            'body': f'{current_sender}: {" ".join(current_content)}'
        })
    
    return messages


def get_messages_by_ocr():
    """使用 OCR 读取消息"""
    # 查找企微窗口
    window = find_wecom_window()
    if not window:
        return []
    
    # 截取底部区域
    image = capture_window_bottom(window, height=500)
    if not image:
        return []
    
    # 保存到临时文件
    temp_file = Path(tempfile.gettempdir()) / 'wecom_chat.png'
    save_image_to_file(image, temp_file)
    
    # OCR 识别
    lines = ocr_image_with_vision(temp_file)
    
    # 解析消息
    messages = parse_messages_from_ocr(lines)
    
    return messages


def main():
    """测试"""
    print('🔍 使用 OCR 读取企微消息...')
    messages = get_messages_by_ocr()
    
    print(f'\n📝 读取到 {len(messages)} 条消息：')
    for i, msg in enumerate(messages[-5:], 1):
        print(f'{i}. [{msg["sender"]}] {msg["content"][:50]}')


if __name__ == '__main__':
    main()
