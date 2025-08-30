import os
from yahoo_fin import stock_info as si
import pandas as pd
import numpy as np
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import datetime
import calendar

# --- Gyertyajelzések függvényei ---

def bullish_engulfing(df):
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
        (abody_prev2 > 0.6 * length.shift(2)) &
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

# --- Részvénylista beolvasása symbols.csv-ból ---

def get_symbols_from_csv(filename="symbols.csv"):
    try:
        df = pd.read_csv(filename, header=None)
        symbols = df[0].dropna().astype(str).tolist()
        return symbols
    except Exception as e:
        print(f"Hiba a {filename} beolvasásakor: {e}")
        return []

# --- Gyertyajelzés vizsgálat ---

def check_candlestick_patterns(symbol, timeframe='1wk'):
    try:
        df = si.get_data(symbol, interval=timeframe)
        if df.empty:
            return None
        df_recent = df.tail(5)
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

# --- Email küldés ---

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

# --- Főfüggvény ---

def main():
    now = datetime.datetime.utcnow()
    run_weekly = (now.weekday() == 4 and now.hour >= 23)  # péntek 23:00 után
    last_day = calendar.monthrange(now.year, now.month)[1]
    run_monthly = (now.day == last_day and now.hour >= 23)  # hó utolsó napja 23:00 után

    if not run_weekly and not run_monthly:
        print("Nem futunk, nem megfelelő időpont.")
        return

    timeframe = '1wk' if run_weekly else '1mo'
    symbols = get_symbols_from_csv("symbols.csv")
    print(f"{len(symbols)} részvény beolvasva a symbols.csv fájlból, elemzés indul...")

    all_signals = {}
    for sym in symbols:
        signals = check_candlestick_patterns(sym, timeframe)
        if signals:
            all_signals[sym] = signals

    if not all_signals:
        print("Nem találtunk gyertyajelzést a megadott időszakra.")
        return

    # CSV generálás
    rows = []
    for sym, sigs in all_signals.items():
        for sig_name in sigs.keys():
            rows.append({'Symbol': sym, 'Signal': sig_name})
    df_signals = pd.DataFrame(rows)
    csv_filename = 'signals.csv'
    df_signals.to_csv(csv_filename, index=False)
    print(f"Jelek CSV fájl mentve: {csv_filename}")

    # Email küldés
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
    TO_EMAIL = EMAIL_USER

    subject = f"Részvény gyertyajelzések - {timeframe} - {now.strftime('%Y-%m-%d %H:%M UTC')}"
    body = f"Csatolva a jelek listája a {timeframe} időszakra.\n\n" + df_signals.to_string(index=False)

    send_email(subject, body, TO_EMAIL, EMAIL_USER, EMAIL_PASS)

if __name__ == "__main__":
    main()


