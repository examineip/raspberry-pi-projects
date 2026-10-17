# raspberry-pi-projects

The ten scripts from the book **Raspberry Pi for Absolute Beginners: Set It Up, Learn It, and Build
Twelve Real Projects** (For Absolute Beginners, volume 6, by [ExamineIP](https://examineip.com)).
Download them here so you never have to type one out.

```bash
git clone https://github.com/examineip/raspberry-pi-projects
cd raspberry-pi-projects
```

The book explains every script line by line and shows the wiring pin by pin. This README is a quick
reference.

## The scripts

| Script | Project | Wiring (physical pin numbers) |
|---|---|---|
| `blink.py` | P1 · Blink an LED | pin 11 (GPIO 17) → 330 Ω resistor → LED long leg; LED short leg → pin 9 (GND) |
| `button_led.py` | P1 · Add a button | as above, plus a button between pin 13 (GPIO 27) and pin 14 (GND) |
| `climate_logger.py` | P2 · Temperature logger | BME280: VIN → pin 1, SDA → pin 3, SCL → pin 5, GND → pin 6 |
| `climate_chart.py` | P2 · Draw the chart | none: reads `~/climate.csv`, writes `~/climate.png` |
| `plant_alert.py` | P3 · Thirsty-plant alert | soil module: VCC → pin 17 (3.3V), DO → pin 15 (GPIO 22), GND → pin 20 |
| `motion_camera.py` | P4 · Motion camera | camera on its ribbon port; PIR: VCC → pin 2 (5V), OUT → pin 7 (GPIO 4), GND → pin 6 |
| `uptime_check.sh` | P5 · Outage logger | none: network cable to the router recommended |
| `outage_report.py` | P5 · Outage report | none: reads `~/uptime.csv` |
| `wifi_watch.py` | P6 · Who's on my Wi-Fi? | none |
| `battery_monitor.py` | P12 · Bluetooth battery monitor | none: reads a JK BMS over Bluetooth |

Projects 7 to 11 (Pi-hole, MagicMirror², media centre, retro console, Home Assistant) install
existing software, so they have no scripts here.

## Setup on the Pi

On Raspberry Pi OS (Trixie or later):

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3-gpiozero python3-venv git
python3 -m venv --system-site-packages ~/pienv
~/pienv/bin/pip install RPi.bme280 bleak
```

Extra packages for some projects:

| Project | Install |
|---|---|
| P2 | `sudo apt install -y i2c-tools python3-matplotlib`, then turn on I2C in `sudo raspi-config` → Interface Options |
| P4 | `sudo apt install -y python3-picamera2` |
| P6 | `sudo apt install -y arp-scan` |

The GPIO scripts use [gpiozero](https://gpiozero.readthedocs.io/), which works on every Pi from the
Pi 2 to the Pi 5. (Older tutorials use `RPi.GPIO`, which does not work on the Pi 5.)

## Before you run them

- **`plant_alert.py` and `wifi_watch.py`** send phone notifications through [ntfy](https://ntfy.sh).
  Change `TOPIC` to your own long, random name. Anyone who knows the topic can read it.
- **`wifi_watch.py`** needs root, because arp-scan does. Schedule it with `sudo crontab -e`. It keeps
  the devices it has seen in `known-devices.txt`, next to the script.
- **`climate_logger.py`**: if `i2cdetect -y 1` shows your sensor at `77` instead of `76`, change
  `ADDRESS` to `0x77`.
- **`battery_monitor.py`** looks for a Bluetooth device whose name starts with `JK`. Turn Bluetooth
  off on your phone first, because the battery accepts only one connection at a time.

## Tests

The scripts were run before publication with **simulated** hardware, not on a physical Pi:
gpiozero's `MockFactory` stands in for the pins, and small fake modules stand in for the BME280,
the camera, ntfy, arp-scan and the Bluetooth battery. The battery test streams a real-format
300-byte JK frame in Bluetooth-sized chunks. `uptime_check.sh` uses a real `ping`.

You can run the same tests on any Linux PC or under WSL, with no Pi:

```bash
python3 -m venv venv
venv/bin/pip install gpiozero matplotlib
venv/bin/python tests/run_tests.py
```

Something not working on real hardware? [Open an issue](https://github.com/examineip/raspberry-pi-projects/issues)
with your Pi model, the command you ran and the full error message.

## Licence

MIT. Use the scripts in your own projects.
