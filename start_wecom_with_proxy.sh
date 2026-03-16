#!/bin/bash
# 使用代理启动企微

export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080

echo "🚀 使用代理启动企业微信..."
echo "   代理: 127.0.0.1:8080"
echo ""

# 启动企微
open -a "企业微信"

echo "✅ 企微已启动（使用代理）"
echo "⚠️  其他应用不受影响"
