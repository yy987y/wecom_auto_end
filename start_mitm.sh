#!/bin/bash
# 启动 mitmproxy 监听企微网络请求

echo "🚀 启动 mitmproxy 监听..."
echo "📝 会话信息将保存到: /tmp/qiyu_session.json"
echo ""
echo "⚠️  首次使用需要："
echo "1. 安装证书: ~/.mitmproxy/mitmproxy-ca-cert.pem"
echo "2. 配置企微代理: 127.0.0.1:8080"
echo ""

# 启动 mitmproxy
mitmdump -s mitm_interceptor.py --listen-port 8080 --set block_global=false
