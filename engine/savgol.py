import numpy as np

def savgol_coeffs(window_length: int, polyorder: int, pos=None, use="conv"):
    if polyorder >= window_length:
        raise ValueError("polyorder must be less than window_length.")

    halflen, rem = divmod(window_length, 2)
    if pos is None:
        pos = halflen - 0.5 if rem == 0 else halflen

    if not (0 <= pos < window_length):
        raise ValueError("pos must be nonnegative and less than window_length.")

    x = np.arange(-pos, window_length - pos, dtype=float)
    if use == "conv":
        x = x[::-1]

    order = np.arange(polyorder + 1).reshape(-1, 1)
    A = x ** order
    y = np.zeros(polyorder + 1)
    y[0] = 1

    coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    return coeffs


def savgol_filter(x, window_length: int = 7, polyorder: int = 2, mode: str = "nearest"):
    x = np.asarray(x)
    if x.dtype != np.float64 and x.dtype != np.float32:
        x = x.astype(np.float64)

    if len(x) < window_length:
        return x

    coeffs = savgol_coeffs(window_length, polyorder)
    if mode == "nearest":
        x_pad = np.pad(x, window_length // 2, mode="edge")
        y = np.convolve(x_pad, coeffs, mode="valid")
    else:
        y = np.convolve(x, coeffs, mode="same")
    return y
