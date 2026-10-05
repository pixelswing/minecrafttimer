#!/bin/bash
set -euo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Bitte mit sudo ausführen"; exit 1; }
script_dir="$(cd "$(dirname "$0")" && pwd)"
plist="/Library/LaunchDaemons/de.askin.minecraft-timer.plist"
python_path="$(/usr/libexec/PlistBuddy -c 'Print :ProgramArguments:0' "$plist")"
"$python_path" --version
launchctl bootout system/de.askin.minecraft-timer 2>/dev/null || true
install -o root -g wheel -m 755 "$script_dir/minecraft_timer.py" "/Library/Application Support/MinecraftTimer/minecraft_timer.py"
launchctl bootstrap system "$plist"
launchctl kickstart -k system/de.askin.minecraft-timer
echo "Aktualisiert. Konfiguration und Verbrauch wurden beibehalten."
