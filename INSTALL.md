# 安装和配置指南

## 📦 必要安装

### 1. Python 依赖（必需）
```bash
pip3 install websocket-client requests
```

**说明：**
- `websocket-client` - 连接 Whistle WebSocket
- `requests` - 调用七鱼 HTTP API

### 2. Whistle 代理（必需）
```bash
# 方式 1：使用 npm（推荐）
npm install -g whistle

# 方式 2：使用 Homebrew
brew install whistle
```

**说明：**
- 用于拦截和捕获 HTTPS 请求
- 提供 WebSocket 接口推送数据

### 3. Swift 运行环境（已内置）
macOS 系统自带，无需安装。

## 🔐 系统权限配置

### 权限 1：Accessibility（辅助功能）- 必需

**用途：**
- 读取企微聊天窗口内容
- 点击侧边栏按钮

**配置步骤：**
1. 打开"系统偏好设置"
2. 进入"安全性与隐私"
3. 选择"隐私"标签
4. 左侧选择"辅助功能"
5. 点击左下角锁图标解锁
6. 添加以下应用：
   - ✅ Terminal（或 iTerm2）
   - ✅ Python
   - ✅ 企业微信

**验证：**
```bash
# 运行测试脚本
python3 -c "from ApplicationServices import AXIsProcessTrustedWithOptions; print('✅ 已授权' if AXIsProcessTrustedWithOptions({'AXTrustedCheckOptionPrompt': True}) else '❌ 未授权')"
```

### 权限 2：系统代理设置 - 必需

**用途：**
- 让企微流量通过 Whistle 代理

**配置步骤：**
1. 打开"系统偏好设置"
2. 进入"网络"
3. 选择当前网络（Wi-Fi 或以太网）
4. 点击"高级"
5. 选择"代理"标签
6. 勾选：
   - ✅ 网页代理（HTTP）
   - ✅ 安全网页代理（HTTPS）
7. 两者都设置为：
   - 服务器：`127.0.0.1`
   - 端口：`8899`
8. 点击"好"，然后"应用"

**验证：**
```bash
# 检查代理设置
scutil --proxy | grep -E "HTTPProxy|HTTPSProxy"
```

### 权限 3：Whistle 证书信任 - 必需

**用途：**
- 解密 HTTPS 流量（企微使用 HTTPS）

**配置步骤：**
1. 启动 Whistle：
   ```bash
   w2 start
   ```

2. 打开浏览器访问：`http://127.0.0.1:8899/`

3. 点击右上角"HTTPS"

4. 下载根证书：
   - 点击"Download RootCA"
   - 保存为 `rootCA.crt`

5. 安装证书：
   - 双击 `rootCA.crt`
   - 在"钥匙串访问"中找到"Whistle"证书
   - 右键 → "显示简介"
   - 展开"信任"
   - "使用此证书时"选择"始终信任"
   - 关闭窗口（需要输入密码）

**验证：**
```bash
# 检查证书
security find-certificate -c "Whistle" -p | openssl x509 -noout -subject
```

## ⚙️ 配置文件

### config.json（必需）

**位置：** `wecom_auto_end/config.json`

**内容：**
```json
{
  "code": "wyzqkj",
  "groupManageId": 6275817,
  "baseUrl": "https://qw.qiyukf.com",
  "cookies": {
    "QIYUFIXED_SESSIONID_QW": "你的Cookie",
    "___csrfToken": "你的Token"
  }
}
```

**获取 Cookie 方法：**
1. 启动 Whistle 并配置代理
2. 在企微中打开网易智企
3. 访问 `http://127.0.0.1:8899/`
4. 点击"Network"标签
5. 搜索 `qiyukf.com`
6. 找到任意请求，查看 Cookie
7. 复制 `QIYUFIXED_SESSIONID_QW` 和 `___csrfToken`

## ✅ 完整检查清单

```
安装检查：
□ Python 3 已安装
□ pip3 install websocket-client requests
□ npm install -g whistle（或 brew install whistle）

权限检查：
□ Accessibility 权限已授予 Terminal/Python
□ Accessibility 权限已授予企业微信
□ 系统代理已设置（127.0.0.1:8899）
□ Whistle 证书已安装并信任

配置检查：
□ config.json 已创建
□ Cookie 已填写
□ groupManageId 已确认

启动检查：
□ w2 start 成功
□ python3 full_auto.py 无报错
□ 企微可以正常使用
```

## 🚨 常见问题

### 问题：Accessibility 权限无效
**解决：**
```bash
# 重启 Terminal
# 或重新添加 Terminal 到 Accessibility 列表
```

### 问题：Whistle 证书不信任
**解决：**
```bash
# 删除旧证书
security delete-certificate -c "Whistle"

# 重新安装
w2 restart
# 然后重新下载并信任证书
```

### 问题：企微无法联网
**解决：**
```bash
# 检查 Whistle 是否运行
w2 status

# 如果未运行
w2 start

# 检查代理设置是否正确
```
