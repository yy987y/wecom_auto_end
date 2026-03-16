#!/usr/bin/env python3
"""
测试完整流程
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from wecom_executor import execute_end_session

if __name__ == '__main__':
    print("开始测试完整流程...\n")
    success, message = execute_end_session()
    print(f"\n结果: {message}")
    sys.exit(0 if success else 1)
