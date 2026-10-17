#!/usr/bin/env python3
# Project 3: send a phone alert when the soil dries out.
import urllib.request
from time import sleep

from gpiozero import DigitalInputDevice

TOPIC = "plants-change-me-7f3k9q"   # make yours long and random
CHECK_EVERY = 600                   # seconds (10 minutes)

sensor = DigitalInputDevice(22)     # module DO -> GPIO 22, pin 15


def notify(message):
    request = urllib.request.Request(
        "https://ntfy.sh/" + TOPIC,
        data=message.encode(),
        headers={"Title": "Plant alert"})
    urllib.request.urlopen(request, timeout=10)


alerted = False
while True:
    dry = sensor.value == 1   # most modules: DO is HIGH when dry
    if dry and not alerted:
        notify("The soil is dry. Time to water the plant.")
        print("Dry: alert sent")
        alerted = True
    elif not dry and alerted:
        print("Watered again")
        alerted = False
    sleep(CHECK_EVERY)
