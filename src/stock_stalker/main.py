import time
from core import Core
from cli import CLI

#
#   TODO: 
#   1.- Add a CLI argument to add and edit elements in data/my_stock_list.csv
#   2.- Add a CLI argument to modify the period (default is 1y)
#   3. Refactor CLI class so that placeholder values appear before data is obtained

def main():
    
    # Initialize Core and CLI
    core = Core()
    cli = CLI(interval=60, period="1y")

    try:
        while True:
            # Fetch data from Core
            ticker_data = core.get_ticker_list()
            
            # Use CLI to display the layout
            cli.display_stock_data(ticker_data)
            
            # Wait for the specified interval
            time.sleep(cli.interval)
    except KeyboardInterrupt:
        print("\nStopping Stock Stalker...")

if __name__ == "__main__":
    main()
