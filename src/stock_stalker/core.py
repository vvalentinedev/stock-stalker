from datetime import datetime
from typing import Any, Literal

from .models import TickerQuote
from .provider import YFinanceProvider
from .repository import TickerRepository, normalize_ticker

Period = Literal["5d", "1mo", "ytd", "1y", "5y"]

VALID_PERIODS: tuple[str, ...] = ("5d", "1mo", "ytd", "1y", "5y")

PERIOD_LABELS: dict[str, tuple[str, ...]] = {
    "5d": ("5d",),
    "1mo": ("5d", "1mo"),
    "ytd": ("5d", "1mo", "ytd"),
    "1y": ("5d", "1mo", "ytd", "1y"),
    "5y": ("5d", "1mo", "ytd", "1y", "5y"),
}

TRADING_DAYS: dict[str, int] = {"5d": 5, "1mo": 21, "1y": 252}


class Core:
    def __init__(
        self,
        period: Period = "1y",
        repository: TickerRepository | None = None,
        provider: YFinanceProvider | None = None,
    ):
        self._validate_period(period)
        self._period: Period = period
        self._repository = repository or TickerRepository()
        self._provider = provider or YFinanceProvider()
        self._tickers: list[str] = self._repository.load()

    @property
    def period(self) -> Period:
        return self._period

    @period.setter
    def period(self, value: Period) -> None:
        self._validate_period(value)
        self._period = value

    @property
    def tickers_list(self) -> list[str]:
        return list(self._tickers)

    @tickers_list.setter
    def tickers_list(self, value: list[str]) -> None:
        self.set_ticker_list(value)

    def get_quotes(self) -> list[TickerQuote]:
        if not self._tickers:
            return []
        now = datetime.now()
        histories = self._provider.fetch(self._tickers, self._period)
        return [
            self._build_quote(symbol, histories.get(symbol), self._period, now)
            for symbol in self._tickers
        ]

    def get_ticker_list(self) -> list[TickerQuote]:
        return self.get_quotes()

    def set_ticker_list(self, tickers: list[str]) -> list[str]:
        self._tickers = self._repository.save(tickers)
        return list(self._tickers)

    def append_item_to_ticker_list(self, ticker: str) -> list[str]:
        symbol = self._validate_ticker(ticker)
        if symbol not in self._tickers:
            self._tickers = self._repository.save([*self._tickers, symbol])
        return list(self._tickers)

    def remove_item_from_ticker_list(self, ticker: str) -> list[str]:
        symbol = normalize_ticker(ticker)
        if symbol in self._tickers:
            remaining = [t for t in self._tickers if t != symbol]
            self._tickers = self._repository.save(remaining)
        return list(self._tickers)

    def _fetch_single_ticker(self, ticker: str) -> TickerQuote:
        return self._build_quote(
            ticker,
            self._provider.fetch_one(ticker, self._period),
            self._period,
            datetime.now(),
        )

    def _get_percentage_change(
        self, hist: object, offset: int, current_price: float
    ) -> float:
        ref = self._row_average(hist, offset)
        return self._pct_change(current_price, ref)

    def _build_quote(
        self, symbol: str, hist: object, period: str, now: datetime
    ) -> TickerQuote:
        if hist is None:
            return TickerQuote(symbol=symbol, average=float("nan"), error="no data")
        try:
            length = len(hist)  # type: ignore[arg-type]
        except TypeError:
            return TickerQuote(symbol=symbol, average=float("nan"), error="no data")
        if length == 0:
            return TickerQuote(symbol=symbol, average=float("nan"), error="no data")
        last_idx = self._last_valid_index(hist, length - 1)
        if last_idx < 0:
            return TickerQuote(symbol=symbol, average=float("nan"), error="no data")
        try:
            current = self._row_average(hist, last_idx)
        except (KeyError, IndexError, ValueError):
            return TickerQuote(symbol=symbol, average=float("nan"), error="no data")
        changes: dict[str, float] = {}
        for label in PERIOD_LABELS[period]:
            try:
                ref_idx = self._reference_index(
                    hist, label, period, last_idx, now, length
                )
                ref = self._row_average(hist, ref_idx)
                changes[label] = self._pct_change(current, ref)
            except (KeyError, IndexError, ValueError, ZeroDivisionError):
                continue
        return TickerQuote(symbol=symbol, average=current, changes=changes)

    def _last_valid_index(self, hist: object, start: int) -> int:
        for idx in range(start, -1, -1):
            try:
                self._row_average(hist, idx)
                return idx
            except (KeyError, IndexError, ValueError):
                continue
        return -1

    def _reference_index(
        self,
        hist: object,
        label: str,
        period: str,
        last_idx: int,
        now: datetime,
        length: int,
    ) -> int:
        if label == period:
            return 0
        if label == "ytd":
            return self._ytd_start_index(hist, last_idx, now)
        lookback = TRADING_DAYS[label]
        return max(0, last_idx - lookback)

    def _ytd_start_index(self, hist: object, last_idx: int, now: datetime) -> int:
        try:
            index = hist.index  # type: ignore[union-attr]
            for i in range(last_idx + 1):
                ts = index[i]
                year = ts.year if hasattr(ts, "year") else int(str(ts)[:4])
                if year >= now.year:
                    return i
        except (IndexError, AttributeError, ValueError, TypeError):
            pass
        return 0

    def _row_average(self, hist: Any, idx: int) -> float:
        import math

        high: Any = self._cell(hist, idx, "high", fallback_pos=1)
        low: Any = self._cell(hist, idx, "low", fallback_pos=2)
        if high is None or low is None:
            raise ValueError("missing price")
        high_f = float(high)  # type: ignore[arg-type]
        low_f = float(low)  # type: ignore[arg-type]
        if math.isnan(high_f) or math.isnan(low_f):
            raise ValueError("missing price")
        return (high_f + low_f) / 2

    def _cell(self, hist: Any, idx: int, name: str, fallback_pos: int) -> Any:
        frame = hist
        cols = getattr(frame, "columns", None)
        if cols is not None:
            names = (
                list(cols)
                if not hasattr(cols, "nlevels") or cols.nlevels == 1
                else None
            )
            if names is None:
                try:
                    flat = frame.copy()  # type: ignore[union-attr]
                    flat.columns = cols.get_level_values(-1)
                    frame = flat
                    names = list(flat.columns)
                except (AttributeError, ValueError):
                    names = []
            lowered = {str(c).lower(): c for c in names}
            if name in lowered:
                return frame[lowered[name]].iloc[idx]  # type: ignore[index]
        iloc = getattr(frame, "iloc", None)
        if iloc is not None:
            return iloc[idx].iloc[fallback_pos]
        raise KeyError(name)

    @staticmethod
    def _pct_change(current: float, reference: float) -> float:
        if reference == 0:
            raise ZeroDivisionError("zero reference price")
        return round(((current - reference) / reference) * 100, 2)

    @staticmethod
    def _validate_period(period: str) -> None:
        if period not in VALID_PERIODS:
            raise ValueError(
                f"invalid period {period!r}, expected one of {VALID_PERIODS}"
            )

    @staticmethod
    def _validate_ticker(ticker: str) -> str:
        symbol = normalize_ticker(ticker)
        if not symbol or len(symbol) > 12:
            raise ValueError(f"invalid ticker {ticker!r}")
        if not all(c.isalnum() or c in ".-" for c in symbol):
            raise ValueError(f"invalid ticker {ticker!r}")
        return symbol

    def _get_ticker_list_dir(self) -> object:
        return self._repository.path

    def _get_ticker_list(self) -> list[str]:
        self._tickers = self._repository.load()
        return list(self._tickers)

    def _set_ticker_list(self, tickers: list[str]) -> list[str]:
        return self.set_ticker_list(tickers)
