import pandas as pd
import yfinance as yf

# --- Symbols beolvasása CSV-ből ---
def get_symbols_from_csv(filename="symbols.csv"):
    try:
        df = pd.read_csv(filename, header=None, sep=';')
        symbols = df[0].dropna().astype(str).str.strip().tolist()
        return symbols
    except Exception as e:
        print(f"Hiba a {filename} beolvasásakor: {e}")
        return []

tickers = get_symbols_from_csv("symbols.csv")
print("Beolvasott tickerek:", tickers)

# --- Yahoo Finance adat letöltés és kiírás ---
for ticker in tickers:
    try:
        data = yf.download(ticker, period="1mo", interval="1d")
        print(f"\n{ticker} adatai:")
        print(data[['Open','High','Low','Close','Volume']])
    except Exception as e:
        print(f"Hiba a {ticker} letöltésekor: {e}")
