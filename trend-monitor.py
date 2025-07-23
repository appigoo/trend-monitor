import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

REFRESH_INTERVAL = 300  # 每 5 分钟自动刷新

# 时间范围与间隔选项
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

st.title("📊 股票监控儀表板（含历史涨跌幅分析）")

# 用户输入股票代号
input_tickers = st.text_input("请输入股票代号（英文逗号分隔，例如：AAPL, MSFT, TSLA）", value="AAPL, MSFT")
selected_tickers = [ticker.strip().upper() for ticker in input_tickers.split(",") if ticker.strip()]

# 选择时间范围与间隔
selected_period = st.selectbox("选择时间范围 (period)", period_options, index=1)
selected_interval = st.selectbox("选择间隔时间 (interval)", interval_options, index=1)

placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"⏱ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not selected_tickers:
            st.warning("⚠️ 请输入至少一个有效的股票代号。")
        else:
            for ticker in selected_tickers:
                stock = yf.Ticker(ticker)
                try:
                    data = stock.history(period=selected_period, interval=selected_interval)
                    data = data.reset_index()

                    # 股价涨跌幅（与前一笔比较）
                    data["Price Change %"] = data["Close"].pct_change() * 100

                    # 成交量变化幅度（与前一笔比较）
                    data["Volume Change %"] = data["Volume"].pct_change() * 100

                    current_price = data["Close"].iloc[-1]
                    previous_close = stock.info.get('previousClose', current_price)
                    price_change = current_price - previous_close
                    price_pct_change = (price_change / previous_close) * 100 if previous_close else 0

                    last_volume = data["Volume"].iloc[-1]
                    prev_volume = data["Volume"].iloc[-2] if len(data) > 1 else last_volume
                    volume_change = last_volume - prev_volume
                    volume_pct_change = (volume_change / prev_volume) * 100 if prev_volume else 0

                    # 显示当前涨跌幅
                    st.metric(label=f"{ticker} 🟢 股价变动", value=f"${current_price:.2f}",
                              delta=f"{price_change:.2f} ({price_pct_change:.2f}%)")
                    st.metric(label=f"{ticker} 🔵 成交量变化", value=f"{last_volume:,}",
                              delta=f"{volume_change:,} ({volume_pct_change:.2f}%)")

                    # 显示含涨跌幅的历史数据
                    st.subheader(f"📋 历史数据与涨跌幅：{ticker}")
                    st.dataframe(data[["Datetime", "Close", "Price Change %", "Volume", "Volume Change %"]].tail(10))

                except Exception as e:
                    st.warning(f"🚫 无法取得 {ticker} 的资料：{e}")

        st.markdown("---")
        st.info("📡 页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
