import time
import os

# TODO: refactor class so that it displays columns based on how far you want to go on price history 
class CLI:
    def __init__(self, interval: int = 60, period: str = "1y"):
        self.interval = interval
        self.period = period

    def _print_header(self):
        print("\n" + "="*107)
        # TODO: truncate tickers bigger than 6 characters
        STATIC_HEADER_SEGMENT = f"{'Symbol':<6} | {'Average':<10} |"

        variable_header_segment = ""
        match self.period:
            case "5d":
                variable_header_segment = f" {'5d':<10} |"
            case "1mo":
                variable_header_segment = f" {'5d':<10} | {'1mo':<10} |"
            case "ytd":
                variable_header_segment = f" {'5d':<10} | {'1mo':<10} | {'ytd':<10} |"
            case "1y":
                variable_header_segment = f" {'5d':<10} | {'1mo':<10} | {'ytd':<10} | {'1y':<10} |"
            case "5y":
                variable_header_segment = f" {'5d':<10} | {'1mo':<10} | {'ytd':<10} | {'1y':<10} | {'5y':<10} |"
        header = STATIC_HEADER_SEGMENT + variable_header_segment

        print(header)
        print("-" * 107)

    def print_header_debug(self, data_list):
        for curr in data_list:
            print(curr)

    def display_stock_data(self, data_list):
        os.system('cls' if os.name == 'nt' else 'clear')
        self._print_header()
        for item in data_list:
            symbol = item.get("symbol", "N/A")
            avg_price = item.get("average", "N/A")

            STATIC_ROW_SEGMENT = f"{symbol:<6} | {avg_price:<20}"
            variable_row_segment = ""
            match self.period:
                case "5d":
                    fiveday_change = item.get("5d", "N/A")
                    variable_row_segment = f" | {fiveday_change:<10} |"
                case "1mo":
                    fiveday_change = item.get("5d", "N/A")
                    onemonth_change = item.get("1mo", "N/A")
                    variable_row_segment = f" | {fiveday_change:<10} | {onemonth_change:<10} |"
                case "ytd":
                    fiveday_change = item.get("5d", "N/A")
                    onemonth_change = item.get("1mo", "N/A")
                    yeartodate_change = item.get("ytd", "N/A")
                    variable_row_segment = f" | {fiveday_change:<10} | {onemonth_change:<10} | {yeartodate_change:<10} |"
                case "1y":
                    fiveday_change = item.get("5d", "N/A")
                    onemonth_change = item.get("1mo", "N/A")
                    yeartodate_change = item.get("ytd", "N/A")
                    oneyear_change = item.get("1y", "N/A")
                    variable_row_segment = f" | {fiveday_change:<10} | {onemonth_change:<10} | {yeartodate_change:<10} | {oneyear_change:<10} |"
                case "5y":
                    fiveday_change = item.get("5d", "N/A")
                    onemonth_change = item.get("1mo", "N/A")
                    yeartodate_change = item.get("ytd", "N/A")
                    oneyear_change = item.get("1y", "N/A")
                    fiveyear_change = item.get("5y", "N/A")
                    variable_row_segment = f" | {fiveday_change:<10} | {onemonth_change:<10} | {yeartodate_change:<10} | {oneyear_change:<10} | {fiveyear_change:<10} |"
            print(STATIC_ROW_SEGMENT + variable_row_segment)
        print("="*107)
        print(f"\nNext update in {self.interval} seconds...")
