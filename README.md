# Stock Stalker

Monitor your favorite stocks from the terminal. Data is fetched from Yahoo Finance via `yfinance` and rendered as a live `rich` table with average price and % changes.

<img width="691" height="411" alt="image" src="https://github.com/user-attachments/assets/6f82a564-840e-420a-824b-7edfba847fd6" />

## Features

- One-shot or continuous (`--watch`) monitoring
- Tracks average of High/Low per day, plus % changes for `5d`, `1mo`, `ytd`, `1y`, `5y` depending on `--period`
- Persistent ticker list (defaults to `AAPL`, `NVDA`, `GOOG`) stored via `platformdirs`
- Batched `yfinance` download with threaded fallback + 60s cache
- Classic ASCII or `--modern` table style, with loading placeholder and color-coded gains/losses

## Installation

```bash
pipx install git+https://github.com/vvalentinedev/stock-stalker.git
```

Or with `pip`:

```bash
pip install git+https://github.com/vvalentinedev/stock-stalker.git
```

Or for development:

```bash
git clone https://github.com/vvalentinedev/stock-stalker.git
cd stock-stalker
uv sync  # or: pip install -e .[test] / pip install -e .
```

Requires Python >= 3.10. Dependencies: `yfinance`, `pandas`, `platformdirs`, `rich`.

## Usage

```bash
# Run once with saved list (default period: 1y)
stock-stalker

# Replace tracked list
stock-stalker --newlist AAPL NVDA MSFT

# Add / remove tickers
stock-stalker --newlist-append MSFT TSLA
stock-stalker --newlist-remove GOOG

# Choose history window (5d, 1mo, ytd, 1y, 5y)
stock-stalker --period 1mo
stock-stalker --period ytd

# Refresh continuously every 30s (default interval: 60s)
stock-stalker --watch --interval 30
stock-stalker --continuous --period 1mo --interval 30

# Modern table style (default is classic ASCII)
stock-stalker --modern
```

All flags (see `stock-stalker --help`):

| Flag | Description |
| ---- | ----------- |
| `--newlist TICKER [...]` | Replace the tracked ticker list |
| `--newlist-append TICKER [...]` | Add tickers to the tracked list |
| `--newlist-remove TICKER [...]` | Remove tickers from the tracked list |
| `--period {5d,1mo,ytd,1y,5y}` | Price history window used for changes (default: `1y`) |
| `--interval SECONDS` | Refresh interval for `--watch` (default: `60`, must be > 0) |
| `--watch, --continuous` | Refresh continuously (default: run once) |
| `--modern` | Use modern table style (default: classic ASCII) |

Tickers are normalized to uppercase, de-duplicated, and validated (`A-Z`, `.`, `-`, max 12 chars). The list persists to `my_stock_list.csv` in the platform user-data dir (e.g. `~/.local/share/Stock Stalker/` on Linux).

## Examples

```bash
stock-stalker --newlist AAPL NVDA
stock-stalker --newlist-append MSFT --period 1mo
stock-stalker --newlist-remove GOOG
stock-stalker --period ytd --interval 30
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check .  # if configured
python -m stock_stalker --help
```
