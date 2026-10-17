"""Run every book script with simulated hardware and check what it does.

GPIO   : gpiozero's MockFactory (real gpiozero code, simulated pins)
BME280 : fake bme280/smbus2 modules
Camera : fake picamera2 module that writes a real file
Network: fake urlopen (ntfy), fake arp-scan output, real ping for uptime_check.sh
Battery: fake bleak module that streams a real-format 300-byte JK frame in BLE-sized chunks

Run on any Linux PC or WSL (no Pi needed):
    python3 -m venv venv
    venv/bin/pip install gpiozero matplotlib
    venv/bin/python tests/run_tests.py
"""
import asyncio, contextlib, csv, io, os, runpy, shutil, subprocess, sys, tempfile, threading, time, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
REAL_SLEEP = time.sleep
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  [" + str(detail) + "]") if detail else ""))


class Stop(Exception):
    pass


def fresh_gpio():
    from gpiozero import Device
    from gpiozero.pins.mock import MockFactory
    if Device.pin_factory is not None:
        Device.pin_factory.close()
    Device.pin_factory = MockFactory()
    return Device.pin_factory


def run(script, sleeps=None, home=None, patches=()):
    """Run a script with time.sleep replaced by `sleeps(n, seconds)` (raise Stop to end)."""
    count = {"n": 0}
    def fake_sleep(sec):
        count["n"] += 1
        if sleeps:
            sleeps(count["n"], sec)
    old_home = os.environ.get("HOME")
    if home:
        os.environ["HOME"] = str(home)
    out = io.StringIO()
    with contextlib.ExitStack() as st:
        st.enter_context(contextlib.redirect_stdout(out))
        time.sleep = fake_sleep
        for obj, attr, val in patches:
            old = getattr(obj, attr)
            setattr(obj, attr, val)
            st.callback(setattr, obj, attr, old)
        try:
            ns = runpy.run_path(str(script), run_name="__main__")
        except Stop:
            ns = None
        finally:
            time.sleep = REAL_SLEEP
            if home:
                os.environ["HOME"] = old_home
    return ns, out.getvalue()


# ---------- Project 1: blink ----------
f = fresh_gpio()
def stop_after(n):
    def s(i, sec):
        if i >= n:
            raise Stop
    return s
run(SCRIPTS / "blink.py", sleeps=stop_after(6))
states = [s.state for s in f.pin(17).states]
check("blink: LED toggles on/off on GPIO 17", states[:7] == [False, True, False, True, False, True, False], states[:7])

# ---------- Project 1: button ----------
f = fresh_gpio()
import signal
ns, out = run(SCRIPTS / "button_led.py", patches=[(signal, "pause", lambda: None)])
btn, led = f.pin(27), f.pin(17)
btn.drive_low(); REAL_SLEEP(0.05); on = led.state
btn.drive_high(); REAL_SLEEP(0.05); off = led.state
check("button: LED on while held, off when released", on is True and off is False, (on, off))

# ---------- Project 2: climate logger ----------
home = Path(tempfile.mkdtemp())
fake_bme = types.ModuleType("bme280")
fake_bme.load_calibration_params = lambda bus, addr: {"addr": addr}
readings = iter([(21.43, 48.2, 1013.4), (21.6, 47.9, 1013.1), (22.04, 47.0, 1012.8)])
def sample(bus, addr, cal):
    t, h, p = next(readings)
    return types.SimpleNamespace(temperature=t, humidity=h, pressure=p)
fake_bme.sample = sample
fake_smbus = types.ModuleType("smbus2"); fake_smbus.SMBus = lambda n: ("bus", n)
sys.modules["bme280"], sys.modules["smbus2"] = fake_bme, fake_smbus
ns, out = run(SCRIPTS / "climate_logger.py", sleeps=stop_after(3), home=home)
rows = list(csv.reader(open(home / "climate.csv")))
check("climate logger: header + 3 rows, rounded", rows[0] == ["time", "temp_c", "humidity_pct", "pressure_hpa"] and len(rows) == 4 and rows[1][1:] == ["21.4", "48.2", "1013.4"], rows[:2])
check("climate logger: prints a readable line", "21.4 C" in out and "hPa" in out, out.splitlines()[0])
del sys.modules["bme280"], sys.modules["smbus2"]

