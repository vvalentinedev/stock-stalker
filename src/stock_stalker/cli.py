import math
import sys
from collections.abc import Callable
from typing import TextIO

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models import PERIOD_LABELS, VALID_PERIODS, TickerQuote


CLASSIC_BOX = box.Box(
    "----\n  | \n----\n  | \n    \n    \n  | \n----\n",
    ascii=True,
)


class TableRenderer:
    def __init__(self, modern: bool = False):
        self.modern = modern

    def build(self, quotes: list[TickerQuote], period: str) -> Table:
        labels = PERIOD_LABELS[period]
        table = self._table(labels)
        for quote in quotes:
            table.add_row(*self._row(quote, labels))
        return table

    def build_loading(self, symbols: list[str], period: str) -> Table:
        labels = PERIOD_LABELS[period]
        table = self._table(labels)
        for symbol in symbols:
            row: list[Text | str] = [Text(symbol, style="bold")]
            row.extend(Text("--", style="dim") for _ in range(len(labels) + 1))
            table.add_row(*row)
        return table

    def _table(self, labels: tuple[str, ...]) -> Table:
        if self.modern:
            table = Table(show_lines=False)
        else:
            table = Table(
                show_lines=False,
                box=CLASSIC_BOX,
                padding=(0, 1),
            )
        table.add_column("Symbol", style="bold", no_wrap=True)
        table.add_column("Average", justify="right")
        for label in labels:
            table.add_column(label, justify="right")
        return table

    def _row(self, quote: TickerQuote, labels: tuple[str, ...]) -> list[Text | str]:
        if quote.error is not None or self._is_nan(quote.average):
            cells: list[Text | str] = [
                Text(quote.symbol, style="bold"),
                Text("N/A", style="dim"),
            ]
            cells.extend(Text("N/A", style="dim") for _ in labels)
            return cells
        cells = [
            Text(quote.symbol, style="bold"),
            Text(f"{quote.average:.2f}", justify="right"),
        ]
        for label in labels:
            value = quote.changes.get(label)
            if value is None or self._is_nan(value):
                cells.append(Text("N/A", style="dim"))
            else:
                style = "green" if value >= 0 else "red"
                cells.append(Text(f"{value:.2f}%", style=style))
        return cells

    @staticmethod
    def _is_nan(value: float) -> bool:
        try:
            return math.isnan(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return False


class CLI:
    def __init__(
        self,
        interval: int = 60,
        period: str = "1y",
        clear: bool = False,
        output: TextIO | None = None,
        console: Console | None = None,
        renderer: TableRenderer | None = None,
        modern: bool = False,
        watch: bool = False,
    ):
        if period not in VALID_PERIODS:
            raise ValueError(
                f"invalid period {period!r}, expected one of {VALID_PERIODS}"
            )
        if interval <= 0:
            raise ValueError(
                f"invalid interval {interval!r}, expected a positive integer"
            )
        self.interval = interval
        self.period = period
        self.clear = clear
        self.modern = modern
        self.watch = watch
        self._renderer = renderer or TableRenderer(modern=modern)
        self._console = console or Console(file=output or sys.stdout)

    def render(self, quotes: list[TickerQuote]) -> Table:
        return self._renderer.build(quotes, self.period)

    def display_stock_data(self, quotes: list[TickerQuote]) -> None:
        if self.clear:
            self._console.clear()
        self._console.print(self.render(quotes))
        errors = [q for q in quotes if q.error is not None]
        for quote in errors:
            self._console.print(f"{quote.symbol}: N/A ({quote.error})", style="dim")
        if self.watch:
            self._console.print(
                f"\nNext update in {self.interval} seconds...", style="dim"
            )

    def display_live(
        self,
        tickers: list[str],
        loader: Callable[[], list[TickerQuote]],
    ) -> list[TickerQuote]:
        if not tickers:
            self.display_stock_data([])
            return []
        loading = self._renderer.build_loading(tickers, self.period)
        if not self._console.is_terminal:
            self._console.print(loading)
            quotes = loader()
            self.display_stock_data(quotes)
            return quotes
        if self.clear:
            self._console.clear()
        from rich.live import Live

        with Live(loading, console=self._console, refresh_per_second=4) as live:
            quotes = loader()
            live.update(self._renderer.build(quotes, self.period))
        for quote in quotes:
            if quote.error is not None:
                self._console.print(f"{quote.symbol}: N/A ({quote.error})", style="dim")
        if self.watch:
            self._console.print(
                f"\nNext update in {self.interval} seconds...", style="dim"
            )
        return quotes
