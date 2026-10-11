# Handwriting Machine Specification & GRBL Configuration

## 1. Board & Controller
* **Microcontroller:** Atmel ATmega328P (16 MHz)
* **USB Interface:** QinHeng Electronics CH340C (`1a86:7523`)
* **Serial Port:** `/dev/ttyUSB0` (Symlink: `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`)
* **Communication Baud Rate:** `115200`
* **Firmware:** GRBL 0.9i (`[0.9i.20150620:]`)

---

## 2. Machine Geometry & Working Area Limits
From extracted GRBL EEPROM settings:
* **X-Axis Maximum Travel:** **200.00 mm** (~7.87 inches)
* **Y-Axis Maximum Travel:** **200.00 mm** (~7.87 inches)
* **Z-Axis Maximum Travel:** **200.00 mm**
* **Work Area:** **200 mm × 200 mm** (Square bed suitable for A5 / standard notebook / letter envelopes)

---

## 3. Motion & Kinematics Calibration
* **X-Axis Step Resolution:** `81.800` steps/mm
* **Y-Axis Step Resolution:** `81.800` steps/mm
  * *Transmission:* Standard GT2 timing belt (2mm pitch) with 16T/20T pulley driven at 1/16 microstepping.
* **Z-Axis Step Resolution:** `250.000` steps/mm
  * *Transmission:* M8 threaded rod / T8 leadscrew OR calibrated servo angle translation.
* **Maximum Feed Rates:**
  * X Max Rate: `5000.000` mm/min (83.3 mm/s)
  * Y Max Rate: `5000.000` mm/min (83.3 mm/s)
  * Z Max Rate: `3000.000` mm/min (50.0 mm/s)
* **Acceleration:**
  * X Acceleration: `150.000` mm/s²
  * Y Acceleration: `150.000` mm/s²
  * Z Acceleration: `500.000` mm/s²

---

## 4. Pin Mapping (Standard GRBL 0.9 on Arduino Uno / CNC Shield V3)

| Function | Arduino Uno Pin | Port / Register | CNC Shield V3 Header | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **X Step** | `D2` | PORTD 2 | X.STEP | Pulse width 10 µs |
| **Y Step** | `D3` | PORTD 3 | Y.STEP | Pulse width 10 µs |
| **Z Step** | `D4` | PORTD 4 | Z.STEP | Pulse width 10 µs |
| **X Direction** | `D5` | PORTD 5 | X.DIR | **Inverted** (`$3=3`) |
| **Y Direction** | `D6` | PORTD 6 | Y.DIR | **Inverted** (`$3=3`) |
| **Z Direction** | `D7` | PORTD 7 | Z.DIR | Normal |
| **Stepper Enable** | `D8` | PORTB 0 | EN | Active LOW (`$4=0`) |
| **X Limit Switch** | `D9` | PORTB 1 | X+ / X- | Normally Open (`$5=0`) |
| **Y Limit Switch** | `D10` | PORTB 2 | Y+ / Y- | Normally Open (`$5=0`) |
| **Z Limit Switch** | `D12` | PORTB 4 | Z+ / Z- | Moved to D12 in GRBL 0.9 |
| **Pen Servo / Spindle PWM** | `D11` | PORTB 3 | SpinEn / Z+ (v3 swap) | Timer2 PWM for Pen Lift |
| **Abort / Reset** | `A0` | PORTC 0 | Reset / Abort | |
| **Feed Hold** | `A1` | PORTC 1 | Hold | |
| **Cycle Start / Resume** | `A2` | PORTC 2 | Resume | |
| **Coolant / Pen Aux** | `A3` | PORTC 3 | CoolEn | |
| **Probe** | `A5` | PORTC 5 | SCL / Probe | |

---

## 5. Inversion Masks & Flags
* `$2 = 0` (00000000): Step pulse port invert mask.
* `$3 = 3` (00000011): Direction port invert mask (X and Y inverted, Z normal).
* `$4 = 0`: Stepper driver enable is active-low (A4988 / DRV8825 standard).
* `$5 = 0`: Limit pins active-high / normally-open.
* `$6 = 0`: Probe pin active-low.
* `$20 = 0`: Soft limits disabled.
* `$21 = 0`: Hard limits disabled.
* `$22 = 0`: Homing cycle disabled.

---

## 6. Complete Extracted Settings Dump
```text
$0=10 (step pulse, usec)
$1=25 (step idle delay, msec)
$2=0 (step port invert mask:00000000)
$3=3 (dir port invert mask:00000011)
$4=0 (step enable invert, bool)
$5=0 (limit pins invert, bool)
$6=0 (probe pin invert, bool)
$10=3 (status report mask:00000011)
$11=0.010 (junction deviation, mm)
$12=0.002 (arc tolerance, mm)
$13=0 (report inches, bool)
$20=0 (soft limits, bool)
$21=0 (hard limits, bool)
$22=0 (homing cycle, bool)
$23=0 (homing dir invert mask:00000000)
$24=25.000 (homing feed, mm/min)
$25=500.000 (homing seek, mm/min)
$26=250 (homing debounce, msec)
$27=1.000 (homing pull-off, mm)
$100=81.800 (x, step/mm)
$101=81.800 (y, step/mm)
$102=250.000 (z, step/mm)
$110=5000.000 (x max rate, mm/min)
$111=5000.000 (y max rate, mm/min)
$112=3000.000 (z max rate, mm/min)
$120=150.000 (x accel, mm/sec^2)
$121=150.000 (y accel, mm/sec^2)
$122=500.000 (z accel, mm/sec^2)
$130=200.000 (x max travel, mm)
$131=200.000 (y max travel, mm)
$132=200.000 (z max travel, mm)
```
