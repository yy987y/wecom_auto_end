#!/usr/bin/osascript
tell application "System Events"
    tell process "企业微信"
        set frontmost to true
        delay 0.5
        
        -- 尝试查找包含"结束会话"的按钮
        try
            set endButton to first button whose name contains "结束会话"
            click endButton
            log "✅ 已点击结束会话"
            
            delay 1
            
            -- 查找确认按钮
            try
                set confirmButton to first button whose name contains "确定" or name contains "结束"
                click confirmButton
                log "✅ 已点击确认"
            on error
                log "⚠️ 未找到确认按钮"
            end try
            
        on error errMsg
            log "❌ 未找到结束会话按钮: " & errMsg
            error number 1
        end try
    end tell
end tell
