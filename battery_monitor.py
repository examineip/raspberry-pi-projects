#!/usr/bin/env python3
# Project 12: read a JK BMS battery over Bluetooth, print the essentials.
import asyncio

from bleak import BleakClient, BleakScanner

CHAR = "0000ffe1-0000-1000-8000-00805f9b34fb"
HEADER = bytes([0x55, 0xAA, 0xEB, 0x90])
LOW_CELL = 3.10          # warn below this many volts per cell


def command(code):
    frame = bytearray(20)              # AA 55 90 EB <code>, then checksum
    frame[0:4] = bytes([0xAA, 0x55, 0x90, 0xEB])
    frame[4] = code
    frame[19] = sum(frame[:19]) & 0xFF
    return bytes(frame)


def num(frame, at, size, signed=False):
    return int.from_bytes(frame[at:at + size], "little", signed=signed)


def decode(frame):                     # a 300-byte cell-info frame
    mask = num(frame, 70, 4)
    cells = [num(frame, 6 + i * 2, 2) / 1000
             for i in range(32) if mask & (1 << i)]
    return {"volts": num(frame, 150, 4) / 1000,
            "amps": num(frame, 158, 4, signed=True) / 1000,
            "charge": frame[173],
            "cells": cells}


async def main():
    print("Looking for a JK battery (15 s)...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: (ad.local_name or d.name or "").upper().startswith("JK"),
        timeout=15)
    if device is None:
        print("Not found. Turn Bluetooth off on your phone and move closer.")
        return
    buf, done, result = bytearray(), asyncio.Event(), {}

    def on_data(_, data):
        buf.extend(data)
        start = buf.find(HEADER)
        if start < 0 or len(buf) - start < 300:
            return
        frame = bytes(buf[start:start + 300])
        del buf[:start + 300]
        if frame[4] == 0x02 and sum(frame[:299]) & 0xFF == frame[299]:
            result.update(decode(frame))
            done.set()

    async with BleakClient(device, timeout=30) as client:
        await client.start_notify(CHAR, on_data)
        await client.write_gatt_char(CHAR, command(0x97), response=False)
        await asyncio.sleep(1)
        await client.write_gatt_char(CHAR, command(0x96), response=False)
        await asyncio.wait_for(done.wait(), 20)

    cells = result["cells"]
    print(f"Pack: {result['volts']:.2f} V  {result['amps']:+.2f} A  "
          f"charge {result['charge']} %")
    print(f"Cells: {len(cells)}  lowest {min(cells):.3f} V  "
          f"highest {max(cells):.3f} V")
    if min(cells) < LOW_CELL:
        print("WARNING: a cell is low. Charge the battery.")


asyncio.run(main())
