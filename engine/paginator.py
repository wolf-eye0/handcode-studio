"""
Smart Multi-Page Layout & Pagination Engine.
Organizes words across lines and multiple pages based on notebook or A4 templates,
aligns handwriting directly onto single-line notebook rules, and generates SVG vector paths.
"""

import math
import random
from typing import Dict, Any, List
import numpy as np
from .handwriting import generate_word_strokes, WordStroke

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "kokuyo_camlin_small": {
        "id": "kokuyo_camlin_small",
        "name": "Kokuyo Camlin Small Single-Line (155 x 190 mm)",
        "width": 155.0,
        "height": 190.0,
        "margin_left": 25.0,
        "margin_right": 10.0,
        "margin_top": 28.0,
        "margin_bottom": 14.0,
        "line_spacing": 8.0,
        "font_size": 5.2,
        "word_spacing": 3.2,
        "show_ruled_lines": True,
        "show_margin_line": True,
        "ruled_line_color": "rgba(80, 140, 200, 0.45)",
        "margin_line_color": "rgba(225, 75, 75, 0.65)"
    },
    "a4_standard": {
        "id": "a4_standard",
        "name": "A4 Standard Sheet (210 x 297 mm)",
        "width": 210.0,
        "height": 297.0,
        "margin_left": 25.0,
        "margin_right": 15.0,
        "margin_top": 25.0,
        "margin_bottom": 20.0,
        "line_spacing": 8.5,
        "font_size": 5.6,
        "word_spacing": 3.6,
        "show_ruled_lines": False,
        "show_margin_line": False,
        "ruled_line_color": "rgba(180, 180, 180, 0.35)",
        "margin_line_color": "rgba(225, 75, 75, 0.5)"
    },
    "a4_ruled": {
        "id": "a4_ruled",
        "name": "A4 Ruled Notebook (210 x 297 mm)",
        "width": 210.0,
        "height": 297.0,
        "margin_left": 28.0,
        "margin_right": 15.0,
        "margin_top": 28.0,
        "margin_bottom": 20.0,
        "line_spacing": 8.5,
        "font_size": 5.6,
        "word_spacing": 3.6,
        "show_ruled_lines": True,
        "show_margin_line": True,
        "ruled_line_color": "rgba(100, 150, 220, 0.4)",
        "margin_line_color": "rgba(230, 80, 80, 0.6)"
    },
    "square_bed_200": {
        "id": "square_bed_200",
        "name": "Machine Square Bed (200 x 200 mm)",
        "width": 200.0,
        "height": 200.0,
        "margin_left": 15.0,
        "margin_right": 15.0,
        "margin_top": 20.0,
        "margin_bottom": 15.0,
        "line_spacing": 8.0,
        "font_size": 5.4,
        "word_spacing": 3.4,
        "show_ruled_lines": False,
        "show_margin_line": False,
        "ruled_line_color": "rgba(180, 180, 180, 0.3)",
        "margin_line_color": "rgba(220, 80, 80, 0.4)"
    },
    "a5_notebook": {
        "id": "a5_notebook",
        "name": "A5 Lined Notebook (148 x 210 mm)",
        "width": 148.0,
        "height": 210.0,
        "margin_left": 22.0,
        "margin_right": 10.0,
        "margin_top": 24.0,
        "margin_bottom": 15.0,
        "line_spacing": 7.5,
        "font_size": 5.0,
        "word_spacing": 3.0,
        "show_ruled_lines": True,
        "show_margin_line": True,
        "ruled_line_color": "rgba(90, 140, 210, 0.4)",
        "margin_line_color": "rgba(220, 75, 75, 0.6)"
    }
}


