import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

REFRESH_INTERVAL = 300  # 每 5 分钟自动刷新

# 时间范围与间隔选项
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

st.title("📊 股票历史数据与即时监控儀表板")

# 使用者输入股票代码（以逗号分隔）
input_tickers = st.text_input("请输入股票代号（用英文逗号分隔，例如：AAPL, MSFT, TSLA）", value="AAPL, MSFT")
selected_tickers = [ticker.strip().upper() for ticker in input_tickers.split(",") if ticker.strip()]

# 使用者选择 period 与 interval
selected_period = st.selectbox("选择时间范围 (period)", period_options, index=1)
selected_interval = st.selectbox("选择间隔时间 (interval)", interval_options, index=1)

placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not selected_tickers:
            st.warning("⚠️ 请输入至少一个有效的股票代号。")
        else:
            for ticker in selected_tickers:
                stock = yf.Ticker(ticker)
                try:
                    data = stock.history(period=selected_period, interval=selected_interval)
                    current_price = data["Close"].iloc[-1]
                    previous_close = stock.info.get('previousClose', current_price)
                    change = current_price - previous_close
                    pct_change = (change / previous_close) * 100
                    
                    st.metric(label=f"{ticker}", value=f"${current_price:.2f}",
                              delta=f"{change:.2f} ({pct_change:.2f}%)")

                    # 显示历史数据表格
                    st.dataframe(data.tail(5))
                except Exception as e:
                    st.warning(f"🚫 无法取得 {ticker} 的资料：{e}")
        
        st.markdown("---")
        st.info("页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
