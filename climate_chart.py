#!/usr/bin/env python3
# Project 2: turn climate.csv into a chart you can open on any device.
import csv
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # draw to a file; no screen needed
import matplotlib.pyplot as plt

LOG = Path.home() / "climate.csv"
CHART = Path.home() / "climate.png"

times, temps, hums = [], [], []
with LOG.open() as f:
    for row in csv.DictReader(f):
        times.append(datetime.fromisoformat(row["time"]))
        temps.append(float(row["temp_c"]))
        hums.append(float(row["humidity_pct"]))

fig, left = plt.subplots(figsize=(10, 4))
left.plot(times, temps, color="tab:red")
left.set_ylabel("Temperature (C)", color="tab:red")
right = left.twinx()
right.plot(times, hums, color="tab:blue")
right.set_ylabel("Humidity (%)", color="tab:blue")
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(CHART, dpi=120)
print("Saved", CHART, "with", len(times), "readings")
