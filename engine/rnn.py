"""
Calligrapher RNN Handwriting Synthesis Engine (Pure NumPy).
Based on Alex Graves' handwriting synthesis / calligrapher.ai / handcode.
Patched for NumPy 2.x and standalone performance.
"""

import math
import random
import typing
import numpy as np

def load_model(filepath: str) -> bytes:
    with open(filepath, "rb") as f:
        return f.read()

def parse_model(filepath: str) -> dict:
    model_raw = load_model(filepath)
    model_raw_length = len(model_raw)
    model_parsed = {}
    index = 0

    while index < model_raw_length:
        name_length = model_raw[index]
        index += 1
        name = model_raw[index:index+name_length].decode("ascii", errors="replace")
        index += name_length

        has_extra_data = model_raw[index]
        index += 1

        chunk_length = int.from_bytes(model_raw[index:index+4], byteorder="little")
        index += 4

        chunk_length_bytes = chunk_length * 4
        chunk = np.frombuffer(model_raw[index:index+chunk_length_bytes], dtype="<f4")
        index += chunk_length_bytes

        offsets = None
        if has_extra_data:
            offsets_length_bytes = chunk_length
            offsets = np.frombuffer(model_raw[index:index+offsets_length_bytes], dtype="<u1")
            index += offsets_length_bytes

        dimensions_length = model_raw[index]
        index += 1

        dimensions_length_bytes = dimensions_length * 2
        matrix_dimensions = np.frombuffer(model_raw[index:index+dimensions_length_bytes], dtype="<u2")
        index += dimensions_length_bytes

        if name in ["y", "w", "r", "l"]:
            chunk = process_model_weights(chunk, offsets, matrix_dimensions)
        elif has_extra_data:
            chunk = unpack_sparse_matrix(chunk, offsets, matrix_dimensions)

        model_parsed[name] = chunk

    return model_parsed

def process_model_weights(weights, cumulative_offsets, matrix_dimensions):
    dim_rows = int(matrix_dimensions[0])
    dim_cols = int(matrix_dimensions[1])
    cumulative_sum = 0
    non_zero_weights = []
    column_offsets = []
    row_indices = []

    for idx in range(len(weights)):
        weight = float(weights[idx])
        cumulative_sum += int(cumulative_offsets[idx])
        row_index = cumulative_sum // dim_cols
        column_offset = cumulative_sum % dim_cols
        if weight != 0.0:
            non_zero_weights.append(weight)
            column_offsets.append(column_offset)
            row_indices.append(row_index)

    row_start_indices = [0]
    current_index = 0
    row_indices_length = len(row_indices)
    for row in range(dim_rows):
        while (current_index < row_indices_length) and (row_indices[current_index] == row):
            current_index += 1
        row_start_indices.append(current_index)

    return [np.array([dim_rows, dim_cols]), np.array(non_zero_weights, dtype=np.float32), np.array(column_offsets, dtype=np.int32), np.array(row_start_indices, dtype=np.int32)]

def unpack_sparse_matrix(values, offsets, dimensions):
    total_elements = int(np.prod(dimensions))
    sparse_matrix = np.zeros(total_elements, dtype=np.float32)
    num_values = len(values)
    cumulative_offset = 0

    for i in range(num_values):
        cumulative_offset += int(offsets[i])
        sparse_matrix[cumulative_offset] = values[i]

    return sparse_matrix

character_map = {
    "\0": 0, " ": 8,  "!": 72, '"': 4,  "#": 56, "'": 16, "(": 66, ")": 67, ",": 37, "-": 40, ".": 7,  "?": 51,
    "0": 62, "1": 59, "2": 63, "3": 69, "4": 68, "5": 61, "6": 71, "7": 70, "8": 76, "9": 60, ":": 74, ";": 73,
    "A": 9,  "B": 47, "C": 57, "D": 52, "E": 42, "F": 53, "G": 45, "H": 41, "I": 23, "J": 64, "K": 58, "L": 48,
    "M": 5,  "N": 38, "O": 36, "P": 46, "R": 55, "S": 18, "T": 31, "U": 65, "V": 39, "W": 54, "Y": 50,
    "a": 14, "b": 32, "c": 20, "d": 27, "e": 19, "f": 35, "g": 33, "h": 30, "i": 13, "j": 43, "k": 28, "l": 26,
    "m": 12, "n": 15, "o": 25, "p": 29, "q": 49, "r": 6,  "s": 17, "t": 21, "u": 11, "v": 34, "w": 24, "x": 44,
    "y": 22, "z": 10,
}

