import os
import datetime
import pandas as pd
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Bullish minták felismerése ---

def bullish_engulfing(df):
    prev, last = df.iloc[-2], df.iloc[-1]
    open_prev, close_prev = prev['Open'], prev['Close']
    open_last, close_last = last['Open'], last['Close']
    high_last, low_last = last['High'], last['Low']

    body_prev = close_prev - open_prev
    body_last = close_last - open_last
    bodytop_prev = max(open_prev, close_prev)
    bodytop_last = max(open_last, close_last)
    bodybottom_prev = min(open_prev, close_prev)
    bodybottom_last = min(open_last, close_last)

    abody_last = abs(body_last)
    length_last = high_last - low_last
    longcandle = (abody_last / length_last) > 0.6 if length_last != 0 else False

    return (body_prev < 0) and (body_last > 0) and \
           (bodybottom_last < bodybottom_prev) and \
           (bodytop_last > bodytop_prev) and longcandle


def piercing_line(df):
    prev, last = df.iloc[-2], df.iloc[-1]
    open_prev, close_prev = prev['Open'], prev['Close']
    open_last, close_last = last['Open'], last['Close']
    high_prev, low_prev = prev['High'], prev['Low']
    high_last, low_last = last['High'], last['Low']

    body_prev = close_prev - open_prev
    body_last = close_last - open_last
    abody_prev, abody_last = abs(body_prev), abs(body_last)
    long_prev = (abody_prev / (high_prev - low_prev)) > 0.6 if (high_prev - low_prev) != 0 else False
    long_last = (abody_last / (high_last - low_last)) > 0.6 if (high_last - low_last) != 0 else False
    middle_prev = (open_prev + close_prev) / 2

    return (body_prev < 0) and (body_last > 0) and long_prev and long_last and \
           (open_last < low_prev) and (close_last > middle_prev) and (close_last < open_prev)


def bullish_pin_bar(df):
    prev, last = df.iloc[-2], df.iloc[-1]
    open_last, close_last = last['Open'], last['Close']
    high_last, low_last = last['High'], last['Low']
    low_prev = prev['Low']

    length_last = high_last - low_last
    shadow_bottom = min(open_last, close_last) - low_last
    return (low_last < low_prev) and (shadow_bottom > 0.67 * length_last)


def morning_star(df):
    c2, c1, c0 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    open2, close2 = c2['Open'], c2['Close']
    open1, close1 = c1['Open'], c1['Close']
    open0, close0 = c0['Open'], c0['Close']
    high2, low2 = c2['High'], c2['Low']
    high1, low1 = c1['High'], c1['Low']
    high0, low0 = c0['High'], c0['Low']

    body2, body1, body0 = close2 - open2, close1 - open1, close0 - open0
    abody2, abody1, abody0 = abs(body2), abs(body1), abs(body0)
    ratio1 = abody1 / (high1 - low1) if (high1 - low1) != 0 else 0

    return (body2 < 0) and (body0 > 0) and (abody2 > 0.6 * (high2 - low2)) and \
           (close1 < close2) and (abody1 < abody2) and (abody1 < abody0) and (ratio1 < 0.3)


def bullish_kicker(df):
    prev, last = df.iloc[-2], df.iloc[-1]
    open_prev, close_prev = prev['Open'], prev['Close']
    open_last, close_last = last['Open'], last['Close']
    high_last, low_last = last['High'], last['Low']

    body_prev = close_prev - open_prev
    body_last = close_last - open_last
    length_last = high_last - low_last
    ratio = abs(body_last) / length_last if length_last != 0 else 0
    longcandle = ratio > 0.6

    return (body_prev < 0) and (body_last > 0) and longcandle and (open_prev < open_last)


# --- Symbol lista beolvasása ---
def get_symbols(filename="symbols.csv"):
    try:
        df = pd.read_csv(filename, header=None, sep=';')
        return df[0].dropna().astype(str).tolist()
    except Exception as e:
        print(f"Hiba a {filename} beolvasásakor: {e}")
        return []


# --- Email küldés ---
def send_email(subject, body, to_email, from_email, app_password, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            attach = MIMEText(f.read(), 'base64', 'utf-8')
            attach.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
            msg.attach(attach)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(from_email, app_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("Email sikeresen elküldve.")
    except Exception as e:
        print(f"Email küldési hiba: {e}")


# --- Fő futás ---
def main():
    now = datetime.datetime.utcnow()
    # csak szombat 20:00 UTC után fusson
    if not (now.weekday() == 5 and now.hour >= 20):
        print("Nem megfelelő időpont, nem fut a script.")
        return

    symbols = get_symbols("symbols.csv")
    all_signals = []

    for symbol in symbols:
        try:
            df = yf.download(symbol, period="3mo", interval="1wk")
            if df.empty or len(df) < 3:
                continue

            if bullish_engulfing(df):
                all_signals.append({'Symbol': symbol, 'Signal': 'Bullish Engulfing'})
            if piercing_line(df):
                all_signals.append({'Symbol': symbol, 'Signal': 'Piercing Line'})
            if bullish_pin_bar(df):
                all_signals.append({'Symbol': symbol, 'Signal': 'Bullish Pin Bar'})
            if morning_star(df):
                all_signals.append({'Symbol': symbol, 'Signal': 'Morning Star'})
            if bullish_kicker(df):
                all_signals.append({'Symbol': symbol, 'Signal': 'Bullish Kicker'})

        except Exception as e:
            print(f"Hiba a {symbol} feldolgozásakor: {e}")

    if all_signals:
        df_signals = pd.DataFrame(all_signals)
        csv_name = "signalsw1_full_v1.csv"
        df_signals.to_csv(csv_name, index=False)
        print(f"Signals mentve: {csv_name}")

        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASS = os.getenv("EMAIL_PASS")
        TO_EMAIL = EMAIL_USER
        subject = f"Bullish gyertyajelek heti jelentés - {now:%Y-%m-%d}"
        body = "Csatolva a heti bullish jelek listája."
        send_email(subject, body, TO_EMAIL, EMAIL_USER, EMAIL_PASS, csv_name)
    else:
        print("Nem találtunk bullish gyertyajeleket.")


if __name__ == "__main__":
    main()
