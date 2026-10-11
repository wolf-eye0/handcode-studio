"""
High-Level Handwriting Generator.
Uses Calligrapher RNN to turn text into smooth vector strokes calibrated in millimeters.
"""

import os
import math
import numpy as np
from .rnn import parse_model, run_model, character_map
from .savgol import savgol_filter

MODEL_CANDIDATES = [
    os.path.expanduser("~/.local/share/handcode/model.ulw"),
    "/home/paradoxpete/.gemini/antigravity-cli/brain/238b83fb-61f7-46dd-8f68-f1fb385b752b/model.ulw",
    "/tmp/calligrapher_model.ulw",
    "/tmp/handcode/src/lib/handwriting/models/calligrapher/model.ulw",
    os.path.join(os.path.dirname(__file__), "model.ulw")
]

MODEL_PATH = None
for p in MODEL_CANDIDATES:
    if os.path.exists(p):
        MODEL_PATH = p
        break

_CACHED_MODEL = None

def get_model():
    global _CACHED_MODEL, MODEL_PATH
    if _CACHED_MODEL is None:
        if not MODEL_PATH or not os.path.exists(MODEL_PATH):
            for p in MODEL_CANDIDATES:
                if os.path.exists(p):
                    MODEL_PATH = p
                    break
        if not MODEL_PATH or not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Calligrapher model not found in candidates: {MODEL_CANDIDATES}")
        _CACHED_MODEL = parse_model(MODEL_PATH)
    return _CACHED_MODEL


REPLACEMENTS = {
    "Q": "O", "X": "x", "Z": "z",
    "Ä": "A", "Ö": "O", "Ü": "U",
    "ä": "a", "ö": "o", "ü": "u",
    "é": "e", "è": "e", "ê": "e",
    "à": "a", "á": "a", "â": "a",
    "ñ": "n", "ß": "ss",
    "\t": "    ", "\r": ""
}

def clean_character(c: str) -> str:
    if c in character_map:
        return c
    if c in REPLACEMENTS:
        return REPLACEMENTS[c]
    if ord(c) < 32 or ord(c) > 126:
        return " "
    return " "

def clean_word(word: str) -> str:
    cleaned = "".join(clean_character(c) for c in word).strip()
    return cleaned

def offsets_to_coords(offsets: np.ndarray) -> np.ndarray:
    return np.concatenate([np.cumsum(offsets[:, :2], axis=0), offsets[:, 2:3]], axis=1)

def align_strokes(coords: np.ndarray) -> np.ndarray:
    coords = np.copy(coords)
    if len(coords) < 3:
        return coords
    X = coords[:, 0].reshape(-1, 1)
    Y = coords[:, 1].reshape(-1, 1)
    X_design = np.concatenate([np.ones([X.shape[0], 1]), X], axis=1)
    try:
        sol = np.linalg.lstsq(X_design, Y, rcond=None)[0]
        offset = sol[0, 0]
        slope = sol[1, 0]
        theta = np.arctan(slope)
        rotation_matrix = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)]
        ])
        coords[:, :2] = np.dot(coords[:, :2], rotation_matrix) - offset
    except Exception:
        pass
    return coords

def denoise_strokes(coords: np.ndarray) -> np.ndarray:
    if len(coords) < 4:
        return coords
    split_indices = np.where(coords[:, 2] == 1)[0] + 1
    sub_strokes = np.split(coords, split_indices, axis=0)
    new_sub = []
    for stroke in sub_strokes:
        if len(stroke) >= 4:
            x_new = savgol_filter(stroke[:, 0], 7, 2, mode='nearest')
            y_new = savgol_filter(stroke[:, 1], 7, 2, mode='nearest')
            xy = np.hstack([x_new.reshape(-1, 1), y_new.reshape(-1, 1)])
            stroke = np.concatenate([xy, stroke[:, 2].reshape(-1, 1)], axis=1)
        new_sub.append(stroke)
    return np.vstack(new_sub) if new_sub else coords

