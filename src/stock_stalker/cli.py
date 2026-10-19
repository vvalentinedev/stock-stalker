import math
import sys
from collections.abc import Callable
from typing import TextIO

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .models import PERIOD_LABELS, VALID_PERIODS, ThemeGroup, TickerQuote


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
            table.add_row(*self._row(quote, labels, period=period))
        return table

    def build_grouped(self, groups: list[ThemeGroup], period: str) -> Table:
        """Option 1 style: single table, theme header rows + indented members.

        No aggregate/summary rows (deferred). A lone ungrouped group renders
        flat so non-theme users see no change.
        """
        labels = PERIOD_LABELS[period]
        table = self._table(labels)
        flat = len(groups) == 1 and groups[0].theme is None
        first = True
        for group in groups:
            if not group.quotes:
                continue
            if not flat:
                if not first:
                    table.add_section()
                table.add_row(*self._theme_header(group, len(labels)))
                first = False
            for quote in group.quotes:
                table.add_row(*self._row(quote, labels, indent=not flat, period=period))
        return table

    def build_loading(self, symbols: list[str], period: str) -> Table:
        labels = PERIOD_LABELS[period]
        table = self._table(labels)
        for symbol in symbols:
            row: list[Text | str] = [Text(symbol, style="bold")]
            row.extend(Text("--", style="dim") for _ in range(len(labels) + 1))
            table.add_row(*row)
        return table

    def build_loading_grouped(
        self, groups: list[tuple[str | None, list[str]]], period: str
    ) -> Table:
        labels = PERIOD_LABELS[period]
        table = self._table(labels)
        flat = len(groups) == 1 and groups[0][0] is None
        first = True
        for theme, symbols in groups:
            if not symbols:
                continue
            if not flat:
                if not first:
                    table.add_section()
                table.add_row(
                    *self._theme_header(
                        ThemeGroup(theme=theme, quotes=[]), len(labels), count=len(symbols)
                    )
                )
                first = False
            for symbol in symbols:
                row: list[Text | str] = [
                    Text(f"  {symbol}" if not flat else symbol, style="bold")
                ]
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

    def _theme_header(
        self, group: ThemeGroup, n_labels: int, count: int | None = None
    ) -> list[Text]:
        n = count if count is not None else len(group.quotes)
        if group.theme is None:
            title = f"▸ OTHER ({n})"
            style = "bold dim"
        else:
            title = f"▸ {group.theme} ({n})"
            style = "bold cyan"
        cells: list[Text] = [Text(title, style=style)]
        cells.extend(Text("", style="dim") for _ in range(n_labels + 1))
        return cells

    def _row(
        self,
        quote: TickerQuote,
        labels: tuple[str, ...],
        indent: bool = False,
        period: str | None = None,
    ) -> list[Text | str]:
        symbol_text = f"  {quote.symbol}" if indent else quote.symbol
        if quote.error is not None or self._is_nan(quote.average):
            cells: list[Text | str] = [
                Text(symbol_text, style="bold"),
                Text("N/A", style="dim"),
            ]
            cells.extend(Text("N/A", style="dim") for _ in labels)
            return cells
        cells = [
            Text(symbol_text, style="bold"),
            Text(f"{quote.average:.2f}", justify="right"),
        ]
        for label in labels:
            value = quote.changes.get(label)
            if value is None or self._is_nan(value):
                cells.append(Text("N/A", style="dim"))
            else:
                style = "green" if value >= 0 else "red"
                text = f"{value:.2f}%"
                if (
                    period is not None
                    and label == period
                    and quote.window_truncated
                ):
                    text += "*"
                cells.append(Text(text, style=style))
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

    def render_grouped(self, groups: list[ThemeGroup]) -> Table:
        return self._renderer.build_grouped(groups, self.period)

    def _print_footnotes(self, quotes: list[TickerQuote]) -> None:
        for quote in quotes:
            if quote.error is not None:
                self._console.print(
                    f"{quote.symbol}: N/A ({quote.error})", style="dim"
                )
                continue
            if quote.coverage_start is None:
                continue
            when = quote.coverage_start.strftime("%Y-%m-%d")
            if self.period == "max":
                self._console.print(
                    f"{quote.symbol}: history available since {when}", style="dim"
                )
            elif quote.window_truncated:
                self._console.print(
                    f"{quote.symbol}: {self.period} window limited to available "
                    f"history since {when}",
                    style="dim",
                )

    def display_stock_data(self, quotes: list[TickerQuote]) -> None:
        if self.clear:
            self._console.clear()
        self._console.print(self.render(quotes))
        self._print_footnotes(quotes)
        if self.watch:
            self._console.print(
                f"\nNext update in {self.interval} seconds...", style="dim"
            )

    def display_grouped_data(self, groups: list[ThemeGroup]) -> None:
        if self.clear:
            self._console.clear()
        self._console.print(self.render_grouped(groups))
        self._print_footnotes([q for group in groups for q in group.quotes])
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
        self._print_footnotes(quotes)
        if self.watch:
            self._console.print(
                f"\nNext update in {self.interval} seconds...", style="dim"
            )
        return quotes

    def display_live_grouped(
        self,
        grouped_symbols: list[tuple[str | None, list[str]]],
        loader: Callable[[], list[ThemeGroup]],
    ) -> list[ThemeGroup]:
        flat_tickers = [t for _, syms in grouped_symbols for t in syms]
        if not flat_tickers:
            self.display_grouped_data([])
            return []
        loading = self._renderer.build_loading_grouped(grouped_symbols, self.period)
        if not self._console.is_terminal:
            self._console.print(loading)
            groups = loader()
            self.display_grouped_data(groups)
            return groups
        if self.clear:
            self._console.clear()
        from rich.live import Live

        with Live(loading, console=self._console, refresh_per_second=4) as live:
            groups = loader()
            live.update(self._renderer.build_grouped(groups, self.period))
        self._print_footnotes([q for group in groups for q in group.quotes])
        if self.watch:
            self._console.print(
                f"\nNext update in {self.interval} seconds...", style="dim"
            )
        return groups
