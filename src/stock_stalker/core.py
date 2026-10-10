from datetime import datetime
from typing import Any

from .models import PERIOD_LABELS, VALID_PERIODS, Period, ThemeGroup, TickerQuote
from .provider import YFinanceProvider
from .repository import (
    ThemeRepository,
    TickerRepository,
    normalize_ticker,
    validate_theme_name,
)

__all__ = ["Core", "PERIOD_LABELS", "VALID_PERIODS", "Period"]

TRADING_DAYS: dict[str, int] = {"5d": 5, "1mo": 21, "1y": 252}


class Core:
    def __init__(
        self,
        period: Period = "1y",
        repository: TickerRepository | None = None,
        provider: YFinanceProvider | None = None,
        theme_repository: ThemeRepository | None = None,
    ):
        self._validate_period(period)
        self._period: Period = period
        self._repository = repository or TickerRepository()
        self._provider = provider or YFinanceProvider()
        self._tickers: list[str] = self._repository.load()
        self._theme_repository = theme_repository or ThemeRepository()
        self._themes: dict[str, list[str]] = self._prune_themes(
            self._theme_repository.load()
        )

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

    @property
    def themes(self) -> dict[str, list[str]]:
        return {name: list(members) for name, members in self._themes.items()}

    def set_theme(self, name: str, tickers: list[str]) -> dict[str, list[str]]:
        theme = validate_theme_name(name)
        members = [self._validate_ticker(t) for t in tickers if str(t).strip()]
        members = list(dict.fromkeys(members))
        if not members:
            return self.delete_theme(theme)
        # Enforce single membership in memory before persisting.
        for other in list(self._themes.keys()):
            if other != theme:
                remaining = [t for t in self._themes[other] if t not in members]
                if remaining:
                    self._themes[other] = remaining
                else:
                    del self._themes[other]
        # Dict assignment keeps position for existing themes and appends
        # new themes at the end, which defines display order.
        self._themes[theme] = members
        self._themes = self._theme_repository.save(self._themes)
        # Theme members become tracked tickers so they are fetched.
        missing = [t for t in members if t not in self._tickers]
        if missing:
            self._tickers = self._repository.save([*self._tickers, *missing])
        return self.themes

    def delete_theme(self, name: str) -> dict[str, list[str]]:
        theme = validate_theme_name(name)
        self._themes.pop(theme, None)
        self._themes = self._theme_repository.save(self._themes)
        return self.themes

    def clear_themes(self) -> dict[str, list[str]]:
        self._themes = self._theme_repository.clear()
        return self.themes

    def get_grouped_quotes(self) -> list[ThemeGroup]:
        quotes = self.get_quotes()
        return self.group_quotes(quotes)

    def get_grouped_symbols(self) -> list[tuple[str | None, list[str]]]:
        """Theme grouping for loading placeholders (no fetch needed)."""
        themes = getattr(self, "_themes", {})
        groups: list[tuple[str | None, list[str]]] = []
        for theme, members in themes.items():
            tracked = [m for m in members if m in self._tickers]
            if tracked:
                groups.append((theme, tracked))
        themed = {m for members in themes.values() for m in members}
        ungrouped = [t for t in self._tickers if t not in themed]
        if ungrouped:
            groups.append((None, ungrouped))
        return groups

    def group_quotes(self, quotes: list[TickerQuote]) -> list[ThemeGroup]:
        by_symbol = {q.symbol: q for q in quotes}
        themes = getattr(self, "_themes", {})
        groups: list[ThemeGroup] = []
        for theme, members in themes.items():
            group_quotes = [by_symbol[m] for m in members if m in by_symbol]
            if group_quotes:
                groups.append(ThemeGroup(theme=theme, quotes=group_quotes))
        themed_symbols = {m for members in themes.values() for m in members}
        ungrouped = [q for q in quotes if q.symbol not in themed_symbols]
        if ungrouped:
            # Preserve ticker-list order for ungrouped members.
            order = {t: i for i, t in enumerate(self._tickers)}
            ungrouped.sort(key=lambda q: order.get(q.symbol, len(order)))
            groups.append(ThemeGroup(theme=None, quotes=ungrouped))
        return groups

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
        self._themes = self._prune_themes(getattr(self, "_themes", {}))
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
            theme_repo = getattr(self, "_theme_repository", None)
            if theme_repo is not None:
                theme_repo.remove_ticker(symbol)
                self._themes = theme_repo.load()
            elif hasattr(self, "_themes"):
                for name in list(self._themes.keys()):
                    if symbol in self._themes[name]:
                        self._themes[name] = [
                            t for t in self._themes[name] if t != symbol
                        ]
                        if not self._themes[name]:
                            del self._themes[name]
        return list(self._tickers)

    def _prune_themes(self, themes: dict[str, list[str]]) -> dict[str, list[str]]:
        """Drop theme members no longer tracked; persist if changed."""
        pruned: dict[str, list[str]] = {}
        for name, members in themes.items():
            remaining = [t for t in members if t in self._tickers]
            if remaining:
                pruned[name] = remaining
        theme_repo = getattr(self, "_theme_repository", None)
        if pruned != themes and theme_repo is not None:
            pruned = theme_repo.save(pruned)
        return pruned

    def get_quote(self, ticker: str) -> TickerQuote:
        """Fetch a one-shot quote for a single ticker without touching the saved list."""
        symbol = self._validate_ticker(ticker)
        return self._build_quote(
            symbol,
            self._provider.fetch_one(symbol, self._period),
            self._period,
            datetime.now(),
        )

    def _fetch_single_ticker(self, ticker: str) -> TickerQuote:
        return self.get_quote(ticker)

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
