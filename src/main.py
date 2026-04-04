import time
from core import Core
from cli import CLI

def main():
    # Initialize Core and CLI
    core = Core()
    cli = CLI(interval=60)

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
