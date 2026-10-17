#!/usr/bin/env python3
# Project 2: log temperature, humidity and pressure from a BME280.
import csv
import time
from datetime import datetime
from pathlib import Path

import bme280
import smbus2

ADDRESS = 0x76          # or 0x77: check with  i2cdetect -y 1
EVERY = 60              # seconds between readings
LOG = Path.home() / "climate.csv"

bus = smbus2.SMBus(1)
calibration = bme280.load_calibration_params(bus, ADDRESS)

is_new = not LOG.exists()
with LOG.open("a", newline="") as f:
    out = csv.writer(f)
    if is_new:
        out.writerow(["time", "temp_c", "humidity_pct", "pressure_hpa"])
    while True:
        r = bme280.sample(bus, ADDRESS, calibration)
        now = datetime.now().isoformat(timespec="seconds")
        out.writerow([now, round(r.temperature, 1),
                      round(r.humidity, 1), round(r.pressure, 1)])
        f.flush()       # write to the card now, not later
        print(f"{now}  {r.temperature:.1f} C  "
              f"{r.humidity:.0f} %  {r.pressure:.0f} hPa")
        time.sleep(EVERY)
