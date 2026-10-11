"""
Comprehensive verification test suite for Handcode Studio.
Tests upright orientation, baseline alignment, multi-template pagination,
G-code generation, and API server endpoints.
"""

import unittest
import numpy as np
from engine.handwriting import generate_word_strokes, clean_word, get_word_metrics, get_word_baseline_factor, _WORD_STROKE_CACHE
from engine.paginator import paginate_and_render, TEMPLATES
from engine.gcode import generate_gcode

class TestHandwritingOrientation(unittest.TestCase):
    def setUp(self):
        _WORD_STROKE_CACHE.clear()

    def test_ascender_descender_upright_orientation(self):
        """
        Verify that in the rendered SVG output:
        - Baseline of lowercase characters without descenders is at the ruled line Y (current_y)
        - Ascenders and capital letters have SVG Y < current_y (higher up on the page)
        - Descenders ('g', 'y', 'p', 'q', 'j') have SVG Y > current_y (hang below ruled line)
        """
        template = TEMPLATES["kokuyo_camlin_small"]
        baseline_y = template["margin_top"] # 28.0 mm
        font_size = template["font_size"]   # 5.2 mm

        # Render word with ascender: 'The'
        pages_asc = paginate_and_render("The", template)
        pts_asc = np.array(pages_asc[0]["strokes_points"])
        y_pts_asc = pts_asc[:, 1]
        
        # Ascender top should reach up to approx baseline_y - font_size
        self.assertLess(y_pts_asc.min(), baseline_y - (font_size * 0.7),
                        f"Ascender top {y_pts_asc.min()} should be well above baseline {baseline_y}")
        # Baseline should be at approx baseline_y (+/- 1.0mm)
        self.assertAlmostEqual(y_pts_asc.max(), baseline_y, delta=1.0,
                               msg=f"Baseline of 'The' {y_pts_asc.max()} should sit near ruled line {baseline_y}")

        # Render word with descender: 'flying'
        pages_desc = paginate_and_render("flying", template)
        pts_desc = np.array(pages_desc[0]["strokes_points"])
        y_pts_desc = pts_desc[:, 1]

        # Descender bottom should hang below baseline_y
        self.assertGreater(y_pts_desc.max(), baseline_y + 0.5,
                           f"Descender bottom {y_pts_desc.max()} should extend below baseline {baseline_y}")
        # Ascender 'f' / 'l' should reach above baseline_y
        self.assertLess(y_pts_desc.min(), baseline_y - (font_size * 0.7),
                        f"Ascender of 'flying' {y_pts_desc.min()} should reach above baseline {baseline_y}")

    def test_multi_line_vertical_ordering(self):
        """
        Verify that line 2 sits below line 1 and both lines are upright.
        """
        template = TEMPLATES["kokuyo_camlin_small"]
        text = "First line here\nSecond line follows"
        pages = paginate_and_render(text, template)
        self.assertEqual(len(pages), 1)

        # SVG draw_path should be non-empty and well-formed
        draw_path = pages[0]["draw_path"]
        self.assertTrue(draw_path.startswith("M "))
        self.assertIn(" L ", draw_path)

        # Check line 1 vs line 2 coordinates
        pts = np.array(pages[0]["strokes_points"])
        line1_pts = pts[pts[:, 1] < 32.0]
        line2_pts = pts[pts[:, 1] >= 32.0]

        self.assertGreater(len(line1_pts), 0)
        self.assertGreater(len(line2_pts), 0)

        # Line 1 mean Y should be around 26-28mm, Line 2 mean Y around 34-36mm
        self.assertLess(line1_pts[:, 1].mean(), line2_pts[:, 1].mean())

    def test_all_templates(self):
        """Verify all template presets render without exceptions."""
        for t_name, t_cfg in TEMPLATES.items():
            pages = paginate_and_render("Quick test on template", t_cfg)
            self.assertGreaterEqual(len(pages), 1, f"Failed on template {t_name}")
            self.assertGreater(pages[0]["words_count"], 0)
            self.assertGreater(pages[0]["draw_distance_mm"], 0.0)

    def test_all_styles(self):
        """Verify handwriting styles 1 through 9 work cleanly."""
        template = TEMPLATES["kokuyo_camlin_small"]
        for st in range(1, 10):
            pages = paginate_and_render("Style test", template, style=st)
            self.assertEqual(len(pages), 1)
            self.assertGreater(len(pages[0]["strokes_points"]), 0)

    def test_edge_cases_empty_and_special_characters(self):
        """Empty input, whitespace, punctuation, numbers."""
        template = TEMPLATES["kokuyo_camlin_small"]
        
        # Empty input
        pages_empty = paginate_and_render("", template)
        self.assertGreaterEqual(len(pages_empty), 1)
        
        # Numbers & symbols
        pages_sym = paginate_and_render("12345 !?.,:; -+=$#@", template)
        self.assertGreaterEqual(len(pages_sym), 1)
        self.assertGreater(len(pages_sym[0]["strokes_points"]), 0)

        # Word metrics character anatomy validation for digits
        w_top, w_mid, w_bot = get_word_metrics("12345")
        self.assertEqual(w_top, 0.5, "Digits should be recognized as full capital/ascender height")
        self.assertEqual(w_mid, 1.0)
        self.assertEqual(w_bot, 0.0)

