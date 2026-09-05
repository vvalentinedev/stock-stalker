# About 
stock-stalker lets you monitor your favorite stocks, data is fetched from Yahoo Finance through the yfinance library. 

<img width="691" height="411" alt="image" src="https://github.com/user-attachments/assets/6f82a564-840e-420a-824b-7edfba847fd6" />

# Installation
```
pipx install git+https://github.com/vvalentinedev/stock-stalker.git
```

# Instructions
You can pass the --newlist argument to define a custom stock list (as many tickers as you want)
```
stock-stalker --newlist <stock-name>
```
To either add or remove items from your ticker list you can use the -remove and -append flags.
```
stock-stalker --newlist-append <stock-name>
stock-stalker --newlist-remove <stock-name>
```
