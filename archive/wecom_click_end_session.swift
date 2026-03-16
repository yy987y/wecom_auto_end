#!/usr/bin/swift
import Cocoa
import ApplicationServices

func findWeComPID() -> pid_t? {
    let names = ["企业微信", "WeCom", "WXWork"]
    for app in NSWorkspace.shared.runningApplications {
        let name = app.localizedName ?? ""
        if names.contains(where: { name.localizedCaseInsensitiveContains($0) }) {
            return app.processIdentifier
        }
    }
    return nil
}

func findElement(_ element: AXUIElement, text: String, depth: Int = 0, maxDepth: Int = 20) -> AXUIElement? {
    if depth >= maxDepth { return nil }
    
    var value: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &value)
    if let val = value as? String, val.contains(text) {
        return element
    }
    
    var title: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &title)
    if let t = title as? String, t.contains(text) {
        return element
    }
    
    var children: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    if let kids = children as? [AXUIElement] {
        if kids.count > 500 { return nil }
        for child in kids {
            if let found = findElement(child, text: text, depth: depth + 1, maxDepth: maxDepth) {
                return found
            }
        }
    }
    return nil
}

func findButtonNearY(_ element: AXUIElement, targetY: Double, buttons: inout [AXUIElement], depth: Int = 0, maxDepth: Int = 15) {
    if depth >= maxDepth { return }
    
    var role: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &role)
    
    if let r = role as? String, r == "AXButton" {
        var pos: AnyObject?
        AXUIElementCopyAttributeValue(element, kAXPositionAttribute as CFString, &pos)
        if let position = pos as? NSValue {
            var point = CGPoint.zero
            position.getValue(&point)
            if abs(point.y - targetY) < 50 {
                buttons.append(element)
            }
        }
    }
    
    var children: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    if let kids = children as? [AXUIElement] {
        if kids.count > 500 { return }
        for child in kids {
            findButtonNearY(child, targetY: targetY, buttons: &buttons, depth: depth + 1, maxDepth: maxDepth)
        }
    }
}

guard let pid = findWeComPID() else {
    print("❌ 未找到企业微信进程")
    exit(1)
}

let app = AXUIElementCreateApplication(pid)

print("🔍 查找'结束会话'按钮...")
if let endBtn = findElement(app, text: "结束会话") {
    print("✅ 找到按钮，点击...")
    AXUIElementPerformAction(endBtn, kAXPressAction as CFString)
    sleep(1)
    
    print("🔍 查找确认按钮（通过位置 y≈785）...")
    var buttons: [AXUIElement] = []
    findButtonNearY(app, targetY: 785, buttons: &buttons)
    
    if buttons.count > 0 {
        print("✅ 点击确认...")
        AXUIElementPerformAction(buttons[0], kAXPressAction as CFString)
        print("✅ 会话已结束")
    } else {
        print("❌ 未找到确认按钮")
        exit(3)
    }
} else {
    print("❌ 未找到'结束会话'按钮")
    exit(2)
}
