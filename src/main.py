from core import Core

"""
tickers = ["RDDT", "NET", "MEGACPO.MX", "GEV", "QCLS", "NEE", "LLY"]

dat = yf.Ticker("NET")
print(dat.history(period="5y"))

for curr in tickers:
    dat = yf.Ticker(curr)
    symbol = dat.info["symbol"]
    price_range = dat.info["regularMarketDayRange"]
    currency = dat.info["financialCurrency"]
    print(f"{symbol}: {price_range} {currency}")
"""

if __name__ == "__main__":
    core = Core()