class PageData:
    def __init__(self, page_number: int, template: dict):
        self.page_number = page_number
        self.template = template
        self.strokes_data = []  # list of tuples: (x, y, penup)
        self.words_data = []    # list of word metadata dicts for selection & continuation
        self.words_count = 0
        self.characters_count = 0
        self.total_draw_distance = 0.0  # in mm
        self.total_travel_distance = 0.0  # in mm

    def to_dict(self) -> dict:
        draw_path, travel_path = self.generate_svg_paths()
        ruled_lines = self.generate_ruled_lines()
        est_seconds = (self.total_draw_distance / 2000.0 * 60.0) + (self.total_travel_distance / 5000.0 * 60.0)

        return {
            "page_number": self.page_number,
            "width": self.template["width"],
            "height": self.template["height"],
            "margin_left": self.template["margin_left"],
            "margin_right": self.template["margin_right"],
            "margin_top": self.template["margin_top"],
            "margin_bottom": self.template["margin_bottom"],
            "line_spacing": self.template["line_spacing"],
            "show_ruled_lines": self.template.get("show_ruled_lines", True),
            "show_margin_line": self.template.get("show_margin_line", True),
            "ruled_line_color": self.template.get("ruled_line_color", "rgba(80, 140, 200, 0.45)"),
            "margin_line_color": self.template.get("margin_line_color", "rgba(225, 75, 75, 0.65)"),
            "draw_path": draw_path,
            "travel_path": travel_path,
            "ruled_lines": ruled_lines,
            "words_count": self.words_count,
            "characters_count": self.characters_count,
            "draw_distance_mm": round(self.total_draw_distance, 1),
            "travel_distance_mm": round(self.total_travel_distance, 1),
            "est_draw_time_min": round(est_seconds / 60.0, 1),
            "words": self.words_data,
            "strokes_points": self.strokes_data
        }

    def generate_ruled_lines(self) -> dict:
        t = self.template
        width = t["width"]
        height = t["height"]
        margin_top = t["margin_top"]
        margin_bottom = t["margin_bottom"]
        margin_left = t["margin_left"]
        margin_right = t["margin_right"]
        line_spacing = t["line_spacing"]

        horizontal_lines = []
        current_y = margin_top
        while current_y <= (height - margin_bottom + 0.1):
            horizontal_lines.append({
                "x1": 0.0,
                "y1": round(current_y, 2),
                "x2": width,
                "y2": round(current_y, 2)
            })
            current_y += line_spacing

        vertical_margin = {
            "x1": round(margin_left, 2),
            "y1": 0.0,
            "x2": round(margin_left, 2),
            "y2": height
        }

        header_top_line = {
            "x1": 0.0,
            "y1": round(margin_top - line_spacing * 0.8, 2),
            "x2": width,
            "y2": round(margin_top - line_spacing * 0.8, 2)
        } if margin_top >= line_spacing else None

        return {
            "horizontal": horizontal_lines,
            "vertical_margin": vertical_margin,
            "header_line": header_top_line
        }

    def generate_svg_paths(self) -> tuple[str, str]:
        draw_cmds = []
        travel_cmds = []
        in_draw = False
        last_x, last_y = None, None

        for pt in self.strokes_data:
            x, y, penup = pt[0], pt[1], pt[2]
            if last_x is not None:
                dist = math.hypot(x - last_x, y - last_y)
                if penup > 0:
                    self.total_travel_distance += dist
                    travel_cmds.append(f"M {last_x:.2f} {last_y:.2f} L {x:.2f} {y:.2f}")
                else:
                    self.total_draw_distance += dist

            if penup > 0:
                if in_draw:
                    in_draw = False
                draw_cmds.append(f"M {x:.2f} {y:.2f}")
            else:
                if not in_draw:
                    draw_cmds.append(f"M {x:.2f} {y:.2f}")
                    in_draw = True
                else:
                    draw_cmds.append(f"L {x:.2f} {y:.2f}")
            last_x, last_y = x, y

        return " ".join(draw_cmds), " ".join(travel_cmds)



