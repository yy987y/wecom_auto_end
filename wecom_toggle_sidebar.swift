#!/usr/bin/swift
import Cocoa
import ApplicationServices

func toggleSidebar() -> Bool {
    let wecomApp = NSWorkspace.shared.runningApplications.first { $0.bundleIdentifier == "com.tencent.WeWorkMac" }
    guard let app = wecomApp, let pid = wecomApp?.processIdentifier else {
        print("❌ 企业微信未运行")
        return false
    }
    
    let axApp = AXUIElementCreateApplication(pid)
    var windowRef: AnyObject?
    let result = AXUIElementCopyAttributeValue(axApp, kAXWindowsAttribute as CFString, &windowRef)
    
    guard result == .success, let windows = windowRef as? [AXUIElement], !windows.isEmpty else {
        print("❌ 无法获取企微窗口")
        return false
    }
    
    let mainWindow = windows[0]
    
    // 查找侧边栏按钮（"更多"或"收起"）
    func findSidebarButton(_ element: AXUIElement, depth: Int = 0) -> AXUIElement? {
        if depth > 10 { return nil }
        
        var roleRef: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &roleRef)
        
        if let role = roleRef as? String, role == "AXButton" {
            var titleRef: AnyObject?
            AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &titleRef)
            if let title = titleRef as? String, (title.contains("更多") || title.contains("收起")) {
                return element
            }
        }
        
        var childrenRef: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &childrenRef)
        if let children = childrenRef as? [AXUIElement] {
            for child in children {
                if let found = findSidebarButton(child, depth: depth + 1) {
                    return found
                }
            }
        }
        
        return nil
    }
    
    if let button = findSidebarButton(mainWindow) {
        var titleRef: AnyObject?
        AXUIElementCopyAttributeValue(button, kAXTitleAttribute as CFString, &titleRef)
        let title = titleRef as? String ?? "未知"
        
        print("🎯 找到侧边栏按钮: \(title)")
        AXUIElementPerformAction(button, kAXPressAction as CFString)
        print("✅ 已切换侧边栏状态")
        return true
    } else {
        print("❌ 未找到侧边栏按钮")
        return false
    }
}

let success = toggleSidebar()
exit(success ? 0 : 1)
