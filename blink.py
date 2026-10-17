#!/usr/bin/env python3
# Project 1: blink an LED on GPIO 17 (physical pin 11).
from gpiozero import LED
from time import sleep

led = LED(17)

while True:
    led.on()
    sleep(0.5)
    led.off()
    sleep(0.5)