def paginate_and_render(
    text: str,
    template: dict,
    style: int = 1,
    bias: float = 0.75,
    font_size: float = None,
    word_spacing: float = None,
    line_spacing: float = None
) -> List[dict]:
    """
    Renders text across pages according to template.
    Returns list of PageData dicts.
    """
    cfg = dict(template)
    if font_size is not None and font_size > 0:
        cfg["font_size"] = font_size
    if word_spacing is not None and word_spacing > 0:
        cfg["word_spacing"] = word_spacing
    if line_spacing is not None and line_spacing > 0:
        cfg["line_spacing"] = line_spacing

    page_width = cfg["width"]
    page_height = cfg["height"]
    margin_left = cfg["margin_left"]
    margin_right = cfg["margin_right"]
    margin_top = cfg["margin_top"]
    margin_bottom = cfg["margin_bottom"]
    line_space = cfg["line_spacing"]
    f_size = cfg["font_size"]
    w_space = cfg["word_spacing"]

    max_x = page_width - margin_right
    max_y = page_height - margin_bottom

    # Split paragraphs and raw words
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    tokens = []  # list of (word, is_newline_after)
    for l_idx, line in enumerate(raw_lines):
        words = line.strip().split()
        if not words:
            tokens.append(("", True))
            continue
        for w_idx, w in enumerate(words):
            is_nl = (w_idx == len(words) - 1) and (l_idx < len(raw_lines) - 1)
            tokens.append((w, is_nl))

    if not tokens:
        tokens = [("", False)]

    # Generate strokes for non-empty words in batch
    words_to_gen = [t[0] for t in tokens if t[0]]
    if words_to_gen:
        word_strokes_list = generate_word_strokes(words_to_gen, style=style, bias=bias, target_height=f_size)
    else:
        word_strokes_list = []

    stroke_iter = iter(word_strokes_list)

    # Layout state
    pages: List[PageData] = []
    current_page = PageData(1, cfg)
    current_x = margin_left
    current_y = margin_top
    global_word_idx = 0
    char_offset = 0

    for word, is_newline in tokens:
        if not word:
            # Empty paragraph newline
            current_x = margin_left
            current_y += line_space
            if current_y > max_y:
                pages.append(current_page)
                current_page = PageData(len(pages) + 1, cfg)
                current_x = margin_left
                current_y = margin_top
            char_offset += 1
            continue

        w_stroke = next(stroke_iter)
        w_width = w_stroke.width

        # Check line wrap
        if (current_x + w_width) > max_x and current_x > (margin_left + 5.0):
            current_x = margin_left
            current_y += line_space

        # Check page wrap
        if current_y > max_y:
            pages.append(current_page)
            current_page = PageData(len(pages) + 1, cfg)
            current_x = margin_left
            current_y = margin_top

        # Position strokes for this word
        stroke_start = len(current_page.strokes_data)
        if len(w_stroke.coords) > 0:
            stroke_pts = np.copy(w_stroke.coords)
            # Add subtle human jitter to baseline (+/- 0.12mm)
            jitter_y = (random.random() - 0.5) * 0.25
            
            # Place at current_x and current_y (baseline)
            stroke_pts[:, 0] += current_x
            stroke_pts[:, 1] = (current_y + jitter_y) - stroke_pts[:, 1]

            for pt in stroke_pts:
                current_page.strokes_data.append((round(float(pt[0]), 3), round(float(pt[1]), 3), int(pt[2])))

            current_page.words_count += 1
            current_page.characters_count += len(word)
        stroke_end = len(current_page.strokes_data)

        current_page.words_data.append({
            "word": word,
            "word_index": global_word_idx,
            "char_start": char_offset,
            "char_end": char_offset + len(word),
            "stroke_start": stroke_start,
            "stroke_end": stroke_end,
            "x": round(current_x, 2),
            "y": round(current_y, 2),
            "width": round(w_width, 2)
        })
        global_word_idx += 1
        char_offset += len(word) + 1

        current_x += (w_width + w_space)

        if is_newline:
            current_x = margin_left
            current_y += line_space
            if current_y > max_y:
                pages.append(current_page)
                current_page = PageData(len(pages) + 1, cfg)
                current_x = margin_left
                current_y = margin_top

    pages.append(current_page)
    return [p.to_dict() for p in pages]
