from datetime import datetime

import pytest

from stock_stalker.cli import CLI
from stock_stalker.core import Core
from stock_stalker.provider import YFinanceProvider
from stock_stalker.repository import ThemeRepository, TickerRepository


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


def make_core(
    tmp_path, period="1y", frames=None, theme_repository=None, tickers=None
):
    repo = TickerRepository(path=tmp_path / "stocks.csv")
    if tickers is not None:
        repo.save(tickers)
    provider = FakeProvider(frames or {})
    core = Core(
        period=period,
        repository=repo,
        provider=provider,
        theme_repository=theme_repository,
    )
    return core, repo, provider


def make_theme_core(tmp_path, **kwargs):
    trepo = ThemeRepository(path=tmp_path / "themes.json")
    core, _, _ = make_core(tmp_path, theme_repository=trepo, **kwargs)
    return core, trepo


def test_invalid_period_rejected(tmp_path):
    with pytest.raises(ValueError):
        make_core(tmp_path, period="100y")


def test_extended_period_labels():
    from stock_stalker.models import PERIOD_LABELS, period_labels

    assert period_labels("5d") == ("5d",)
    assert period_labels("1y") == ("5d", "1mo", "ytd", "1y")
    assert period_labels("5y") == ("5d", "1mo", "ytd", "1y", "5y")
    assert period_labels("10y") == ("5d", "1mo", "ytd", "1y", "5y", "10y")
    assert period_labels("25y") == ("5d", "1mo", "ytd", "1y", "5y", "25y")
    assert period_labels("max") == ("5d", "1mo", "ytd", "1y", "5y", "max")
    assert set(PERIOD_LABELS) == {
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
    }


def test_window_kwargs_period_vs_start():
    from stock_stalker.provider import YFinanceProvider

    assert YFinanceProvider._window_kwargs("5y") == {"period": "5y"}
    assert YFinanceProvider._window_kwargs("max") == {"period": "max"}
    kwargs = YFinanceProvider._window_kwargs("25y")
    assert set(kwargs) == {"start"}
    datetime.strptime(kwargs["start"], "%Y-%m-%d")


def test_long_window_truncated_marked(tmp_path):
    frames = {"YOUNG": FakeHist([100.0] * 3, [100.0] * 3)}
    core, _, _ = make_core(tmp_path, period="25y", frames=frames)
    core.set_ticker_list(["YOUNG"])
    quote = core.get_quotes()[0]
    assert quote.window_truncated is True
    assert quote.coverage_start is not None


def test_long_window_keeps_5y_column(tmp_path):
    years = list(range(2016, 2027))
    highs = [100.0] * len(years)
    lows = [100.0] * len(years)
    highs[-1] = lows[-1] = 200.0
    frames = {"AAPL": FakeHist(highs, lows, years=years)}
    core, _, _ = make_core(tmp_path, period="10y", frames=frames)
    core.set_ticker_list(["AAPL"])
    quote = core.get_quotes()[0]
    assert "5y" in quote.changes
    assert "10y" in quote.changes
    assert quote.changes["10y"] == 100.0
    assert quote.changes["5y"] == 100.0


def test_full_coverage_not_truncated(tmp_path):
    years = [2020, 2025, 2026]
    frames = {"OLD": FakeHist([100.0] * 3, [100.0] * 3, years=years)}
    core, _, _ = make_core(tmp_path, period="1y", frames=frames)
    core.set_ticker_list(["OLD"])
    quote = core.get_quotes()[0]
    assert quote.window_truncated is False


def test_cli_shows_window_coverage():
    import io
    from datetime import datetime as dt

    from rich.console import Console

    from stock_stalker.models import TickerQuote

    stream = io.StringIO()
    cli = CLI(interval=60, period="25y", console=Console(file=stream, width=140))
    cli.display_stock_data(
        [
            TickerQuote(
                symbol="AAPL",
                average=10.0,
                changes={"5d": 1.0, "1mo": 2.0, "ytd": 3.0, "1y": 4.0, "25y": 5.0},
                coverage_start=dt(2015, 6, 1),
                window_truncated=True,
            )
        ]
    )
    out = stream.getvalue()
    assert "5.00%*" in out
    assert "25y window limited" in out
    assert "2015-06-01" in out


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


