import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
st.set_page_config(page_title="股票監控儀表板", layout="wide")

load_dotenv() 
# 异动阈值设定
REFRESH_INTERVAL = 300  # 秒，5 分钟自动刷新
PRICE_THRESHOLD = 2.0   # 股价变化百分比
VOLUME_THRESHOLD = 50.0 # 成交量变化百分比

# Gmail 发信者帐号设置

##
 # 本地开发使用，线上部署不会用到 .env 文件

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# 邮件发送函数
def send_email_alert(ticker, price_pct, volume_pct):
    subject = f"📣 股票異動通知：{ticker}"
    body = f"""
    股票代號：{ticker}
    股價變動：{price_pct:.2f}%
    成交量變動：{volume_pct:.2f}%
    
    系統偵測到價格與成交量同時異常變動，請立即查看市場情況。
    """
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        st.toast(f"📬 Email 已發送給 {RECIPIENT_EMAIL}")
    except Exception as e:
        st.error(f"Email 發送失敗：{e}")

# UI 設定
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

st.title("📊 股票監控儀表板（含異動提醒與 Email 通知 ✅）")
input_tickers = st.text_input("請輸入股票代號（逗號分隔）", value="TSLA, NIO, TSLL")
selected_tickers = [t.strip().upper() for t in input_tickers.split(",") if t.strip()]
selected_period = st.selectbox("選擇時間範圍", period_options, index=1)
selected_interval = st.selectbox("選擇資料間隔", interval_options, index=1)
window_size = st.slider("滑動平均窗口大小", min_value=2, max_value=40, value=5)

placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"⏱ 更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for ticker in selected_tickers:
            stock = yf.Ticker(ticker)
            try:
                data = stock.history(period=selected_period, interval=selected_interval).reset_index()

                # 計算漲跌幅百分比
                data["Price Change %"] = data["Close"].pct_change() * 100
                data["Volume Change %"] = data["Volume"].pct_change() * 100
                ### 1 ###
                
                # 計算前 5 筆平均收盤價與平均成交量
                data["前5均價"] = data["Price Change %"].rolling(window=5).mean()
                data["前5均量"] = data["Volume"].rolling(window=5).mean()
                # 每筆收盤價相對於前 5 筆平均漲跌幅 (%)
                data["📈 股價漲跌幅 (%)"] = ((data["Price Change %"] - data["前5均價"]) / data["前5均價"]) * 100
                # 每筆成交量相對於前 5 筆平均成交量變動幅 (%)
                data["📊 成交量變動幅 (%)"] = ((data["Volume"] - data["前5均量"]) / data["前5均量"]) * 100
                ### 1 ###
                # 標記是否量價異動
                def mark_signal(row):
                    if abs(row["Price Change %"]) >= PRICE_THRESHOLD and abs(row["Volume Change %"]) >= VOLUME_THRESHOLD:
                        return "✅"
                    return ""
                data["異動標記"] = data.apply(mark_signal, axis=1)

                # 當前資料
                current_price = data["Close"].iloc[-1]
                previous_close = stock.info.get("previousClose", current_price)
                price_change = current_price - previous_close
                price_pct_change = (price_change / previous_close) * 100 if previous_close else 0

                last_volume = data["Volume"].iloc[-1]
                prev_volume = data["Volume"].iloc[-2] if len(data) > 1 else last_volume
                volume_change = last_volume - prev_volume
                volume_pct_change = (volume_change / prev_volume) * 100 if prev_volume else 0

                # 顯示當前資料
                st.metric(f"{ticker} 🟢 股價變動", f"${current_price:.2f}",
                          f"{price_change:.2f} ({price_pct_change:.2f}%)")
                st.metric(f"{ticker} 🔵 成交量變動", f"{last_volume:,}",
                          f"{volume_change:,} ({volume_pct_change:.2f}%)")

                # 異動提醒 + Email 推播
                if abs(price_pct_change) >= PRICE_THRESHOLD and abs(volume_pct_change) >= VOLUME_THRESHOLD:
                    alert_msg = f"{ticker} 異動：價格 {price_pct_change:.2f}%、成交量 {volume_pct_change:.2f}%"
                    st.warning(f"📣 {alert_msg}")
                    st.toast(f"📣 {alert_msg}")
                    send_email_alert(ticker, price_pct_change, volume_pct_change)

                # 顯示含異動標記的歷史資料
                st.subheader(f"📋 歷史資料：{ticker}")
                #st.dataframe(data[["Datetime", "Close", "Price Change %", "Volume", "Volume Change %", "異動標記"]].tail(10))
                ### 2 ###
                #st.dataframe(data[[ "Datetime", "Close", "Price Change %", "📈 股價漲跌幅 (%)", "Volume", "Volume Change %", "📊 成交量變動幅 (%)", "異動標記" ]].tail(10),height=600,use_container_width=True)
                st.dataframe(data[[ "Datetime", "Close", "Price Change %", "Volume", "Volume Change %", "📈 股價漲跌幅 (%)", "📊 成交量變動幅 (%)", "異動標記" ]].tail(10),height=600,use_container_width=True)
                ### 2 ###
            except Exception as e:
                st.error(f"⚠️ 無法取得 {ticker} 的資料：{e}")

        st.markdown("---")
        st.info("📡 頁面將在 5 分鐘後自動刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
