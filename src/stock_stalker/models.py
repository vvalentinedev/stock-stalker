from dataclasses import dataclass, field


@dataclass(frozen=True)
class TickerQuote:
    symbol: str
    average: float
    changes: dict[str, float] = field(default_factory=dict)
    error: str | None = None