class TestGCodeGeneration(unittest.TestCase):
    def test_gcode_servo_and_z_axis(self):
        template = TEMPLATES["kokuyo_camlin_small"]
        pages = paginate_and_render("G-Code Machine Test", template)

        # Test Servo mode
        gc_servo = generate_gcode(pages, pen_mode="servo", pen_down_cmd="M3 S90", pen_up_cmd="M5")
        self.assertIn("M3 S90", gc_servo)
        self.assertIn("M5", gc_servo)
        self.assertIn("G21", gc_servo)
        self.assertIn("M2", gc_servo)

        # Test Z-Axis mode
        gc_z = generate_gcode(pages, pen_mode="z_axis", z_down_pos=0.0, z_up_pos=5.0)
        self.assertIn("Z0.00", gc_z)
        self.assertIn("Z5.00", gc_z)

    def test_gcode_default_servo_commands_flipped(self):
        """Verify default servo commands are flipped: M5 for pen down (drawing) and M3 S90 for pen up (travel)."""
        template = TEMPLATES["kokuyo_camlin_small"]
        pages = paginate_and_render("Test Default Servo", template)
        gc = generate_gcode(pages)
        # Default pen down is M5
        self.assertIn("M5", gc)
        # Default pen up is M3 S90
        self.assertIn("M3 S90", gc)

    def test_gcode_invert_y(self):
        template = TEMPLATES["kokuyo_camlin_small"]
        pages = paginate_and_render("Invert Y Test", template)

        gc_normal = generate_gcode(pages, invert_y=False)
        gc_inverted = generate_gcode(pages, invert_y=True)

        self.assertNotEqual(gc_normal, gc_inverted)

    def test_gcode_lab_record_mode_180_inversion(self):
        """
        Verify that in Lab Record Mode:
        - X is inverted: actual_x = width - x
        - Y is inverted 180 degrees:
          if invert_y=False: actual_y = height - y
          if invert_y=True:  actual_y = y
        - Coordinates stay positive and within paper boundaries.
        """
        template = TEMPLATES["kokuyo_camlin_small"]
        width = template["width"]    # 155.0 mm
        height = template["height"]  # 190.0 mm
        pages = paginate_and_render("Lab Record Test", template)

        # Standard normal mode G-code
        gc_normal = generate_gcode(pages, invert_y=False, flip_lab_record=False)
        # Lab Record Mode G-code
        gc_lab = generate_gcode(pages, invert_y=False, flip_lab_record=True)

        self.assertIn("; Mode: LAB RECORD (180° Inverted Physical Plot)", gc_lab)
        self.assertNotIn("LAB RECORD", gc_normal)

        # Parse coordinate moves
        import re
        def extract_coords(gc_text):
            coords = []
            for line in gc_text.splitlines():
                m = re.search(r'(?:G0|G1)\s+X([\d\.]+)\s+Y([\d\.]+)', line)
                if m:
                    coords.append((float(m.group(1)), float(m.group(2))))
            return coords

        normal_coords = extract_coords(gc_normal)
        lab_coords = extract_coords(gc_lab)

        self.assertGreater(len(normal_coords), 5)
        self.assertEqual(len(normal_coords), len(lab_coords))

        for (nx, ny), (lx, ly) in zip(normal_coords, lab_coords):
            # If nx=0 and ny=0 (origin return), check or skip
            if nx == 0.0 and ny == 0.0:
                self.assertEqual(lx, 0.0)
                self.assertEqual(ly, 0.0)
                continue
            self.assertAlmostEqual(lx, width - nx, delta=0.02, msg=f"X must be width - nx: {lx} vs {width - nx}")
            self.assertAlmostEqual(ly, height - ny, delta=0.02, msg=f"Y must be height - ny: {ly} vs {height - ny}")
            self.assertGreaterEqual(lx, 0.0)
            self.assertLessEqual(lx, width)
            self.assertGreaterEqual(ly, 0.0)
            self.assertLessEqual(ly, height)

        # Test Lab Record with invert_y=True
        gc_lab_inv = generate_gcode(pages, invert_y=True, flip_lab_record=True)
        gc_norm_inv = generate_gcode(pages, invert_y=True, flip_lab_record=False)
        lab_inv_coords = extract_coords(gc_lab_inv)
        norm_inv_coords = extract_coords(gc_norm_inv)

        for (nx, ny), (lx, ly) in zip(norm_inv_coords, lab_inv_coords):
            if nx == 0.0 and ny == 0.0:
                continue
            self.assertAlmostEqual(lx, width - nx, delta=0.02)
            # When invert_y is True, normal Y is (height - y). Rotated Y is y = height - normal Y.
            self.assertAlmostEqual(ly, height - ny, delta=0.02)

    def test_multipage_pagination(self):
        template = TEMPLATES["kokuyo_camlin_small"]
        # Long text that spans multiple pages
        long_text = "This is a comprehensive test of multi-page pagination. " * 16
        pages = paginate_and_render(long_text, template)
        self.assertGreater(len(pages), 1, "Should paginate across at least 2 pages")
        
        # Test combined G-code generation with M0 paper change pause
        gc_all = generate_gcode(pages, page_index=None)
        self.assertIn("M0 (CHANGE PAPER", gc_all)
        self.assertIn("PAGE 1", gc_all)
        self.assertIn("PAGE 2", gc_all)

class TestServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        from server import HandcodeHandler, ThreadedHTTPServer

        cls.port = 8899
        cls.server = ThreadedHTTPServer(("127.0.0.1", cls.port), HandcodeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_api_templates(self):
        import urllib.request
        import json
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/templates")
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertIn("kokuyo_camlin_small", data["templates"])

    def test_api_render_and_gcode(self):
        import urllib.request
        import json
        payload = json.dumps({
            "text": "Hello world from API test",
            "template_id": "kokuyo_camlin_small",
            "style": 1
        }).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/render", data=payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertGreater(len(data["pages"]), 0)
            self.assertTrue(data["pages"][0]["draw_path"].startswith("M "))

            # G-code API
            gc_payload = json.dumps({
                "pages": data["pages"],
                "pen_mode": "servo",
                "feed_draw": 1800,
                "feed_travel": 5000,
                "invert_y": True
            }).encode("utf-8")
            gc_req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/gcode", data=gc_payload, headers={"Content-Type": "application/json"})
            with self.opener.open(gc_req) as gc_resp:
                gc_data = json.loads(gc_resp.read().decode("utf-8"))
                self.assertTrue(gc_data["success"])
                self.assertIn("G21", gc_data["gcode"])

    def test_static_assets(self):
        import urllib.request
        for path in ["/", "/static/style.css", "/static/app.js"]:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
            with self.opener.open(req) as resp:
                self.assertEqual(resp.status, 200)
                body = resp.read().decode("utf-8")
                self.assertGreater(len(body), 50)
                if path == "/":
                    # Check all 4 sections have scroll controls
                    self.assertIn('data-target="card1Body"', body)
                    self.assertIn('data-target="card2Body"', body)
                    self.assertIn('data-target="card3Body"', body)
                    self.assertIn('data-target="card4Body"', body)
                    self.assertIn('btn-card-scroll', body)
                    self.assertIn('data-jump="card1"', body)
                    self.assertIn('data-jump="card4"', body)
                    self.assertIn('livePenMarker', body)
                    self.assertIn('chkShowPenTip', body)
                    self.assertIn('chkTouchToMove', body)
                    self.assertIn('touch-hint-box', body)
                    self.assertIn('chkLabRecordFlip', body)
                    self.assertIn('chkLabRecordFlipToolbar', body)
                    self.assertIn('lab-record-toggle-container', body)
                    self.assertIn('penDownCmd', body)
                    self.assertIn('penUpCmd', body)
                    self.assertIn('btnFlipPenCmds', body)
                elif path == "/static/style.css":
                    self.assertIn('.btn-card-scroll', body)
                    self.assertIn('.card-scrollable-body', body)
                    self.assertIn('.live-pen-marker', body)
                    self.assertIn('.touch-hint-box', body)
                    self.assertIn('.lab-record-toggle-container', body)
                    self.assertIn('.lab-record-pill', body)
                elif path == "/static/app.js":
                    self.assertIn('setupCardScrollControls', body)
                    self.assertIn('setupSectionJumpNavigation', body)
                    self.assertIn('btnJogYPlus', body)
                    self.assertIn('btnJogXPlus', body)
                    self.assertIn('updateLivePenMarker', body)
                    self.assertIn('startLiveMachinePoller', body)
                    self.assertIn('handlePaperTouchMove', body)
                    self.assertIn('sendMachineMoveTo', body)
                    self.assertIn('chkLabRecordFlip', body)

    def test_streamer_cleaning_and_methods(self):
        from engine.streamer import GRBLStreamer
        self.assertEqual(GRBLStreamer.clean_line("G21 ; millimeter units"), "G21")
        self.assertEqual(GRBLStreamer.clean_line("G0 X10 Y20 (rapid travel)"), "G0 X10 Y20")
        self.assertEqual(GRBLStreamer.clean_line("; full line comment"), "")
        self.assertEqual(GRBLStreamer.clean_line("M3 S90 ; pen down"), "M3 S90")
        self.assertEqual(GRBLStreamer.clean_line("M2   ; end of job"), "M2")

    def test_gcode_rs274ngc_compliance(self):
        from engine.paginator import TEMPLATES, paginate_and_render
        from engine.gcode import generate_gcode
        tpl = TEMPLATES["kokuyo_camlin_small"]
        pages = paginate_and_render("Hi", tpl)
        gc = generate_gcode(pages, page_index=0, pen_mode="servo", servo_delay_ms=150)
        lines = gc.splitlines()
        
        # Verify G94 per minute feedrate is present
        self.assertTrue(any("G94" in l for l in lines))
        # Verify G21 mm is present
        self.assertTrue(any("G21" in l for l in lines))
        # Verify G90 absolute is present
        self.assertTrue(any("G90" in l for l in lines))
        # Verify G4 dwell is present for servo
        self.assertTrue(any("G4 P0.15" in l for l in lines))
        # Verify no standalone F lines
        for l in lines:
            trimmed = l.split(";")[0].strip()
            if trimmed.startswith("F"):
                self.fail(f"Found standalone feedrate line: {trimmed}")

    def test_machine_api_endpoints(self):
        import urllib.request
        import json
        
        # Test jog endpoint
        jog_payload = json.dumps({"dx": 0.0, "dy": 0.0, "feed": 1500}).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/machine/jog", data=jog_payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("success", data)
        # Test moveto endpoint (Touch Coordination)
        moveto_payload = json.dumps({"x": 20.0, "y": 30.0, "feed": 3500}).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/machine/moveto", data=moveto_payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("success", data)
            self.assertIn("status", data)

        # Test pen test endpoint
        pen_payload = json.dumps({"down": False}).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/machine/pen", data=pen_payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("success", data)

        # Test zero origin endpoint
        zero_payload = json.dumps({}).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/machine/zero", data=zero_payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("success", data)

        # Test unlock endpoint
        unlock_payload = json.dumps({}).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/machine/unlock", data=unlock_payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("success", data)

        # Test live status endpoint for live pen marker tracking
        status_req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/stream/status")
        with self.opener.open(status_req) as resp:
            s_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(s_data["success"])
            st = s_data["status"]
            self.assertIn("wpos", st)
            self.assertIn("mpos", st)
            self.assertIn("pen_down", st)

    def test_continuation_word_metadata_and_slicing(self):
        """
        Verify that words metadata tracks precise stroke boundaries,
        and that slicing strokes for paper continuation generates accurate G-code.
        """
        template = TEMPLATES["kokuyo_camlin_small"]
        text = "Alpha Beta Gamma Delta"
        pages = paginate_and_render(text, template)
        self.assertEqual(len(pages), 1)
        page = pages[0]
        
        self.assertIn("words", page)
        words = page["words"]
        self.assertEqual(len(words), 4)
        
        # Check word metadata fields
        for idx, w in enumerate(words):
            self.assertEqual(w["word_index"], idx)
            self.assertIn("stroke_start", w)
            self.assertIn("stroke_end", w)
            self.assertLess(w["stroke_start"], w["stroke_end"])
        
        # Slicing after word 1 ("Alpha" and "Beta" marked as written, cutoff = 2)
        # Remaining words should be "Gamma Delta"
        gamma_start_stroke = words[2]["stroke_start"]
        sliced_strokes = page["strokes_points"][gamma_start_stroke:]
        self.assertGreater(len(sliced_strokes), 0)
        
        sliced_page = dict(page)
        sliced_page["strokes_points"] = sliced_strokes
        
        gcode = generate_gcode([sliced_page], pen_down_cmd="M5", pen_up_cmd="M3 S90")
        self.assertIn("M5", gcode)
        self.assertIn("M3 S90", gcode)
        
        # When all words are written (cutoff = 4)
        empty_page = dict(page)
        empty_page["strokes_points"] = []
        empty_gcode = generate_gcode([empty_page], pen_down_cmd="M5", pen_up_cmd="M3 S90")
        self.assertIn("(Page is empty)", empty_gcode)

    def test_resume_from_touched_position_skip_origin(self):
        """
        Verify that when return_to_origin is False (resume from touched position):
        - NO 'G0 X0.00 Y0.00' appears at the start sequence.
        - NO 'G0 X0.00 Y0.00' appears at the end of the page or job.
        - The plotter lifts pen and moves directly from its current position to the writing place.
        """
        template = TEMPLATES["kokuyo_camlin_small"]
        pages = paginate_and_render("Direct resume test", template)
        
        # Test default (return_to_origin=False, resume_from_current=True)
        gc_direct = generate_gcode(pages, return_to_origin=False)
        self.assertNotIn("G0 X0.00 Y0.00", gc_direct)
        self.assertIn("DIRECT FROM CURRENT/TOUCHED POSITION", gc_direct)
        self.assertIn("M3 S90", gc_direct)
        self.assertIn("M5", gc_direct)

        # Test with return_to_origin=True
        gc_origin = generate_gcode(pages, return_to_origin=True)
        self.assertIn("G0 X0.00 Y0.00", gc_origin)
        self.assertIn("; Return to home origin", gc_origin)

        # Test API endpoint with return_to_origin=False
        import urllib.request
        import json
        payload = json.dumps({
            "pages": pages,
            "return_to_origin": False,
            "resume_from_current": True
        }).encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/gcode", data=payload, headers={"Content-Type": "application/json"})
        with self.opener.open(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertNotIn("G0 X0.00 Y0.00", data["gcode"])

if __name__ == "__main__":
    unittest.main()