# ---------- Project 2: chart ----------
with open(home / "climate.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["time", "temp_c", "humidity_pct", "pressure_hpa"])
    for i in range(60):
        w.writerow([f"2026-10-18T{10 + i // 60:02d}:{i % 60:02d}:00", 20 + i / 30, 50 - i / 20, 1013])
ns, out = run(SCRIPTS / "climate_chart.py", home=home)
png = home / "climate.png"
check("chart: PNG written from 60 readings", png.exists() and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and "60 readings" in out, out.strip())

# ---------- Project 3: plant alert ----------
import urllib.request
sent = []
def fake_urlopen(req, timeout=None):
    sent.append((req.full_url, req.data.decode(), dict(req.header_items())))
    return io.BytesIO(b"ok")
f = fresh_gpio()
seq = ["wet", "dry", "dry", "wet", "dry"]           # state before each check
def plant_sleep(i, sec):
    if i >= len(seq):
        raise Stop
    (f.pin(22).drive_high if seq[i] == "dry" else f.pin(22).drive_low)()
ns, out = run(SCRIPTS / "plant_alert.py", sleeps=plant_sleep, patches=[(urllib.request, "urlopen", fake_urlopen)])
check("plant: one alert per dry spell (2 alerts for wet,dry,dry,wet,dry)", len(sent) == 2, len(sent))
check("plant: alert goes to ntfy.sh/<topic> with a title", sent and sent[0][0].startswith("https://ntfy.sh/") and sent[0][2].get("Title") == "Plant alert", sent[:1])

# ---------- Project 4: motion camera ----------
home = Path(tempfile.mkdtemp())
fake_cam = types.ModuleType("picamera2")
class Picamera2:
    def create_still_configuration(self): return {"still": True}
    def configure(self, cfg): self.cfg = cfg
    def start(self): self.started = True
    def capture_file(self, path): Path(path).write_bytes(b"\xff\xd8fakejpeg")
fake_cam.Picamera2 = Picamera2
sys.modules["picamera2"] = fake_cam
f = fresh_gpio()
def motion_pause():                      # runs while the script is "waiting": simulate someone walking past
    REAL_SLEEP(0.3)
    f.pin(4).drive_high()
    for _ in range(40):
        if list((home / "motion-photos").glob("*.jpg")):
            break
        REAL_SLEEP(0.05)
    f.pin(4).drive_low()
ns, out = run(SCRIPTS / "motion_camera.py", home=home, patches=[(signal, "pause", motion_pause)])
photos = list((home / "motion-photos").glob("*.jpg"))
check("motion: a photo is saved when the PIR goes high", len(photos) == 1, [p.name for p in photos])
del sys.modules["picamera2"]

# ---------- Project 5: uptime_check.sh (real ping) ----------
home = Path(tempfile.mkdtemp())
env = dict(os.environ, HOME=str(home))
subprocess.run(["bash", str(SCRIPTS / "uptime_check.sh")], env=env, check=True)
subprocess.run(["bash", str(SCRIPTS / "uptime_check.sh")], env=env, check=True)
lines = (home / "uptime.csv").read_text().splitlines()
ok_line = len(lines) == 3 and lines[0] == "time,status,ms" and lines[1].split(",")[1] == "up" and float(lines[1].split(",")[2]) > 0
check("uptime: header once, then 'up' with a real ping time", ok_line, lines)
fakebin = Path(tempfile.mkdtemp())
(fakebin / "ping").write_text("#!/bin/sh\nexit 1\n"); (fakebin / "ping").chmod(0o755)
env2 = dict(env, PATH=str(fakebin) + ":" + os.environ["PATH"])
subprocess.run(["bash", str(SCRIPTS / "uptime_check.sh")], env=env2, check=True)
last = (home / "uptime.csv").read_text().splitlines()[-1]
check("uptime: writes 'down' when every target fails", last.endswith(",down,"), last)

# ---------- Project 5: outage report ----------
home = Path(tempfile.mkdtemp())
data = ["time,status,ms"]
pattern = ["up"] * 5 + ["down"] * 3 + ["up"] * 4 + ["down"] * 12 + ["up"] * 2 + ["down"] * 2
for i, st in enumerate(pattern):
    data.append(f"2026-10-18 09:{i:02d}:00,{st},{'12.3' if st == 'up' else ''}")
(home / "uptime.csv").write_text("\n".join(data) + "\n")
ns, out = run(SCRIPTS / "outage_report.py", home=home)
check("outages: 3 outages found (incl. one still ongoing)", "Outages: 3" in out, out.splitlines()[1] if out else out)
check("outages: durations 3, 12 and 1 min", "about 3 min" in out and "about 12 min" in out and "about 1 min" in out, out)
check("outages: uptime percentage", "up: 39.29 %" in out, out.splitlines()[0])

# ---------- Project 6: wifi watch ----------
work = Path(tempfile.mkdtemp()); shutil.copy(SCRIPTS / "wifi_watch.py", work / "wifi_watch.py")
scan_outputs = [
    "192.168.1.1\t00:11:22:33:44:55\tTP-LINK TECHNOLOGIES CO.,LTD.\n192.168.1.23\tAA:BB:CC:00:11:22\tApple, Inc.\n",
    "192.168.1.1\t00:11:22:33:44:55\tTP-LINK TECHNOLOGIES CO.,LTD.\n192.168.1.23\tAA:BB:CC:00:11:22\tApple, Inc.\n192.168.1.57\tde:ad:be:ef:00:01\t(Unknown: locally administered)\n",
]
def fake_run(cmd, **kw):
    assert cmd == ["/usr/sbin/arp-scan", "--localnet", "--plain"], cmd
    return types.SimpleNamespace(stdout=scan_outputs.pop(0), returncode=0)
sent.clear()
ns, out1 = run(work / "wifi_watch.py", patches=[(subprocess, "run", fake_run), (urllib.request, "urlopen", fake_urlopen)])
check("wifi: first run learns devices, sends no alert", len(sent) == 0 and "2 devices online, 2 known" in out1, out1.strip())
ns, out2 = run(work / "wifi_watch.py", patches=[(subprocess, "run", fake_run), (urllib.request, "urlopen", fake_urlopen)])
check("wifi: second run alerts once for the new device", len(sent) == 1 and "192.168.1.57" in sent[0][1] and "3 devices online, 3 known" in out2, (sent, out2.strip()))
check("wifi: MACs stored lower-case, one per line", (work / "known-devices.txt").read_text().split() == sorted(["00:11:22:33:44:55", "aa:bb:cc:00:11:22", "de:ad:be:ef:00:01"]))

# ---------- Project 12: battery monitor ----------
def jk_frame(cells_mv, volts_mv, amps_ma, soc):
    fr = bytearray(300); fr[0:4] = bytes([0x55, 0xAA, 0xEB, 0x90]); fr[4] = 0x02
    mask = 0
    for i, mv in enumerate(cells_mv):
        fr[6 + i * 2:8 + i * 2] = mv.to_bytes(2, "little"); mask |= 1 << i
    fr[70:74] = mask.to_bytes(4, "little")
    fr[150:154] = volts_mv.to_bytes(4, "little")
    fr[158:162] = amps_ma.to_bytes(4, "little", signed=True)
    fr[173] = soc
    fr[299] = sum(fr[:299]) & 0xFF
    return bytes(fr)

cells = [3725, 3731, 3728, 3719, 3740, 3733, 3722, 3729, 3735, 3727, 3724, 3730]
frame = jk_frame(cells, 44743, -5210, 67)
writes = []
class FakeDev:
    name = "JK_DEMO_PACK"
class FakeAdv:
    local_name = "JK_DEMO_PACK"
class Scanner:
    @staticmethod
    async def find_device_by_filter(fn, timeout=None):
        return FakeDev() if fn(FakeDev(), FakeAdv()) else None
class Client:
    def __init__(self, dev, timeout=None): self.cb = None
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def start_notify(self, char, cb): self.cb = cb
    async def write_gatt_char(self, char, data, response=None):
        writes.append(bytes(data))
        if data[4] == 0x96:                      # cell info request -> stream junk + frame in 20-byte packets
            stream = b"\x01\x02junk" + frame
            for i in range(0, len(stream), 20):
                self.cb(None, bytearray(stream[i:i + 20]))
fake_bleak = types.ModuleType("bleak"); fake_bleak.BleakScanner = Scanner; fake_bleak.BleakClient = Client
sys.modules["bleak"] = fake_bleak
real_async_sleep = asyncio.sleep
async def quick_sleep(s): await real_async_sleep(0)
ns, out = run(SCRIPTS / "battery_monitor.py", patches=[(asyncio, "sleep", quick_sleep)])
check("battery: requests device info (0x97) then cell info (0x96)", [w[4] for w in writes] == [0x97, 0x96], [hex(w[4]) for w in writes])
check("battery: command frame = AA 55 90 EB + code, byte-sum checksum", all(len(w) == 20 and w[:4] == bytes([0xAA, 0x55, 0x90, 0xEB]) and w[19] == sum(w[:19]) & 0xFF for w in writes))
check("battery: pack volts / amps / charge decoded", "Pack: 44.74 V  -5.21 A  charge 67 %" in out, out.strip())
check("battery: 12 cells, lowest 3.719, highest 3.740", "Cells: 12  lowest 3.719 V  highest 3.740 V" in out, out.strip())
check("battery: no low-cell warning at 3.7 V", "WARNING" not in out)
frame = jk_frame([3725, 3050, 3728], 9800, 0, 4); writes.clear()
ns, out = run(SCRIPTS / "battery_monitor.py", patches=[(asyncio, "sleep", quick_sleep)])
check("battery: warns when a cell is below 3.10 V", "WARNING: a cell is low" in out, out.strip())
class NoScanner:
    @staticmethod
    async def find_device_by_filter(fn, timeout=None): return None
fake_bleak.BleakScanner = NoScanner
ns, out = run(SCRIPTS / "battery_monitor.py", patches=[(asyncio, "sleep", quick_sleep)])
check("battery: friendly message when no battery is found", "Not found." in out, out.strip())

# ---------- summary ----------
bad = [r for r in results if not r[1]]
print(f"\n{len(results) - len(bad)} passed, {len(bad)} failed")
sys.exit(1 if bad else 0)
