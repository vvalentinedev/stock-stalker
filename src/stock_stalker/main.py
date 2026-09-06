import argparse
import time

from .cli import CLI
from .core import Core
from .models import VALID_PERIODS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock-stalker",
        description="Monitor your favorite stocks from Yahoo Finance.",
        epilog="examples:\n"
        "  stock-stalker --newlist AAPL NVDA\n"
        "  stock-stalker --newlist-append MSFT --period 1mo\n"
        "  stock-stalker --newlist-remove GOOG\n"
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
    args = build_parser().parse_args(argv)
    my_core = Core(period=args.period)

    if args.newlist is not None:
        my_core.set_ticker_list(list(args.newlist))
    elif args.newlist_append is not None:
        for ticker in args.newlist_append:
            my_core.append_item_to_ticker_list(ticker)
    elif args.newlist_remove is not None:
        for ticker in args.newlist_remove:
            my_core.remove_item_from_ticker_list(ticker)

    cli = CLI(
        interval=args.interval,
        period=args.period,
        clear=args.watch,
        modern=args.modern,
        watch=args.watch,
    )

    try:
        if args.watch:
            first = True
            while True:
                if first:
                    cli.display_live(my_core.tickers_list, my_core.get_quotes)
                    first = False
                else:
                    cli.display_stock_data(my_core.get_quotes())
                time.sleep(cli.interval)
        else:
            cli.display_live(my_core.tickers_list, my_core.get_quotes)
    except KeyboardInterrupt:
        print("\nStopping Stock Stalker...")


if __name__ == "__main__":
    main()
