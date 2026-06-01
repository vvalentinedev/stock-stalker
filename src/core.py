import yfinance as yf
import os
from concurrent.futures import ThreadPoolExecutor

class Core:
    tickers_list = []

    def __init__(self):
        self._set_ticker_list()

    def _set_ticker_list(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "..", "data", "my_stock_list.csv")
        
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            with open(csv_path) as file:
                self.tickers_list = [line.strip() for line in file if line.strip()]
        else: 
            # if my_stock_list.csv doesn't exist or is empty, a default ticker list is loaded.
            self.tickers_list = ["AAPL", "NVDA", "GOOG"]

    def _fetch_single_ticker(self, current_ticker):
        dat = yf.Ticker(current_ticker)
        
        # Using get() to handle missing keys gracefully
        info = dat.info
        symbol = info.get("symbol", current_ticker)
        price_range = info.get("regularMarketDayRange", "N/A")
        currency = info.get("financialCurrency", "N/A")
        
        return {
            "symbol": symbol,
            "price_range": price_range,
            "currency": currency
        }

    def get_ticker_list(self): 
        with ThreadPoolExecutor() as executor:
            data_list = list(executor.map(self._fetch_single_ticker, self.tickers_list))
            
        return data_list

             

