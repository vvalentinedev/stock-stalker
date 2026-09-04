from dataclasses import dataclass, field
from typing import Literal

Period = Literal["5d", "1mo", "ytd", "1y", "5y"]

VALID_PERIODS: tuple[str, ...] = ("5d", "1mo", "ytd", "1y", "5y")

PERIOD_LABELS: dict[str, tuple[str, ...]] = {
    "5d": ("5d",),
    "1mo": ("5d", "1mo"),
    "ytd": ("5d", "1mo", "ytd"),
    "1y": ("5d", "1mo", "ytd", "1y"),
    "5y": ("5d", "1mo", "ytd", "1y", "5y"),
}


@dataclass(frozen=True)
class TickerQuote:
    symbol: str
    average: float
    changes: dict[str, float] = field(default_factory=dict)
    error: str | None = None
