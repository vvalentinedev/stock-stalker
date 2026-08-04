import time
import sys
from .core import Core
from .cli import CLI

#
#   TODO: 
#   0.- Add append and remove flags 
#   1.- Ensure data persistency on my_stock_list.csv
#   2.- Add a CLI argument to modify the period (default is 1y)
#   3. Refactor CLI class so that placeholder values appear before data is obtained

def main():
    ticker_list = []
    modify_list = False
    my_args = sys.argv

    my_core = Core()

    if len(my_args) > 1: 
        if my_args[1] == "--newlist" and len(my_args) > 2:
            modify_list = True
            for ticker in my_args[2:]:
                ticker_list.append(ticker)
        elif my_args[1] == "--newlist-append" and len(my_args) > 2:
            for ticker in my_args[2:]:
                my_core.append_item_to_ticker_list(ticker)
        elif my_args[1] == "--newlist-remove" and len(my_args) > 2:
            for ticker in my_args[2:]:
                my_core.remove_item_from_ticker_list(ticker)
    
    if modify_list:
        my_core._set_ticker_list(ticker_list)

    cli = CLI(interval=60, period="1y")

    try:
        while True:
            # Fetch data from Core
            ticker_data = my_core.get_ticker_list()
            
            # Use CLI to display the layout
            cli.display_stock_data(ticker_data)
            
            # Wait for the specified interval
            time.sleep(cli.interval)
    except KeyboardInterrupt:
        print("\nStopping Stock Stalker...")

if __name__ == "__main__":
    main()
