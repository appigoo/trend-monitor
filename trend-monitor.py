import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import time
import threading
import numpy as np

# Streamlit 頁面設置
st.set_page_config(page_title="進階股票監視器", layout="wide")
st.title("進階股票價格監視器")

# 初始化 session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = {}
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# 輸入股票代碼（允許多個）
st.subheader("股票選擇")
tickers_input = st.text_input("輸入股票代碼 (用逗號分隔，例如 AAPL,MSFT,GOOGL):", "AAPL,MSFT").upper()
tickers = [ticker.strip() for ticker in tickers_input.split(",")]

# 時間範圍選項
period_options = {"1小時": "1h", "1天": "1d", "1週": "1w", "1個月": "1mo"}
interval_options = {"1小時": "5m", "1天": "15m", "1週": "1h", "1個月": "1d"}
period = st.selectbox("選擇時間範圍", list(period_options.keys()), index=0)
interval = interval_options[period]

# 警報設置
st.subheader("價格警報設置")
alert_ticker = st.selectbox("選擇股票用於警報", tickers, key="alert_ticker")
alert_price = st.number_input("設置警報價格 (USD)", min_value=0.0, value=100.0, step=0.1)
alert_type = st.selectbox("警報類型", ["高於", "低於"])
if st.button("添加警報"):
    st.session_state.alerts.append({"ticker": alert_ticker, "price": alert_price, "type": alert_type})
    st.success(f"已添加警報：{alert_ticker} {alert_type} ${alert_price}")

# 顯示當前警報
if st.session_state.alerts:
    st.subheader("當前警報")
    for alert in st.session_state.alerts:
        st.write(f"{alert['ticker']} {alert['type']} ${alert['price']}")

# 計算技術指標
def calculate_technical_indicators(data):
    # 計算移動平均線 (20 期)
    data['MA20'] = data['Close'].rolling(window=20).mean()
    # 計算 RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    return data

# 獲取股票數據的函數
def fetch_stock_data(ticker_symbol, period, interval):
    stock = yf.Ticker(ticker_symbol)
    try:
        data = stock.history(period=period, interval=interval)
        data = calculate_technical_indicators(data)
        return data
    except Exception as e:
        st.error(f"獲取 {ticker_symbol} 數據時發生錯誤: {e}")
        return pd.DataFrame()

# 更新數據的後台任務
def update_data():
    while True:
        for ticker in tickers:
            st.session_state.stock_data[ticker] = fetch_stock_data(ticker, period_options[period], interval)
        # 檢查警報
        for alert in st.session_state.alerts:
            ticker = alert['ticker']
            if ticker in st.session_state.stock_data and not st.session_state.stock_data[ticker].empty:
                latest_price = st.session_state.stock_data[ticker]['Close'].iloc[-1]
                if (alert['type'] == "高於" and latest_price >= alert['price']) or \
                   (alert['type'] == "低於" and latest_price <= alert['price']):
                    st.session_state.alerts.remove(alert)
                    st.warning(f"警報觸發：{ticker} 當前價格 ${latest_price:.2f} {alert['type']} ${alert['price']}")
        time.sleep(300)  # 每 5 分鐘更新一次

# 啟動後台線程
if 'thread_started' not in st.session_state:
    st.session_state.thread_started = True
    thread = threading.Thread(target=update_data, daemon=True)
    thread.start()

# 顯示股票數據
st.subheader("股票數據")
for ticker in tickers:
    if ticker in st.session_state.stock_data and not st.session_state.stock_data[ticker].empty:
        data = st.session_state.stock_data[ticker]
        # 顯示最新價格
        latest_data = data.iloc[-1]
        st.metric(
            label=f"{ticker} 最新價格",
            value=f"${latest_data['Close']:.2f}",
            delta=f"{latest_data['Close'] - data.iloc[-2]['Close']:.2f}"
        )

# 繪製價格走勢圖（多股票比較）
fig = go.Figure()
for ticker in tickers:
    if ticker in st.session_state.stock_data and not st.session_state.stock_data[ticker].empty:
        data = st.session_state.stock_data[ticker]
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['Close'],
                mode='lines+markers',
                name=f"{ticker} 收盤價"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data['MA20'],
                mode='lines',
                name=f"{ticker} 20期移動平均線",
                line=dict(dash='dash')
            )
        )
fig.update_layout(
    title=f"股票價格走勢比較 ({period})",
    xaxis_title="時間",
    yaxis_title="價格 (USD)",
    template="plotly_dark",
    showlegend=True
)
st.plotly_chart(fig, use_container_width=True)

# 繪製 RSI 圖表
fig_rsi = go.Figure()
for ticker in tickers:
    if ticker in st.session_state.stock_data and not st.session_state.stock_data[ticker].empty:
        data = st.session_state.stock_data[ticker]
        fig_rsi.add_trace(
            go.Scatter(
                x=data.index,
                y=data['RSI'],
                mode='lines',
                name=f"{ticker} RSI"
            )
        )
fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超買 (70)")
fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超賣 (30)")
fig_rsi.update_layout(
    title="相對強弱指數 (RSI)",
    xaxis_title="時間",
    yaxis_title="RSI",
    template="plotly_dark",
    showlegend=True
)
st.plotly_chart(fig_rsi, use_container_width=True)

# 顯示數據表格
st.subheader("最近數據")
for ticker in tickers:
    if ticker in st.session_state.stock_data and not st.session_state.stock_data[ticker].empty:
        st.write(f"{ticker} 數據")
        st.dataframe(st.session_state.stock_data[ticker][['Open', 'High', 'Low', 'Close', 'Volume', 'MA20', 'RSI']].tail(10))

# 顯示最後更新時間
st.write(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
