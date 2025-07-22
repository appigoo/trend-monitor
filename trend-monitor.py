import yfinance as yf
import pandas as pd
import streamlit as st
import datetime

# --- 配置與用戶輸入 ---
st.sidebar.header("股票設定")

# 股票代碼輸入，並轉換為大寫以保持一致性
symbol = st.sidebar.text_input("輸入股票代碼 (例如: AAPL)", "AAPL").upper()

# 數據間隔選擇，增加了更多選項
interval = st.sidebar.selectbox(
    "數據間隔",
    ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
    index=3 # 預設選擇 '15m'
)

# 日期選擇器，用於指定數據的開始和結束日期
today = datetime.date.today()
default_start_date = today - datetime.timedelta(days=30) # 預設為過去30天
start_date = st.sidebar.date_input("開始日期", default_start_date)
end_date = st.sidebar.date_input("結束日期", today)

# 觸發數據獲取的按鈕
fetch_button = st.sidebar.button("獲取數據")

# --- 函數：數據下載與快取 ---

@st.cache_data(ttl=3600) # 快取數據，有效期為1小時
def get_stock_data(ticker_symbol, start, end, interval_val):
    """
    從 Yahoo Finance 下載股票數據。
    使用 Streamlit 的快取功能提升性能。
    """
    try:
        with st.spinner(f"正在下載 {ticker_symbol} 的數據..."):
            data = yf.download(ticker_symbol, start=start, end=end, interval=interval_val)
        if data.empty:
            st.warning(f"沒有找到 {ticker_symbol} 在 {start} 到 {end} 期間，間隔為 {interval_val} 的數據。請檢查股票代碼或日期範圍。")
            return None
        return data
    except Exception as e:
        st.error(f"下載數據時發生錯誤: {e}")
        return None

# --- 函數：指標計算與快取 ---

