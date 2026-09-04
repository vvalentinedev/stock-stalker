from datetime import datetime

import pytest

from stock_stalker.cli import CLI
from stock_stalker.core import Core
from stock_stalker.provider import YFinanceProvider
from stock_stalker.repository import TickerRepository


class FakeIloc:
    def __init__(self, values):
        self._values = values

    def __getitem__(self, idx):
        return self._values[idx]


class FakeColumn:
    def __init__(self, values):
        self.iloc = FakeIloc(list(values))


class FakeHist:
    def __init__(self, highs, lows, years=None):
        assert len(highs) == len(lows)
        self._cols = {"high": list(highs), "low": list(lows)}
        self.columns = ["High", "Low"]
        now_year = datetime.now().year
        if years is None:
            years = [now_year] * len(highs)
        self.index = [datetime(y, 6, 1) for y in years]

    def __len__(self):
        return len(self._cols["high"])

    def __getitem__(self, key):
        return FakeColumn(self._cols[str(key).lower()])


class FakeProvider(YFinanceProvider):
    def __init__(self, frames):
        super().__init__(cache_ttl=60)
        self.frames = frames
        self.fetch_calls = 0

    def fetch(self, tickers, period):
        self.fetch_calls += 1
        return {t: self.frames[t] for t in tickers if t in self.frames}

    def fetch_one(self, ticker, period):
        return self.frames[ticker]


def make_core(tmp_path, period="1y", frames=None):
    repo = TickerRepository(path=tmp_path / "stocks.csv")
    provider = FakeProvider(frames or {})
    core = Core(period=period, repository=repo, provider=provider)
    return core, repo, provider


def test_invalid_period_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_core(tmp_path, period="10y")


def test_tickers_not_shared_between_instances(tmp_path):
    c1, _, _ = make_core(tmp_path, frames={})
    c1.append_item_to_ticker_list("MSFT")
    c2 = Core(period="1y", repository=TickerRepository(path=tmp_path / "other.csv"))
    assert "MSFT" not in c2.tickers_list


def test_persistence_auto_sync(tmp_path):
    core, repo, _ = make_core(tmp_path, frames={})
    core.set_ticker_list(["aapl", "aapl", " msft "])
    assert core.tickers_list == ["AAPL", "MSFT"]
    assert repo.load() == ["AAPL", "MSFT"]
    core.append_item_to_ticker_list("tsla")
    assert repo.load() == ["AAPL", "MSFT", "TSLA"]
    core.remove_item_from_ticker_list("aapl")
    assert repo.load() == ["MSFT", "TSLA"]


def test_invalid_ticker_rejected(tmp_path):
    core, _, _ = make_core(tmp_path, frames={})
    with pytest.raises(ValueError):
        core.append_item_to_ticker_list("!!!")


def test_quote_math_and_single_batch_call(tmp_path):
    highs = [100.0] * 30
    lows = [100.0] * 30
    highs[-1] = 110.0
    lows[-1] = 110.0
    frames = {"AAPL": FakeHist(highs, lows)}
    core, _, provider = make_core(tmp_path, period="1mo", frames=frames)
    core.set_ticker_list(["AAPL"])
    quotes = core.get_quotes()
    assert provider.fetch_calls == 1
    assert quotes[0].average == 110.0
    assert quotes[0].changes["1mo"] == 10.0
    assert quotes[0].changes["5d"] == pytest.approx(10.0)


def test_trailing_nan_row_skipped(tmp_path):
    frames = {"AAPL": FakeHist([100.0, float("nan")], [100.0, float("nan")])}
    core, _, _ = make_core(tmp_path, period="5d", frames=frames)
    core.set_ticker_list(["AAPL"])
    quotes = core.get_quotes()
    assert quotes[0].average == 100.0


def test_empty_hist_returns_error_quote(tmp_path):
    frames = {"AAPL": FakeHist([], [])}
    core, _, _ = make_core(tmp_path, frames=frames)
    core.set_ticker_list(["AAPL"])
    quotes = core.get_quotes()
    assert quotes[0].error is not None


def test_provider_caches_batch(tmp_path):
    provider = YFinanceProvider(cache_ttl=600)
    calls = {"n": 0}

    def fake_batch(tickers, period):
        calls["n"] += 1
        return {t: FakeHist([10.0], [10.0]) for t in tickers}

    provider._batch_download = fake_batch  # type: ignore[method-assign]
    provider.fetch(["AAPL"], "1y")
    provider.fetch(["AAPL"], "1y")
    assert calls["n"] == 1


def test_cli_handles_dataclass_and_legacy_dict(capsys):
    cli = CLI(interval=60, period="1mo")
    from stock_stalker.models import TickerQuote

    cli.display_stock_data(
        [TickerQuote(symbol="AAPL", average=10.0, changes={"5d": 1.5, "1mo": -2.0})]
    )
    out = capsys.readouterr().out
    assert "AAPL" in out and "1.50%" in out
    cli.display_stock_data([{"symbol": "MSFT", "average": 20.0, "5d": 3.0, "1mo": 4.0}])
    out = capsys.readouterr().out
    assert "MSFT" in out and "3.00%" in out