writing_style_map = {
    1: 44,
    2: 54,
    3: 23,
    4: 1,
    5: 19,
    6: 6,
    7: 30,
    8: 11,
    9: 21,
}

def sigmoid(arr):
    arr = np.clip(arr, -88, 88)
    return 1 / (1 + np.exp(-arr))

def softplus(arr):
    arr = np.clip(arr, None, 88)
    return np.log(1 + np.exp(arr))

def softmax(arr):
    e = np.exp(arr - np.max(arr))
    return e / np.sum(e)

def compute_weighted_group_sums(r, e):
    matrix_shape, weights, column_offsets, start_indices = e
    weights_premultiplied = weights * r[column_offsets]
    return np.add.reduceat(weights_premultiplied, start_indices[:-1])

def extract_elements_by_indices(array, indices, group_size):
    return array.reshape(-1, group_size)[indices].flatten()

def calculate_char_embeddings(model, char_raws):
    char_raws = [0, *char_raws, 0]
    all_char_embeddings = model["s"].reshape(-1, 256)
    char_embeddings = all_char_embeddings[char_raws]
    
    all_char_embedding_weights = model["b"].reshape(-1, 256).T.reshape(256, 3, 256)
    sliding_window_embeddings = np.lib.stride_tricks.sliding_window_view(char_embeddings, (3, 256))
    weighted_embeddings = (sliding_window_embeddings * all_char_embedding_weights).sum(axis=2).sum(axis=2)
    weighted_embeddings += model["t"]
    weighted_embeddings = np.tanh(weighted_embeddings)

    char_embeddings = char_embeddings[1:-1]
    concatenated_embeddings = np.concatenate((char_embeddings, weighted_embeddings), axis=1)
    intermediate = (concatenated_embeddings.reshape((-1, 512, 1)) * model["j"].reshape(1, 512, -1)).sum(axis=1)
    intermediate += model["E"]
    return intermediate

def rnn_layer(model, r, state, stage):
    if stage == 1:
        a = state[0]
        l = state[3]
        n = model["y"]
        i = model["p"]
    elif stage == 2:
        a = state[1]
        l = state[4]
        n = model["w"]
        i = model["q"]
    else:
        a = state[2]
        l = state[5]
        n = model["r"]
        i = model["f"]

    r = np.concatenate((r, l))
    f = compute_weighted_group_sums(r, n) + i
    h, d, c, p = np.split(f, 4)
    m = sigmoid(c) * a + sigmoid(h) * np.tanh(d)
    M = sigmoid(p) * np.tanh(m)

    if stage == 1:
        state[0] = m
        state[3] = M
    elif stage == 2:
        state[1] = m
        state[4] = M
    else:
        state[2] = m
        state[5] = M
    return M

def js_k(model, r, state):
    t = np.sum(r.reshape(-1, 1) * model["h"].reshape(256, -1), axis=0)
    t = t + model["n"]
    a, l, v = np.split(t, 3)
    l = softplus(l)
    v = softplus(v)
    a = softmax(a)
    v = state[7] + (v / 15)
    state[7] = v
    i = state[8]
    a = a.reshape(10, -1)
    l = l.reshape(10, -1)
    v = v.reshape(10, -1)
    c = sigmoid((i - v) / l)

    p = a * np.diff(c)

    w = p.sum(axis=0)
    t = state[10]
    g = np.sum(w.reshape(-1, 1) * t, axis=0)
    state[6] = g
    return g

