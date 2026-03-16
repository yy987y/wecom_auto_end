#!/usr/bin/swift
import Cocoa
import ApplicationServices

func findWeComApp() -> NSRunningApplication? {
    let names = ["企业微信", "WeCom", "WXWork"]
    for app in NSWorkspace.shared.runningApplications {
        let name = app.localizedName ?? ""
        if names.contains(where: { name.localizedCaseInsensitiveContains($0) }) {
            return app
        }
    }
    return nil
}

guard let app = findWeComApp() else {
    print("❌ 未找到企业微信")
    exit(1)
}

// 激活企微窗口
app.activate(options: .activateIgnoringOtherApps)
sleep(1)

print("✅ 企微已激活，PID: \(app.processIdentifier)")
print("现在可以运行查找按钮的脚本")
