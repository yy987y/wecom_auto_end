#!/bin/bash
set -e

CALIBRATE_ONLY=false
for arg in "$@"; do
    if [ "$arg" = "--calibrate" ]; then
        CALIBRATE_ONLY=true
    fi
done

echo "🎯 企微自动结束会话 - 一键启动"
echo "================================"
echo ""

# 检查 Swift 编译环境
echo "🔍 检查 Swift 编译环境..."
if ! swiftc --version &>/dev/null; then
    echo "❌ Swift 编译器未安装"
    echo "正在安装 Command Line Tools..."
    xcode-select --install
    echo "请在弹出窗口中完成安装，然后重新运行此脚本"
    exit 1
fi

# 测试 Swift 编译
TEST_SWIFT="/tmp/test_swift_$$.swift"
cat > "$TEST_SWIFT" << 'SWIFT_EOF'
import Cocoa
print("OK")
SWIFT_EOF

if ! swiftc "$TEST_SWIFT" -o /tmp/test_swift_$$ 2>/dev/null; then
    echo "⚠️  检测到 Swift 编译环境问题"
    echo "正在修复..."
    
    # 清理缓存
    rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null || true
    rm -rf ~/Library/Caches/com.apple.dt.Xcode/* 2>/dev/null || true
    
    # 重置 Xcode 路径
    sudo xcode-select --reset 2>/dev/null || true
    
    # 再次测试
    if ! swiftc "$TEST_SWIFT" -o /tmp/test_swift_$$ 2>/dev/null; then
        echo "❌ Swift 编译环境修复失败"
        echo "请手动执行："
        echo "  sudo rm -rf /Library/Developer/CommandLineTools"
        echo "  xcode-select --install"
        rm -f "$TEST_SWIFT" /tmp/test_swift_$$
        exit 1
    fi
    echo "✅ Swift 编译环境已修复"
fi
rm -f "$TEST_SWIFT" /tmp/test_swift_$$
echo "✅ Swift 编译环境正常"
echo ""

# 检查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安装"
    echo "请运行: brew install python3"
    exit 1
fi
echo "✅ Python 3: $(python3 --version)"

# 创建并使用虚拟环境
echo "📦 检查 Python 虚拟环境..."
if [ ! -d ".venv" ]; then
    echo "🛠️  创建虚拟环境 .venv ..."
    python3 -m venv .venv
else
    # 检查虚拟环境是否损坏（路径不匹配）
    if [ -f ".venv/bin/python" ]; then
        if ! .venv/bin/python --version &>/dev/null; then
            echo "⚠️  虚拟环境损坏，重新创建..."
            rm -rf .venv
            python3 -m venv .venv
        fi
    fi
fi

VENV_PY="$(pwd)/.venv/bin/python"
VENV_PIP="$(pwd)/.venv/bin/pip"

# 检查依赖是否已安装
echo "📦 检查 Python 依赖..."
DEPS_OK=true
for pkg in websocket-client requests pyobjc pyyaml playwright; do
    if ! "$VENV_PY" -c "import ${pkg//-/_}" &>/dev/null 2>&1; then
        DEPS_OK=false
        break
    fi
done

if [ "$DEPS_OK" = true ]; then
    echo "✅ Python 依赖已就绪"
else
    echo "📦 安装缺失的 Python 依赖..."
    "$VENV_PIP" install --quiet --upgrade pip setuptools wheel 2>/dev/null || true
    "$VENV_PIP" install --trusted-host pypi.org --trusted-host files.pythonhosted.org websocket-client requests pyobjc pyyaml playwright || {
        echo "❌ 虚拟环境依赖安装失败"
        exit 1
    }
    "$VENV_PY" -m playwright install chromium >/dev/null 2>&1 || true
    echo "✅ Python 依赖已安装"
fi

# 检查 Whistle
if ! command -v w2 &> /dev/null; then
    echo "📦 安装 Whistle..."
    if command -v npm &> /dev/null; then
        npm install -g whistle
    else
        echo "❌ npm 未安装，请先安装 Node.js"
        exit 1
    fi
fi
echo "✅ Whistle: $(w2 --version)"

# 启动 Whistle
echo "🚀 启动 Whistle..."
w2 start 2>/dev/null || echo "⚠️  Whistle 可能已在运行"
sleep 2
echo "✅ Whistle 已启动"

# 检查 Brainmaker 配置（可选）
echo ""
echo "🔐 检查 Brainmaker 配置..."
if [ ! -f "credentials.local.yaml" ]; then
    echo "⚠️  未找到 credentials.local.yaml"
    echo ""
    echo "💡 如需 AI 兜底判断，请创建 credentials.local.yaml："
    echo "   username: your_email@example.com"
    echo "   password: your_password"
    echo ""
    echo "或使用 --debug 模式跳过 AI 判断"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Brainmaker 配置已存在"
fi
echo ""

# 检查证书
echo "🔐 检查 Whistle 证书..."
if ! security find-certificate -c "Whistle" &>/dev/null; then
    echo "⚠️  证书未安装，正在安装..."
    CERT_PATH="/tmp/whistle-rootca.crt"
    curl -s http://127.0.0.1:8899/cgi-bin/rootca > "$CERT_PATH"
    
    echo "💡 需要输入密码来安装证书..."
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$CERT_PATH" && {
        echo "✅ 证书已安装"
    } || {
        echo "❌ 证书安装失败，请手动安装"
    }
else
    echo "✅ 证书已安装"
fi

# UI 校准
if [ "$CALIBRATE_ONLY" = true ] || [ ! -f "data/ui_mapping.json" ]; then
    echo ""
    echo "🧭 启动前 UI 校准..."
    echo "请先把企业微信切到目标会话窗口，再根据输出确认当前群名 + 当前聊天区"
    echo ""
    "$VENV_PY" ui_calibrator.py
    if [ "$CALIBRATE_ONLY" = true ]; then
        echo "✅ 校准完成"
        exit 0
    fi
fi

# 启动主程序
echo ""
echo "🎯 启动监控程序..."
echo ""
"$VENV_PY" full_auto.py

