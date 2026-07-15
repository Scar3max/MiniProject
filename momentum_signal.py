# momentum_signal.py
# Helper module implementing the sliding-window-2 momentum signal
# Usage: from momentum_signal import compute_momentum

from typing import List, Dict

def compute_momentum(recent_scores: List[float],
                     normalization_divisor: float = 10.0,
                     weight: float = 0.8) -> Dict:
    """
    Compute the sliding-window-2 momentum signal based on the last scores.

    recent_scores: list of floats in chronological order (oldest ... newest).
                   Need at least 3 values to compute the net momentum.
    normalization_divisor: divisor used to normalize the raw net to approx [-1,1].
    weight: how strongly this momentum will be scaled (returned as 'weighted').

    Returns a dict:
    {
      "raw": raw_net (float),
      "norm": normalized (clamped -1..1),
      "weighted": norm * weight,
      "signal": one of "STRONG_POSITIVE","MILD_POSITIVE","NEUTRAL",
                         "MILD_NEGATIVE","STRONG_NEGATIVE"
    }
    """

    # default neutral
    if len(recent_scores) < 3:
        return {"raw": 0.0, "norm": 0.0, "weighted": 0.0, "signal": "NEUTRAL"}

    s_n   = float(recent_scores[-1])
    s_n1  = float(recent_scores[-2])
    s_n2  = float(recent_scores[-3])

    diff1 = s_n - s_n1
    diff2 = s_n1 - s_n2
    raw_net = diff1 + diff2

    # normalize
    norm = raw_net / normalization_divisor
    if norm > 1.0:
        norm = 1.0
    if norm < -1.0:
        norm = -1.0

    weighted = norm * weight

    # thresholds (tunable)
    STRONG_THRESH = 0.30
    MILD_THRESH = 0.15

    if norm >= STRONG_THRESH:
        signal = "STRONG_POSITIVE"
    elif norm >= MILD_THRESH:
        signal = "MILD_POSITIVE"
    elif norm <= -STRONG_THRESH:
        signal = "STRONG_NEGATIVE"
    elif norm <= -MILD_THRESH:
        signal = "MILD_NEGATIVE"
    else:
        signal = "NEUTRAL"

    return {
        "raw": raw_net,
        "norm": norm,
        "weighted": weighted,
        "signal": signal
    }
