"""
Serial Streamer for Arduino Uno GRBL controller.
Supports sending G-code line-by-line, tracking progress, feed hold, resume,
manual jogging, pen lift testing, and origin zeroing.
"""

import os
import re
import glob
import time
import threading
import serial

class GRBLStreamer:
    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self.serial = None
        self.is_streaming = False
        self.is_paused = False
        self.should_stop = False
        self.total_lines = 0
        self.sent_lines = 0
        self.current_command = ""
        self.machine_state = "Disconnected"
        self.mpos = [0.0, 0.0, 0.0]
        self.wpos = [0.0, 0.0, 0.0]
        self.pen_down = False
        self.pen_down_cmd = "M5"
        self.pen_up_cmd = "M3 S90"
        self.log_messages = []
        self._lock = threading.Lock()
        self._thread = None

    @staticmethod
    def list_ports() -> list[str]:
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        by_id = glob.glob("/dev/serial/by-id/*")
        ports.extend(by_id)
        return sorted(list(set(ports)))

    def is_connected(self) -> bool:
        return self.serial is not None and self.serial.is_open

    def connect(self) -> bool:
        with self._lock:
            if self.is_connected():
                return True
            try:
                self.serial = serial.Serial(self.port, self.baud, timeout=1.0)
                time.sleep(2.0)  # Wait for Arduino auto-reset on DTR toggle
                boot = self.serial.read_all().decode("utf-8", errors="replace")
                self._log(f"Connected to {self.port}: {boot.strip() or 'GRBL ready'}")
                self.machine_state = "Idle"
                return True
            except Exception as e:
                self._log(f"Connection failed to {self.port}: {e}")
                self.serial = None
                self.machine_state = "Disconnected"
                return False

    def disconnect(self):
        self.stop()
        with self._lock:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.close()
                except Exception:
                    pass
            self.serial = None
            self.machine_state = "Disconnected"
            self._log("Disconnected from serial port")

    def _log(self, msg: str):
        self.log_messages.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(self.log_messages) > 120:
            self.log_messages.pop(0)

    @staticmethod
    def clean_line(raw_line: str) -> str:
        """Strip comments and whitespace according to NIST RS274NGC standards."""
        # Strip semicolon comments (; ...)
        line = raw_line.split(";")[0]
        # Strip parenthesis comments ((...))
        line = re.sub(r"\(.*?\)", "", line)
        return line.strip()

    def send_command(self, cmd: str, timeout: float = 10.0) -> str:
        """Send a single G-code command or real-time query and wait for ok/error."""
        if not self.connect():
            return "ERROR: Not connected"

        with self._lock:
            try:
                # Real-time single byte commands don't require newline
                if cmd in ["?", "!", "~", "\x18"]:
                    self.serial.write(cmd.encode("utf-8"))
                    time.sleep(0.05)
                    resp = self.serial.read_all().decode("utf-8", errors="replace").strip()
                    self._parse_status_report(resp)
                    return resp

                clean = self.clean_line(cmd)
                if not clean:
                    return "ok"

                self.serial.write((clean + "\n").encode("utf-8"))
                start_time = time.time()
                collected = []

                while time.time() - start_time < timeout:
                    resp_line = self.serial.readline().decode("utf-8", errors="replace").strip()
                    if not resp_line:
                        continue
                    collected.append(resp_line)
                    if resp_line == "ok" or resp_line.startswith("error:"):
                        break

                full_resp = "\n".join(collected)
                if not collected:
                    return "TIMEOUT"
                return full_resp
            except Exception as e:
                self._log(f"Send command '{cmd}' error: {e}")
                return f"ERROR: {e}"

    def _parse_status_report(self, report: str):
        """Parse GRBL '?' status response like <Idle,MPos:0.000,0.000,0.000,WPos:0.000,0.000,0.000>"""
        if not report:
            return
        state_match = re.search(r'<(\w+)[,>]', report)
        if state_match:
            self.machine_state = state_match.group(1)

        wpos_match = re.search(r'WPos:([-\d\.]+),([-\d\.]+),([-\d\.]+)', report)
        mpos_match = re.search(r'MPos:([-\d\.]+),([-\d\.]+),([-\d\.]+)', report)

        if mpos_match:
            try:
                self.mpos = [float(x) for x in mpos_match.groups()]
            except Exception:
                pass

        if wpos_match:
            try:
                self.wpos = [float(x) for x in wpos_match.groups()]
            except Exception:
                pass
        elif mpos_match and not wpos_match:
            self.wpos = list(self.mpos)

    def jog(self, dx: float, dy: float, feed: int = 1500) -> bool:
        """Jog the machine relative to current position."""
        res1 = self.send_command(f"G91 G0 X{dx:.2f} Y{dy:.2f} F{feed}")
        res2 = self.send_command("G90")
        # Query immediate position after jog
        self.send_command("?")
        self._log(f"Jog X{dx:+.1f} Y{dy:+.1f} mm -> {res1}")
        return "ok" in res1

    def move_to(self, x: float, y: float, feed: int = 3500) -> bool:
        """Move pen carriage directly to an absolute (X, Y) coordinate in mm with pen up."""
        if self.is_streaming:
            self._log("Cannot move to point: Machine is busy plotting")
            return False

        # Ensure pen is lifted before rapid move
        if self.pen_down:
            self.pen_test(False)

        res1 = self.send_command("G90")  # Absolute mode
        res2 = self.send_command(f"G0 X{x:.2f} Y{y:.2f} F{feed}")
        self.send_command("?")  # Query live status
        self._log(f"Touch-to-Move -> X{x:.2f} Y{y:.2f} mm -> {res2}")
        return "ok" in res2

    def pen_test(self, down: bool) -> bool:
        """Test pen lift servo."""
        self.pen_down = down
        cmd = self.pen_down_cmd if down else self.pen_up_cmd
        res = self.send_command(cmd)
        self.send_command("G4 P0.2")  # dwell to let servo reach position
        self._log(f"Pen {'DOWN' if down else 'UP'} ({cmd}) -> {res}")
        return "ok" in res

    def set_zero(self) -> bool:
        """Set current head position as work origin (0, 0, 0)."""
        res = self.send_command("G92 X0 Y0 Z0")
        self.wpos = [0.0, 0.0, 0.0]
        self._log(f"Origin Zero Set (G92 X0 Y0 Z0) -> {res}")
        return "ok" in res

    def unlock(self) -> bool:
        """Unlock GRBL from Alarm lock state."""
        res = self.send_command("$X")
        self._log(f"GRBL Alarm Unlock ($X) -> {res}")
        return "ok" in res

    def start_stream(self, gcode_text: str) -> bool:
        if self.is_streaming:
            return False
        if not self.connect():
            return False

        # Clean and extract all non-empty lines
        raw_lines = gcode_text.splitlines()
        clean_lines = []
        for l in raw_lines:
            c = self.clean_line(l)
            if c:
                clean_lines.append(c)

        if not clean_lines:
            self._log("No valid G-code lines to stream")
            return False

        self.total_lines = len(clean_lines)
        self.sent_lines = 0
        self.is_streaming = True
        self.is_paused = False
        self.should_stop = False

        self._thread = threading.Thread(target=self._stream_worker, args=(clean_lines,), daemon=True)
        self._thread.start()
        return True

    def _stream_worker(self, lines: list[str]):
        self._log(f"Starting plot streaming ({len(lines)} executable commands)...")
        # Ensure machine is unlocked before streaming
        self.unlock()

        try:
            for line in lines:
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)

                if self.should_stop:
                    self._log("Streaming aborted by user")
                    break

                if self.pen_down_cmd and self.pen_down_cmd in line:
                    self.pen_down = True
                elif self.pen_up_cmd and self.pen_up_cmd in line:
                    self.pen_down = False
                elif "M5" in line:
                    self.pen_down = True
                elif "M3" in line:
                    self.pen_down = False

                self.current_command = line
                with self._lock:
                    self.serial.write((line + "\n").encode("utf-8"))

                    # Wait for 'ok' or 'error:' response (handling notices like [Pgm End])
                    resp = ""
                    start_t = time.time()
                    while time.time() - start_t < 30.0:  # 30-sec safety timeout for long moves
                        r = self.serial.readline().decode("utf-8", errors="replace").strip()
                        if not r:
                            continue
                        if r == "ok" or r.startswith("error:"):
                            resp = r
                            break
                        else:
                            # Informational message (e.g. [Pgm End])
                            self._log(f"GRBL notice: {r}")

                if "error" in resp.lower():
                    self._log(f"GRBL warning on '{line}': {resp}")
                elif not resp:
                    self._log(f"GRBL timeout on '{line}'")

                self.sent_lines += 1

                # Periodically query live position during stream
                if self.sent_lines % 5 == 0:
                    with self._lock:
                        try:
                            self.serial.write(b"?")
                            time.sleep(0.02)
                            s_rep = self.serial.read_all().decode("utf-8", errors="replace")
                            self._parse_status_report(s_rep)
                        except Exception:
                            pass

            self._log("Streaming completed successfully!")
            # Lift pen at finish
            self.send_command(self.pen_up_cmd)
            self.pen_down = False
        except Exception as e:
            self._log(f"Streaming error: {e}")
        finally:
            self.is_streaming = False
            self.current_command = ""

    def pause(self):
        self.is_paused = True
        if self.serial and self.serial.is_open:
            self.serial.write(b"!")  # GRBL feed hold
        self._log("Plot Paused (Feed Hold)")

    def resume(self):
        self.is_paused = False
        if self.serial and self.serial.is_open:
            self.serial.write(b"~")  # GRBL cycle start
        self._log("Plot Resumed (Cycle Start)")

    def stop(self):
        self.should_stop = True
        self.is_paused = False
        self.pen_down = False
        if self.serial and self.serial.is_open:
            try:
                self.serial.write(b"\x18")  # Ctrl-X Soft Reset
                time.sleep(0.1)
                self.serial.write(f"{self.pen_up_cmd}\n".encode("utf-8"))   # Ensure pen up
            except Exception:
                pass
        self._log("Plot Aborted & Reset")

    def get_status(self) -> dict:
        progress_pct = (self.sent_lines / self.total_lines * 100.0) if self.total_lines > 0 else 0.0
        # Quick query if connected and not in tight loop
        if self.is_connected() and not self.is_streaming:
            try:
                self.send_command("?")
            except Exception:
                pass

        return {
            "connected": self.is_connected(),
            "port": self.port,
            "machine_state": self.machine_state,
            "mpos": self.mpos,
            "wpos": self.wpos,
            "pen_down": self.pen_down,
            "available_ports": self.list_ports(),
            "is_streaming": self.is_streaming,
            "is_paused": self.is_paused,
            "total_lines": self.total_lines,
            "sent_lines": self.sent_lines,
            "progress_percent": round(progress_pct, 1),
            "current_command": self.current_command,
            "logs": list(self.log_messages)
        }

streamer_instance = GRBLStreamer()
