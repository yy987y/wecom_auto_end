# 企微自动结束会话 v1.5

自动监控企业微信客服会话，智能判断对话是否结束，并自动关闭七鱼客服会话。

## 核心特性

- **智能判断**：本地关键词评分 + Brainmaker AI 兜底
- **自动监控**：实时监听企微会话切换和消息变化
- **精准关闭**：通过七鱼 HTTP API 关闭会话
- **可配置**：支持自定义关键词词库

## 快速开始

### 1. 环境要求

- macOS 系统
- Python 3.8+
- 企业微信
- Whistle 代理

### 2. 安装

```bash
./start.sh
```

脚本会自动：
- 创建虚拟环境
- 安装依赖
- 配置 Whistle
- 启动程序

### 3. 配置

编辑 `config.json`：

```json
{
  "groupManageId": 6275817,
  "debug": false
}
```

编辑 `keywords.yaml` 自定义关键词和评分。

### 4. 运行

```bash
# 正常模式
python3 full_auto.py

# 调试模式（跳过 AI 判断）
python3 full_auto.py --debug
```

## 工作原理

1. **监听会话**：检测企微会话切换和消息变化
2. **提取消息**：通过 Accessibility API 读取聊天内容
3. **本地判断**：基于关键词评分（可配置）
4. **AI 兜底**：不确定时调用 Brainmaker AI
5. **关闭会话**：通过七鱼 API 结束会话

## 判断逻辑

### 本地评分

- 客户确认词（好的、OK）：+3 分
- 客户感谢词（谢谢）：+2 分
- 我方承诺词（稍后、明天）：+2 分
- 问题已解决（已修复）：+2 分
- 新问题出现（还有个问题）：-5 分

### 三态判断

- 评分 ≥ 4：强制关闭
- 评分 < 0：保留会话
- 其他：调用 AI 判断

## 文件说明

### 核心文件

- `full_auto.py` - 主程序
- `wecom_monitor.py` - 消息监控
- `wecom_judge.py` - 本地判断
- `wecom_agent.py` - AI 调用
- `wecom_executor.py` - UI 自动化

### 配置文件

- `config.json` - 基础配置
- `keywords.yaml` - 关键词词库
- `credentials.local.yaml` - Brainmaker 凭证（可选）

### Swift 脚本

- `wecom_click_sidebar_candidate.swift` - 打开侧边栏
- `wecom_click_netease.swift` - 点击网易智企
- `wecom_click_relogin.swift` - 处理登录

### 工具脚本

- `start.sh` - 一键启动
- `repair_whistle_env.sh` - 修复 Whistle 环境

## 故障排查

### 1. 未捕获到 qiyukf 请求

```bash
./repair_whistle_env.sh
```

然后重启企业微信。

### 2. 消息识别不准

检查 `keywords.yaml` 配置，调整关键词和评分。

### 3. 关闭会话失败

- 检查 token 和 cookie 是否获取成功
- 确认 sessionId 是否正确
- 查看日志中的错误信息

## 更多文档

- [架构说明](ARCHITECTURE.md)
- [流程图](FLOWCHART.md)
- [使用指南](USAGE.md)
- [安装配置](INSTALL.md)

## 版本历史

### v1.5 (2026-03-18)

- ✅ 优化消息提取逻辑
- ✅ 支持可配置关键词词库
- ✅ 修复侧边栏打开时的识别问题
- ✅ 改进 sessionId 获取机制

### v1.4

- 完善文档系统
- 优化日志输出

### v1.3

- 引入 Brainmaker AI 兜底
- 优化判断逻辑

### v1.2

- 状态机架构
- 本地三态判断

## License

MIT
