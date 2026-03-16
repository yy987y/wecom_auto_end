#!/usr/bin/swift
import Cocoa
import ApplicationServices

func findWeComPID() -> pid_t? {
    for app in NSWorkspace.shared.runningApplications {
        let name = app.localizedName ?? ""
        if name.contains("企业微信") || name.contains("WeCom") {
            return app.processIdentifier
        }
    }
    return nil
}

func getAllAttributes(_ element: AXUIElement) -> [String] {
    var names: CFArray?
    let err = AXUIElementCopyAttributeNames(element, &names)
    if err == .success, let attrs = names as? [String] {
        return attrs
    }
    return []
}

func getAttr(_ element: AXUIElement, _ key: String) -> String {
    var value: AnyObject?
    AXUIElementCopyAttributeValue(element, key as CFString, &value)
    if let v = value {
        return "\(v)"
    }
    return ""
}

func dumpElement(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 30, found: inout Int) {
    if depth >= maxDepth || found >= 5 { return }
    
    let role = getAttr(element, kAXRoleAttribute)
    let value = getAttr(element, kAXValueAttribute)
    let title = getAttr(element, kAXTitleAttribute)
    let desc = getAttr(element, kAXDescriptionAttribute)
    
    // 查找任何包含"结束"的元素
    if value.contains("结束会话") || title.contains("结束会话") || desc.contains("结束会话") {
        found += 1
        print("\n=== 找到匹配元素 #\(found) ===")
        print("深度: \(depth)")
        print("Role: \(role)")
        print("Value: \(value)")
        print("Title: \(title)")
        print("Description: \(desc)")
        print("所有属性: \(getAllAttributes(element))")
        print("========================\n")
    }
    
    var children: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    if let kids = children as? [AXUIElement], kids.count < 1000 {
        for child in kids {
            dumpElement(child, depth: depth + 1, maxDepth: maxDepth, found: &found)
        }
    }
}

guard let pid = findWeComPID() else {
    print("❌ 未找到企微")
    exit(1)
}

print("企微 PID: \(pid)")
print("开始扫描...")

let app = AXUIElementCreateApplication(pid)
var found = 0
dumpElement(app, found: &found)

if found == 0 {
    print("\n❌ 未找到任何包含'结束会话'的元素")
    print("这说明按钮在 WebView 中，Accessibility API 无法访问")
} else {
    print("\n✅ 找到 \(found) 个匹配元素")
}
