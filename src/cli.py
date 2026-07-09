import time
import os

class CLI:
    def __init__(self, interval: int = 60):
        self.interval = interval

    def _print_header(self):
        print("\n" + "="*107)
        print(f"{'Symbol':<6} | {'Price Range':<20} | {'Currency':<8} | {'5d':<10} | {'1mo':<10} | {'ytd':<10} | {'1y':<10} | {'5y':<10} |")
        print("-" * 107)

    def display_stock_data(self, data_list):
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_header()
        for item in data_list:
            symbol = item.get("symbol", "N/A")
            price_range = item.get("price_range", "N/A")
            currency = item.get("currency", "N/A")
            fiveday_change = item.get("5d", "N/A")
            onemonth_change = item.get("1m", "N/A")
            yeartodate_change = item.get("ytd", "N/A")
            oneyear_change = item.get("1y", "N/A")
            fiveyear_change = item.get("5y", "N/A")
            print(f"{symbol:<6} | {price_range:<20} | {currency:<8} | {fiveday_change:<10} | {onemonth_change:<10} | {yeartodate_change:<10} | {oneyear_change:<10} | {fiveyear_change:<10} |")
        print("="*107)
        print(f"\nNext update in {self.interval} seconds...")
