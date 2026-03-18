# 企微自动结束会话 - 技术交接文档

## 当前问题

**问题描述：**
最后一条消息无法被正确识别和提取。

**日志示例：**
```
📝 最近消息内容：
  1. [云信技术支持-严超's quick meeting￼￼] 云信技术支持-严超's quick meeting Today 03/18 17:38 - 18:38 meeting mini end Meeting 云信技术支持-严超 Meeting Minutes Initiator Attendee
  2. [17:50] @sunshine 也想了解下，现在查半年前会议的场景多么？实际使用过程中
  3. [sunshine@WeChat]  ⁠@严超⁠  多的，因为有人要回顾历史录屏和纪要
  4. [18:31] @sunshine 
  5. [联友会议组件需求问题跟进表] 云信技术支持-严超 created
📝 最后一条消息 - 发送者: 联友会议组件需求问题跟进表
```

**实际情况：**
- 前面的消息都能识别
- 最后一条消息（"云信技术支持-严超 created"）被识别为发送者是"联友会议组件需求问题跟进表"
- 真实的最后一条消息可能在界面上，但没有被提取到

## 技术背景

### 消息提取逻辑

**文件：** `wecom_monitor.py`

**核心函数：** `get_messages(focused, debug=False)`

**提取流程：**
1. 查找 AXTable（聊天区域）
2. 提取所有 AXRow（每行可能包含一条或多条消息）
3. 对每个 row 调用 `flatten_texts()` 提取所有文本
4. 假设 `tokens[0]` 是发送者，`tokens[1:]` 是内容

**路径过滤：**
- `window.0.31.9` → 中间聊天区域（高分）
- `window.0.26` → 左侧边栏（负分，排除）

**当前策略：**
只取最后 20 个 rows：
```python
recent_rows = all_rows[-20:] if len(all_rows) > 20 else all_rows
```

### 已知问题

1. **消息合并问题**
   - 一个 row 可能包含多条消息
   - 会被合并成一条，例如：
     ```
     [无名小卒:] 发送音视频通话邀请的时候, 会有 im会话抄送吗 @无名小卒 会有信令的抄送，不过呼叫组件层面是拿不到信令id的
     ```
   - 实际是两条消息

2. **最后一条消息丢失**
   - 最新的消息可能在 UI 上，但 Accessibility API 没有及时更新
   - 或者消息在不同的 UI 元素中（不在 AXTable 里）

3. **性能问题**
   - 主循环轮询频率过高会导致打字卡顿
   - 已优化：每次循环 sleep 1秒

## 尝试过的方案

### 方案1：按消息气泡分组（已回滚）
**commit:** `a4bdf27`

**思路：**
查找 AXGroup，每个 group 当作一个消息气泡

**问题：**
误把成员列表当成消息，提取到的是人名而不是聊天内容

**结论：**
不可行，已回滚

### 方案2：切换群后刷新侧边栏
**commit:** `be06874`

**思路：**
切换群后主动点击"网易智企"标签，强制刷新侧边栏内容

**效果：**
部分有效，但不能解决最后一条消息丢失的问题

### 方案3：多次采样
**代码位置：** `full_auto.py` 第 615-640 行

**思路：**
检测到消息变化后，在 0ms、400ms、900ms、1200ms 四个时间点采样，选择消息数最多的结果

**效果：**
理论上能捕获到延迟更新的消息，但实际效果待验证

## 调试建议

### 1. 增强 UI 元素探测

**目标：**
找出最后一条消息在 UI 树中的位置

**方法：**
```python
# 在 wecom_monitor.py 中增加调试代码
def debug_ui_tree(focused):
    """打印完整的 UI 树结构"""
    def walk_print(el, depth=0, max_depth=10):
        if depth > max_depth:
            return
        r = role(el)
        val = ax_str(el, kAXValueAttribute) or ax_str(el, kAXTitleAttribute) or ''
        print(f'{"  " * depth}{r}: {val[:50]}')
        for child in ax_children(el)[:20]:
            walk_print(child, depth + 1, max_depth)
    
    walk_print(focused)
```

**使用：**
在 `get_messages` 开头调用 `debug_ui_tree(focused)`，查看完整的 UI 结构

### 2. 检查 AXTable 之外的元素

**假设：**
最后一条消息可能不在 AXTable 中，而是在其他容器里

**方法：**
```python
# 查找所有 AXStaticText，不限制在 AXTable 内
all_texts = walk_collect(focused, lambda el: role(el) == 'AXStaticText', max_depth=12)
```

### 3. 对比 OCR 结果

**思路：**
用 OCR 截图识别最后一条消息，对比 Accessibility API 的结果，找出差异

**已有代码：**
`wecom_monitor.py` 曾经有 OCR 方案（commit `df41055`），但已移除

## 关键文件

### 核心逻辑
- `full_auto.py` - 主流程和状态机
- `wecom_monitor.py` - UI 元素读取（群名、消息）
- `wecom_judge.py` - 本地三态判断
- `wecom_agent.py` - Brainmaker AI 兜底

### 执行器
- `wecom_executor.py` - Swift 脚本调用封装
- `wecom_click_netease.swift` - 点击"网易智企"标签
- `wecom_click_relogin.swift` - 点击"重新登录"按钮
- `wecom_click_sidebar_candidate.swift` - 打开侧边栏

### 配置和日志
- `config.json` - groupManageId、Cookie
- `logs/wecom_auto_YYYY-MM-DD.log` - 运行日志
- `data/session_mapping.txt` - 群名 → sessionId 映射

## 环境依赖

- Python 3.x + .venv
- Whistle 代理（端口 8899）
- macOS Accessibility API 权限
- Swift 运行环境

## 启动命令

```bash
./start.sh
```

## Git 分支

当前分支：`feature/message-monitoring`

最新 commit：`5be6671`

## 下一步建议

1. **优先级1：** 调试 UI 树结构，找出最后一条消息的位置
2. **优先级2：** 尝试不同的元素查找策略（AXStaticText、AXTextArea 等）
3. **优先级3：** 考虑结合 OCR 作为兜底方案

## 联系方式

如有问题，请在飞书群 `oc_9af234149f64dd4107dfc82a961a7673` 中 @小弟1号
