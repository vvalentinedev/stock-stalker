import yfinance as yf
import pandas as pd
import os
import math
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from platformdirs import user_data_dir

class Core:
    tickers_list = []

    # TODO: add validation so only valid periods are accepted as atribute
    def __init__(self, period: str = "1y"):
        self._get_ticker_list()
        self.period = period

    def _get_ticker_list_dir(self) -> Path:
        data_dir = Path(
            
        user_data_dir(
            appname="Stock Stalker",
            appauthor=False,  
            )
        )

        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "my_stock_list.csv"

    def _get_ticker_list(self):
        csv_path = self._get_ticker_list_dir()

        if csv_path.exists() and csv_path.stat().st_size > 0:
            with csv_path.open(encoding="utf-8") as f:
                self.tickers_list = [
                    line.strip()
                    for line in f
                    if line.strip()
                ]
        
        else: 
            # if my_stock_list.csv doesn't exist or is empty, a default ticker list is loaded.
            self.tickers_list = ["AAPL", "NVDA", "GOOG"]

    def _set_ticker_list(self, tickers: list[str]):
        csv_path = self._get_ticker_list_dir()

        csv_path.write_text(
            "\n".join(tickers),
            encoding="utf-8",
        )

    def _fetch_single_ticker(self, current_ticker:str) -> dict:
        hist = yf.download(
            current_ticker,
            period = self.period,
            auto_adjust = True, 
            progress = False,
            group_by = "date",
        )

        # TODO: fix magic numbers in order to make code clearer 

        day_off = 0
        if math.isnan(hist.iloc[-1].iloc[1]): day_off = 1

        highest_point = hist.iloc[-1 - day_off].iloc[1]
        lowest_point = hist.iloc[-1 - day_off].iloc[2]
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
                ytd_change = self._get_percentage_change(hist, int(ytd_offset), avg_price)
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
                ytd_change = self._get_percentage_change(hist, int(ytd_offset), avg_price)
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

    def get_ticker_list(self) -> list[dict]: 
        data_list = []
        for curr in self.tickers_list:
            data_list.append(self._fetch_single_ticker(curr))
        #with ThreadPoolExecutor() as executor:
        #    data_list = list(executor.map(self._fetch_single_ticker, self.tickers_list))
            
        return data_list

    def append_item_to_ticker_list(self, ticker: str): 
        self.tickers_list.append(ticker)

    def remove_item_from_ticker_list(self, ticker: str):
        if ticker in self.tickers_list:
            self.tickers_list.remove(ticker)