def test_cli_renders_gains_losses_and_errors():
    import io

    from rich.console import Console

    from stock_stalker.models import TickerQuote

    stream = io.StringIO()
    cli = CLI(interval=60, period="1mo", console=Console(file=stream, width=120))
    cli.display_stock_data(
        [
            TickerQuote(symbol="AAPL", average=10.0, changes={"5d": 1.5, "1mo": -2.0}),
            TickerQuote(symbol="FAIL", average=float("nan"), error="no data"),
        ]
    )
    out = stream.getvalue()
    assert "AAPL" in out and "1.50%" in out and "-2.00%" in out
    assert "FAIL" in out and "N/A" in out and "no data" in out


def test_cli_validates_args():
    import pytest as pt

    with pt.raises(ValueError):
        CLI(interval=0, period="1mo")
    with pt.raises(ValueError):
        CLI(interval=60, period="100y")


def test_cli_does_not_clear_by_default():
    import io

    from rich.console import Console

    from stock_stalker.models import TickerQuote

    stream = io.StringIO()
    cleared = {"n": 0}
    console = Console(file=stream, width=120)

    def _fail_clear():
        cleared["n"] += 1
        raise AssertionError("clear should be opt-in")

    console.clear = _fail_clear  # type: ignore[method-assign]
    cli = CLI(interval=60, period="5d", console=console)
    cli.display_stock_data(
        [TickerQuote(symbol="AAPL", average=10.0, changes={"5d": 0.0})]
    )
    assert cleared["n"] == 0


def test_help_lists_all_flags(capsys):
    import pytest as pt

    from stock_stalker.main import build_parser

    with pt.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in (
        "--newlist",
        "--newlist-append",
        "--newlist-remove",
        "--period",
        "--interval",
    ):
        assert flag in out
    assert "examples:" in out


def test_bad_period_exits_with_error(capsys):
    import pytest as pt

    from stock_stalker.main import build_parser

    with pt.raises(SystemExit) as exc:
        build_parser().parse_args(["--period", "100y"])
    assert exc.value.code == 2


def test_newlist_replaces_persisted_tickers(tmp_path, monkeypatch):
    from stock_stalker import main as main_module


    repo = TickerRepository(path=tmp_path / "stocks.csv")
    monkeypatch.setattr(
        main_module.Core,
        "__init__",
        lambda self, period="1y", repository=None, provider=None: (
            setattr(self, "_period", period)
            or setattr(self, "_tickers", repo.load())
            or setattr(self, "_repository", repo)
            or setattr(self, "_provider", None)
        ),
    )
    monkeypatch.setattr(
        main_module.Core,
        "get_quotes",
        lambda self: (_ for _ in ()).throw(KeyboardInterrupt),
    )
    monkeypatch.setattr(
        main_module.CLI, "display_stock_data", lambda self, quotes: None
    )
    monkeypatch.setattr(main_module.time, "sleep", lambda seconds: None)
    main_module.main(["--newlist", "AAPL", "MSFT"])
    assert repo.load() == ["AAPL", "MSFT"]


def test_parse_theme_spec_subfolders():
    from stock_stalker.repository import parse_theme_spec

    assert parse_theme_spec("TECH:GOOG,NVDA") == (["TECH"], ["GOOG", "NVDA"])
    assert parse_theme_spec("TECH:FAANG:GOOG,NVDA") == (
        ["TECH", "FAANG"],
        ["GOOG", "NVDA"],
    )
    assert parse_theme_spec("tech:faang=goog,nvda") == (
        ["TECH", "FAANG"],
        ["GOOG", "NVDA"],
    )
    assert parse_theme_spec("TECH:FAANG:") == (["TECH", "FAANG"], [])


def test_parse_theme_spec_requires_separator():
    from stock_stalker.repository import parse_theme_spec

    with pytest.raises(ValueError):
        parse_theme_spec("TECH")


def test_set_theme_subfolder(tmp_path):
    core, _ = make_theme_core(tmp_path, tickers=["GOOG", "NVDA"])
    core.set_theme(["TECH", "FAANG"], ["GOOG", "NVDA"])
    assert core.themes == {"TECH/FAANG": ["GOOG", "NVDA"]}
    assert set(core.tickers_list) == {"GOOG", "NVDA"}


