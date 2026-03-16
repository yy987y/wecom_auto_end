# 企微自动结束会话 - 完整流程梳理

## 📋 整体流程

### 阶段 1：启动初始化
```
1. 用户运行：python3 full_auto.py
2. 启动 Whistle 代理（w2 start）
3. 建立 WebSocket 连接到 Whistle
4. 开始监控企微窗口
```

### 阶段 2：群切换检测
```
循环执行（每 2 秒）：
1. AppleScript 读取企微窗口标题
2. 对比上次记录的群名
3. 如果群名变化 → 触发处理流程
```

### 阶段 3：自动打开侧边栏
```
检测到群切换后：
1. 执行 Swift 脚本：wecom_click_sidebar_candidate.swift
2. 查找企微侧边栏按钮（通过 Accessibility API）
3. 模拟点击"网易智企"按钮
4. 等待 3 秒让页面加载
```

### 阶段 4：数据捕获（Whistle）
```
侧边栏打开后：
1. 网易智企页面发起 API 请求
   → GET /chat/api/session/chat/service/record
2. Whistle 代理拦截请求
3. 通过 WebSocket 实时推送给 Python
4. Python 接收消息：
   - 提取 token（从 URL 参数）
   - 解析 base64 响应体
   - 提取会话列表（sessionId, userId, userName）
```

### 阶段 5：读取聊天内容
```
对每个会话：
1. 使用 macOS Accessibility API
2. 读取企微聊天窗口的 UI 元素
3. 遍历 AXTable → AXRow
4. 提取消息内容：
   [{sender: "客服名", content: "消息内容"}]
```

### 阶段 6：智能判断
```
调用 wecom_judge.py：
1. 分析最近 4 条消息
2. 关键词匹配：
   - 客户确认词（好的、OK）→ +3 分
   - 客户感谢词（谢谢）→ +2 分
   - 我方承诺（稍后答复）→ +2 分
   - 问题已解决（已修复）→ +2 分
   - 检测到新问题（还有个问题）→ -5 分
3. 计算总分：
   - ≥ 4 分 → strong_end_candidate（关闭）
   - < 0 分 → not_end（保留）
   - 其他 → uncertain（跳过）
```

### 阶段 7：批量关闭
```
筛选出 strong_end_candidate 的会话：
1. 遍历需要关闭的会话
2. 调用七鱼 API：
   POST /chat/api/session/closeWXCSSession
   Body: sessionId=xxx&groupManageId=6275817
   Cookie: ___csrfToken=xxx
3. 统计成功/失败数量
4. 输出结果
```

### 阶段 8：继续监控
```
处理完成后：
1. 清空会话缓存
2. 继续监控下一次群切换
3. 循环执行
```

## 🔄 数据流转

```
企微群切换
    ↓
AppleScript 检测到新群名
    ↓
Swift 点击侧边栏
    ↓
触发 API: /chat/api/session/chat/service/record
    ↓
Whistle 捕获 → WebSocket 推送
    ↓
Python 解析 → 提取会话列表
    ↓
Accessibility API → 读取聊天内容
    ↓
wecom_judge.py → 关键词评分
    ↓
筛选 strong_end_candidate
    ↓
批量调用关闭 API
    ↓
返回统计结果
```
