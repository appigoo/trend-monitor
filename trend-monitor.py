import yfinance as yf
import pandas as pd
import streamlit as st
import datetime
import plotly.graph_objects as go

# --- 配置與用戶輸入 ---
st.sidebar.header("股票設定")
symbol = st.sidebar.text_input("輸入股票代碼 (例如: AAPL)", "AAPL").upper()

interval = st.sidebar.selectbox(
    "數據間隔",
    ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    index=3
)

period = st.sidebar.selectbox(
    "數據週期",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    index=2
)

fetch_button = st.sidebar.button("獲取數據")

# --- 函數：數據下載與快取 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol, period_val, interval_val):
    try:
        with st.spinner(f"正在下載 {ticker_symbol} 的數據..."):
            data = yf.download(ticker_symbol, period=period_val, interval=interval_val)
        if data.empty:
            st.warning(f"沒有找到 {ticker_symbol} 的數據。")
            return None
        return data
    except Exception as e:
        st.error(f"下載錯誤: {e}")
        return None

# --- 函數：技術指標計算 ---
@st.cache_data(ttl=3600)
def calculate_indicators(df):
    if df is None or df.empty:
        st.warning("輸入數據為空。")
        return None

    df_copy = df.copy()
    df_copy["MA20"] = pd.NA
    df_copy["EMA20"] = pd.NA
    df_copy["MACD"] = pd.NA
    df_copy["Signal"] = pd.NA
    df_copy["Upper"] = pd.NA
    df_copy["Lower"] = pd.NA
    df_copy["RSI"] = pd.NA

    # MA / EMA
    if len(df_copy) >= 20:
        df_copy["MA20"] = df_copy["Close"].rolling(window=20).mean()
        df_copy["EMA20"] = df_copy["Close"].ewm(span=20, adjust=False).mean()

    # MACD
    if len(df_copy) >= 26:
        ema12 = df_copy["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df_copy["Close"].ewm(span=26, adjust=False).mean()
        df_copy["MACD"] = ema12 - ema26
        df_copy["Signal"] = df_copy["MACD"].ewm(span=9, adjust=False).mean()

    # Bollinger Bands
    if len(df_copy) >= 20 and df_copy["MA20"].notna().any():
        df_copy["Upper"] = df_copy["MA20"] + 2 * df_copy["Close"].rolling(window=20).std()
        df_copy["Lower"] = df_copy["MA20"] - 2 * df_copy["Close"].rolling(window=20).std()

    # RSI
    if len(df_copy) >= 14:
        delta = df_copy["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df_copy["RSI"] = 100 - (100 / (1 + rs))

    return df_copy

# --- 趨勢分析略（可保留原本的 analyze_trend 函數）---

# --- 主程式邏輯 ---
st.title("📊 股票趨勢監測系統")

if fetch_button:
    stock_data = get_stock_data(symbol, period, interval)

    if stock_data is not None:
        data_with_indicators = calculate_indicators(stock_data)

        if data_with_indicators is not None:
            st.write(f"當前股票：**{symbol}**")

            # 🎯 價格與技術指標（Plotly）
            st.subheader("互動式價格圖")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators["Close"], mode='lines', name='Close'))
            for col in ["MA20", "EMA20", "Upper", "Lower"]:
                if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                    fig.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators[col], mode='lines', name=col))
            fig.update_layout(title=f"{symbol} 價格與技術指標", xaxis_title="日期", yaxis_title="價格")
            st.plotly_chart(fig)

            # 📉 MACD 指標
            st.subheader("MACD 指標")
            fig_macd = go.Figure()
            for col in ["MACD", "Signal"]:
                if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                    fig_macd.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators[col], mode='lines', name=col))
            fig_macd.update_layout(title="MACD", xaxis_title="日期", yaxis_title="值")
            st.plotly_chart(fig_macd)

            # 💡 RSI 指標
            if "RSI" in data_with_indicators.columns and data_with_indicators["RSI"].notna().any():
                st.subheader("RSI 指標")
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators["RSI"], mode='lines', name='RSI'))
                fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
                fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
                fig_rsi.update_layout(title="RSI 指標", xaxis_title="日期", yaxis_title="RSI")
                st.plotly_chart(fig_rsi)
            else:
                st.info("沒有足夠的 RSI 數據可供繪製。")

            # 🧾 數據表格
            st.subheader("最新數據概覽")
            st.dataframe(data_with_indicators.tail(10))

        else:
            st.info("無法計算指標。")
    else:
        st.info("無法獲取數據。請檢查股票代碼或網路連線。")
else:
    st.info("請在左側設定參數後點擊 '獲取數據'。")
