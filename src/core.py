import yfinance as yf
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

class Core:
    tickers_list = []

    # TODO: add validation so only valid periods are accepted as atribute
    def __init__(self, period: str = "1y"):
        self._set_ticker_list()
        self.period = period

    def _set_ticker_list(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, "..", "data", "my_stock_list.csv")
        
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            with open(csv_path) as file:
                self.tickers_list = [line.strip() for line in file if line.strip()]
        else: 
            # if my_stock_list.csv doesn't exist or is empty, a default ticker list is loaded.
            self.tickers_list = ["AAPL", "NVDA", "GOOG"]

    # TODO: refactor function so that it returns avg price of latest trading day, as well as the rest of the data we want to display
    def _fetch_single_ticker(self, current_ticker:str) -> dict:
        hist = yf.download(
            current_ticker,
            period = self.period,
            auto_adjust = True, 
            progress = False,
            group_by = "date",
        )

        # TODO: fix magic numbers in order to make code clearer 
        highest_point = hist.iloc[-1].iloc[1]
        lowest_point = hist.iloc[-1].iloc[2]
        avg_price = (highest_point + lowest_point) / 2

        ticker_data = {
            "symbol" : current_ticker,
            "average" : avg_price,
        }

        match self.period:
            case "5d":
                fivedayago_change = self._get_percentage_change(hist, 0, avg_price)
                ticker_data = ticker_data | { "5d":fivedayago_change }
            case "1mo":
                fivedayago_change = self._get_percentage_change(hist, -5, avg_price)
                onemonth_change = self._get_percentage_change(hist, 0, avg_price)
                ticker_data = ticker_data | {
                    "5d":fivedayago_change,
                    "1mo":onemonth_change,
                }
            case "ytd":
                fivedayago_change = self._get_percentage_change(hist, -5, avg_price)
                onemonth_change = self._get_percentage_change(hist, -21, avg_price)
                ytd_change = self._get_percentage_change(hist, 0, avg_price)
                ticker_data = ticker_data | {
                    "5d":fivedayago_change,
                    "1mo":onemonth_change,
                    "ytd":ytd_change,
                }
            case "1y":
                fivedayago_change = self._get_percentage_change(hist, -5, avg_price)
                onemonth_change = self._get_percentage_change(hist, -21, avg_price)
                ytd_offset = datetime.now().strftime("%j")
                ytd_change = self._get_percentage_change(hist, ytd_offset, avg_price)
                oneyear_change = self._get_percentage_change(hist, 0, avg_price)
                ticker_data = ticker_data | {
                    "5d":fivedayago_change,
                    "1mo":onemonth_change,
                    "ytd":ytd_change,
                    "1y":oneyear_change,
                }
            case "5y":
                fivedayago_change = self._get_percentage_change(hist, -5, avg_price)
                onemonth_change = self._get_percentage_change(hist, -21, avg_price)
                ytd_offset = datetime.now().strftime("%j")
                ytd_change = self._get_percentage_change(hist, ytd_offset, avg_price)
                oneyear_change = self._get_percentage_change(hist, -252, avg_price)
                fiveyear_change = self._get_percentage_change(hist, 0, avg_price)
                ticker_data = ticker_data | {
                    "5d":fivedayago_change,
                    "1mo":onemonth_change,
                    "ytd":ytd_change,
                    "1y":oneyear_change,
                    "5y":fiveyear_change
                }

        return ticker_data

    def _get_percentage_change(self, hist:pd.DataFrame, offset:int, current_price:int) -> str:
        average = (hist.iloc[offset].iloc[1] + hist.iloc[offset].iloc[2]) / 2
        percentage_change = ((current_price - average) / average) * 100

        return f"{percentage_change:.2f}%"

    def get_ticker_list(self): 
        with ThreadPoolExecutor() as executor:
            data_list = list(executor.map(self._fetch_single_ticker, self.tickers_list))
            
        return data_list

             

