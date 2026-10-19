from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Period = Literal[
    "5d", "1mo", "ytd", "1y", "2y", "5y", "10y", "15y", "20y", "25y", "max"
]

PERIOD_ORDER: tuple[str, ...] = (
    "5d",
    "1mo",
    "ytd",
    "1y",
    "2y",
    "5y",
    "10y",
    "15y",
    "20y",
    "25y",
    "max",
)

VALID_PERIODS: tuple[str, ...] = PERIOD_ORDER

# Bounded set of quick-glance change columns. The selected window is appended
# as its own column whenever it is not already part of this ladder, so long
# windows keep their baseline columns and add a single extra column.
BASE_LADDER: tuple[str, ...] = ("5d", "1mo", "ytd", "1y", "5y")

_PERIOD_RANK: dict[str, int] = {p: i for i, p in enumerate(PERIOD_ORDER)}


def period_labels(period: str) -> tuple[str, ...]:
    if period not in _PERIOD_RANK:
        raise ValueError(
            f"invalid period {period!r}, expected one of {VALID_PERIODS}"
        )
    rank = _PERIOD_RANK[period]
    labels = tuple(p for p in BASE_LADDER if _PERIOD_RANK[p] <= rank)
    if period not in BASE_LADDER:
        labels = (*labels, period)
    return labels


PERIOD_LABELS: dict[str, tuple[str, ...]] = {
    p: period_labels(p) for p in VALID_PERIODS
}


@dataclass(frozen=True)
class TickerQuote:
    symbol: str
    average: float
    changes: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    coverage_start: datetime | None = None
    window_truncated: bool = False


@dataclass(frozen=True)
class ThemeGroup:
    """One visual group: a named theme/subtheme, or None for ungrouped tickers."""

    theme: str | None
    quotes: list[TickerQuote] = field(default_factory=list)
    children: list["ThemeGroup"] = field(default_factory=list)


@dataclass(frozen=True)
class ThemeTree:
    """Symbol-only counterpart of ThemeGroup used for loading placeholders."""

    name: str | None
    symbols: list[str] = field(default_factory=list)
    children: list["ThemeTree"] = field(default_factory=list)
