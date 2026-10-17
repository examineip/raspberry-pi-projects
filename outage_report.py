#!/usr/bin/env python3
# Project 5: read uptime.csv and list every outage.
import csv
from datetime import datetime
from pathlib import Path

LOG = Path.home() / "uptime.csv"

rows = []
with LOG.open() as f:
    for row in csv.DictReader(f):
        when = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S")
        rows.append((when, row["status"]))

outages, start = [], None
for when, status in rows:
    if status == "down" and start is None:
        start = when                       # an outage begins
    elif status == "up" and start is not None:
        outages.append((start, when))      # back up: it ended
        start = None
if start is not None:
    outages.append((start, rows[-1][0]))   # still down at the end

up = sum(1 for _, s in rows if s == "up")
print(f"Checks: {len(rows)}   up: {100 * up / len(rows):.2f} %")
print(f"Outages: {len(outages)}")
for begin, end in outages:
    minutes = round((end - begin).total_seconds() / 60)
    print(f"  {begin:%a %d %b %H:%M}  about {max(minutes, 1)} min")
