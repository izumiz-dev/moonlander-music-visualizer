"""
Circular hue math shared by anything that treats hue as a value on the QMK
0-255 hue wheel (screen color extraction today; music-mode palette rotation
and the terminal dashboard could reuse this later).

Hue is an *angle*, not a scalar: averaging, lerping, or clamping two hues as
plain numbers is wrong whenever they straddle the 0/255 wrap point (e.g. a
naive average of hue 250 and hue 10 gives 130 -- the opposite side of the
wheel -- instead of the correct answer near 4). Every function here goes
through the shortest-arc / unit-vector representation instead.

Dependency-light on purpose: numpy only, nothing screen-capture-specific.
"""
import numpy as np

TWO_PI = 2.0 * np.pi
HUE_RANGE = 256.0


def hue_to_vec(hue_u8):
    """Unit vector at angle `hue_u8 * 2*pi/256`. Works on scalars or ndarrays."""
    theta = np.asarray(hue_u8, dtype=np.float64) * (TWO_PI / HUE_RANGE)
    return np.cos(theta), np.sin(theta)


def vec_to_hue(x, y):
    """Inverse of hue_to_vec: angle of (x, y) mapped back to 0-255 (int)."""
    theta = np.arctan2(y, x)
    hue = (theta * (HUE_RANGE / TWO_PI)) % HUE_RANGE
    return int(round(float(hue))) % 256


def hue_delta(a, b):
    """Shortest signed arc from hue `a` to hue `b`, in [-128, 127]."""
    return ((int(b) - int(a) + 128) % 256) - 128


def hue_lerp(a, b, t):
    """Lerp from hue `a` toward hue `b` by fraction `t`, along the shortest arc."""
    return (a + t * hue_delta(a, b)) % 256.0


def circular_smooth(hist, taps=(1, 2, 3, 2, 1)):
    """
    Smooth a 1D histogram treating it as circular (wraps around, no seam at
    bin 0/N-1). Uses np.roll rather than zero-padded convolution, which would
    otherwise dim the histogram near its edges as if a "wall" sat there.
    """
    hist = np.asarray(hist, dtype=np.float64)
    n_taps = len(taps)
    center = n_taps // 2
    weight_sum = float(sum(taps))
    out = np.zeros_like(hist)
    for i, w in enumerate(taps):
        shift = i - center
        out += w * np.roll(hist, -shift)
    return out / weight_sum


def clip01(x):
    """Clamp a scalar to [0, 1]."""
    return float(np.clip(x, 0.0, 1.0))


def smoothstep(x, edge0, edge1):
    """Classic smoothstep: 0 below edge0, 1 above edge1, smooth (no kink) between."""
    if edge0 == edge1:
        return 1.0 if x >= edge0 else 0.0
    t = clip01((x - edge0) / (edge1 - edge0))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    """Plain linear interpolation (non-circular -- for scalars like spread/tau)."""
    return a + (b - a) * t
