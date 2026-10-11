# Handcode Studio — CNC Handwriting & OCR Plotter

A modern AI-powered handwriting synthesis and CNC plotter application tailored for **Arduino Uno (CH340C) + GRBL 0.9i**.

---

## 🌟 Key Features

1. **Multi-Format Ingestion & OCR:**
   - **Images:** Scanned notes or photos extracted via Tesseract OCR (`.png`, `.jpg`, `.jpeg`, `.webp`).
   - **PDFs:** Text extraction via Poppler `pdftotext` with automated OCR fallback for scanned PDFs.
   - **Word Documents:** Microsoft Word `.docx` parsing.
   - **Direct Text:** Real-time editable text box with live character and word counters.

2. **Accurate Paper & Notebook Templates:**
   - **Kokuyo Camlin Small Single-Line (`155 × 190 mm`):**
     - Calibrated for 8.0 mm single-line notebook ruling.
     - 25 mm left margin with authentic red margin line.
     - 28 mm top header margin with header rule.
   - **A4 Standard Plain Sheet (`210 × 297 mm`):** Full-size A4 drawing area.
   - **A4 Ruled Notebook (`210 × 297 mm`):** 8.5 mm rule spacing with margins.
   - **Square Machine Bed (`200 × 200 mm`):** Matches the GRBL EEPROM envelope.
   - **A5 Lined Notebook (`148 × 210 mm`):** 7.5 mm rule spacing.
   - **⚙️ Custom Configuration Drawer:** Full live control over page width, height, margins, and line spacing.

3. **Handcode AI Neural Handwriting Engine:**
   - **9 Distinct Human Handwriting Styles** powered by Calligrapher RNN (Alex Graves synthesis).
   - **Natural Cursive Connections & Variations:** Letters flow seamlessly with authentic human slant, subtle baseline jitter, and stroke dynamics.
   - **Adjustable Legibility Bias:** Tune handwriting from neat and structured (high bias) to relaxed and casual (lower bias).
   - **Multiple Ink Types:** Notebook Blue, Dark Fountain Pen, Gel Pen Black, Graphite.

4. **Multi-Page Layout & Live Visual Plotter:**
   - Automated pagination that splits long texts or documents across multiple pages.
   - Interactive SVG canvas with real-time preview of handwritten strokes, notebook rules, and pen-up rapid paths.
   - Page switcher (`◀ Page 1 of N ▶`) with thumbnail tabs.
   - Real-time job metrics: total pen path distance (meters) and estimated plotting time.

5. **Paper Continuation & Selection Marking:**
   - Test-run a few words on paper, mark them as written (highlighted in emerald green `🟢`), and append new text (in notebook blue `🖊️`).
   - **Skip Written Mode (`⏭️`):** Plotter starts plotting directly from unwritten parts without re-writing or scratching existing ink.
   - Mark via **Mark Selection**, **Mark to Cursor**, **Mark All**, or interactive **Word Stepper**.

6. **Interactive Touch Coordination & Direct Resume:**
   - **👆 Touch to Move:** Click or tap anywhere on the virtual page to drive the physical pen directly to that coordinate.
   - **🎯 Direct Resume (No (0,0) Homing):** When you align the pen at the starting of your notebook using touch-to-move, the machine resumes plotting directly from there to the writing point without traveling back to (0,0) home every time.
   - **📍 Live Pen Tip HUD:** Real-time crosshair reticle tracking current machine coordinates (`X`, `Y`) and pen state (`UP`/`DOWN`).

7. **📖 Lab Record Mode (180° Inverted Physical Plot):**
   - Rotates machine motion 180° for bound notebooks and lab records where the binding obstructs the machine rails.
   - Virtual page preview stays right-side up while the physical machine plots inverted so notebook pages can be placed upside-down next to the rails.

8. **Machine & G-Code Export:**
   - **Single Page or Multi-Page:** Download G-code for a single page or a combined multi-page file with `M0` pause commands for changing paper.
   - **Pen Lift Modes:**
     - **Servo PWM (M5 Down / M3 S90 Up):** Tailored for pen lift micro-servos (pin D11 on CNC Shield v3) with one-click swap button.
     - **Z-Axis (G0 / G1):** For leadscrew or linear slide mechanisms.
   - **Direct Machine Streamer:** Connect and plot directly to `/dev/ttyUSB0` with live progress tracking, pause, and abort controls.

---

## 🚀 How to Run

1. Start the web server:
   ```bash
   python3 server.py 8080
   ```

2. Open in your browser:
   👉 **`http://localhost:8080`**

3. Run verification test suite:
   ```bash
   python3 -B test_suite.py
   ```

4. Run hardware diagnostics over serial:
   ```bash
   python3 test_machine.py
   ```
