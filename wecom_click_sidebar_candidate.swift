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

func parentOf(_ element: AXUIElement) -> AXUIElement? {
    var value: CFTypeRef?
    let err = AXUIElementCopyAttributeValue(element, kAXParentAttribute as CFString, &value)
    guard err == .success, let v = value else { return nil }
    return unsafeBitCast(v, to: AXUIElement.self)
}

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

func findElement(_ element: AXUIElement, depth: Int = 0, maxDepth: Int = 8, matcher: (AXUIElement) -> Bool) -> AXUIElement? {
    if matcher(element) { return element }
    if depth >= maxDepth { return nil }
    let children = axChildren(element)
    if children.count > 150 { return nil }
    for child in children {
        if let found = findElement(child, depth: depth + 1, maxDepth: maxDepth, matcher: matcher) {
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

guard let qm = findElement(focused, matcher: { e in 
    role(e) == "AXButton" && (
        title(e).localizedCaseInsensitiveContains("Quick Meeting") ||
        title(e).contains("快速会议")
    )
}) else {
    print("❌ 未找到 Quick Meeting / 快速会议")
    exit(2)
}

guard let parent = parentOf(qm) else { print("❌ 未找到 Quick Meeting parent"); exit(3) }
let siblings = axChildren(parent)

// 选 Quick Meeting 右侧的无标题按钮
let qmIndex = siblings.firstIndex(where: { $0 == qm }) ?? -1
let candidates = siblings
    .enumerated()
    .compactMap { (idx, e) -> (Int, AXUIElement)? in
        guard role(e) == "AXButton" else { return nil }
        let t = title(e)
        if !t.isEmpty { return nil }  // 只要无标题按钮
        if idx <= qmIndex { return nil }  // 只要右侧
        return (idx, e)
    }

// 优先索引13，否则取第一个
let candidate = candidates.first(where: { $0.0 == 13 }) ?? candidates.first

if let (idx, btn) = candidate {
    let err = AXUIElementPerformAction(btn, kAXPressAction as CFString)
    print(err == .success ? "✅ 已点击候选侧边栏按钮(sib\(idx))" : "❌ 点击失败: \(err.rawValue)")
} else {
    print("❌ 未找到候选按钮")
    exit(4)
}
