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

func role(_ element: AXUIElement) -> String { axString(element, kAXRoleAttribute) ?? "-" }
func title(_ element: AXUIElement) -> String { axString(element, kAXTitleAttribute) ?? "-" }
func desc(_ element: AXUIElement) -> String { axString(element, kAXDescriptionAttribute) ?? "-" }

func findWeComApp() -> NSRunningApplication? {
    let names = ["企业微信", "WeCom", "WXWork"]
    for app in NSWorkspace.shared.runningApplications {
        let name = app.localizedName ?? ""
        if names.contains(where: { name.localizedCaseInsensitiveContains($0) }) { return app }
    }
    return nil
}

func focusedWindow(of appEl: AXUIElement) -> AXUIElement? {
    var value: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(appEl, kAXFocusedWindowAttribute as CFString, &value)
    guard err == .success, let v = value else { return nil }
    return unsafeBitCast(v, to: AXUIElement.self)
}

func findButton(_ element: AXUIElement, target: String, depth: Int = 0, maxDepth: Int = 6) -> AXUIElement? {
    let r = role(element)
    let t = title(element)
    let d = desc(element)
    if r == "AXButton" && (t == target || d == target || t.contains(target) || d.contains(target)) {
        return element
    }
    if depth >= maxDepth { return nil }
    let children = axChildren(element)
    if children.count > 120 { return nil }
    for child in children {
        if let found = findButton(child, target: target, depth: depth + 1, maxDepth: maxDepth) {
            return found
        }
    }
    return nil
}

func press(_ element: AXUIElement) -> AXError {
    AXUIElementPerformAction(element, kAXPressAction as CFString)
}

let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
guard AXIsProcessTrustedWithOptions(options) else {
    print("❌ Accessibility 权限未开启")
    exit(1)
}

guard let app = findWeComApp() else {
    print("❌ 未找到企业微信进程")
    exit(1)
}
let appEl = AXUIElementCreateApplication(app.processIdentifier)
guard let focused = focusedWindow(of: appEl) else {
    print("❌ 未获取到 Focused Window")
    exit(1)
}

print("🔍 查找按钮: 网易智企")
if let btn = findButton(focused, target: "网易智企") {
    let err = press(btn)
    print(err == .success ? "✅ 已触发 网易智企" : "❌ 触发失败: \(err.rawValue)")
} else {
    print("❌ 未找到 网易智企 按钮")
    exit(2)
}