def test_append_creates_and_deduplicates(tmp_path):
    core, _ = make_theme_core(tmp_path)
    core.append_to_theme(["TECH", "FAANG"], ["GOOG"])
    assert core.themes == {"TECH/FAANG": ["GOOG"]}
    core.append_to_theme(["TECH", "FAANG"], ["GOOG", "NVDA"])
    assert core.themes == {"TECH/FAANG": ["GOOG", "NVDA"]}


def test_append_enforces_single_membership(tmp_path):
    core, _ = make_theme_core(tmp_path)
    core.append_to_theme(["TECH", "FAANG"], ["GOOG", "NVDA"])
    core.append_to_theme(["TECH", "SEMI"], ["NVDA"])
    assert core.themes == {"TECH/FAANG": ["GOOG"], "TECH/SEMI": ["NVDA"]}


def test_delete_theme_removes_subtree(tmp_path):
    core, _ = make_theme_core(tmp_path)
    core.set_theme(["TECH", "FAANG"], ["GOOG"])
    core.set_theme(["TECH", "SEMI"], ["NVDA"])
    core.set_theme(["BANK"], ["JPM"])
    core.delete_theme(["TECH"])
    assert set(core.themes) == {"BANK"}


def test_get_grouped_symbols_nested(tmp_path):
    from stock_stalker.models import ThemeTree

    core, _ = make_theme_core(
        tmp_path, tickers=["MSFT", "GOOG", "NVDA", "JPM"]
    )
    core.set_theme(["TECH"], ["MSFT"])
    core.set_theme(["TECH", "FAANG"], ["GOOG", "NVDA"])
    core.set_theme(["BANK"], ["JPM"])
    groups = core.get_grouped_symbols()
    assert [g.name for g in groups] == ["TECH", "BANK"]
    tech = groups[0]
    assert tech.symbols == ["MSFT"]
    assert tech.children == [ThemeTree(name="FAANG", symbols=["GOOG", "NVDA"])]


def test_group_quotes_nested(tmp_path):
    from stock_stalker.models import TickerQuote

    core, _ = make_theme_core(tmp_path)
    core.set_theme(["TECH"], ["MSFT"])
    core.set_theme(["TECH", "FAANG"], ["GOOG", "NVDA"])
    quotes = [
        TickerQuote(symbol=s, average=1.0) for s in ("MSFT", "GOOG", "NVDA", "TSLA")
    ]
    groups = core.group_quotes(quotes)
    assert groups[0].theme == "TECH"
    assert [q.symbol for q in groups[0].quotes] == ["MSFT"]
    assert groups[0].children[0].theme == "FAANG"
    assert [q.symbol for q in groups[0].children[0].quotes] == ["GOOG", "NVDA"]
    assert groups[-1].theme is None
    assert [q.symbol for q in groups[-1].quotes] == ["TSLA"]


def test_cli_renders_subthemes():
    import io

    from rich.console import Console

    from stock_stalker.models import ThemeGroup, TickerQuote

    stream = io.StringIO()
    cli = CLI(interval=60, period="1mo", console=Console(file=stream, width=140))
    groups = [
        ThemeGroup(
            theme="TECH",
            quotes=[TickerQuote(symbol="MSFT", average=1.0)],
            children=[
                ThemeGroup(
                    theme="FAANG",
                    quotes=[TickerQuote(symbol="GOOG", average=1.0)],
                )
            ],
        )
    ]
    cli.display_grouped_data(groups)
    out = stream.getvalue()
    assert "TECH" in out and "FAANG" in out
    assert "MSFT" in out and "GOOG" in out
    assert "▸ FAANG" in out


def test_theme_append_flag_wiring(monkeypatch):
    from stock_stalker import main as main_module

    calls = []

    def _fake_init(self, period="1y", **kwargs):
        self._period = period
        self._tickers = []
        self._themes = {"TECH/FAANG": ["GOOG"]}

    monkeypatch.setattr(main_module.Core, "__init__", _fake_init)
    monkeypatch.setattr(
        main_module.Core,
        "append_to_theme",
        lambda self, path, members: calls.append((list(path), list(members))),
    )
    monkeypatch.setattr(main_module.CLI, "display_live_grouped", lambda *a, **k: None)
    main_module.main(["--theme-append", "TECH:FAANG:GOOG,NVDA"])
    assert calls == [(["TECH", "FAANG"], ["GOOG", "NVDA"])]
