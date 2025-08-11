# --- Telepítések ---
import os
import pandas as pd
import numpy as np
from yahoo_fin import stock_info as si
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import datetime
import calendar

# --- Email beállítások GitHub Secretsből ---
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL", EMAIL_USER)  # ha nincs külön megadva, magadnak küldi

# --- Gyertyajelzések definíciói ---
def bullish_engulfing(df):
    body = df['close'] - df['open']
    body_prev = body.shift(1)
    bodytop = df[['open', 'close']].max(axis=1)
    bodytop_prev = bodytop.shift(1)
    bodybottom = df[['open', 'close']].min(axis=1)
    bodybottom_prev = bodybottom.shift(1)
    length = df['high'] - df['low']
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
    body = df['close'] - df['open']
    body_prev = body.shift(1)
    length = df['high'] - df['low']
    abody = body.abs()
    ratio = abody / length
    longcandle = (ratio > 0.6)
    middle_prev = (df['open'].shift(1) + df['close'].shift(1)) / 2
    condition = (
        (body_prev < 0) &
        (body > 0) &
        (longcandle.shift(1)) &
        longcandle &
        (df['open'] < df['low'].shift(1)) &
        (df['close'] > middle_prev) &
        (df['close'] < df['open'].shift(1))
    )
    return condition.fillna(False)

def bullish_pin_bar(df):
    length = df['high'] - df['low']
    shadowbottom = df[['open', 'close']].min(axis=1) - df['low']
    condition = (df['low'] < df['low'].shift(1)) & (shadowbottom > 0.67 * length)
    return condition.fillna(False)

def morning_star(df):
    body = df['close'] - df['open']
    abody = body.abs()
    length = df['high'] - df['low']
    ratio = abody / length
    abody_prev1 = abody.shift(1)
    abody_prev2 = abody.shift(2)
    body_prev2 = body.shift(2)
    condition = (
        (body_prev2 < 0) &
        (body > 0) &
        (abody_prev2 > 0.6 * length.shift(2)) &
        (df['open'].shift(1) < df['close'].shift(2)) &
        (df['close'].shift(1) < df['close'].shift(2)) &
        (df['open'] > df['open'].shift(1)) &
        (df['open'] > df['close'].shift(1)) &
        (ratio.shift(1) < 0.3) &
        (abody_prev1 < abody_prev2) &
        (abody_prev1 < abody) &
        (df['low'].shift(1) < df['low']) &
        (df['low'].shift(1) < df['low'].shift(2)) &
        (df['high'].shift(1) < df['open'].shift(2)) &
        (df['high'].shift(1) < df['close'])
    )
    return condition.fillna(False)

def bullish_kicker(df):
    body = df['close'] - df['open']
    body_prev = body.shift(1)
    length = df['high'] - df['low']
    abody = body.abs()
    ratio = abody / length
    longcandle = (ratio > 0.6)
    condition = (
        (body_prev < 0) &
        (body > 0) &
        (longcandle.shift(1)) &
        longcandle &
        (df['open'].shift(1) < df['open'])
    )
    return condition.fillna(False)

# --- Részvénylista ---
def get_nyse_nasdaq_symbols():
    nasdaq_url = 'https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
    nyse_url = 'https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
    nasdaq_df = pd.read_csv(nasdaq_url, sep='|')
    nyse_df = pd.read_csv(nyse_url, sep='|')
    nasdaq_symbols = nasdaq_df['Symbol'].tolist()
    nyse_symbols = nyse_df[nyse_df['Exchange'] == 'N']['ACT Symbol'].tolist()
    all_symbols = [sym for sym in (nasdaq_symbols + nyse_symbols) if sym.isalnum()]
    return all_symbols

# --- Jel ellenőrzés ---
def check_candlestick_patterns(symbol, timeframe='1wk'):
    try:
        df = si.get_data(symbol, interval=timeframe)
        if df.empty:
            return None
        df_recent = df.tail(5).reset_index()
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
    except:
        return None

# --- Email küldése CSV melléklettel ---
def send_email_with_csv(subject, body, csv_path, to_email, from_email, app_password):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    with open(csv_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(csv_path)}"')
    msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(from_email, app_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email elküldve.")
    except Exception as e:
        print(f"Email küldési hiba: {e}")

# --- Fő program ---
def main():
    now = datetime.datetime.utcnow()
    run_weekly = (now.weekday() == 4)  # péntek
    run_monthly = (now.day == calendar.monthrange(now.year, now.month)[1])
    timeframe = '1wk' if run_weekly else '1mo'

    symbols = get_nyse_nasdaq_symbols()
    all_signals = []

    for sym in symbols:
        sigs = check_candlestick_patterns(sym, timeframe)
        if sigs:
            all_signals.append({"Symbol": sym, "Signals": ", ".join(sigs.keys())})

    if all_signals:
        df = pd.DataFrame(all_signals)
        csv_path = "signals.csv"
        df.to_csv(csv_path, index=False)
        send_email_with_csv(
            subject=f"Részvény jelek {now.strftime('%Y-%m-%d')}",
            body="A mellékelt fájlban találod a jeleket.",
            csv_path=csv_path,
            to_email=TO_EMAIL,
            from_email=EMAIL_USER,
            app_password=EMAIL_PASS
        )
    else:
        print("Nem találtam jelet.")

if __name__ == "__main__":
    main()
