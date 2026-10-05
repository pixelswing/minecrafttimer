#!/usr/bin/env python3
"""Systemweiter, dependency-freier Minecraft-Zeitwächter für Linux."""

import json
import logging
import os
import pwd
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

CONFIG_PATH = Path("/etc/minecraft-timer/config.json")
STATE_PATH = Path("/var/lib/minecraft-timer/state.json")
MINECRAFT_MARKERS = (
    "net.minecraft.client.main.Main",
    "net.fabricmc.loader.impl.launch.knot.KnotClient",
    "cpw.mods.modlauncher.Launcher",
    "org.multimc.EntryPoint",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("minecraft-timer")


def load_json(path, fallback):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return fallback


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, STATE_PATH)


def minecraft_processes():
    active = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            uid = entry.stat().st_uid
            if uid < 1000:
                continue
            args = (entry / "cmdline").read_bytes().split(b"\0")
            if not args or Path(os.fsdecode(args[0])).name != "java":
                continue
            command = b" ".join(args).decode(errors="replace")
            markers = MINECRAFT_MARKERS + (
                "org.prismlauncher.EntryPoint",
                "net.fabricmc.loader.launch.knot.KnotClient",
                "net.minecraft.launchwrapper.Launch",
                "net.neoforged.bootstrap",
            )
            if any(marker in command for marker in markers):
                active.setdefault(pwd.getpwuid(uid).pw_name, []).append(int(entry.name))
        except (OSError, KeyError, ValueError):
            continue
    return active


class LimitSource:
    def __init__(self, config):
        self.default = max(0, int(config.get("default_limit_minutes", 60)))
        self.url = str(config.get("webservice_url", "")).rstrip("/")
        self.token = str(config.get("api_token", ""))
        self.refresh_seconds = max(5, int(config.get("webservice_poll_seconds", 30)))
        self.values = {}
        self.windows = load_json(STATE_PATH.parent / "windows.json", {})
        self.reports = {}

    def get(self, username):
        now = time.monotonic()
        cached = self.values.get(username)
        if cached and now - cached[0] < self.refresh_seconds:
            return cached[1]

        limit = self.default
        if self.url:
            quoted_user = urllib.parse.quote(username, safe="")
            query = urllib.parse.urlencode({"host": socket.gethostname()})
            request = urllib.request.Request(
                f"{self.url}/api/v1/limits/{quoted_user}?{query}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            try:
                with urllib.request.urlopen(request, timeout=3) as response:
                    payload = json.load(response)
                limit = max(0, int(payload["effective_limit_minutes"]))
                self.windows[username] = [payload.get("window_start"), payload.get("window_end")]
                path = STATE_PATH.parent / "windows.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".tmp")
                temporary.write_text(json.dumps(self.windows))
                os.chmod(temporary, 0o600)
                os.replace(temporary, path)
            except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
                LOG.warning("Webservice für %s nicht erreichbar; Standardlimit %s min (%s)", username, self.default, error)

        self.values[username] = (now, limit)
        return limit


    def allowed(self, username):
        start, end = self.windows.get(username, [None, None])
        return not start or start <= datetime.now().strftime("%H:%M") < end

    def report(self, username, state):
        now = time.monotonic()
        if not self.url or now-self.reports.get(username, -1000)<self.refresh_seconds:
            return
        self.reports[username] = now
        try:
            request = urllib.request.Request(
                self.url+"/api/v1/users/"+urllib.parse.quote(username, safe="")+"/usage",
                data=json.dumps({"date":state["date"], "host":socket.gethostname(),
                                 "used_seconds":state["users"][username]["used_seconds"]}).encode(),
                headers={"Authorization":"Bearer "+self.token,"Content-Type":"application/json"},
                method="POST")
            with urllib.request.urlopen(request, timeout=3) as response:
                response.read()
        except (OSError, ValueError) as error:
            LOG.warning("Verbrauchsmeldung fehlgeschlagen: %s", error)


def notify(username, message):
    try:
        uid = pwd.getpwnam(username).pw_uid
        runtime = f"/run/user/{uid}"
        if not Path(runtime + "/bus").exists():
            return
        subprocess.run(
            ["/usr/bin/runuser", "-u", username, "--", "/usr/bin/env",
             f"XDG_RUNTIME_DIR={runtime}",
             f"DBUS_SESSION_BUS_ADDRESS=unix:path={runtime}/bus",
             "/usr/bin/notify-send", "--app-name=Minecraft Timer",
             "Minecraft Timer", message],
            check=False, timeout=5, capture_output=True)
    except (KeyError, OSError, subprocess.SubprocessError):
        pass


def terminate(pids, username, message="Deine Minecraft-Zeit für heute ist abgelaufen."):
    LOG.info("Limit für %s erreicht; beende Minecraft PIDs %s", username, pids)
    notify(username, message)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    time.sleep(5)
    for pid in pids:
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main():
    with CONFIG_PATH.open() as handle:
        config = json.load(handle)
    parsed = urllib.parse.urlparse(config.get("webservice_url", ""))
    if parsed.scheme not in ("http", "https") or not parsed.hostname or "[" in config["webservice_url"]:
        raise ValueError("webservice_url muss eine reine http(s)-URL sein")

    poll_seconds = max(2, int(config.get("poll_seconds", 10)))
    warnings = sorted({max(0, int(item)) for item in config.get("warning_minutes", [10, 5, 1])}, reverse=True)
    limits = LimitSource(config)
    state = load_json(STATE_PATH, {"date": str(date.today()), "users": {}})
    last_tick = time.monotonic()

    LOG.info("Timer gestartet; Offline-Standardlimit: %s Minuten", limits.default)
    while True:
        today = str(date.today())
        if state.get("date") != today:
            state = {"date": today, "users": {}}
            limits.values.clear()

        now = time.monotonic()
        elapsed = min(now - last_tick, poll_seconds * 2)
        last_tick = now
        active = minecraft_processes()

        for username, pids in active.items():
            user_state = state["users"].setdefault(username, {"used_seconds": 0.0, "warnings_sent": []})
            user_state["used_seconds"] = float(user_state.get("used_seconds", 0.0)) + elapsed
            limit_minutes = limits.get(username)
            if not limits.allowed(username):
                terminate(pids, username, "Minecraft ist außerhalb deines erlaubten Zeitfensters.")
                continue
            remaining = limit_minutes * 60 - user_state["used_seconds"]

            for warning in warnings:
                if 0 < remaining <= warning * 60 and warning not in user_state["warnings_sent"]:
                    notify(username, f"Noch {warning} Minute(n) Minecraft-Zeit.")
                    user_state["warnings_sent"].append(warning)

            if remaining <= 0:
                terminate(pids, username)

        save_state(state)
        for username in state["users"]:
            limits.report(username, state)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
