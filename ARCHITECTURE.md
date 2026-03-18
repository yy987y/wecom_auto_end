# 架构说明

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        企业微信                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  聊天窗口    │  │   侧边栏     │  │  网易智企    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ Accessibility      │ Swift 脚本         │ HTTP 请求
         │ API                │ 自动化             │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    full_auto.py (主程序)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. 监听会话切换 (wecom_monitor.py)                  │  │
│  │  2. 提取消息内容 (Accessibility API)                 │  │
│  │  3. 本地判断 (wecom_judge.py + keywords.yaml)        │  │
│  │  4. AI 兜底 (wecom_agent.py + Brainmaker)            │  │
│  │  5. 关闭会话 (七鱼 HTTP API)                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                            │
         │ WebSocket                                  │ HTTP
         ▼                                            ▼
┌──────────────────┐                        ┌──────────────────┐
│  Whistle 代理    │                        │  七鱼 API        │
│  (端口 8899)     │                        │  qiyukf.com      │
└──────────────────┘                        └──────────────────┘
```

## 核心模块

### 1. full_auto.py - 主程序

**职责：**
- 启动 Whistle 代理
- 初始化 UI 状态（侧边栏、网易智企）
- 主循环：监听会话变化
- 协调各模块工作

**关键方法：**
- `run()` - 主循环
- `get_current_context()` - 获取当前会话和消息
- `judge_current_chat()` - 判断是否结束
- `execute_end_session()` - 执行关闭

### 2. wecom_monitor.py - 消息监控

**职责：**
- 通过 Accessibility API 读取企微 UI
- 提取群名和消息内容
- 滚动到底部确保最新消息可见

**关键方法：**
- `get_group_name()` - 提取群名
- `get_messages()` - 提取消息列表
- `scroll_to_bottom()` - 滚动到底部

**消息提取逻辑：**
```python
# 路径过滤
window.0.31.9.0.0.0.N  # 聊天消息（N 是消息 ID）
window.0.31.9.9        # 侧边栏（需排除）
window.0.26            # 其他侧边栏（需排除）

# 按路径第 8 级（索引 7）分组
parts[7] = 消息 ID
```

### 3. wecom_judge.py - 本地判断

**职责：**
- 基于关键词评分
- 三态判断：not_end / strong_end_candidate / uncertain

**评分规则：**
```python
客户确认词: +3 分
客户感谢词: +2 分
我方承诺词: +2 分
问题已解决: +2 分
新问题出现: -5 分

评分 >= 4: 强制关闭
评分 < 0:  保留会话
其他:      调用 AI
```

### 4. wecom_agent.py - AI 兜底

**职责：**
- 调用 Brainmaker API
- 缓存 AI 结果（避免重复调用）
- 管理 Cookie 和认证

**模型：** `claude-opus-4-5-20251101`

### 5. wecom_executor.py - UI 自动化

**职责：**
- 执行 Swift 脚本
- 打开侧边栏、点击网易智企
- 处理登录状态

## 数据流

### 1. 启动阶段

```
启动 Whistle
  ↓
打开侧边栏
  ↓
点击网易智企
  ↓
检查登录状态
  ↓
提取 token/cookie/sessionId
  ↓
进入监听循环
```

### 2. 监听阶段

```
检测会话切换
  ↓
刷新侧边栏（加载最新消息）
  ↓
多次采样读取消息（4 次）
  ↓
选择消息数最多的结果
  ↓
过滤无效消息
  ↓
进入判断阶段
```

### 3. 判断阶段

```
本地关键词评分
  ↓
评分 >= 4? ──Yes──> 关闭会话
  │
  No
  ↓
评分 < 0? ──Yes──> 保留会话
  │
  No
  ↓
调用 Brainmaker AI
  ↓
AI 判断结束? ──Yes──> 关闭会话
  │
  No
  ↓
保留会话
```

### 4. 关闭阶段

```
重新点击网易智企（刷新数据）
  ↓
再次提取 sessionId（确保最新）
  ↓
调用七鱼 API 关闭会话
  ↓
返回监听循环
```

## 关键技术

### 1. Accessibility API

macOS 提供的无障碍 API，用于读取和操作 UI 元素。

**优势：**
- 无需 OCR
- 实时获取最新内容
- 可以模拟点击

**挑战：**
- 路径可能变化
- 需要权限授权

### 2. Whistle 代理

拦截企微的网络请求，提取 token、cookie、sessionId。

**配置：**
```
HTTP/HTTPS 代理: 127.0.0.1:8899
证书: 已安装到系统钥匙串
```

**关键请求：**
- `/chat/api/session/latest` - 当前会话
- `/chat/api/session/list` - 会话列表

### 3. Swift 脚本

通过 AppleScript 和 Accessibility API 自动化 UI 操作。

**脚本：**
- `wecom_click_sidebar_candidate.swift` - 打开侧边栏
- `wecom_click_netease.swift` - 点击网易智企
- `wecom_click_relogin.swift` - 处理登录

## 配置文件

### config.json

```json
{
  "groupManageId": 6275817,
  "debug": false
}
```

### keywords.yaml

```yaml
customer_confirm:
  score: 3
  keywords: [好的, OK, 可以]

customer_thanks:
  score: 2
  keywords: [谢谢, 感谢]

thresholds:
  strong_end: 4
  keep: 0
```

## 性能优化

1. **消息采样**：4 次采样取最多的，避免 UI 未刷新
2. **去重逻辑**：已移除，避免丢失消息
3. **缓存机制**：缓存会话列表和 AI 结果
4. **限流控制**：主循环 sleep 1 秒

## 错误处理

1. **企微未运行**：等待 10 秒重试
2. **未获取焦点窗口**：等待 10 秒重试
3. **消息过少**：跳过判断
4. **AI 调用失败**：降级为保留会话
5. **关闭失败**：记录日志，继续监听
