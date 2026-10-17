#!/usr/bin/env python3
# Project 1: the LED lights while you hold the button.
from gpiozero import LED, Button
from signal import pause

led = LED(17)          # GPIO 17, physical pin 11
button = Button(27)    # GPIO 27, physical pin 13; other leg to GND

button.when_pressed = led.on
button.when_released = led.off

print("Press the button. Ctrl+C to stop.")
pause()                # wait for button events forever
