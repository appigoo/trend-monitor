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

# 數據週期選擇器，替換了日期選擇器
period = st.sidebar.selectbox(
    "數據週期",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    index=2 # 預設選擇 '1mo'
)

# 觸發數據獲取的按鈕
fetch_button = st.sidebar.button("獲取數據")

# --- 函數：數據下載與快取 ---

@st.cache_data(ttl=3600) # 快取數據，有效期為1小時
def get_stock_data(ticker_symbol, period_val, interval_val):
    """
    從 Yahoo Finance 下載股票數據。
    使用 Streamlit 的快取功能提升性能。
    """
    try:
        with st.spinner(f"正在下載 {ticker_symbol} 的數據..."):
            # 使用 period 參數下載數據
            data = yf.download(ticker_symbol, period=period_val, interval=interval_val)
        if data.empty:
            st.warning(f"沒有找到 {ticker_symbol} 在週期 {period_val} 內，間隔為 {interval_val} 的數據。請檢查股票代碼或數據週期。")
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
        st.warning("輸入數據為空，無法計算指標。")
        return None

    df_copy = df.copy() # 在數據副本上操作，避免 SettingWithCopyWarning

    # 初始化所有指標列為 NaN，確保它們在任何情況下都存在且長度正確
    df_copy["MA20"] = pd.NA
    df_copy["EMA20"] = pd.NA
    df_copy["MACD"] = pd.NA
    df_copy["Signal"] = pd.NA
    df_copy["Upper"] = pd.NA
    df_copy["Lower"] = pd.NA

    # 移動平均線 (Moving Averages)
    if len(df_copy) >= 20:
        df_copy["MA20"] = df_copy["Close"].rolling(window=20).mean()
        df_copy["EMA20"] = df_copy["Close"].ewm(span=20, adjust=False).mean()
    else:
        st.warning("數據點不足以計算MA20和EMA20 (至少需要20個點)。")


    # MACD (Moving Average Convergence Divergence)
    if len(df_copy) >= 26: # EMA26 需要至少26個週期
        ema12 = df_copy["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df_copy["Close"].ewm(span=26, adjust=False).mean()
        df_copy["MACD"] = ema12 - ema26
        df_copy["Signal"] = df_copy["MACD"].ewm(span=9, adjust=False).mean()
    else:
        st.warning("數據點不足以計算MACD (至少需要26個點)。")

    # 布林帶 (Bollinger Bands)
    if len(df_copy) >= 20: # MA20 和標準差需要至少20個週期
        # Ensure MA20 is calculated before using it for Bollinger Bands
        # 使用 .notna().any() 檢查 MA20 是否有任何非 NaN 值
        if df_copy["MA20"].notna().any():
            df_copy["Upper"] = df_copy["MA20"] + 2 * df_copy["Close"].rolling(window=20).std()
            df_copy["Lower"] = df_copy["MA20"] - 2 * df_copy["Close"].rolling(window=20).std()
        else:
            st.warning("MA20數據不足，無法計算布林帶。")
    else:
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

    # 在進行比較前，檢查關鍵指標是否存在 NaN 值
    # 使用 .item() 確保獲取的是標量值，避免 Series 的布林值歧義錯誤
    try:
        # 檢查 'Close' 列是否存在於 latest Series 中，並確保其不是 NaN
        if "Close" not in latest or pd.isna(latest["Close"].item()):
            return "最新收盤價數據缺失或無效，無法判斷趨勢"
    except ValueError: # 如果 .item() 失敗 (例如，latest["Close"] 不是單一標量)
        return "最新收盤價數據格式異常，無法判斷趨勢"
    except KeyError: # 如果 'Close' 列不存在
        return "數據中缺少 'Close' 列，無法判斷趨勢"

    # 提取所有需要判斷的標量值，並處理潛在的 KeyError
    try:
        close_price = latest["Close"].item()
        ma20 = latest["MA20"].item() if "MA20" in latest else pd.NA
        ema20 = latest["EMA20"].item() if "EMA20" in latest else pd.NA
        macd = latest["MACD"].item() if "MACD" in latest else pd.NA
        signal = latest["Signal"].item() if "Signal" in latest else pd.NA
        upper_band = latest["Upper"].item() if "Upper" in latest else pd.NA
        lower_band = latest["Lower"].item() if "Lower" in latest else pd.NA
    except ValueError:
        return "數據格式異常，無法提取指標值"
    except KeyError as e:
        return f"缺少關鍵指標列: {e}，無法判斷趨勢"

    # 布林帶突破判斷
    if not pd.isna(upper_band) and close_price > upper_band:
        trend_message = "可能突破上漲 📈 (布林帶)"
    elif not pd.isna(lower_band) and close_price < lower_band:
        trend_message = "可能突破下跌 📉 (布林帶)"
    # MACD 金叉/死叉判斷 (需要前一個數據點來判斷交叉)
    elif not pd.isna(macd) and not pd.isna(signal) and len(df) >= 2:
        # 確保前一個數據點的 MACD 和 Signal 也存在
        prev_macd = df["MACD"].iloc[-2].item() if "MACD" in df.columns else pd.NA
        prev_signal = df["Signal"].iloc[-2].item() if "Signal" in df.columns else pd.NA

        if not pd.isna(prev_macd) and not pd.isna(prev_signal):
            # MACD 金叉：MACD 線上穿 Signal 線
            if macd > signal and prev_macd <= prev_signal:
                trend_message = "MACD金叉，上漲趨勢可能形成 🔼"
            # MACD 死叉：MACD 線下穿 Signal 線
            elif macd < signal and prev_macd >= prev_signal:
                trend_message = "MACD死叉，下跌趨勢可能形成 🔽"
            # MACD 線在 Signal 線上方，表示看漲
            elif macd > signal:
                trend_message = "MACD看漲，上漲趨勢中 ⬆️"
            # MACD 線在 Signal 線下方，表示看跌
            elif macd < signal:
                trend_message = "MACD看跌，下跌趨勢中 ⬇️"

    # 簡單的移動平均線判斷 (作為補充或備用)
    # 僅在布林帶和MACD沒有給出更明確的趨勢時才使用
    if not pd.isna(ma20) and not pd.isna(ema20):
        if close_price > ma20 and close_price > ema20:
            # 如果當前趨勢判斷不是更具體的上漲，則更新為上漲趨勢
            if "上漲" not in trend_message and "下跌" not in trend_message: # Avoid overwriting more specific trends
                trend_message = "上漲趨勢 ⬆️"
        elif close_price < ma20 and close_price < ema20:
            # 如果當前趨勢判斷不是更具體的下跌，則更新為下跌趨勢
            if "上漲" not in trend_message and "下跌" not in trend_message: # Avoid overwriting more specific trends
                trend_message = "下跌趨勢 ⬇️"

    return trend_message

# --- 主應用程式邏輯 ---
st.title("📊 股票趨勢監測系統")

# 當點擊「獲取數據」按鈕時執行
if fetch_button:
    # 1. 下載數據
    # 傳遞 period 參數給 get_stock_data
    stock_data = get_stock_data(symbol, period, interval)

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
            # 確保只繪製 DataFrame 中存在的列，並且該列包含至少一個非 NaN 值
            plot_cols_price = ["Close", "MA20", "EMA20", "Upper", "Lower"]
            available_price_cols = [col for col in plot_cols_price if col in data_with_indicators.columns and data_with_indicators[col].notna().any()]
            if available_price_cols:
                st.line_chart(data_with_indicators[available_price_cols])
            else:
                st.info("沒有足夠的價格或移動平均線數據可供繪製。")


            # 繪製 MACD 指標圖
            st.subheader("MACD 指標")
            plot_cols_macd = ["MACD", "Signal"]
            available_macd_cols = [col for col in plot_cols_macd if col in data_with_indicators.columns and data_with_indicators[col].notna().any()]
            if available_macd_cols:
                st.line_chart(data_with_indicators[available_macd_cols])
            else:
                st.info("沒有足夠的MACD數據可供繪製。")


            # 顯示最新數據概覽
            st.subheader("最新數據概覽")
            st.dataframe(data_with_indicators.tail(10))
        else:
            st.info("無法計算指標，請檢查數據是否足夠。")
    else:
        st.info("無法獲取股票數據。請檢查股票代碼或網路連接。")
else:
    # 應用程式啟動時的提示訊息
    st.info("請在左側邊欄輸入股票代碼、選擇數據週期和數據間隔，然後點擊 '獲取數據'。")
