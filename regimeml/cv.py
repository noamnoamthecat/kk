"""Purged walk-forward cross-validation with an embargo (Lopez de Prado).

Labels are forward ``horizon``-day returns, so a training row near the
test boundary shares outcome days with the test set. We purge those rows,
and add an embargo gap after each test block when training on later data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
import pandas as pd


@dataclass
class PurgedWalkForward:
    horizon: int = 5
    min_train_days: int = 750
    test_days: int = 126
    embargo_days: int = 5
    expanding: bool = True
    max_train_days: int | None = None

    def split(self, dates: pd.DatetimeIndex) -> Iterator[tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
        """Yield (train_dates, test_dates). Test blocks tile the tail of the sample."""
        u = pd.DatetimeIndex(np.unique(dates))
        start = self.min_train_days
        while start < len(u):
            test = u[start:start + self.test_days]
            # Purge: training labels must end strictly before the first test day.
            train_end = start - self.horizon - self.embargo_days
            train_start = 0 if self.expanding else max(0, train_end - (self.max_train_days or train_end))
            yield u[train_start:train_end], test
            start += self.test_days
