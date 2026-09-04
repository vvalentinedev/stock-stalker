import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any


class YFinanceProvider:
    def __init__(self, cache_ttl: int = 60, max_workers: int = 8):
        self.cache_ttl = cache_ttl
        self.max_workers = max_workers
        self._cache: dict[
            tuple[tuple[str, ...], str], tuple[float, dict[str, Any]]
        ] = {}
        self._single_cache: dict[tuple[str, str], tuple[float, Any]] = {}

    def fetch(self, tickers: list[str], period: str) -> dict[str, Any]:
        key = (tuple(sorted(tickers)), period)
        now = time.monotonic()
        if key in self._cache:
            ts, data = self._cache[key]
            if now - ts < self.cache_ttl:
                return data
        try:
            data = self._batch_download(tickers, period)
        except Exception:
            data = self._threaded_download(tickers, period)
        self._cache[key] = (now, data)
        return data

    def fetch_one(self, ticker: str, period: str) -> Any:
        key = (ticker, period)
        now = time.monotonic()
        if key in self._single_cache:
            ts, frame = self._single_cache[key]
            if now - ts < self.cache_ttl:
                return frame
        frame = self._download_one(ticker, period)
        self._single_cache[key] = (now, frame)
        return frame

    def _batch_download(self, tickers: list[str], period: str) -> dict[str, Any]:
        import yfinance as yf  # type: ignore[import-not-found]

        frame: Any = yf.download(
            tickers if len(tickers) > 1 else tickers[0],
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
        )
        result: dict[str, Any] = {}
        if frame is None or len(frame) == 0:
            raise ValueError("empty batch result")
        columns: Any = getattr(frame, "columns", None)
        nlevels: Any = getattr(columns, "nlevels", 1)
        if nlevels > 1:
            top = list(columns.get_level_values(0).unique())
            if top and top[0] in tickers:
                for ticker in tickers:
                    try:
                        sub = frame[ticker].dropna(how="all")
                    except KeyError:
                        continue
                    if sub is not None and len(sub) > 0:
                        result[ticker] = sub
                if result:
                    return result
        if len(tickers) == 1:
            result[tickers[0]] = frame
            return result
        raise ValueError("unexpected batch frame shape")

    def _threaded_download(self, tickers: list[str], period: str) -> dict[str, Any]:
        workers = max(1, min(self.max_workers, len(tickers)))
        result: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=workers) as executor:
            frames = list(executor.map(lambda t: self.fetch_one(t, period), tickers))
        for ticker, frame in zip(tickers, frames):
            if frame is None:
                continue
            try:
                is_empty = len(frame) == 0
            except TypeError:
                is_empty = False
            if not is_empty:
                result[ticker] = frame
        return result

    def _download_one(self, ticker: str, period: str) -> Any:
        import yfinance as yf  # type: ignore[import-not-found]

        return yf.download(
            ticker,
            period=period,
            auto_adjust=True,
            progress=False,
            group_by="column",
        )
