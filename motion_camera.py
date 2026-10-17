#!/usr/bin/env python3
# Project 4: take a photo whenever the PIR sensor sees movement.
from datetime import datetime
from pathlib import Path
from signal import pause

from gpiozero import MotionSensor
from picamera2 import Picamera2

PHOTOS = Path.home() / "motion-photos"
PHOTOS.mkdir(exist_ok=True)

pir = MotionSensor(4)              # PIR OUT -> GPIO 4, pin 7
camera = Picamera2()
camera.configure(camera.create_still_configuration())
camera.start()


def snap():
    name = PHOTOS / datetime.now().strftime("%Y-%m-%d_%H-%M-%S.jpg")
    camera.capture_file(str(name))
    print("Motion! Saved", name)


pir.when_motion = snap
print("Watching for motion. Ctrl+C to stop.")
pause()
