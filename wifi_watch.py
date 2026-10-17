#!/usr/bin/env python3
# Project 6: alert when a device you have never seen joins your network.
# Runs as root (arp-scan needs it):  sudo crontab -e
import subprocess
import urllib.request
from pathlib import Path

TOPIC = "wifi-change-me-4n8w2r"           # long and random
KNOWN = Path(__file__).with_name("known-devices.txt")


def scan():
    # full path, because cron's PATH does not include /usr/sbin
    out = subprocess.run(["/usr/sbin/arp-scan", "--localnet", "--plain"],
                         capture_output=True, text=True, check=True).stdout
    found = {}
    for line in out.splitlines():
        parts = line.split("\t")           # IP <tab> MAC <tab> maker
        if len(parts) >= 2:
            maker = parts[2] if len(parts) > 2 else "unknown maker"
            found[parts[1].lower()] = (parts[0], maker)
    return found


def notify(message):
    request = urllib.request.Request(
        "https://ntfy.sh/" + TOPIC, data=message.encode(),
        headers={"Title": "New device on your Wi-Fi"})
    urllib.request.urlopen(request, timeout=10)


first_run = not KNOWN.exists()
known = set(KNOWN.read_text().split()) if not first_run else set()

found = scan()
for mac, (ip, maker) in found.items():
    if mac not in known:
        if not first_run:                  # first run: learn, don't alert
            notify(f"{ip}  {mac}  {maker}")
            print("NEW:", ip, mac, maker)
        known.add(mac)

KNOWN.write_text("\n".join(sorted(known)) + "\n")
print(f"{len(found)} devices online, {len(known)} known")
