#!/bin/bash

echo "=== 完整流程测试 ==="

cd ~/.openclaw/workspace/wecom_auto_end

echo ""
echo "步骤1: 检查并确保侧边栏打开"
swift wecom_click_netease.swift 2>&1 | grep -q "已触发"
if [ $? -eq 0 ]; then
    echo "✅ 侧边栏已打开"
else
    echo "侧边栏未打开，尝试打开..."
    swift wecom_click_sidebar_candidate.swift
    sleep 1
fi

echo ""
echo "步骤2: 点击网易智企"
swift wecom_click_netease.swift
if [ $? -ne 0 ]; then
    echo "❌ 点击网易智企失败"
    exit 1
fi

echo ""
echo "步骤3: 等待并查找结束会话按钮（最多10次）"
for i in {1..10}; do
    sleep 1
    echo "尝试 $i/10..."
    swift wecom_click_end_session.swift 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ 完整流程成功！"
        exit 0
    fi
done

echo "❌ 10次尝试后仍未找到按钮"
echo "请手动检查页面状态"
exit 1
