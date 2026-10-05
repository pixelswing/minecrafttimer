#!/bin/bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "Bitte mit sudo starten: sudo $0"
    exit 1
fi

script_dir="$(cd "$(dirname "$0")" && pwd)"
install_dir="/Library/Application Support/MinecraftTimer"
plist_path="/Library/LaunchDaemons/de.askin.minecraft-timer.plist"
python_path="$(command -v python3 || true)"

if [[ -z "$python_path" ]]; then
    echo "Python 3 wurde nicht gefunden. Bitte zuerst Python 3 installieren."
    exit 1
fi

mkdir -p "$install_dir" /var/db/minecraft-timer
install -o root -g wheel -m 755 "$script_dir/minecraft_timer.py" "$install_dir/minecraft_timer.py"
install -o root -g wheel -m 600 "$script_dir/config.json" "$install_dir/config.json"

sed "s|__PYTHON__|$python_path|g" "$script_dir/de.askin.minecraft-timer.plist.template" > "$plist_path"
chown root:wheel "$plist_path"
chmod 644 "$plist_path"
plutil -lint "$plist_path"

launchctl bootout system/de.askin.minecraft-timer 2>/dev/null || true
launchctl bootstrap system "$plist_path"
launchctl enable system/de.askin.minecraft-timer
launchctl kickstart -k system/de.askin.minecraft-timer

echo "Minecraft Timer wurde installiert und gestartet."
echo "Status: sudo launchctl print system/de.askin.minecraft-timer"
