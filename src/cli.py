import time
import os

class CLI:
    def __init__(self, interval: int = 60):
        self.interval = interval

    def _print_header(self):
        print("\n" + "="*40)
        print(f"{'Symbol':<10} | {'Price Range':<20} | {'Currency':<10}")
        print("-" * 40)

    def display_stock_data(self, data_list):
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_header()
        for item in data_list:
            symbol = item.get("symbol", "N/A")
            price_range = item.get("price_range", "N/A")
            currency = item.get("currency", "N/A")
            print(f"{symbol:<10} | {price_range:<20} | {currency:<10}")
        print("="*40)
        print(f"\nNext update in {self.interval} seconds...")
