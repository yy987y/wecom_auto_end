# 企微自动结束会话 - 实现架构

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     企微自动结束会话系统                        │
└─────────────────────────────────────────────────────────────┘

1️⃣ 监控层
   ┌──────────────┐
   │ AppleScript  │ → 检测企微群切换
   │ 窗口监控     │ → 获取当前群名
   └──────────────┘

2️⃣ 触发层
   ┌──────────────┐
   │ Swift UI     │ → 点击侧边栏按钮
   │ 自动化       │ → 打开网易智企标签
   └──────────────┘

3️⃣ 捕获层
   ┌──────────────┐
   │ Whistle      │ → 代理 HTTPS 请求
   │ 代理         │ → 捕获七鱼 API
   └──────────────┘
         ↓
   ┌──────────────┐
   │ WebSocket    │ → 实时推送数据
   │ 监听         │ → 解析会话列表
   └──────────────┘

4️⃣ 分析层
   ┌──────────────┐
   │ Accessibility│ → 读取聊天窗口
   │ API          │ → 提取消息内容
   └──────────────┘
         ↓
   ┌──────────────┐
   │ 关键词判断   │ → 评分系统
   │ wecom_judge  │ → 三态输出
   └──────────────┘

5️⃣ 执行层
   ┌──────────────┐
   │ HTTP API     │ → POST 关闭请求
   │ 批量关闭     │ → 返回结果
   └──────────────┘
```

## 🔄 数据流

```
企微群切换事件
    ↓
检测到新群名
    ↓
执行 Swift 脚本
    ↓
点击侧边栏 → 打开网易智企
    ↓
触发 API 请求
    ↓
Whistle 捕获 → /chat/api/session/chat/service/record
    ↓
WebSocket 推送 → Python 接收
    ↓
解析 base64 响应 → 提取会话列表
    ↓
遍历每个会话
    ↓
读取企微聊天窗口 → Accessibility API
    ↓
提取消息内容 → [{sender, content}]
    ↓
关键词匹配 → 计算评分
    ↓
判断状态 → strong_end_candidate / uncertain / not_end
    ↓
筛选需要关闭的会话
    ↓
批量调用关闭 API
    ↓
返回成功/失败统计
```

## 📦 模块职责

### full_auto.py（主控制器）
- 启动 Whistle
- 监控群切换
- 协调各模块
- 执行关闭操作

### wecom_monitor.py（窗口读取）
- 使用 Accessibility API
- 遍历 UI 元素树
- 提取聊天消息
- 返回结构化数据

### wecom_judge.py（判断引擎）
- 关键词词典
- 评分算法
- 三态判断
- 返回置信度

### wecom_click_sidebar_candidate.swift（UI 自动化）
- 查找侧边栏按钮
- 模拟点击事件
- 等待页面加载

## 🔑 关键技术点

### 1. Whistle WebSocket 协议
```
ws://127.0.0.1:8899/cgi-bin/socket.io/?transport=websocket

消息格式：42["event", {...data}]
- 42 = Socket.IO 消息类型
- event = 事件名
- data = 请求/响应数据
```

### 2. 七鱼 API 认证
```
Cookie: ___csrfToken=xxx
Body: sessionId=xxx&groupManageId=6275817
```

### 3. macOS Accessibility
```python
AXUIElementCreateApplication(pid)
AXUIElementCopyAttributeValue(element, kAXChildrenAttribute)
遍历 UI 树 → 查找 AXTable → 提取 AXRow
```

### 4. 评分系统
```
基础分 = 0
+ 客户确认词 (+3)
+ 客户感谢词 (+2)
+ 我方承诺 (+2)
+ 问题已解决 (+2)
- 检测到新问题 (-5)

≥ 4 分 → 关闭
< 0 分 → 保留
其他 → 跳过
```

## 📊 性能指标

- 群切换检测延迟：~2s
- 侧边栏打开时间：~3s
- 数据捕获延迟：实时（WebSocket）
- 单个会话判断：<100ms
- 批量关闭速度：~200ms/会话

## 🔒 安全考虑

- Cookie 本地存储（config.json）
- HTTPS 证书验证（verify=False 仅开发）
- Accessibility 权限最小化
- 无敏感数据上传

## 🚧 已知限制

1. 依赖企微窗口在前台
2. Accessibility 权限必需
3. Whistle 代理必须运行
4. 仅支持 macOS
5. 判断逻辑基于关键词（非 AI）
