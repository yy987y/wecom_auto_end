#!/bin/bash
# 配置透明代理，只拦截企微的流量

echo "🔧 配置透明代理..."

# 1. 启动 mitmproxy 透明模式
echo "启动 mitmproxy..."
mitmdump -s mitm_interceptor.py --mode transparent --listen-port 8080 &
MITM_PID=$!
echo "mitmproxy PID: $MITM_PID"

# 2. 配置 pf 规则（需要 sudo）
echo ""
echo "⚠️  需要 sudo 权限配置防火墙规则"
sudo pfctl -f - <<EOF
rdr pass on lo0 inet proto tcp from any to any port 443 -> 127.0.0.1 port 8080
rdr pass on lo0 inet proto tcp from any to any port 80 -> 127.0.0.1 port 8080
EOF

sudo pfctl -e 2>/dev/null

echo ""
echo "✅ 透明代理已启动"
echo "📝 会话信息保存到: /tmp/qiyu_session.json"
echo ""
echo "停止代理："
echo "  kill $MITM_PID"
echo "  sudo pfctl -d"
