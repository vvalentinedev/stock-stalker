import yfinance as yf
import os

class Core:
    tickers_list = []

    def __init__(self):
        self._set_ticker_list()

    def _set_ticker_list(self):
        if os.path.exists("my_stock_list.csv") and os.path.getsize("my_stock_list.csv") > 0:
            with open("my_stock_list.csv") as file:
                self.tickers_list = [line.strip() for line in file if line.strip()]
        else: 
            # if my_stock_list.csv doesn't exist or is empty, a default ticker list is loaded.
            self.tickers_list = ["AAPL", "NVDA", "GOOG"]

    def get_ticker_list(self): 
        data_list = []
        for current_ticker in self.tickers_list:
            dat = yf.Ticker(current_ticker)
            
            # Using get() to handle missing keys gracefully
            info = dat.info
            symbol = info.get("symbol", current_ticker)
            price_range = info.get("regularMarketDayRange", "N/A")
            currency = info.get("financialCurrency", "N/A")
            
            data_list.append({
                "symbol": symbol,
                "price_range": price_range,
                "currency": currency
            })
        return data_list

             

