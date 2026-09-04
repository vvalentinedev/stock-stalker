import sys
import stock_stalker.core as core 

my_core = core.Core()
my_core.period = "1y"
my_core.tickers_list = ["AAPL", "NVDA", "MSFT"]

#for curr in my_tickers:
#    res.append(my_core._fetch_single_ticker(curr))
res = my_core.get_ticker_list
print(res)
#my_data = my_core._fetch_single_ticker("RDDT")
#print(my_data)

#arguments = sys.argv[0:]
#print(f"args: {arguments}")