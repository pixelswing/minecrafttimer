#!/bin/bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Bitte: sudo bash linux/install.sh"; exit 1; }
source_dir="$(cd "$(dirname "$0")" && pwd)"
/usr/bin/python3 --version
command -v systemctl >/dev/null
install -d -m 755 /opt/minecraft-timer
install -d -m 700 /etc/minecraft-timer /var/lib/minecraft-timer
if [[ ! -f /etc/minecraft-timer/config.json ]]; then
    read -r -p "Webservice-URL [http://192.168.178.2:8787]: " timer_url
    timer_url="${timer_url:-http://192.168.178.2:8787}"
    read -r -s -p "API-Token (wie im Webservice): " timer_token
    echo
    export TIMER_URL="$timer_url" TIMER_TOKEN="$timer_token"
    /usr/bin/python3 - <<'PY'
import json,os
from urllib.parse import urlparse
url=os.environ["TIMER_URL"]
assert urlparse(url).scheme in ("http","https") and urlparse(url).hostname and "[" not in url, "Ungültige URL"
assert os.environ["TIMER_TOKEN"], "Token fehlt"
with open("/etc/minecraft-timer/config.json","w") as f:
 json.dump(dict(default_limit_minutes=60,webservice_url=url,api_token=os.environ["TIMER_TOKEN"],poll_seconds=10,webservice_poll_seconds=30,warning_minutes=[10,5,1]),f,indent=2)
os.chmod("/etc/minecraft-timer/config.json",0o600)
PY
    unset TIMER_URL TIMER_TOKEN timer_token
fi
install -m 755 "$source_dir/minecraft_timer.py" /opt/minecraft-timer/minecraft_timer.py
install -m 644 "$source_dir/minecraft-timer.service" /etc/systemd/system/minecraft-timer.service
systemctl daemon-reload
systemctl enable minecraft-timer.service
systemctl restart minecraft-timer.service
echo "Installiert. Status: sudo systemctl status minecraft-timer"
