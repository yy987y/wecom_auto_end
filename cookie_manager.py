import json
import time
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

COOKIE_FILE = Path(__file__).parent / "data" / ".cookies.json"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.local.yaml"
PROFILE_DIR = Path(__file__).parent / "data" / "brainmaker-profile"
COOKIE_TTL = 23 * 3600
BRAINMAKER_URL = "https://brainmaker.netease.com/v3"
SSO_URL = (
    "https://login-choice.nie.netease.com/"
    "?openid=http://brainmaker.netease.com/login?type=openid"
    "&oscar=http://brainmaker.netease.com/login/oscar"
    "&next=https://brainmaker.netease.com/v3"
)


def _is_cookie_set_valid(cookies):
    return bool(cookies) and any(name in cookies for name in ["NETEASE_WDA_UID", "NTES_YD_SESS", "P_INFO"])


def _save_cookie_cache(cookies):
    COOKIE_FILE.parent.mkdir(exist_ok=True)
    COOKIE_FILE.write_text(
        json.dumps({"timestamp": time.time(), "cookies": cookies}, ensure_ascii=False, indent=2)
    )


def _extract_netease_cookies(cookies):
    return {
        c["name"]: c["value"]
        for c in cookies
        if "netease.com" in c.get("domain", "")
    }


def _load_cached():
    if not COOKIE_FILE.exists():
        return None
    try:
        data = json.loads(COOKIE_FILE.read_text())
        if time.time() - data["timestamp"] < COOKIE_TTL:
            cookies = data.get("cookies") or {}
            if _is_cookie_set_valid(cookies):
                return cookies
    except Exception:
        return None
    return None


def _load_credentials():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"请创建 {CREDENTIALS_FILE} 并填写 username 和 password")
    with open(CREDENTIALS_FILE) as f:
        creds = yaml.safe_load(f)
    return creds["username"], creds["password"]


def _load_from_persistent_profile():
    if not PROFILE_DIR.exists():
        return None

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
        )
        try:
            page = context.new_page()
            page.goto(BRAINMAKER_URL, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            cookies = _extract_netease_cookies(context.cookies())
            if _is_cookie_set_valid(cookies):
                _save_cookie_cache(cookies)
                return cookies
            return None
        finally:
            context.close()


def _goto_login_entry(page):
    page.goto(SSO_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)

    # 尽量不依赖中英文文案，优先用 URL 和表单状态判断是否已进入 oidc 登录表单
    for _ in range(10):
        if page.locator("input[name='corpid']").count() and page.locator("input[name='corppw']").count():
            return

        clicked = False
        selectors = [
            "button[data-testid='openid-login']",
            "[data-login-type='openid']",
            ".oidc-login-entry",
            "button:has-text('Login with OpenID')",
            "button:has-text('OpenID')",
            "text=OpenID",
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.count():
                    locator.click(timeout=2000)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            try:
                page.goto(page.url, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass

        page.wait_for_timeout(1000)

    if not (page.locator("input[name='corpid']").count() and page.locator("input[name='corppw']").count()):
        raise RuntimeError("未能进入 Brainmaker 登录表单页面")


def _submit_login_form(page, username, password):
    corp_prefix = username.split("@")[0]
    page.locator("input[name='corpid']").fill(corp_prefix)
    page.locator("input[name='corppw']").fill(password)

    try:
        page.evaluate(
            """
            () => {
              const checkbox = document.getElementById('corp_id_for_privacy');
              if (checkbox) checkbox.checked = true;
            }
            """
        )
    except Exception:
        pass

    submit_selectors = [
        ".oidc-active input[type='button']",
        "input[type='submit']",
        "button[type='submit']",
        "button.login-btn",
    ]
    for selector in submit_selectors:
        try:
            locator = page.locator(selector).first
            if locator.count():
                locator.click(force=True, timeout=3000)
                return
        except Exception:
            continue

    # 最后兜底，直接提交 form
    page.evaluate(
        """
        () => {
          const form = document.querySelector('form');
          if (form) form.submit();
        }
        """
    )


def _fetch_via_browser():
    username, password = _load_credentials()
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        try:
            page = context.new_page()
            page.goto(BRAINMAKER_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            cookies = _extract_netease_cookies(context.cookies())
            if _is_cookie_set_valid(cookies):
                _save_cookie_cache(cookies)
                return cookies

            _goto_login_entry(page)
            _submit_login_form(page, username, password)

            # 等待登录态建立，尽量按 URL / cookie 判断，不依赖界面文案
            for _ in range(30):
                page.wait_for_timeout(1000)
                try:
                    if "brainmaker.netease.com" in page.url:
                        cookies = _extract_netease_cookies(context.cookies())
                        if _is_cookie_set_valid(cookies):
                            _save_cookie_cache(cookies)
                            return cookies
                except Exception:
                    pass

            cookies = _extract_netease_cookies(context.cookies())
            if _is_cookie_set_valid(cookies):
                _save_cookie_cache(cookies)
                return cookies
            raise RuntimeError("登录后未获取到有效 Brainmaker cookies")
        finally:
            context.close()


def get_cookies():
    """获取有效 cookie，优先缓存和持久化登录态，最后才登录刷新"""
    return _load_cached() or _load_from_persistent_profile() or _fetch_via_browser()
