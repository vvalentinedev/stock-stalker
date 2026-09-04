import sys
import time

from .cli import CLI
from .core import Core


def main():
    my_args = sys.argv
    my_core = Core()
    pending: list[str] = []

    if len(my_args) > 1:
        if my_args[1] == "--newlist" and len(my_args) > 2:
            pending = list(my_args[2:])
        elif my_args[1] == "--newlist-append" and len(my_args) > 2:
            for ticker in my_args[2:]:
                my_core.append_item_to_ticker_list(ticker)
        elif my_args[1] == "--newlist-remove" and len(my_args) > 2:
            for ticker in my_args[2:]:
                my_core.remove_item_from_ticker_list(ticker)

    if pending:
        my_core.set_ticker_list(pending)

    cli = CLI(interval=60, period=my_core.period)

    try:
        while True:
            ticker_data = my_core.get_quotes()
            cli.display_stock_data(ticker_data)
            time.sleep(cli.interval)
    except KeyboardInterrupt:
        print("\nStopping Stock Stalker...")


if __name__ == "__main__":
    main()
