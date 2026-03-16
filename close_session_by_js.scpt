#!/usr/bin/osascript
-- 通过 JavaScript 调用网易智企的 closeSession 接口
tell application "企业微信"
    activate
    delay 0.5
end tell

-- 执行 JavaScript
tell application "System Events"
    tell process "企业微信"
        -- 尝试通过 AppleScript 执行 JavaScript
        -- 注意：这需要企微支持 JavaScript 执行
        try
            do shell script "osascript -e 'tell application \"企业微信\" to do JavaScript \"
                var iframe = document.querySelector('iframe');
                if (iframe) {
                    iframe.contentWindow.postMessage({
                        method: 'closeSession',
                        params: {
                            type: 'close',
                            id: 100000626355
                        }
                    }, '*');
                }
            \"'"
            log "✅ 已发送结束会话消息"
        on error errMsg
            log "❌ 执行失败: " & errMsg
            error number 1
        end try
    end tell
end tell
