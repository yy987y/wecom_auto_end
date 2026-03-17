# 企微自动结束会话 v1.4

自动化工具，实时监听企微会话切换，智能判断是否需要结束七鱼客服会话。结合本地关键词评分 + Brainmaker AI 兜底，自动完成"侧边栏 → 网易智企 → Whistle 抓取 → HTTP API 关闭"全链路。

## 🎯 核心功能

- ✅ **实时监听**：自动检测企微会话切换
- ✅ **智能判断**：本地三态评分 + AI 兜底
- ✅ **自动执行**：一键完成从判断到关闭的完整流程
- ✅ **完整日志**：所有关键步骤可追溯

## 🚀 快速开始

```bash
cd /Users/yanchao/.openclaw/workspace/wecom_auto_end
./start.sh
```

脚本自动完成：
1. 检查并安装依赖（venv + websocket-client + requests + pyobjc + pyyaml + playwright）
2. 启动 Whistle 代理
3. 检查并安装证书
4. 启动监控程序

## 📊 工作流程

```
启动 → 环境检查 → 进入网易智企就绪态
  ↓
监听会话切换（AppleScript）
  ↓
读取群名 + 消息（Accessibility API）
  ↓
本地三态判断（关键词评分）
  ├─ not_end → 继续监听
  ├─ uncertain → Brainmaker AI 兜底
  └─ strong_end_candidate → 执行关闭
       ↓
  Whistle HTTP 拉取请求
       ↓
  提取 token/cookie/sessionId
       ↓
  调用七鱼 closeWXCSSession API
```

## 🧠 判断逻辑

### 本地评分规则
- 客户确认词（好的、OK、收到）：+3分
- 客户感谢词（谢谢、感谢）：+2分
- 我方明确承诺（有结论随时同步、稍后联系等）：+4分（直接触发关闭）
- 问题已解决（已修复、已处理）：+2分
- 检测到新问题（还有、另外）：-5分

### 超时自动关闭
- 最后一条消息是我方发送
- 超过 20 分钟无客户回复
- 自动关闭，无需 AI 判断

### 消息过滤
- 自动过滤界面元素（未读消息、群聊、标签等）
- 有效消息 < 2 条时跳过判断
- 避免浪费 AI 调用

### 三态输出
- **评分 ≥ 4**：`strong_end_candidate` → 直接关闭
- **评分 < 0**：`not_end` → 继续监听
- **其他**：`uncertain` → 调用 Brainmaker AI

### AI 兜底
- 模型：`claude-opus-4-5-20251101`
- 输入：群名 + 最近消息
- 输出：关闭 / 保留

## 📁 项目结构

```
wecom_auto_end/
├── start.sh                          # 一键启动脚本
├── full_auto.py                      # 主程序（状态机）
├── wecom_monitor.py                  # 会话监听（Accessibility API）
├── wecom_executor.py                 # 执行器（UI 自动化）
├── wecom_judge.py                    # 本地三态判断
├── wecom_agent.py                    # Brainmaker AI 兜底
├── brainmaker_api.py                 # Brainmaker API 封装
├── cookie_manager.py                 # Cookie 管理
├── logger.py                         # 日志系统
├── config.json                       # 配置文件
├── wecom_click_sidebar_candidate.swift   # 打开侧边栏
├── wecom_click_netease.swift         # 切换网易智企
├── wecom_click_relogin.swift         # 处理重登录
└── logs/                             # 日志目录
```

## 📊 日志系统

位置：`logs/wecom_auto_YYYY-MM-DD.log`

记录内容：
- 会话切换事件
- 群名和消息读取
- 本地判断结果（评分 + 三态）
- AI 调用（输入/输出/耗时）
- Whistle 请求数量
- token/cookie/session 提取
- API 调用结果
- 所有异常堆栈

## ⚙️ 配置说明