@st.cache_data(ttl=3600) # 快取指標計算結果
def calculate_indicators(df):
    """
    為給定的 DataFrame 計算各種技術指標。
    """
    if df is None or df.empty:
        return None

    df_copy = df.copy() # 在數據副本上操作，避免 SettingWithCopyWarning

    # 移動平均線 (Moving Averages)
    df_copy["MA20"] = df_copy["Close"].rolling(window=20).mean()
    df_copy["EMA20"] = df_copy["Close"].ewm(span=20, adjust=False).mean()

    # MACD (Moving Average Convergence Divergence)
    # 確保有足夠的數據點來計算 EMA
    if len(df_copy) >= 26: # EMA26 需要至少26個週期
        ema12 = df_copy["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df_copy["Close"].ewm(span=26, adjust=False).mean()
        df_copy["MACD"] = ema12 - ema26
        df_copy["Signal"] = df_copy["MACD"].ewm(span=9, adjust=False).mean()
    else:
        df_copy["MACD"] = pd.NA # 使用 pandas 的 NA 表示缺失值
        df_copy["Signal"] = pd.NA
        st.warning("數據點不足以計算MACD (至少需要26個點)。")

    # 布林帶 (Bollinger Bands)
    # 確保有足夠的數據點來計算滾動標準差和平均值
    if len(df_copy) >= 20: # MA20 和標準差需要至少20個週期
        df_copy["Upper"] = df_copy["MA20"] + 2 * df_copy["Close"].rolling(window=20).std()
        df_copy["Lower"] = df_copy["MA20"] - 2 * df_copy["Close"].rolling(window=20).std()
    else:
        df_copy["Upper"] = pd.NA
        df_copy["Lower"] = pd.NA
        st.warning("數據點不足以計算布林帶 (至少需要20個點)。")

    return df_copy

# --- 函數：趨勢分析 ---

def analyze_trend(df):
    """
    根據最新的數據和指標分析股票趨勢。
    """
    if df is None or df.empty:
        return "無數據"

    # 獲取最新一行的數據
    latest = df.iloc[-1]
    # 預設趨勢為震盪
    trend_message = "震盪 ↔️"

    # 在進行比較前，檢查指標是否存在 NaN 值
    if pd.isna(latest["Close"]) or pd.isna(latest["MA20"]) or pd.isna(latest["EMA20"]):
        return "數據不足，無法判斷趨勢"

    # 布林帶突破判斷
    if not pd.isna(latest["Upper"]) and latest["Close"] > latest["Upper"]:
        trend_message = "可能突破上漲 � (布林帶)"
    elif not pd.isna(latest["Lower"]) and latest["Close"] < latest["Lower"]:
        trend_message = "可能突破下跌 📉 (布林帶)"
    # MACD 金叉/死叉判斷 (需要前一個數據點來判斷交叉)
    elif not pd.isna(latest["MACD"]) and not pd.isna(latest["Signal"]) and len(df) >= 2:
        # MACD 金叉：MACD 線上穿 Signal 線
        if latest["MACD"] > latest["Signal"] and df["MACD"].iloc[-2] <= df["Signal"].iloc[-2]:
            trend_message = "MACD金叉，上漲趨勢可能形成 🔼"
        # MACD 死叉：MACD 線下穿 Signal 線
        elif latest["MACD"] < latest["Signal"] and df["MACD"].iloc[-2] >= df["Signal"].iloc[-2]:
            trend_message = "MACD死叉，下跌趨勢可能形成 🔽"
        # MACD 線在 Signal 線上方，表示看漲
        elif latest["MACD"] > latest["Signal"]:
            trend_message = "MACD看漲，上漲趨勢中 ⬆️"
        # MACD 線在 Signal 線下方，表示看跌
        elif latest["MACD"] < latest["Signal"]:
            trend_message = "MACD看跌，下跌趨勢中 ⬇️"

    # 簡單的移動平均線判斷 (作為補充或備用)
    if latest["Close"] > latest["MA20"] and latest["Close"] > latest["EMA20"]:
        # 如果當前趨勢判斷不是更具體的上漲，則更新為上漲趨勢
        if "上漲" not in trend_message:
            trend_message = "上漲趨勢 ⬆️"
    elif latest["Close"] < latest["MA20"] and latest["Close"] < latest["EMA20"]:
        # 如果當前趨勢判斷不是更具體的下跌，則更新為下跌趨勢
        if "下跌" not in trend_message:
            trend_message = "下跌趨勢 ⬇️"

    return trend_message

# --- 主應用程式邏輯 ---
st.title("📊 股票趨勢監測系統")

# 當點擊「獲取數據」按鈕時執行
if fetch_button:
    # 檢查日期範圍是否有效
    if start_date >= end_date:
        st.error("錯誤：開始日期必須早於結束日期。")
    else:
        # 1. 下載數據
        stock_data = get_stock_data(symbol, start_date, end_date, interval)

        if stock_data is not None:
            # 2. 計算指標
            data_with_indicators = calculate_indicators(stock_data)

            if data_with_indicators is not None:
                # 3. 分析趨勢
                current_trend = analyze_trend(data_with_indicators)

                # 顯示股票代碼和趨勢判斷
                st.write(f"當前股票：**{symbol}**")
                st.markdown(f"**趨勢判斷：{current_trend}**")

                # 繪製價格與移動平均線圖
                st.subheader("價格與移動平均線")
                # 確保只繪製 DataFrame 中存在的列
                plot_cols_price = ["Close", "MA20", "EMA20", "Upper", "Lower"]
                available_price_cols = [col for col in plot_cols_price if col in data_with_indicators.columns]
                st.line_chart(data_with_indicators[available_price_cols])

                # 繪製 MACD 指標圖
                st.subheader("MACD 指標")
                plot_cols_macd = ["MACD", "Signal"]
                available_macd_cols = [col for col in plot_cols_macd if col in data_with_indicators.columns]
                st.line_chart(data_with_indicators[available_macd_cols])

                # 顯示最新數據概覽
                st.subheader("最新數據概覽")
                st.dataframe(data_with_indicators.tail(10))
            else:
                st.info("無法計算指標，請檢查數據是否足夠。")
        else:
            st.info("無法獲取股票數據。請檢查股票代碼或網路連接。")
else:
    # 應用程式啟動時的提示訊息
    st.info("請在左側邊欄輸入股票代碼、選擇日期範圍和數據間隔，然後點擊 '獲取數據'。")
�
