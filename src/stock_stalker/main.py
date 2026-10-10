import argparse
import time

from .cli import CLI
from .core import Core
from .models import VALID_PERIODS, TickerQuote
from .repository import normalize_ticker, parse_theme_spec


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-stalker",
        description="Monitor your favorite stocks from Yahoo Finance.",
        epilog="examples:\n"
        "  stock-stalker --newlist AAPL NVDA\n"
        "  stock-stalker --newlist-append MSFT --period 1mo\n"
        "  stock-stalker --newlist-remove GOOG\n"
        "  stock-stalker --theme \"TECH:AAPL,NVDA,GOOG\"\n"
        "  stock-stalker --theme \"TECH:AAPL,NVDA\" --theme \"BANK:JPM,BAC\"\n"
        "  stock-stalker --theme-list\n"
        "  stock-stalker --theme-clear\n"
        "  stock-stalker --peek GOOG\n"
        "  stock-stalker --peek GOOG --period 1mo\n"
        "  stock-stalker --period ytd --interval 30\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument(
        "--newlist",
        nargs="+",
        metavar="TICKER",
        help="replace the tracked ticker list",
    )
    targets.add_argument(
        "--newlist-append",
        nargs="+",
        metavar="TICKER",
        help="add tickers to the tracked list",
    )
    targets.add_argument(
        "--newlist-remove",
        nargs="+",
        metavar="TICKER",
        help="remove tickers from the tracked list",
    )
    targets.add_argument(
        "--peek",
        metavar="TICKER",
        help="look up a single ticker without changing the saved list",
    )
    parser.add_argument(
        "--theme",
        action="append",
        default=None,
        metavar='"NAME:AAPL,NVDA,..."',
        help='create/replace theme NAME with given tickers (repeatable; empty members deletes, e.g. --theme "TECH:")',
    )
    parser.add_argument(
        "--theme-clear",
        action="store_true",
        help="delete all themes",
    )
    parser.add_argument(
        "--theme-list",
        action="store_true",
        help="list persisted themes and exit (no fetch)",
    )
    parser.add_argument(
        "--period",
        choices=VALID_PERIODS,
        default="1y",
        help="price history window used for changes (default: 1y)",
    )
    parser.add_argument(
        "--interval",
        type=_positive_int,
        default=60,
        metavar="SECONDS",
        help="refresh interval in seconds for --watch (default: 60)",
    )
    parser.add_argument(
        "--modern",
        action="store_true",
        help="use modern table style (default: classic ASCII)",
    )
    parser.add_argument(
        "--watch",
        "--continuous",
        dest="watch",
        action="store_true",
        help="refresh continuously every --interval seconds (default: run once)",
    )
    return parser


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            f"invalid interval {value!r}, expected a positive integer"
        )
    return parsed


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    my_core = Core(period=args.period)

    cli = CLI(
        interval=args.interval,
        period=args.period,
        clear=args.watch,
        modern=args.modern,
        watch=args.watch,
    )

    if args.peek is not None and (args.theme or args.theme_clear or args.theme_list):
        parser.error("--peek cannot be combined with --theme/--theme-clear/--theme-list")

    if args.peek is not None:
        # One-shot lookup that never touches the persisted list.
        # Placeholder uses the normalized symbol; Core.get_quote()
        # validates the ticker when fetching.
        peek_symbol = normalize_ticker(args.peek)

        def _peek_quotes() -> list[TickerQuote]:
            return [my_core.get_quote(peek_symbol)]

        try:
            if args.watch:
                first = True
                while True:
                    if first:
                        cli.display_live([peek_symbol], _peek_quotes)
                        first = False
                    else:
                        cli.display_stock_data(_peek_quotes())
                    time.sleep(cli.interval)
            else:
                cli.display_live([peek_symbol], _peek_quotes)
        except KeyboardInterrupt:
            print("\nStopping Stock Stalker...")
        return

    if args.newlist is not None:
        my_core.set_ticker_list(list(args.newlist))
    elif args.newlist_append is not None:
        for ticker in args.newlist_append:
            my_core.append_item_to_ticker_list(ticker)
    elif args.newlist_remove is not None:
        for ticker in args.newlist_remove:
            my_core.remove_item_from_ticker_list(ticker)

    if args.theme_clear:
        my_core.clear_themes()

    if args.theme:
        parsed: list[tuple[str, list[str]]] = []
        for spec in args.theme:
            try:
                parsed.append(parse_theme_spec(spec))
            except ValueError as exc:
                parser.error(str(exc))
        # A ticker may belong to only one theme: reject duplicates
        # across specs in a single invocation.
        seen: dict[str, str] = {}
        for theme, members in parsed:
            for symbol in members:
                if symbol in seen and seen[symbol] != theme:
                    parser.error(
                        f"ticker {symbol!r} is in multiple themes "
                        f"({seen[symbol]!r} and {theme!r}); "
                        "a ticker may belong to only one theme"
                    )
                seen[symbol] = theme
        for theme, members in parsed:
            try:
                my_core.set_theme(theme, members)
            except ValueError as exc:
                parser.error(str(exc))

    if args.theme_list:
        themes = my_core.themes
        if not themes:
            print("No themes defined.")
        else:
            for name, members in themes.items():
                print(f"{name}: {', '.join(members)}")
        return

    use_themes = bool(my_core.themes)

    try:
        if args.watch:
            first = True
            while True:
                if first:
                    if use_themes:
                        cli.display_live_grouped(
                            my_core.get_grouped_symbols(),
                            my_core.get_grouped_quotes,
                        )
                    else:
                        cli.display_live(my_core.tickers_list, my_core.get_quotes)
                    first = False
                else:
                    if use_themes:
                        cli.display_grouped_data(my_core.get_grouped_quotes())
                    else:
                        cli.display_stock_data(my_core.get_quotes())
                time.sleep(cli.interval)
        else:
            if use_themes:
                cli.display_live_grouped(
                    my_core.get_grouped_symbols(), my_core.get_grouped_quotes
                )
            else:
                cli.display_live(my_core.tickers_list, my_core.get_quotes)
    except KeyboardInterrupt:
        print("\nStopping Stock Stalker...")


if __name__ == "__main__":
    main()
