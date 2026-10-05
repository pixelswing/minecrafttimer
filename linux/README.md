# CachyOS / Arch Linux

Benötigt python; libnotify für optionale Desktop-Meldungen:

    sudo pacman -Syu --needed python libnotify

Im entpackten minecraft-timer-Verzeichnis:

    sudo bash linux/install.sh

Der Installer fragt URL und Token ab; bestehende Konfiguration wird bei Updates
beibehalten. Systemweiter root-Dienst, startet beim Booten für Benutzer mit UID >=1000.
Keine Änderung am V3-Webservice oder an Macs erforderlich.
Im Dashboard den tatsächlichen Linux-Kurznamen verwenden (whoami im Konto der Tochter),
Groß-/Kleinschreibung beachten. Anzeige erfolgt nach erkanntem Minecraft-Start.
Desktop-Meldungen benötigen eine aktive Benutzer-D-Bus-Sitzung.

    sudo systemctl status minecraft-timer
    sudo journalctl -u minecraft-timer -n 50 --no-pager
    sudo cat /var/lib/minecraft-timer/state.json
    sudo nano /etc/minecraft-timer/config.json
    sudo systemctl restart minecraft-timer

Minecraft Java: Vanilla, Fabric, Forge/NeoForge, Prism/MultiMC-Marker.
Sonderlauncher müssen ggf. ergänzt werden; Bedrock wird nicht erfasst.
Zeitfenster aus V3 werden nach lokaler Systemzeit durchgesetzt.
Offline: 60 Minuten (konfigurierbar), zuletzt empfangenes Zeitfenster bleibt bestehen.
Zählung misst Prozesslaufzeit, auch Hauptmenü; keine rückwirkende Erfassung.
Dashboard summiert gleiche Benutzernamen mehrerer Hosts, Limits gelten je Rechner.
Ein Benutzer mit sudo/root kann den Dienst administrieren.

Deinstallieren (Daten/Konfiguration bleiben erhalten):

    sudo systemctl disable --now minecraft-timer
    sudo rm /etc/systemd/system/minecraft-timer.service
    sudo systemctl daemon-reload
    sudo rm /opt/minecraft-timer/minecraft_timer.py

Tests in Linux-Umgebung: Syntax, Prozesserkennung mit simulierten /proc-Daten,
API-Kompatibilität über unveränderten V3-Client. Desktop-Benachrichtigung und
systemd-Start müssen auf dem Zielgerät geprüft werden.
