from pathlib import Path

from platformdirs import user_data_dir

DEFAULT_TICKERS = ("AAPL", "NVDA", "GOOG")
APP_NAME = "Stock Stalker"


def default_csv_path() -> Path:
    data_dir = Path(user_data_dir(appname=APP_NAME, appauthor=False))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "my_stock_list.csv"


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


class TickerRepository:
    def __init__(self, path: Path | None = None):
        self.path = path or default_csv_path()

    def load(self) -> list[str]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return list(DEFAULT_TICKERS)
        tickers: list[str] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            symbol = normalize_ticker(line)
            if symbol and symbol not in tickers:
                tickers.append(symbol)
        return tickers or list(DEFAULT_TICKERS)

    def save(self, tickers: list[str]) -> list[str]:
        cleaned = [normalize_ticker(t) for t in tickers if t.strip()]
        deduped = list(dict.fromkeys(cleaned))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(deduped), encoding="utf-8")
        return deduped
