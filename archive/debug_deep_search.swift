import Cocoa
import ApplicationServices

func axValue<T>(_ element: AXUIElement, _ key: String) -> T? {
    var value: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(element, key as CFString, &value)
    guard err == .success, let v = value else { return nil }
    return (v as AnyObject) as? T
}

func axString(_ element: AXUIElement, _ key: String) -> String? {
    if let s: NSString = axValue(element, key) { return s as String }
    return nil
}

func axChildren(_ element: AXUIElement) -> [AXUIElement] {
    if let arr: [AXUIElement] = axValue(element, kAXChildrenAttribute) { return arr }
    return []
}

func role(_ e: AXUIElement) -> String { axString(e, kAXRoleAttribute) ?? "-" }
func title(_ e: AXUIElement) -> String { axString(e, kAXTitleAttribute) ?? "-" }

func findWeComApp() -> NSRunningApplication? {
    let names = ["企业微信", "WeCom", "WXWork"]
    for app in NSWorkspace.shared.runningApplications {
        let name = app.localizedName ?? ""
        if names.contains(where: { name.localizedCaseInsensitiveContains($0) }) { return app }
    }
    return nil
}

func findAllButtons(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 20, buttons: inout [(String, Int)]) {
    if depth >= maxDepth { return }
    let children = axChildren(element)
    if children.count > 500 { return }
    
    for child in children {
        if role(child) == "AXButton" {
            let t = title(child)
            if !t.isEmpty && t != "-" {
                buttons.append((t, depth))
            }
        }
        findAllButtons(child, depth: depth + 1, maxDepth: maxDepth, buttons: &buttons)
    }
}

let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
guard AXIsProcessTrustedWithOptions(options) else { print("❌ Accessibility 权限未开启"); exit(1) }
guard let app = findWeComApp() else { print("❌ 未找到企业微信进程"); exit(1) }
let appEl = AXUIElementCreateApplication(app.processIdentifier)

let windows: [AXUIElement] = axValue(appEl, kAXWindowsAttribute) ?? []
print("🔍 深度搜索所有按钮（最大深度20）...")

var allButtons: [(String, Int)] = []
for window in windows {
    findAllButtons(window, maxDepth: 20, buttons: &allButtons)
}

print("共找到 \(allButtons.count) 个按钮：")
for (title, depth) in allButtons.sorted(by: { $0.1 < $1.1 }) {
    if title.contains("结束") || title.contains("End") || title.contains("会话") {
        print("  ⭐️ \(title) (depth \(depth))")
    } else {
        print("  - \(title) (depth \(depth))")
    }
}
