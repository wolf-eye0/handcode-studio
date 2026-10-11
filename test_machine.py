#!/usr/bin/env python3
"""
Interactive / Diagnostic Controller for Arduino Handwriting Machine (GRBL 0.9i)
Port: /dev/ttyUSB0 @ 115200 baud
"""

import sys
import time
import serial

PORT = "/dev/ttyUSB0"
BAUD = 115200

def connect():
    print(f"Connecting to {PORT} at {BAUD} baud...")
    try:
        s = serial.Serial(PORT, BAUD, timeout=1.5)
        time.sleep(2.0)  # Wait for Arduino reset
        boot = s.read_all().decode('utf-8', errors='replace').strip()
        print(f"Connected! Firmware banner:\n{boot}\n")
        return s
    except Exception as e:
        print(f"Error opening {PORT}: {e}")
        sys.exit(1)

def send(s, cmd):
    cmd = cmd.strip()
    s.write((cmd + "\n").encode('utf-8'))
    time.sleep(0.15)
    resp = s.read_all().decode('utf-8', errors='replace').strip()
    print(f"[{cmd}] -> {resp}")
    return resp

def main():
    s = connect()
    
    print("Commands:")
    print("  ?          : Query machine position / state")
    print("  $$         : Show all GRBL settings")
    print("  pen_up     : Lift pen (M5 / G0 Z5)")
    print("  pen_down   : Lower pen (M3 S90 / G0 Z0)")
    print("  zero       : Set current position as origin (G92 X0 Y0 Z0)")
    print("  move X Y   : Rapid move to X, Y (e.g. 'move 10 20')")
    print("  exit / q   : Quit")
    print("-" * 50)
    
    try:
        while True:
            cmd = input("grbl> ").strip()
            if not cmd:
                continue
            if cmd in ["exit", "q", "quit"]:
                break
            elif cmd == "pen_up":
                send(s, "M5")
                send(s, "G0 Z5")
            elif cmd == "pen_down":
                send(s, "M3 S90")
                send(s, "G0 Z0")
            elif cmd == "zero":
                send(s, "G92 X0 Y0 Z0")
            elif cmd.startswith("move "):
                parts = cmd.split()
                if len(parts) >= 3:
                    x, y = parts[1], parts[2]
                    send(s, f"G0 X{x} Y{y}")
            else:
                send(s, cmd)
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        s.close()

if __name__ == "__main__":
    main()
