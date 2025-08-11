# --- Telepítések Google Colabhoz ---
!pip install --quiet yahoo_fin
!pip install --quiet pandas
!pip install --quiet numpy

# --- Importok ---
from yahoo_fin import stock_info as si
import pandas as pd
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import datetime
import calendar

# --- Gyertyajelzések definíciói (a korábbi PineScript alapján Pythonban) ---

def bullish_engulfing(df):
    # Feltételezve, hogy df-ben van: Open, Close, High, Low, és index időrendi
    body = df['Close'] - df['Open']
    body_prev = body.shift(1)
    bodytop = df[['Open', 'Close']].max(axis=1)
    bodytop_prev = bodytop.shift(1)
    bodybottom = df[['Open', 'Close']].min(axis=1)
    bodybottom_prev = bodybottom.shift(1)
    length = df['High'] - df['Low']
    abody = body.abs()
    ratio = abody / length
    longcandle = (ratio > 0.6)

    condition = (
        (body_prev < 0) &
        (body > 0) &
        (bodybottom < bodybottom_prev) &
        (bodytop > bodytop_prev) &
        longcandle
    )
    return condition.fillna(False)

def piercing_line(df):
    body = df['Close'] - df['Open']
    body_prev = body.shift(1)
    bodytop = df[['Open', 'Close']].max(axis=1)
    bodytop_prev = bodytop.shift(1)
    bodybottom = df[['Open', 'Close']].min(axis=1)
    bodybottom_prev = bodybottom.shift(1)
    length = df['High'] - df['Low']
    abody = body.abs()
    ratio = abody / length
    longcandle = (ratio > 0.6)
    middle_prev = (df['Open'].shift(1) + df['Close'].shift(1)) / 2

    condition = (
        (body_prev < 0) &
        (body > 0) &
        (longcandle.shift(1)) &
        longcandle &
        (df['Open'] < df['Low'].shift(1)) &
        (df['Close'] > middle_prev) &
        (df['Close'] < df['Open'].shift(1))
    )
    return condition.fillna(False)

def bullish_pin_bar(df):
    length = df['High'] - df['Low']
    shadowbottom = df[['Open', 'Close']].min(axis=1) - df['Low']
    condition = (df['Low'] < df['Low'].shift(1)) & (shadowbottom > 0.67 * length)
    return condition.fillna(False)

def morning_star(df):
    body = df['Close'] - df['Open']
    body_prev1 = body.shift(1)
    body_prev2 = body.shift(2)
    abody = body.abs()
    abody_prev1 = abody.shift(1)
    abody_prev2 = abody.shift(2)
    length = df['High'] - df['Low']
    ratio = abody / length

    condition = (
        (body_prev2 < 0) &
        (body > 0) &
        (abody_prev2 > 0.6 * length.shift(2)) &  # longcandle[2]
        (df['Open'].shift(1) < df['Close'].shift(2)) &
        (df['Close'].shift(1) < df['Close'].shift(2)) &
        (df['Open'] > df['Open'].shift(1)) &
        (df['Open'] > df['Close'].shift(1)) &
        (ratio.shift(1) < 0.3) &
        (abody_prev1 < abody_prev2) &
        (abody_prev1 < abody) &
        (df['Low'].shift(1) < df['Low']) &
        (df['Low'].shift(1) < df['Low'].shift(2)) &
        (df['High'].shift(1) < df['Open'].shift(2)) &
        (df['High'].shift(1) < df['Close'])
    )
    return condition.fillna(False)

def bullish_kicker(df):
    body = df['Close'] - df['Open']
    body_prev = body.shift(1)
    length = df['High'] - df['Low']
    abody = body.abs()
    ratio = abody / length
    longcandle = (ratio > 0.6)

    condition = (
        (body_prev < 0) &
        (body > 0) &
        (longcandle.shift(1)) &
        longcandle &
        (df['Open'].shift(1) < df['Open'])
    )
    return condition.fillna(False)

# --- Részvénylista lekérése NYSE és Nasdaq-ról (ingyenes) ---

def get_nyse_nasdaq_symbols():
    # Nasdaq listát lekérjük
    nasdaq_url = 'https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
    nyse_url = 'https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'

    nasdaq_df = pd.read_csv(nasdaq_url, sep='|')
    nyse_df = pd.read_csv(nyse_url, sep='|')

    nasdaq_symbols = nasdaq_df['Symbol'].tolist()
    nyse_symbols = nyse_df[nyse_df['Exchange'] == 'N']['ACT Symbol'].tolist()

    # Összefűzzük, és kiszűrjük azokat, amik ponttal kezdődnek vagy speciális karakterek vannak bennük
    all_symbols = [sym for sym in (nasdaq_symbols + nyse_symbols) if sym.isalnum()]

    return all_symbols

# --- Gyertyajelek ellenőrzése adott timeframe alapján ---

def check_candlestick_patterns(symbol, timeframe='1wk'):
    try:
        # Heti vagy havi adat lekérése
        df = si.get_data(symbol, interval=timeframe)
        if df.empty:
            return None

        # Válasszuk csak a legutolsó 3-5 gyertyát (a minták miatt)
        df_recent = df.tail(5)

        # Adatok átalakítása Pine script minták szerint
        # Szűrés gyertyajelzésekre
        signals = {}

        if bullish_engulfing(df_recent).iloc[-1]:
            signals['Bullish Engulfing'] = True
        if piercing_line(df_recent).iloc[-1]:
            signals['Piercing Line'] = True
        if bullish_pin_bar(df_recent).iloc[-1]:
            signals['Bullish Pin Bar'] = True
        if morning_star(df_recent).iloc[-1]:
            signals['Morning Star'] = True
        if bullish_kicker(df_recent).iloc[-1]:
            signals['Bullish Kicker'] = True

        return signals if signals else None

    except Exception as e:
        print(f"Hiba a {symbol} feldolgozásakor: {e}")
        return None

# --- Email küldése ---

def send_email(subject, body, to_email, from_email, app_password):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(from_email, app_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sikeresen elküldve.")
    except Exception as e:
        print(f"Email küldési hiba: {e}")

# --- Fő futtatófüggvény ---

def main():
    now = datetime.datetime.now()

    # Csak péntek 23:00 után fusson heti, hónap utolsó napján havi elemzés
    run_weekly = (now.weekday() == 4 and now.hour >= 23)
    last_day = calendar.monthrange(now.year, now.month)[1]
    run_monthly = (now.day == last_day and now.hour >= 23)

    if not run_weekly and not run_monthly:
        print("Nem futunk, nem megfelelő időpont.")
        return

    symbols = get_nyse_nasdaq_symbols()
    print(f"{len(symbols)} részvény lekérve, elemzés indul...")

    timeframe = '1wk' if run_weekly else '1mo'
    all_signals = {}

    for sym in symbols:
        signals = check_candlestick_patterns(sym, timeframe)
        if signals:
            all_signals

