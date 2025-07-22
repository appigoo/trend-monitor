import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# --- 配置與用戶輸入 ---
st.sidebar.header("股票設定")
symbol = st.sidebar.text_input("輸入股票代碼 (例如: AAPL)", "AAPL").upper()
interval = st.sidebar.selectbox("數據間隔", ["1d"], index=0)  # 穩定日線
period = st.sidebar.selectbox("數據週期", ["3mo"], index=0)    # 最近三個月
fetch_button = st.sidebar.button("獲取數據")

# --- 快取函數：下載股票資料 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol, period_val, interval_val):
    try:
        with st.spinner(f"正在下載 {ticker_symbol} 的數據..."):
            data = yf.download(ticker_symbol, period=period_val, interval=interval_val)
        return data if not data.empty else None
    except Exception as e:
        st.error(f"下載錯誤：{e}")
        return None

# --- 函數：檢查指標可用性 ---
def check_indicator_availability(df):
    if df is None or df.empty:
        return []
    n = len(df)
    available = []
    if n >= 20:
        available += ["MA20", "EMA20", "Bollinger Bands"]
    if n >= 26:
        available += ["MACD", "Signal"]
    if n >= 14:
        available.append("RSI")
    return available

# --- 快取函數：計算技術指標 ---
@st.cache_data(ttl=3600)
def calculate_indicators(df):
    df_copy = df.copy()
    df_copy["MA20"] = pd.NA
    df_copy["EMA20"] = pd.NA
    df_copy["MACD"] = pd.NA
    df_copy["Signal"] = pd.NA
    df_copy["Upper"] = pd.NA
    df_copy["Lower"] = pd.NA
    df_copy["RSI"] = pd.NA

    if len(df_copy) >= 20:
        df_copy["MA20"] = df_copy["Close"].rolling(window=20).mean()
        df_copy["EMA20"] = df_copy["Close"].ewm(span=20, adjust=False).mean()
        df_copy["Upper"] = df_copy["MA20"] + 2 * df_copy["Close"].rolling(window=20).std()
        df_copy["Lower"] = df_copy["MA20"] - 2 * df_copy["Close"].rolling(window=20).std()

    if len(df_copy) >= 26:
        ema12 = df_copy["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df_copy["Close"].ewm(span=26, adjust=False).mean()
        df_copy["MACD"] = ema12 - ema26
        df_copy["Signal"] = df_copy["MACD"].ewm(span=9, adjust=False).mean()

    if len(df_copy) >= 14:
        delta = df_copy["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df_copy["RSI"] = 100 - (100 / (1 + rs))

    return df_copy

# --- 主應用程式邏輯 ---
st.title("📊 股票趨勢監測系統")

if fetch_button:
    stock_data = get_stock_data(symbol, period, interval)
    if stock_data is None:
        st.warning("⚠️ 無法獲取數據。請確認股票代碼或網路連線。")
    else:
        available_indicators = check_indicator_availability(stock_data)
        if available_indicators:
            st.success(f"✅ 可計算指標：{', '.join(available_indicators)}")
        else:
            st.warning("⚠️ 資料不足，無法計算任何指標。請選擇更長週期。")

        data_with_indicators = calculate_indicators(stock_data)

        st.subheader("💹 價格與指標圖表")
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators["Close"], mode='lines', name='Close'))

        for col in ["MA20", "EMA20", "Upper", "Lower"]:
            if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                fig_price.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators[col], mode='lines', name=col))

        fig_price.update_layout(title=f"{symbol} 價格與技術指標", xaxis_title="日期", yaxis_title="價格")
        st.plotly_chart(fig_price)

        st.subheader("📉 MACD 指標")
        fig_macd = go.Figure()
        for col in ["MACD", "Signal"]:
            if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                fig_macd.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators[col], mode='lines', name=col))
        fig_macd.update_layout(title="MACD", xaxis_title="日期", yaxis_title="值")
        st.plotly_chart(fig_macd)

        st.subheader("📊 RSI 指標")
        if "RSI" in data_with_indicators.columns and data_with_indicators["RSI"].notna().any():
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=data_with_indicators.index, y=data_with_indicators["RSI"], mode='lines', name='RSI'))
            fig_rsi.add_hline(y=70, line_dash="dot", line_color="red")
            fig_rsi.add_hline(y=30, line_dash="dot", line_color="green")
            fig_rsi.update_layout(title="RSI", xaxis_title="日期", yaxis_title="RSI")
            st.plotly_chart(fig_rsi)
        else:
            st.info("無足夠 RSI 數據可供繪製。")

        st.subheader("🧾 最新數據概覽")
        st.dataframe(data_with_indicators.tail(10))
else:
    st.info("請在左側設定參數後點擊『獲取數據』。")