def js_F(model, r, state):
    t = np.sum(r.reshape(-1, 1) * model["i"].reshape(-1, 256), axis=0)
    t += model["W"] * state[9]
    t = t * math.sqrt(1 / 2)
    a = rnn_layer(model, t, state, 1)
    t = (t + a) * math.sqrt(1 / 2)
    l = np.concatenate((t, state[6]))
    n = rnn_layer(model, l, state, 2)
    i = js_k(model, n, state)
    f = np.concatenate((n, i))
    f = compute_weighted_group_sums(f, model["l"])
    f = f + model["Q"]
    f = np.tanh(f)
    t = (t + f) * math.sqrt(1 / 2)
    stop_probability = sigmoid(np.sum(i * model["c"]) + model["u"])
    d = rnn_layer(model, t, state, 3)
    t = (t + d) * math.sqrt(1 / 2)
    c = np.sum(t.reshape(-1, 1) * model["z"].reshape(256, -1), axis=0)
    c = c + model["v"]
    return c, stop_probability

def js_U(r, bias):
    e = r[:120]
    a = sigmoid(r[120:])[0]
    penup = 1.0 if random.random() < a else 0.0
    
    e = e.reshape(-1, 6)
    f = e[:, 0]
    c = e[:, 1:3].flatten()
    p = e[:, 3]
    w = e[:, 4:6].flatten()

    p = np.tanh(p)
    g = bias
    c = softplus(c) / np.exp(g)
    f = np.log(softmax(f)) * (1 + g)

    for i in range(len(f)):
        if f[i] < np.log(0.02):
            f[i] -= 100

    b = np.argmax(f - np.log(-np.log(np.random.random(f.shape))))
    M = extract_elements_by_indices(w, b, 2)
    y = extract_elements_by_indices(c, b, 2)
    C = extract_elements_by_indices(p, b, 1)[0]
    A = y[0]
    k = y[1]
    F = np.array([[A, 0], [C * k, k * np.sqrt(max(0.0, 1 - C * C))]])

    U = np.sqrt(-2 * np.log(1 - np.random.random(2))) * np.cos(2 * np.pi * np.random.random(2))
    L = M + np.sum(U * F, axis=1)
    return np.array([L[0], L[1], penup])

def js_L(model, r, state, bias):
    t, stop_certainty = js_F(model, r, state)
    return [js_U(t, bias), stop_certainty, state]

def run_model(model: dict, words: list[str], writing_style: int = 1, bias: float = 0.75) -> list[np.ndarray]:
    writing_style_index = writing_style_map.get(writing_style, 44)
    strokes_all = []
    scaled_bias = 2.5 * bias

    for word in words:
        if not word:
            continue
        word_filtered = [character_map.get(c, 0) for c in word]
        word_filtered = [c for c in word_filtered if c != 0]
        if not word_filtered:
            continue
        word_filtered = [2, *word_filtered, 3]
        word_len = len(word_filtered)

        er = calculate_char_embeddings(model, word_filtered)
        writing_styles = model["g"].reshape(-1, 64)
        o = writing_styles[writing_style_index]
        n = model["k"].reshape(64, -1).T
        v = model["R"]
        o = np.sum(o * n, axis=1) + v

        state = [
            model["d"],
            model["o"],
            model["e"],
            model["m"],
            model["x"],
            model["a"],
            model["T"],
            np.zeros(10, dtype=np.float32),
            np.zeros((10, word_len+1)) + np.arange(word_len+1) - 0.5,
            o,
            er,
        ]

        sample_tsteps = 0
        strokes = [np.array([0.0, 0.0, 1.0])]
        stop_condition = 40 * len(word)

        while True:
            stroke, stop_certainty, state = js_L(model, strokes[-1], state, scaled_bias)
            sample_tsteps += 1
            if (sample_tsteps > stop_condition) or (stop_certainty > 0.5):
                break
            strokes.append(stroke)

        strokes_all.append(np.array(strokes))

    return strokes_all
