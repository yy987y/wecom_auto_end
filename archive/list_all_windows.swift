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
    return (value as? String) ?? ""
}

guard let pid = findWeComPID() else {
    print("❌ 未找到企微")
    exit(1)
}

let app = AXUIElementCreateApplication(pid)

var windows: AnyObject?
AXUIElementCopyAttributeValue(app, kAXWindowsAttribute as CFString, &windows)

if let wins = windows as? [AXUIElement] {
    print("找到 \(wins.count) 个窗口：\n")
    for (idx, win) in wins.enumerated() {
        let title = getAttr(win, kAXTitleAttribute)
        let role = getAttr(win, kAXRoleAttribute)
        print("窗口 \(idx + 1): \(title.isEmpty ? "(无标题)" : title) - \(role)")
    }
}