def get_word_metrics(word: str) -> tuple[float, float, float]:
    """
    Returns (word_top, word_middle, word_bottom) proportions for character anatomy:
    word_top: ascender proportion (0.5 for capitals and ascenders, 0.0 otherwise)
    word_middle: nominal lowercase x-height proportion (1.0)
    word_bottom: descender proportion (0.4 for descenders, 0.0 otherwise)
    """
    word_top = 0.0
    word_middle = 1.0
    word_bottom = 0.0

    for c in "qpygj":
        if c in word:
            word_bottom = max(0.4, word_bottom)
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZbdfhklt0123456789!?()#$":
        if c in word:
            word_top = max(0.5, word_top)
    for c in "ij":
        if c in word:
            word_top = max(0.35, word_top)

    return word_top, word_middle, word_bottom

def get_word_baseline_factor(word: str) -> float:
    # Backwards-compatibility wrapper
    w_top, w_mid, w_bot = get_word_metrics(word)
    return (0.5 - w_top) / (w_top + w_mid + w_bot)


class WordStroke:
    def __init__(self, raw_word: str, coords: np.ndarray, width: float, height: float):
        self.raw_word = raw_word
        self.coords = coords  # Nx3 array: x, y (baseline at y=0, +Y is up, -Y is down), penup
        self.width = width
        self.height = height


_WORD_STROKE_CACHE: dict = {}

def generate_word_strokes(words: list[str], style: int = 1, bias: float = 0.75, target_height: float = 6.0) -> list[WordStroke]:
    """
    Generate normalized strokes for a list of words.
    target_height: nominal capital/line height in mm.
    Baseline is calibrated at y = 0.0, with ascenders at +Y and descenders at -Y.
    Uses memory cache so repeated words or re-renders are near instantaneous.
    """
    model = get_model()
    cleaned_words = [clean_word(w) for w in words]
    bias_key = round(float(bias), 2)

    # Check which words are already cached
    needed_words = []
    needed_indices = []
    processed_map = {}

    for idx, w in enumerate(cleaned_words):
        if not w:
            processed_map[idx] = None
            continue
        cache_key = (w, style, bias_key)
        if cache_key in _WORD_STROKE_CACHE:
            processed_map[idx] = _WORD_STROKE_CACHE[cache_key]
        else:
            needed_words.append(w)
            needed_indices.append(idx)

    # Synthesize missing words using RNN
    if needed_words:
        raw_strokes = run_model(model, needed_words, writing_style=style, bias=bias)
        for w, strokes, idx in zip(needed_words, raw_strokes, needed_indices):
            cache_key = (w, style, bias_key)
            if len(strokes) < 2 or not w.strip():
                _WORD_STROKE_CACHE[cache_key] = None
                processed_map[idx] = None
                continue
            c = offsets_to_coords(strokes)
            c = denoise_strokes(c)
            c[:, :2] = align_strokes(c[:, :2])
            c[:, 0] -= c[:, 0].min()
            c[:, 1] -= c[:, 1].max()  # top is at 0, bottom is at -h
            h = -c[:, 1].min()

            w_top, w_mid, w_bot = get_word_metrics(w)
            total_units = w_top + w_mid + w_bot
            # Exact position of the word baseline in c[:, 1]
            y_base = - (w_top + w_mid) / total_units * h if total_units > 0 else -h
            # Shift coordinates so that the baseline is precisely at y = 0
            c[:, 1] -= y_base

            # Equivalent full capital height (ascender-to-baseline = 1.5 units)
            unit_h = h / total_units if total_units > 0 else h
            h_cap = 1.5 * unit_h
            entry = (w, c, h_cap)
            _WORD_STROKE_CACHE[cache_key] = entry
            processed_map[idx] = entry

    # Compute reference scale from ascender/cap height
    sample_heights = [processed_map[i][2] for i in range(len(cleaned_words)) if processed_map.get(i) is not None]
    median_h = float(np.median(sample_heights)) if sample_heights else 16.0
    scale = (target_height / median_h) if median_h > 0 else 0.32

    results = []
    for idx in range(len(cleaned_words)):
        item = processed_map.get(idx)
        if item is None:
            results.append(WordStroke("", np.zeros((0, 3)), width=target_height * 0.4, height=target_height))
            continue
        w, c, _ = item
        scaled = np.copy(c)
        scaled[:, :2] *= scale
        width = float(scaled[:, 0].max()) if len(scaled) > 0 else (target_height * 0.4)
        height = float(scaled[:, 1].max() - scaled[:, 1].min()) if len(scaled) > 0 else target_height
        results.append(WordStroke(w, scaled, width, height))

    return results

