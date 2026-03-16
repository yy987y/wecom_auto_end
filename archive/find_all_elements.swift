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

func dumpElement(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 25, prefix: String = "") {
    if depth >= maxDepth { return }
    
    var role: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXRoleAttribute as CFString, &role)
    let r = (role as? String) ?? "?"
    
    var value: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXValueAttribute as CFString, &value)
    let v = (value as? String) ?? ""
    
    var title: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXTitleAttribute as CFString, &title)
    let t = (title as? String) ?? ""
    
    if v.contains("结束") || t.contains("结束") || v.contains("会话") || t.contains("会话") {
        print("\(prefix)[\(depth)] \(r) - value:\(v) title:\(t)")
    }
    
    var children: AnyObject?
    AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children)
    if let kids = children as? [AXUIElement], kids.count < 1000 {
        for child in kids {
            dumpElement(child, depth: depth + 1, maxDepth: maxDepth, prefix: prefix)
        }
    }
}

guard let pid = findWeComPID() else {
    print("❌ 未找到企微")
    exit(1)
}

let app = AXUIElementCreateApplication(pid)
print("🔍 深度扫描所有包含'结束'或'会话'的元素...")
dumpElement(app)
print("扫描完成")
