import yfinance as yf
import pandas as pd
import streamlit as st
import datetime

# 设置股票代码和时间范围
symbol = st.sidebar.text_input("输入股票代码", "AAPL")
interval = st.sidebar.selectbox("数据间隔", ["5m", "15m", "1h"])
period = st.sidebar.selectbox("数据周期", ["1d", "5d", "1mo"])

# 下载股票数据
data = yf.download(symbol, interval=interval, period=period)

# 计算指标
data["MA20"] = data["Close"].rolling(window=20).mean()
data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()

# MACD
ema12 = data["Close"].ewm(span=12, adjust=False).mean()
ema26 = data["Close"].ewm(span=26, adjust=False).mean()
data["MACD"] = ema12 - ema26
data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

# 布林带
data["Upper"] = data["MA20"] + 2 * data["Close"].rolling(window=20).std()
data["Lower"] = data["MA20"] - 2 * data["Close"].rolling(window=20).std()

# 趋势判断逻辑（示例）
latest = data.iloc[-1]
trend = "震荡"
if latest["Close"] > latest["Upper"]:
    trend = "可能突破上涨 📈"
elif latest["Close"] < latest["Lower"]:
    trend = "可能突破下跌 📉"
elif latest["MACD"] > latest["Signal"]:
    trend = "MACD金叉，上涨趋势加强 🔼"

# 显示内容
st.title("📊 股票趋势监测系统")
st.write(f"当前股票：**{symbol}**，趋势判断：**{trend}**")
st.line_chart(data[["Close", "MA20", "EMA20", "Upper", "Lower"]])
st.line_chart(data[["MACD", "Signal"]])
st.dataframe(data.tail(10))
