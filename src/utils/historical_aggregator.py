# CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
# SPDX-FileCopyrightText: 2026 Noxfort Systems
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import deque
from typing import Dict, List, Tuple

import numpy as np


class SlidingWindowMax:
    """
    Computes sliding window maximum using an amortized O(1) monotonic queue.
    """

    def __init__(self, window_size: int):
        self.window_size = window_size
        self.deque = deque()  # stores tuples of (index, value)
        self.index = 0

    def update(self, val: float) -> float:
        # 1. Remove elements from the back that are smaller than current value
        while self.deque and self.deque[-1][1] <= val:
            self.deque.pop()

        # 2. Add current value to the back
        self.deque.append((self.index, val))

        # 3. Remove old elements from the front that fell outside the window
        while self.deque and self.index - self.deque[0][0] >= self.window_size:
            self.deque.popleft()

        self.index += 1
        return self.deque[0][1]

    def peek(self, val: float) -> float:
        """Returns window maximum including `val` without mutating deque or index."""
        best = val
        for idx, entry_val in self.deque:
            if self.index - idx < self.window_size:
                if entry_val > best:
                    best = entry_val
                break  # deque is monotonically non-increasing
        return best

    def reset(self):
        self.deque.clear()
        self.index = 0


class HistoricalAggregator:
    """
    Computes incremental real-time traffic statistics over a 5-minute horizon (~1500 steps).
    Calculates 4 main metrics per variable to construct the extended state vector:
    1. EMA (5m) - Long-term baseline average.
    2. Trend - Difference between short-term (1m) EMA and long-term (5m) EMA.
    3. Volatility - Running standard deviation using online variance estimation.
    4. Recent Peak - Monotonic queue sliding window maximum.
    """

    def __init__(self, input_dim: int, window_size: int = 1500, short_window: int = 300):
        self.input_dim = input_dim
        self.window_size = window_size
        self.short_window = short_window

        # EMA alpha parameters: alpha = 2 / (N + 1)
        self.alpha_long = 2.0 / (window_size + 1)
        self.alpha_short = 2.0 / (short_window + 1)

        # Running statistics states
        self.ema_long = np.zeros(input_dim, dtype=np.float32)
        self.ema_short = np.zeros(input_dim, dtype=np.float32)
        self.ema_sq_long = np.zeros(input_dim, dtype=np.float32)

        # Peak calculators for each variable
        self.peaks = [SlidingWindowMax(window_size) for _ in range(input_dim)]
        self.initialized = False

    @staticmethod
    def _format_augmented(
        x: np.ndarray,
        ema_long: np.ndarray,
        ema_short: np.ndarray,
        ema_sq_long: np.ndarray,
        recent_peaks: np.ndarray,
    ) -> np.ndarray:
        """Builds the 5x augmented vector `[x, ema_long, trend, volatility, peaks]`."""
        variance = ema_sq_long - (ema_long**2)
        volatility = np.sqrt(np.clip(variance, 0.0, None))
        trend = ema_short - ema_long
        return np.concatenate([x, ema_long, trend, volatility, recent_peaks])

    def update(self, state_vector: np.ndarray) -> np.ndarray:
        """
        Updates the running metrics with a new state_vector and returns the augmented vector.

        Args:
            state_vector: Raw 1D numpy array of size input_dim.

        Returns:
            Augmented 1D numpy array of size 5 * input_dim.
        """
        assert (
            len(state_vector) == self.input_dim
        ), f"Input size mismatch. Expected {self.input_dim}, got {len(state_vector)}"

        x = state_vector.astype(np.float32)

        if not self.initialized:
            self.ema_long = x.copy()
            self.ema_short = x.copy()
            self.ema_sq_long = (x**2).copy()
            self.initialized = True
        else:
            self.ema_long = self.alpha_long * x + (1.0 - self.alpha_long) * self.ema_long
            self.ema_short = self.alpha_short * x + (1.0 - self.alpha_short) * self.ema_short
            self.ema_sq_long = self.alpha_long * (x**2) + (1.0 - self.alpha_long) * self.ema_sq_long

        recent_peaks = np.array([peak.update(val) for peak, val in zip(self.peaks, x)], dtype=np.float32)
        return self._format_augmented(x, self.ema_long, self.ema_short, self.ema_sq_long, recent_peaks)

    def peek(self, state_vector: np.ndarray) -> np.ndarray:
        """
        Computes the augmented state vector for `state_vector` without mutating running EMAs or peak windows.
        Used by secondary readers in the same simulation step to avoid double-updating statistics.
        """
        assert (
            len(state_vector) == self.input_dim
        ), f"Input size mismatch. Expected {self.input_dim}, got {len(state_vector)}"

        x = state_vector.astype(np.float32)
        if not self.initialized:
            ema_long = x
            ema_short = x
            ema_sq_long = x**2
            recent_peaks = x
        else:
            ema_long = self.alpha_long * x + (1.0 - self.alpha_long) * self.ema_long
            ema_short = self.alpha_short * x + (1.0 - self.alpha_short) * self.ema_short
            ema_sq_long = self.alpha_long * (x**2) + (1.0 - self.alpha_long) * self.ema_sq_long
            recent_peaks = np.array([peak.peek(val) for peak, val in zip(self.peaks, x)], dtype=np.float32)

        return self._format_augmented(x, ema_long, ema_short, ema_sq_long, recent_peaks)

    def reset(self):
        self.ema_long.fill(0.0)
        self.ema_short.fill(0.0)
        self.ema_sq_long.fill(0.0)
        for peak in self.peaks:
            peak.reset()
        self.initialized = False
