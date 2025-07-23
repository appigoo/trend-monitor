import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
from datetime import datetime
import time
import threading

# Streamlit 頁面設置
st.set_page_config(page_title="股票監視器", layout="wide")
st.title("即時股票價格監視器")

# 輸入股票代碼
ticker = st.text_input("輸入股票代碼 (例如 AAPL for Apple):", "AAPL").upper()

# 用於儲存數據的全局變量
stock_data = pd.DataFrame()

# 獲取股票數據的函數
def fetch_stock_data(ticker_symbol):
    global stock_data
    stock = yf.Ticker(ticker_symbol)
    # 獲取最近 1 小時的數據，間隔為 5 分鐘
    data = stock.history(period="1h", interval="5m")
    return data

# 更新數據並顯示
def update_data():
    global stock_data
    while True:
        try:
            stock_data = fetch_stock_data(ticker)
            time.sleep(300)  # 每 5 分鐘更新一次 (300 秒)
        except Exception as e:
            st.error(f"獲取數據時發生錯誤: {e}")
            time.sleep(60)  # 如果出錯，等待 1 分鐘後重試

# 啟動後台線程以更新數據
def start_background_thread():
    thread = threading.Thread(target=update_data, daemon=True)
    thread.start()

# 初始化數據並啟動後台線程
if 'thread_started' not in st.session_state:
    st.session_state.thread_started = True
    start_background_thread()

# 顯示股票數據
if not stock_data.empty:
    # 顯示最新價格
    latest_data = stock_data.iloc[-1]
    st.metric(
        label=f"{ticker} 最新價格",
        value=f"${latest_data['Close']:.2f}",
        delta=f"{latest_data['Close'] - stock_data.iloc[-2]['Close']:.2f}"
    )

    # 繪製價格走勢圖
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stock_data.index,
            y=stock_data['Close'],
            mode='lines+markers',
            name='收盤價'
        )
    )
    fig.update_layout(
        title=f"{ticker} 股票價格走勢 (每 5 分鐘更新)",
        xaxis_title="時間",
        yaxis_title="價格 (USD)",
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 顯示數據表格
    st.subheader("最近數據")
    st.dataframe(stock_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10))

else:
    st.write("正在加載數據，請稍候...")

# 添加更新時間
st.write(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
