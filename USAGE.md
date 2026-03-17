# 使用说明

## 快速上手

### 1. 首次安装

```bash
cd /Users/yanchao/.openclaw/workspace/wecom_auto_end
./start.sh
```

首次运行会自动：
- 创建 Python 虚拟环境（.venv）
- 安装所有依赖
- 启动 Whistle 代理
- 检查并安装证书（需要输入系统密码）

### 2. 日常使用

每次使用前：
1. 确保企业微信已打开
2. 运行 `./start.sh`
3. 观察终端输出，确认"网易智企就绪"

### 3. 停止程序

按 `Ctrl+C` 停止监控

## 工作原理

### 监听流程

```
企微会话切换
  ↓
读取群名和消息
  ↓
本地关键词评分
  ↓
判断是否需要关闭
  ↓
自动执行关闭流程
```

### 判断规则

程序会分析最近的聊天内容，根据以下规则评分：

**加分项（倾向关闭）：**
- 客户说"好的"、"OK"、"收到" → +3分
- 客户说"谢谢"、"感谢" → +2分
- 客服说"稍后"、"回复您" → +2分
- 提到"已修复"、"已处理" → +2分

**减分项（倾向保留）：**
- 客户说"还有"、"另外" → -5分

**判断结果：**
- 评分 ≥ 4：直接关闭
- 评分 < 0：继续监听
- 其他：调用 AI 判断

### AI 兜底

当本地规则不确定时，会调用 Brainmaker AI（Claude Opus 4.5）进行智能判断。

## 日志查看

### 实时查看
```bash
tail -f logs/wecom_auto_$(date +%Y-%m-%d).log
```

### 查看历史
```bash
ls logs/
cat logs/wecom_auto_2026-03-17.log
```

### 日志内容

每条日志包含：
- 时间戳
- 日志级别（INFO/DEBUG/ERROR）
- 事件描述
- 相关数据

示例：
```
2026-03-17 09:47:23 INFO 🔄 检测到会话切换: None -> VIP云信-杭州甘之草科技-dx
2026-03-17 09:47:24 INFO 本地判断: uncertain / 0.50 / 评分0: 无明显信号
2026-03-17 09:47:25 INFO 本地判断不确定，调用 Brainmaker 兜底...
```

## 常见场景

### 场景 1：客户问题已解决

**聊天内容：**
```
客服：问题已修复，您可以重新尝试
客户：好的，谢谢
```

**程序行为：**
- 本地评分：+2（已修复）+3（好的）+2（谢谢）= 7分
- 判断：strong_end_candidate
- 动作：自动关闭会话

### 场景 2：客户有新问题

**聊天内容：**
```
客服：这个问题已处理
客户：好的，还有个问题想问下
```

**程序行为：**
- 本地评分：+2（已处理）+3（好的）-5（还有）= 0分
- 判断：uncertain
- 动作：调用 AI 判断 → 保留会话

### 场景 3：对话不明确

**聊天内容：**
```
客服：我们会尽快处理
客户：嗯
```

**程序行为：**
- 本地评分：0分（无明显信号）
- 判断：uncertain
- 动作：调用 AI 判断

## 配置调整

### 修改判断规则

编辑 `wecom_judge.py`，调整评分权重：

```python
# 客户确认词权重
if any(word in text for word in ['好的', 'OK', '收到']):
    score += 3  # 可调整为 2 或 4

# 新问题惩罚
if any(word in text for word in ['还有', '另外']):
    score -= 5  # 可调整为 -3 或 -7
```

### 修改 AI 模型

编辑 `config.json`：

```json
{
  "brainmaker_model": "claude-opus-4-5-20251101"
}
```

可选模型：
- `claude-opus-4-5-20251101`（推荐）
- `claude-sonnet-4-5`
- `gpt-4o`

### 修改 Whistle 端口

编辑 `config.json`：

```json
{
  "whistle_port": 8899
}
```

修改后需要同步更新系统代理设置。

## 故障处理

### 问题：Whistle 无法捕获请求

**症状：**
- 日志显示 "Whistle qiyukf 请求数: 0"
- 无法获取 token/cookie

**解决：**
```bash
./repair_whistle_env.sh
```

脚本会自动：
- 设置系统代理为 127.0.0.1:8899
- 关闭 SOCKS 直连
- 验证 Whistle 状态

### 问题：无法读取聊天内容

**症状：**
- 日志显示 "当前群/会话: None"
- 无法获取消息

**解决：**
1. 打开"系统设置 → 隐私与安全性 → 辅助功能"
2. 确认 Terminal.app 或 iTerm.app 已授权
3. 重启程序

### 问题：关闭 API 调用失败

**症状：**
- 日志显示 "❌ 关闭会话失败"
- HTTP 401/403 错误

**解决：**
1. 手动打开企微侧边栏
2. 点击"网易智企"
3. 如果需要登录，完成登录
4. 重启程序

### 问题：Brainmaker 调用失败

**症状：**
- 日志显示 "Brainmaker 调用失败"
- HTTP 401 错误

**解决：**
1. 浏览器访问 https://brainmaker.ai
2. 登录账号
3. 重启程序（会自动获取新 Cookie）

## 性能优化

### 减少 AI 调用次数

调整本地判断规则，让更多场景能直接判断：

```python
# 增加确认词权重，减少 uncertain 情况
if any(word in text for word in ['好的', 'OK', '收到']):
    score += 4  # 原来是 3
```

### 加快响应速度

减少 Whistle 轮询间隔（不推荐，会增加 CPU 占用）：

```python
# full_auto.py
time.sleep(0.5)  # 原来是 1
```

## 安全建议

1. **不要分享 Cookie**：`config.json` 和日志中包含敏感信息
2. **定期更新密码**：Brainmaker 和七鱼账号
3. **限制访问权限**：只在必要时授予 Accessibility 权限
4. **审查日志**：定期检查是否有异常行为

## 技术支持

遇到问题时，请提供：
1. 完整的错误日志
2. 系统版本（macOS 版本）
3. Python 版本（`python3 --version`）
4. Whistle 版本（`w2 --version`）

可以通过以下方式收集信息：

```bash
# 收集诊断信息
echo "=== 系统信息 ===" > diagnostic.txt
sw_vers >> diagnostic.txt
echo "\n=== Python 版本 ===" >> diagnostic.txt
python3 --version >> diagnostic.txt
echo "\n=== Whistle 版本 ===" >> diagnostic.txt
w2 --version >> diagnostic.txt
echo "\n=== 系统代理 ===" >> diagnostic.txt
scutil --proxy >> diagnostic.txt
echo "\n=== 最近日志 ===" >> diagnostic.txt
tail -100 logs/wecom_auto_$(date +%Y-%m-%d).log >> diagnostic.txt
```
