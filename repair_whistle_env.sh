#!/bin/bash
set -euo pipefail

WHISTLE_PORT=8899
CLASH_PORT=7890
WHISTLE_HOST=127.0.0.1
LOG_PREFIX="[Whistle修复]"

say() { echo "$LOG_PREFIX $1"; }

get_active_service() {
  local service
  service=$(route get default 2>/dev/null | awk '/interface:/{print $2}' | head -n1 || true)
  if [[ -n "$service" ]]; then
    local mapped
    mapped=$(networksetup -listallhardwareports 2>/dev/null | awk -v dev="$service" '
      $1=="Hardware" && $2=="Port:" {port=substr($0,index($0,$3))}
      $1=="Device:" && $2==dev {print port}
    ' | head -n1 || true)
    if [[ -n "$mapped" ]]; then
      echo "$mapped"
      return
    fi
  fi
  echo "Wi-Fi"
}

SERVICE="$(get_active_service)"
say "当前网络服务: $SERVICE"

check_whistle_listener() {
  if command -v lsof >/dev/null 2>&1; then
    if lsof -iTCP:${WHISTLE_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
      say "Whistle 监听正常: ${WHISTLE_HOST}:${WHISTLE_PORT}"
      return
    fi
  else
    if ps -ef | grep '[n]ode .*whistle' >/dev/null 2>&1 || ps -ef | grep '[w]histle' >/dev/null 2>&1; then
      say "检测到 Whistle 相关进程在运行（当前系统无 lsof，使用进程回退判断）"
      return
    fi
  fi

  say "未检测到 Whistle 监听，尝试启动..."
  w2 start || true
  sleep 2

  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:${WHISTLE_PORT} -sTCP:LISTEN >/dev/null 2>&1 || { say "Whistle 启动失败"; exit 1; }
  else
    ps -ef | grep '[n]ode .*whistle' >/dev/null 2>&1 || ps -ef | grep '[w]histle' >/dev/null 2>&1 || { say "Whistle 启动失败"; exit 1; }
  fi
  say "Whistle 已启动"
}

check_whistle_web() {
  if curl -sI "http://${WHISTLE_HOST}:${WHISTLE_PORT}/" >/dev/null; then
    say "Whistle Web UI 可访问"
  else
    say "Whistle Web UI 不可访问"
    exit 1
  fi
}

configure_system_proxy() {
  say "设置系统 HTTP/HTTPS 代理到 Whistle ${WHISTLE_HOST}:${WHISTLE_PORT} ..."
  networksetup -setwebproxy "$SERVICE" "$WHISTLE_HOST" "$WHISTLE_PORT"
  networksetup -setsecurewebproxy "$SERVICE" "$WHISTLE_HOST" "$WHISTLE_PORT"
  networksetup -setwebproxystate "$SERVICE" on
  networksetup -setsecurewebproxystate "$SERVICE" on
  
  say "关闭系统 SOCKS 直连，避免绕过 Whistle..."
  networksetup -setsocksfirewallproxystate "$SERVICE" off || true
}

show_proxy_status() {
  say "当前代理状态："
  networksetup -getwebproxy "$SERVICE" || true
  networksetup -getsecurewebproxy "$SERVICE" || true
  networksetup -getsocksfirewallproxy "$SERVICE" || true
}

check_clash_listener() {
  if lsof -iTCP:${CLASH_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    say "检测到 Clash/上游代理端口 ${CLASH_PORT} 正在监听"
    return 0
  fi
  say "未检测到 ${CLASH_PORT} 监听，后续若需要外网/VPN出口，Whistle 上游代理可能不可用"
  return 1
}

configure_whistle_upstream_hint() {
  cat <<EOF
$LOG_PREFIX 建议将 Whistle 上游代理设置为 Clash：
  - HTTP/HTTPS 上游代理: ${WHISTLE_HOST}:${CLASH_PORT}
  - 这样链路为：系统代理 -> Whistle(8899) -> Clash(7890)

如果你在 Whistle 页面里手动设置：
  1. 打开 http://${WHISTLE_HOST}:${WHISTLE_PORT}/
  2. 进入配置/网络设置
  3. 将上游代理指向 ${WHISTLE_HOST}:${CLASH_PORT}
EOF
}

check_certificate() {
  if security find-certificate -a -c "Whistle" /Library/Keychains/System.keychain >/dev/null 2>&1; then
    say "System.keychain 中存在 Whistle 证书"
  elif security find-certificate -a -c "Whistle" ~/Library/Keychains/login.keychain-db >/dev/null 2>&1; then
    say "仅在 login.keychain 中检测到 Whistle 证书，建议后续补到 System.keychain"
  else
    say "未检测到 Whistle 证书，尝试下载..."
    curl -fsSL "http://${WHISTLE_HOST}:${WHISTLE_PORT}/cgi-bin/rootca" -o /tmp/whistle-rootca.crt || true
    if [[ -f /tmp/whistle-rootca.crt ]]; then
      say "已下载证书到 /tmp/whistle-rootca.crt，请手动确认安装/信任"
    else
      say "证书下载失败"
    fi
  fi
}

check_whistle_api() {
  if curl -s "http://${WHISTLE_HOST}:${WHISTLE_PORT}/cgi-bin/get-data?count=1" | grep -q '"ec":0'; then
    say "Whistle API 正常"
  else
    say "Whistle API 异常"
    exit 1
  fi
}

main() {
  say "开始检测并修复 Whistle + Clash 并存环境..."
  check_whistle_listener
  check_whistle_web
  configure_system_proxy
  show_proxy_status
  check_clash_listener || true
  configure_whistle_upstream_hint
  check_certificate
  check_whistle_api
  say "修复完成。下一步请："
  echo "  1. 确认 Whistle 上游代理是否指向 ${WHISTLE_HOST}:${CLASH_PORT}"
  echo "  2. 重启企业微信"
  echo "  3. 打开网易智企页面"
  echo "  4. 再观察 Whistle 是否出现 qiyukf.com 请求"
}

main "$@"
