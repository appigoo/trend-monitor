import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# 自动刷新与异动门槛设定
REFRESH_INTERVAL = 300  # 每 5 分钟
PRICE_THRESHOLD = 2.0   # 价格变动 ±2%
VOLUME_THRESHOLD = 50.0 # 成交量变动 ±50%

# UI选项
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

# 标题与用户输入
st.title("📊 股票监控儀表板（含异动标记 ✅ 与双提醒）")
input_tickers = st.text_input("请输入股票代号（英文逗号分隔）", value="AAPL, MSFT, TSLA")
selected_tickers = [t.strip().upper() for t in input_tickers.split(",") if t.strip()]
selected_period = st.selectbox("选择时间范围", period_options, index=1)
selected_interval = st.selectbox("选择间隔时间", interval_options, index=1)

placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"⏱ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for ticker in selected_tickers:
            stock = yf.Ticker(ticker)
            try:
                data = stock.history(period=selected_period, interval=selected_interval).reset_index()

                # 计算涨跌幅百分比
                data["Price Change %"] = data["Close"].pct_change() * 100
                data["Volume Change %"] = data["Volume"].pct_change() * 100

                # ✅ 异动标记：价格 + 成交量同时超出门槛
                def mark_signal(row):
                    if abs(row["Price Change %"]) >= PRICE_THRESHOLD and abs(row["Volume Change %"]) >= VOLUME_THRESHOLD:
                        return "✅"
                    return ""

                data["异动标记"] = data.apply(mark_signal, axis=1)

                # 最新数据计算
                current_price = data["Close"].iloc[-1]
                previous_close = stock.info.get("previousClose", current_price)
                price_change = current_price - previous_close
                price_pct_change = (price_change / previous_close) * 100 if previous_close else 0

                last_volume = data["Volume"].iloc[-1]
                prev_volume = data["Volume"].iloc[-2] if len(data) > 1 else last_volume
                volume_change = last_volume - prev_volume
                volume_pct_change = (volume_change / prev_volume) * 100 if prev_volume else 0

                # 显示当前指标
                st.metric(f"{ticker} 🟢 股价变动", f"${current_price:.2f}",
                          f"{price_change:.2f} ({price_pct_change:.2f}%)")
                st.metric(f"{ticker} 🔵 成交量变化", f"{last_volume:,}",
                          f"{volume_change:,} ({volume_pct_change:.2f}%)")

                # 异动提醒机制（toast + warning）
                if abs(price_pct_change) >= PRICE_THRESHOLD and abs(volume_pct_change) >= VOLUME_THRESHOLD:
                    alert_msg = f"📣 {ticker} 出现异动：价格 {price_pct_change:.2f}%，成交量 {volume_pct_change:.2f}%"
                    st.warning(alert_msg)
                    st.toast(alert_msg)

                # 显示历史表格含 ✅ 异动标记
                st.subheader(f"📋 历史数据：{ticker}")
                st.dataframe(data[["Datetime", "Close", "Price Change %", "Volume", "Volume Change %", "异动标记"]].tail(10))

            except Exception as e:
                st.error(f"⚠️ 无法取得 {ticker} 的资料：{e}")

        st.markdown("---")
        st.info("📡 页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
