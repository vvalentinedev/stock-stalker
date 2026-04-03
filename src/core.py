import yfinance as yf
import os

class Core:
    tickers_list = []
    interval = 15

    def __init__(self):
        self._setTickerList()
        self._start()


    def _setTickerList(self):
        if os.path.exists("my_stock_list.csv") and os.path.getsize("my_stock_list.csv") > 0:
            with open("my_stock_list.csv") as file:
                self.tickers_list = [line.strip() for line in file if line.strip()]
        else: 
            # if my_stock_list.csv doesn't exist or is empty, a default ticker list is loaded.
            self.tickers_list = ["AAPL", "NVDA", "GOOG"]

    def _start(self):
        for current_ticker in self.tickers_list:
            dat = yf.Ticker(current_ticker)

            symbol = dat.info["symbol"]
            price_range = dat.info["regularMarketDayRange"]
            currency = dat.info["financialCurrency"]
            print(f"{symbol}: {price_range} {currency}")

             

