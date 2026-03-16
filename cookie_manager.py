import json
import time
from pathlib import Path
import yaml
from playwright.sync_api import sync_playwright

# 修改为当前目录下的路径
COOKIE_FILE = Path(__file__).parent / "data" / ".cookies.json"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.local.yaml"
COOKIE_TTL = 23 * 3600


def _load_cached():
    if COOKIE_FILE.exists():
        data = json.loads(COOKIE_FILE.read_text())
        if time.time() - data["timestamp"] < COOKIE_TTL:
            return data["cookies"]
    return None


def _load_credentials():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"请创建 {CREDENTIALS_FILE} 并填写 username 和 password")
    with open(CREDENTIALS_FILE) as f:
        creds = yaml.safe_load(f)
    return creds["username"], creds["password"]


def _fetch_via_browser():
    username, password = _load_credentials()
    SSO_URL = (
        "https://login-choice.nie.netease.com/"
        "?openid=http://brainmaker.netease.com/login?type=openid"
        "&oscar=http://brainmaker.netease.com/login/oscar"
        "&next=https://brainmaker.netease.com/v3"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # 第一步：选择登录方式
        page.goto(SSO_URL, wait_until="networkidle", timeout=20000)
        page.click('button:has-text("Login with OpenID")')
        page.wait_for_load_state("networkidle", timeout=15000)

        # 第二步：直接填写账号密码并提交（corpid 只填邮箱前缀）
        corp_prefix = username.split("@")[0]
        page.fill("input[name='corpid']", corp_prefix)
        page.fill("input[name='corppw']", password)
        # 勾选隐私政策
        page.evaluate("document.getElementById('corp_id_for_privacy').checked = true")
        page.locator(".oidc-active input[type='button']").click(force=True)

        # 等待跳回 brainmaker（导航可能在 click 返回前已完成）
        page.wait_for_load_state("networkidle", timeout=30000)

        cookies = {
            c["name"]: c["value"]
            for c in context.cookies()
            if "netease.com" in c.get("domain", "")
        }
        browser.close()

    COOKIE_FILE.write_text(json.dumps({"timestamp": time.time(), "cookies": cookies}))
    return cookies


def get_cookies():
    """获取有效 cookie，过期则自动登录刷新"""
    return _load_cached() or _fetch_via_browser()
