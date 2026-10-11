import serial
import time
import sys

PORT = "/dev/ttyUSB0"
BAUD = 115200

def run_diagnostic():
    print(f"Connecting to {PORT} at {BAUD}...")
    with serial.Serial(PORT, BAUD, timeout=1.5) as s:
        time.sleep(2.0)
        boot = s.read_all().decode(errors="replace")
        print("BOOT:", boot.strip())

        def send(cmd, delay=0.5):
            print(f" -> SEND: {cmd}")
            s.write((cmd + "\n").encode())
            time.sleep(delay)
            resp = s.read_all().decode(errors="replace").strip()
            print(f" <- RECV: {resp}")
            return resp

        # 1. Status Check
        send("?")
        send("$G")

        # 2. Test Pen Lift (Servo PWM commands M3/M5)
        print("\n=== Testing Pen Lift (Servo PWM M3/M5) ===")
        print("Activating Pen Down (M3 S90)...")
        send("M3 S90", delay=1.0)
        send("?")
        
        print("Activating Pen Up (M5)...")
        send("M5", delay=1.0)
        send("?")

        # 3. Test Micro-Jog (2mm gentle move and return)
        print("\n=== Testing Gentle 2mm Motion (X & Y) ===")
        print("Moving +2mm on X and Y in relative mode...")
        send("G91 G0 X2.0 Y2.0 F1000", delay=0.8)
        send("?")
        
        print("Returning -2mm to original position...")
        send("G0 X-2.0 Y-2.0 F1000", delay=0.8)
        send("G90", delay=0.3)
        send("?")

        print("\nDiagnostic complete! Final state:")
        send("?")

if __name__ == "__main__":
    run_diagnostic()
