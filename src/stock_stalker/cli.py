import os
from typing import Any

PERIOD_LABELS: dict[str, tuple[str, ...]] = {
    "5d": ("5d",),
    "1mo": ("5d", "1mo"),
    "ytd": ("5d", "1mo", "ytd"),
    "1y": ("5d", "1mo", "ytd", "1y"),
    "5y": ("5d", "1mo", "ytd", "1y", "5y"),
}


class CLI:
    def __init__(self, interval: int = 60, period: str = "1y"):
        self.interval = interval
        self.period = period

    def _print_header(self):
        print("\n" + "=" * 107)
        static = f"{'Symbol':<6} | {'Average':<10} |"
        labels = PERIOD_LABELS.get(self.period, ())
        variable = "".join(f" {label:<10} |" for label in labels)
        print(static + variable)
        print("-" * 107)

    def print_header_debug(self, data_list):
        for curr in data_list:
            print(curr)

    def display_stock_data(self, data_list):
        os.system("cls" if os.name == "nt" else "clear")
        self._print_header()
        for item in data_list:
            symbol, avg_text = self._symbol_and_average(item)
            cells = [
                self._format_change(item, label)
                for label in PERIOD_LABELS.get(self.period, ())
            ]
            row = f"{symbol:<6.6} | {avg_text:<10}" + "".join(
                f" | {c:<10} |" for c in cells
            )
            print(row)
        print("=" * 107)
        print(f"\nNext update in {self.interval} seconds...")

    def _symbol_and_average(self, item: Any) -> tuple[str, str]:
        symbol = self._field(item, "symbol", "N/A")
        average = self._field(item, "average", "N/A")
        try:
            avg_text = f"{float(average):.2f}"  # type: ignore[arg-type]
        except (TypeError, ValueError):
            avg_text = str(average)
        return str(symbol), avg_text

    def _format_change(self, item: Any, label: str) -> str:
        value = self._change_value(item, label)
        if value is None or value == "N/A":
            return "N/A"
        try:
            return f"{float(value):.2f}%"  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _field(item: Any, name: str, default: Any) -> Any:
        if hasattr(item, name):
            return getattr(item, name)
        if isinstance(item, dict):
            return item.get(name, default)
        return default

    @classmethod
    def _change_value(cls, item: Any, label: str) -> Any:
        changes = cls._field(item, "changes", None)
        if isinstance(changes, dict) and label in changes:
            return changes[label]
        if isinstance(item, dict):
            return item.get(label, "N/A")
        return "N/A"