### config.json
```json
{
  "groupManageId": "6275817",
  "whistle_port": 8899,
  "brainmaker_model": "claude-opus-4-5-20251101"
}
```

### Whistle 设置
- 端口：8899
- 证书：需安装并信任（系统钥匙串）
- 系统代理：HTTP/HTTPS 都设为 `127.0.0.1:8899`

### macOS 权限
- **Accessibility**（辅助功能）：读取企微窗口内容
- **企业微信**：需授权脚本控制

## 🛠️ 手动安装（可选）

如果一键脚本失败：

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 安装 Python 依赖
pip install websocket-client requests pyobjc pyyaml playwright

# 3. 安装 Whistle
npm install -g whistle

# 4. 启动 Whistle
w2 start

# 5. 配置证书
open http://127.0.0.1:8899/
# 下载 rootCA.crt 并双击安装，设为"始终信任"

# 6. 配置系统代理
# 系统设置 → 网络 → 高级 → 代理
# HTTP/HTTPS: 127.0.0.1:8899

# 7. 运行
python3 full_auto.py
```

## 🐛 故障排查

### Whistle 无法捕获请求
- 检查系统代理：`scutil --proxy`
- 确认证书已信任：钥匙串访问 → 系统 → Whistle CA
- 重启企业微信
- 运行修复脚本：`./repair_whistle_env.sh`

### 无法读取聊天内容
- 授予 Accessibility 权限：系统设置 → 隐私与安全性 → 辅助功能
- 确保企微窗口在前台
- 检查日志：`tail -f logs/wecom_auto_*.log`

### 关闭 API 失败
- Cookie 过期：重新登录网易智企
- groupManageId 错误：检查 config.json
- sessionId 未提取：查看 Whistle 是否捕获到 qiyukf 请求

### Brainmaker 调用失败
- Cookie 过期：重新登录 brainmaker.ai
- 模型不可用：检查 config.json 中的模型名称
- 频控限制：查看日志中的调用次数

## 📈 性能指标

- **启动时间**：~5秒（含环境检查）
- **会话切换响应**：<1秒
- **本地判断耗时**：<100ms
- **AI 判断耗时**：2-5秒
- **关闭执行耗时**：3-8秒

## 🔄 版本历史

### v1.5 (2026-03-17)
- ✅ 新增：20分钟超时自动关闭（无需 AI）
- ✅ 新增：明确承诺类消息直接关闭（+4分权重）
- ✅ 新增：消息有效性过滤（界面元素）
- ✅ 优化：使用 session/latest 接口获取当前会话
- ✅ 优化：按时间戳排序，确保使用最新 sessionId
- ✅ 修复：完善关闭 API 参数（code/token/完整Cookie）
- ✅ 修复：只关闭当前会话，不再批量关闭
- ✅ 修复：持久化会话映射，支持离线关闭
- ✅ 修复：Brainmaker JSON 解析容错
- ✅ 修复：启动脚本依赖检测，二次启动更快

### v1.4 (2026-03-17)
- ✅ 完整链路验证通过
- ✅ Whistle 环境收敛完成
- ✅ Brainmaker 固定模型 + 频控记录
- ✅ 日志系统完善
- ✅ 文档和架构图更新

### v1.3 (2026-03-16)
- ✅ 切换到 .venv（规避 PEP 668）
- ✅ 补齐运行依赖
- ✅ 恢复执行链路文件
- ✅ 状态机改为强制就绪态

### v1.2
- ✅ 本地三态判断
- ✅ Brainmaker AI 兜底

### v1.1
- ✅ Whistle WebSocket 实时监听
- ✅ 基础关闭流程

## 📄 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 技术架构详解
- [WORKFLOW.md](WORKFLOW.md) - 流程梳理
- [EXAMPLES.md](EXAMPLES.md) - 执行示例
- [INSTALL.md](INSTALL.md) - 安装配置指南

## 📝 许可

MIT License

## 🤝 贡献

欢迎提交 Issue 和 PR
