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
func desc(_ e: AXUIElement) -> String { axString(e, kAXDescriptionAttribute) ?? "-" }

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

func findButton(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 8, matcher: (AXUIElement) -> Bool) -> AXUIElement? {
    if matcher(element) { return element }
    if depth >= maxDepth { return nil }
    let children = axChildren(element)
    if children.count > 180 { return nil }
    for child in children {
        if let found = findButton(child, depth: depth + 1, maxDepth: maxDepth, matcher: matcher) {
            return found
        }
    }
    return nil
}

let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
guard AXIsProcessTrustedWithOptions(options) else { print("❌ Accessibility 权限未开启"); exit(1) }
guard let app = findWeComApp() else { print("❌ 未找到企业微信进程"); exit(1) }
let appEl = AXUIElementCreateApplication(app.processIdentifier)
guard let focused = focusedWindow(of: appEl) else { print("❌ 未获取到 Focused Window"); exit(1) }

let keywords = ["重新登录", "登录", "去登录", "立即登录", "重新授权", "授权登录"]
print("🔍 查找 登录相关按钮")
if let btn = findButton(focused, matcher: { e in
    guard role(e) == "AXButton" else { return false }
    let t = title(e)
    let d = desc(e)
    return keywords.contains(where: { t.contains($0) || d.contains($0) })
}) {
    let err = AXUIElementPerformAction(btn, kAXPressAction as CFString)
    print(err == .success ? "✅ 已点击 登录相关按钮" : "❌ 点击失败: \(err.rawValue)")
} else {
    print("❌ 未找到 登录相关按钮")
    exit(2)
}
