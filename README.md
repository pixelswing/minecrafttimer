# Minecraft Timer für macOS

Der Timer überwacht Minecraft für **alle lokalen Benutzer** eines Macs. Pro Benutzer
wird die tatsächliche Laufzeit des Minecraft-Java-Prozesses pro Kalendertag gezählt.
Nach Ablauf des Limits wird Minecraft zunächst normal (`TERM`) und kurz darauf
notfalls hart (`KILL`) beendet.

Das Tageslimit kommt nach Möglichkeit vom Webservice. Ist dieser nicht erreichbar,
gilt immer das lokal konfigurierte Standardlimit (voreingestellt: 60 Minuten).

## 1. Webservice mit Docker starten

In `docker-compose.yml` vor dem Start unbedingt `MCTIMER_TOKEN` ändern:

```bash
docker compose up -d --build
```

Danach ist die Oberfläche erreichbar unter:

```text
http://SERVER-IP:8787/
```

In der Oberfläche einmal den Token eingeben. Benutzer und Host erscheinen
automatisch, sobald ein Mac den Webservice erfolgreich abgefragt hat. Alternativ
kann ein Benutzer manuell hinzugefügt werden. Pro Benutzer kann das heutige
Limit mit `+15`, `-15`, einer freien Minutenzahl oder `Standard` geändert werden.
Änderungen gelten nur für den aktuellen Kalendertag.

Die minimale Persistenz liegt ausschließlich in:

```text
./data/minecraft-timer.db
```

Es ist keine externe Datenbank erforderlich.

## 2. Timer auf dem Mac installieren

`macos/config.json` anpassen:

```json
{
  "default_limit_minutes": 60,
  "webservice_url": "http://SERVER-IP:8787",
  "api_token": "DASSELBE-GEHEIME-TOKEN",
  "poll_seconds": 10,
  "webservice_poll_seconds": 30,
  "warning_minutes": [10, 5, 1]
}
```

Dann aus dem Projektverzeichnis installieren:

```bash
sudo ./macos/install.sh
```

Der Installer erzeugt einen systemweiten `LaunchDaemon`. Er läuft unabhängig
davon, welcher Benutzer gerade angemeldet ist.

Status und Logs prüfen:

```bash
sudo launchctl print system/de.askin.minecraft-timer
tail -f /var/log/minecraft-timer.log
tail -f /var/log/minecraft-timer-error.log
```

Aktuellen lokalen Stand anzeigen:

```bash
sudo cat /var/db/minecraft-timer/state.json
```

Deinstallieren:

```bash
sudo ./macos/uninstall.sh
```

## API

Alle API-Aufrufe benötigen den Header `Authorization: Bearer TOKEN`.

```bash
# Limit abfragen
curl -H "Authorization: Bearer TOKEN" \
  http://SERVER-IP:8787/api/v1/limits/oskar

# 15 Minuten hinzufügen
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"delta_minutes":15}' \
  http://SERVER-IP:8787/api/v1/users/oskar/adjust

# Heutige Anpassung zurücksetzen
curl -X DELETE -H "Authorization: Bearer TOKEN" \
  http://SERVER-IP:8787/api/v1/users/oskar/adjust
```

## Wichtige Details

- Benutzernamen sind die macOS-Kurznamen, beispielsweise `oskar`.
- Die Nutzung wird einmal pro Benutzer gezählt, auch wenn mehrere erkannte
  Minecraft-Prozesse gleichzeitig laufen.
- Ein Serverausfall setzt nicht die verbrauchte Zeit zurück. Nur das gültige Limit
  fällt dann auf 60 Minuten zurück.
- Systembenutzer (`root`, Benutzer-ID kleiner 500) werden ignoriert.
- Der Timer erkennt Vanilla, Fabric, Forge/ModLauncher sowie MultiMC/Prism.
- Der Mac und der Docker-Host sollten dieselbe Zeitzone verwenden.

## V3 aktualisieren

ZIP in einen separaten Ordner entpacken. Auf dem Docker-Server nur
webservice/server.py in den bestehenden webservice-Ordner übernehmen,
danach im bestehenden Compose-Verzeichnis:

    docker compose up -d --build minecraft-timer-web

Bestehende docker-compose.yml, Token und data beibehalten.
Auf jedem Mac aus dem entpackten minecraft-timer-Verzeichnis:

    sudo bash macos/update.sh

Der Update-Befehl erhält installierte Konfiguration, Python-Pfad und Tagesverbrauch.
Das Dashboard zeigt gemeldeten heutigen Verbrauch (Aktualisierung ca. 30 Sekunden).
Ohne Meldung erscheint „–“, nicht fälschlich null Minuten.
Mehrere Hosts mit gleichem Benutzernamen werden im Dashboard summiert; das
Minutenlimit wird weiterhin je Mac durchgesetzt. Hostnamen müssen eindeutig bleiben.
Alte Macs unterstützen weder Verbrauchsmeldungen noch Zeitfenster.

Entfernen blendet einen Nutzer dauerhaft aus; Verbrauch und Regeln bleiben erhalten.
Durch erneutes Hinzufügen wird der Nutzer wieder sichtbar und das heutige Limit
auf den Standard gesetzt. Zeitfenster bleiben dabei erhalten.

Zeitfenster gelten täglich nach lokaler Mac-Uhr: Start inklusive, Ende exklusiv.
14:00 bis 18:00 erlaubt Minecraft innerhalb dieser Zeiten zusätzlich zum Tageslimit.
Außerhalb beendet der Timer Minecraft innerhalb des Prüfintervalls.
Ganztägig entfernt die Zeitbeschränkung. Fenster über Mitternacht werden abgelehnt.
Das zuletzt erfolgreich empfangene Fenster wird auf dem Mac gespeichert und gilt
auch offline/nach Neustarts. Vor dem ersten Empfang gibt es kein Zeitfenster.
Das Minutenlimit fällt offline weiterhin auf die lokale Standardzeit zurück.
Mac und Server müssen das gleiche Datum / dieselbe Zeitzone verwenden.
