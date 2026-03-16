# 企微自动结束会话 v1.3

自动化工具，监听企微当前会话，结合本地规则 + Brainmaker 判断是否需要结束，并在需要时走“侧边栏 → 网易智企 → 登录 → Whistle 抓取 → HTTP API 结束会话”完整链路。

## 🎯 功能特性

- ✅ 读取真实当前会话标题与消息（不再依赖窗口标题）
- ✅ 本地三态判断 + Brainmaker AI 兜底
- ✅ 复用老版本已验证的执行链路：侧边栏 → 网易智企 → 重登录
- ✅ 通过 Whistle HTTP 拉取最近请求（不再依赖未验证的 WebSocket）
- ✅ 调用七鱼 HTTP API 结束会话
- ✅ 完整日志系统，便于排查

## 🚀 一键启动

```bash
cd /Users/yanchao/.openclaw/workspace/wecom_auto_end
./start.sh
```

脚本会自动：
1. 检查并安装依赖（使用 `.venv`，避免系统 Python/PEP 668 问题；自动安装 websocket-client / requests / pyobjc / pyyaml / playwright）
2. 启动 Whistle
3. 检查并安装证书（需要输入密码）
4. 启动监控程序

## 📋 当前主流程

```
启动脚本
  ↓
检查环境（venv / whistle / 日志）
  ↓
强制将 UI 调整到“网易智企就绪态”
  ├─ 打开侧边栏
  ├─ 切到网易智企
  ├─ 如需则登录
  └─ 验证是否已产生 qiyukf 请求 / token / cookie / session
  ↓
读取当前会话标题 + 最近消息
  ↓
本地三态判断
  ├─ not_end → 继续监听
  ├─ uncertain → 调用 Brainmaker AI（固定模型 claude-opus-4-5-20251101）
  └─ strong_end_candidate → 进入结束链路
       ↓
  Whistle HTTP 拉取最近请求
       ↓
  提取 token / cookie / sessionId
       ↓
  调用 closeWXCSSession
```

**本地判断逻辑：**
- 客户确认词（好的、OK）+3分
- 客户感谢词（谢谢）+2分
- 我方承诺（稍后答复）+2分
- 问题已解决（已修复）+2分
- 检测到新问题（还有个问题）-5分
- 评分≥4：直接结束
- 评分<0：继续监听
- 其他：交给 Brainmaker 判断

## 📁 核心文件

- `start.sh` - 一键启动脚本
- `full_auto.py` - 主程序（v1.2 状态机）
- `wecom_monitor.py` - 读取真实群名和消息（老版本验证逻辑）
- `wecom_executor.py` - 执行器：侧边栏 → 网易智企 → 重登录
- `wecom_click_sidebar_candidate.swift` - 打开侧边栏
- `wecom_click_netease.swift` - 点击网易智企
- `wecom_click_relogin.swift` - 处理重新登录
- `wecom_judge.py` - 本地三态判断
- `wecom_agent.py` - Brainmaker AI 兜底
- `logger.py` - 日志系统
- `config.json` - 配置文件

## 📊 日志

日志位置：`logs/wecom_auto_YYYY-MM-DD.log`

包含：
- 当前会话标题读取
- 当前消息数量
- 本地判断 / AI 兜底判断
- 执行器链路每一步结果
- Whistle HTTP 拉取与解析结果
- token / cookie / session 提取情况
- API 调用结果
- 所有异常信息

## 🛠️ 手动安装（可选）

如果一键脚本失败，可手动安装：

```bash
# 1. 安装依赖
pip3 install websocket-client requests
npm install -g whistle

# 2. 启动 Whistle
w2 start

# 3. 配置证书
open http://127.0.0.1:8899/
# 下载证书并信任

# 4. 配置系统代理
# 系统偏好设置 → 网络 → 高级 → 代理
# HTTP/HTTPS: 127.0.0.1:8899

# 5. 运行
python3 full_auto.py
```

## 📊 技术架构

```
企微群切换 → AppleScript 监控
    ↓
自动打开侧边栏 → Swift UI 自动化
    ↓
触发 API 请求 → Whistle 代理捕获
    ↓
WebSocket 实时推送 → Python 接收
    ↓
读取聊天记录 → macOS Accessibility API
    ↓
关键词判断 → wecom_judge.py
    ↓
调用关闭 API → HTTP POST
```

## ⚙️ 配置说明

### Whistle 设置
- 端口：8899
- 证书：需安装并信任
- 系统代理：HTTP/HTTPS 都设为 127.0.0.1:8899

### macOS 权限
- Accessibility（辅助功能）
- 企业微信需授权

### 七鱼 API
- 端点：`https://qw.qiyukf.com/chat/api/session/closeWXCSSession`
- 参数：`sessionId` + `groupManageId`
- 认证：Cookie（___csrfToken）

## 🐛 故障排查

**Whistle 无法捕获：**
- 检查系统代理设置
- 确认证书已安装
- 重启企业微信

**无法读取聊天：**
- 授予 Accessibility 权限
- 确保企微窗口在前台

**关闭失败：**
- 检查 Cookie 是否过期
- 确认 groupManageId 正确

## 📝 开发日志

详见 `ARCHITECTURE.md`

## 📄 许可

MIT
