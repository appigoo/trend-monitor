import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# 参数设定
REFRESH_INTERVAL = 300  # 每 5 分钟自动刷新
PRICE_THRESHOLD = 2.0   # 股价变动超过 ±2%
VOLUME_THRESHOLD = 50.0 # 成交量变动超过 ±50%

# UI 设置
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

st.title("📊 股票监控儀表板（双重异动提醒）")

# 用户输入
input_tickers = st.text_input("请输入股票代号（用英文逗号分隔）", value="AAPL, MSFT, TSLA")
selected_tickers = [t.strip().upper() for t in input_tickers.split(",") if t.strip()]
selected_period = st.selectbox("选择时间范围 (period)", period_options, index=1)
selected_interval = st.selectbox("选择间隔时间 (interval)", interval_options, index=1)

# 主内容区
placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"⏱ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for ticker in selected_tickers:
            stock = yf.Ticker(ticker)
            try:
                data = stock.history(period=selected_period, interval=selected_interval)
                data = data.reset_index()

                # 计算涨跌幅
                data["Price Change %"] = data["Close"].pct_change() * 100
                data["Volume Change %"] = data["Volume"].pct_change() * 100

                # 当前数据
                current_price = data["Close"].iloc[-1]
                previous_close = stock.info.get("previousClose", current_price)
                price_change = current_price - previous_close
                price_pct_change = (price_change / previous_close) * 100 if previous_close else 0

                last_volume = data["Volume"].iloc[-1]
                prev_volume = data["Volume"].iloc[-2] if len(data) > 1 else last_volume
                volume_change = last_volume - prev_volume
                volume_pct_change = (volume_change / prev_volume) * 100 if prev_volume else 0

                # 显示基本数据
                st.metric(f"{ticker} 🟢 股价变动", f"${current_price:.2f}",
                          f"{price_change:.2f} ({price_pct_change:.2f}%)")
                st.metric(f"{ticker} 🔵 成交量变化", f"{last_volume:,}",
                          f"{volume_change:,} ({volume_pct_change:.2f}%)")

                # 双重提醒机制
                if abs(price_pct_change) >= PRICE_THRESHOLD and abs(volume_pct_change) >= VOLUME_THRESHOLD:
                    message = f"🚨 {ticker} 异动提醒：价格 {price_pct_change:.2f}%、成交量 {volume_pct_change:.2f}%"
                    st.warning(message)
                    st.toast(message)

                # 显示含涨跌幅的历史数据
                st.dataframe(data[["Datetime", "Close", "Price Change %", "Volume", "Volume Change %"]].tail(10))

            except Exception as e:
                st.error(f"⚠️ 无法取得 {ticker} 的数据：{e}")

        st.markdown("---")
        st.info("📡 页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
