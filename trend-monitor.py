import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

# 设置页面刷新时间（单位为秒）
REFRESH_INTERVAL = 300  # 5 分钟

# 要监控的股票代码（可自行修改）
tickers = ["AAPL", "MSFT", "TSLA"]

st.title("📈 即时股票监控儀表板")

# 创建一个区域显示股票价格
placeholder = st.empty()

while True:
    with placeholder.container():
        st.subheader(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for ticker in tickers:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d", interval="1m")
            current_price = data["Close"].iloc[-1]
            previous_close = stock.info['previousClose']
            change = current_price - previous_close
            pct_change = (change / previous_close) * 100
            
            st.metric(label=f"{ticker}", value=f"${current_price:.2f}",
                      delta=f"{change:.2f} ({pct_change:.2f}%)")
        
        st.markdown("---")
        st.info("页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
