#!/bin/bash
set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "Bitte mit sudo starten: sudo $0"
    exit 1
fi

launchctl bootout system/de.askin.minecraft-timer 2>/dev/null || true
rm -f "/Library/LaunchDaemons/de.askin.minecraft-timer.plist"
rm -rf "/Library/Application Support/MinecraftTimer"

echo "Dienst und Programm wurden entfernt."
echo "Die Verbrauchsdaten bleiben unter /var/db/minecraft-timer erhalten."
