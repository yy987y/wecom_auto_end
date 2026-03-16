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

func getAttr(_ element: AXUIElement, _ key: String) -> String {
    var value: AnyObject?
    AXUIElementCopyAttributeValue(element, key as CFString, &value)
    if let v = value {
        return "\(v)"
    }
    return ""
}

func listAllContent(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 25, prefix: String = "") {
    if depth >= maxDepth { return }
    
    let role = getAttr(element, kAXRoleAttribute)
    let value = getAttr(element, kAXValueAttribute)
    let title = getAttr(element, kAXTitleAttribute)
    
    // 只显示有内容的元素
    if !value.isEmpty || !title.isEmpty {
        let indent = String(repeating: "  ", count: depth)
        print("\(indent)[\(depth)] \(role)")
        if !title.isEmpty { print("\(indent)  title: \(title)") }
        if !value.isEmpty { print("\(indent)  value: \(value.prefix(100))") }
    }
    
    var children: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    if let kids = children as? [AXUIElement], kids.count < 1000 {
        for child in kids {
            listAllContent(child, depth: depth + 1, maxDepth: maxDepth, prefix: prefix)
        }
    }
}

guard let pid = findWeComPID() else {
    print("❌ 未找到企微")
    exit(1)
}

print("企微 PID: \(pid)")
print("列出所有可读取的内容：\n")

let app = AXUIElementCreateApplication(pid)
listAllContent(app)
