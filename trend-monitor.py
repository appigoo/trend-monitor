import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 配置與相容性檢查 ---
VALID_INTERVALS = {
    "1m": ["1d", "5d"],
    "2m": ["1d", "5d", "1mo"],
    "5m": ["1d", "5d", "1mo"],
    "15m": ["1d", "5d", "1mo"],
    "30m": ["1d", "5d", "1mo", "3mo"],
    "60m": ["1d", "5d", "1mo", "3mo", "6mo"],
    "90m": ["1d", "5d", "1mo", "3mo", "6mo"],
    "1h": ["1d", "5d", "1mo", "3mo", "6mo"],
    "1d": ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    "5d": ["3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    "1wk": ["1y", "2y", "5y", "10y", "ytd", "max"],
    "1mo": ["5y", "10y", "ytd", "max"],
    "3mo": ["10y", "max"]
}

# --- 用戶輸入界面 ---
st.sidebar.header("股票設定")

# 股票代碼輸入並驗證
symbol = st.sidebar.text_input("輸入股票代碼 (例如: AAPL)", "AAPL").upper().strip()
if not symbol or not symbol.isalnum():
    st.sidebar.error("請輸入有效的股票代碼（僅限字母和數字）。")
    symbol = "AAPL"  # 恢復預設值

# 數據週期選擇
period = st.sidebar.selectbox(
    "數據週期",
    ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
    index=2  # 預設 '1mo'
)

# 動態更新 interval 選項
available_intervals = [interval for interval, periods in VALID_INTERVALS.items() if period in periods]
interval = st.sidebar.selectbox(
    "數據間隔",
    available_intervals,
    index=available_intervals.index("15m") if "15m" in available_intervals else 0
)

# 觸發數據獲取
fetch_button = st.sidebar.button("獲取數據")

# --- 函數：數據下載與快取 ---
def get_stock_data(ticker_symbol, period_val, interval_val):
    """
    從 Yahoo Finance 下載股票數據。
    根據 interval_val 動態設置 TTL。
    """
    ttl = 300 if interval_val in ["1m", "2m", "5m", "15m"] else 3600
    logger.info(f"Fetching data for {ticker_symbol}, period={period_val}, interval={interval_val}, ttl={ttl}")
    
    @st.cache_data(ttl=ttl)
    def _fetch_data(ticker_symbol, period_val, interval_val):
        try:
            with st.spinner(f"正在下載 {ticker_symbol} 的數據..."):
                data = yf.download(ticker_symbol, period=period_val, interval=interval_val, progress=False, auto_adjust=False)
            if data.empty or 'Close' not in data.columns:
                logger.warning(f"No data found for {ticker_symbol}, period={period_val}, interval={interval_val}")
                st.warning(f"沒有找到 {ticker_symbol} 在週期 {period_val} 內，間隔為 {interval_val} 的數據。請檢查股票代碼或數據週期。")
                return None
            logger.info(f"Successfully fetched data for {ticker_symbol}, shape={data.shape}")
            return data
        except ValueError as ve:
            logger.error(f"Invalid parameter combination: {ve}")
            st.error(f"無效的參數組合：{ve}。請檢查數據週期和間隔是否相容。")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            st.error(f"下載數據失敗：{e}。可能是網絡問題或無效的股票代碼。")
            return None
    
    return _fetch_data(ticker_symbol, period_val, interval_val)

# --- 函數：指標計算 ---
@st.cache_data(ttl=3600)
def calculate_indicators(df):
    """
    為給定的 DataFrame 計算技術指標。
    返回包含所有指標的 DataFrame。
    """
    if df is None or df.empty or 'Close' not in df.columns:
        logger.warning("Invalid input data for calculate_indicators")
        st.warning("輸入數據為空或缺少 'Close' 列，無法計算指標。")
        return None

    df_copy = df.copy()
    warnings = []

    # 初始化指標列
    indicators = ["MA20", "EMA20", "MACD", "Signal", "Upper", "Lower"]
    for ind in indicators:
        df_copy[ind] = pd.NA

    # 檢查數據點數量
    def check_data_length(min_length, indicator_name):
        if len(df_copy) < min_length:
            warnings.append(f"數據點不足以計算 {indicator_name} (需要至少 {min_length} 個點)。")
            return False
        return True

    # 移動平均線
    if check_data_length(20, "MA20 和 EMA20"):
        df_copy["MA20"] = df_copy["Close"].rolling(window=20).mean()
        df_copy["EMA20"] = df_copy["Close"].ewm(span=20, adjust=False).mean()

    # MACD
    if check_data_length(26, "MACD"):
        ema12 = df_copy["Close"].ewm(span=12, adjust=False).mean()
        ema26 = df_copy["Close"].ewm(span=26, adjust=False).mean()
        df_copy["MACD"] = ema12 - ema26
        df_copy["Signal"] = df_copy["MACD"].ewm(span=9, adjust=False).mean()

    # 布林帶
    if check_data_length(20, "布林帶") and df_copy["MA20"].notna().any():
        df_copy["Upper"] = df_copy["MA20"] + 2 * df_copy["Close"].rolling(window=20).std()
        df_copy["Lower"] = df_copy["MA20"] - 2 * df_copy["Close"].rolling(window=20).std()
    elif not df_copy["MA20"].notna().any():
        warnings.append("MA20數據不足，無法計算布林帶。")

    # 顯示所有警告
    if warnings:
        st.warning("\n".join(warnings))
        logger.warning(f"Indicator calculation warnings: {warnings}")

    logger.info(f"Indicators calculated, shape={df_copy.shape}")
    return df_copy

# --- 函數：趨勢分析 ---
def analyze oggetti_trend(df):
    """
    根據技術指標分析股票趨勢。
    返回趨勢描述和詳細解釋。
    """
    if df is None or df.empty or "Close" not in df.columns:
        logger.warning("Invalid input data for analyze_trend")
        return "無數據", "無法分析趨勢：數據缺失或無效。"

    # 提取最新數據
    latest = df.iloc[-1]
    trend_message = "震盪 ↔️"
    explanation = []

    # 提取指標值
    def get_indicator(indicator):
        try:
            return latest[indicator].item() if indicator in latest and not pd.isna(latest[indicator]) else None
        except (ValueError, KeyError):
            return None

    close_price = get_indicator("Close")
    ma20 = get_indicator("MA20")
    ema20 = get_indicator("EMA20")
    macd = get_indicator("MACD")
    signal = get_indicator("Signal")
    upper_band = get_indicator("Upper")
    lower_band = get_indicator("Lower")

    if close_price is None:
        logger.warning("Close price is missing")
        return "無數據", "最新收盤價數據缺失或無效，無法判斷趨勢。"

    # 布林帶判斷
    if upper_band is not None and lower_band is not None:
        if close_price > upper_band:
            trend_message = "可能突破上漲 📈"
            explanation.append("收盤價突破布林帶上軌，顯示強勢上漲信號。")
        elif close_price < lower_band:
            trend_message = "可能突破下跌 📉"
            explanation.append("收盤價跌破布林帶下軌，顯示強勢下跌信號。")

    # MACD 判斷
    if macd is not None and signal is not None and len(df) >= 2:
        prev_row = df.iloc[-2]
        prev_macd = get_indicator("MACD") if "MACD" in prev_row else None
        prev_signal = get_indicator("Signal") if "Signal" in prev_row else None
        if prev_macd is not None and prev_signal is not None:
            prev_macd = prev_row["MACD"].item() if "MACD" in prev_row else None
            prev_signal = prev_row["Signal"].item() if "Signal" in prev_row else None
            if prev_macd is not None and prev_signal is not None:
                if macd > signal and prev_macd <= prev_signal:
                    trend_message = "MACD金叉，上漲趨勢可能形成 🔼"
                    explanation.append("MACD線上穿信號線，形成金叉，預示上漲趨勢。")
                elif macd < signal and prev_macd >= prev_signal:
                    trend_message = "MACD死叉，下跌趨勢可能形成 🔽"
                    explanation.append("MACD線下穿信號線，形成死叉，預示下跌趨勢。")
                elif macd > signal:
                    trend_message = "MACD看漲，上漲趨勢中 ⬆️"
                    explanation.append("MACD線位於信號線上方，顯示看漲趨勢。")
                elif macd < signal:
                    trend_message = "MACD看跌，下跌趨勢中 ⬇️"
                    explanation.append("MACD線位於信號線下方，顯示看跌趨勢。")

    # 移動平均線判斷（作為備用）
    if ma20 is not None and ema20 is not None and "上漲" not in trend_message and "下跌" not in trend_message:
        if close_price > ma20 and close_price > ema20:
            trend_message = "上漲趨勢 ⬆️"
            explanation.append("收盤價高於20日均線和指數移動平均線，顯示上漲趨勢。")
        elif close_price < ma20 and close_price < ema20:
            trend_message = "下跌趨勢 ⬇️"
            explanation.append("收盤價低於20日均線和指數移動平均線，顯示下跌趨勢。")

    # 歷史趨勢分析
    if len(df) >= 5:
        recent_closes = df["Close"].tail(5)
        if recent_closes.is_monotonic_increasing:
            explanation.append("過去5個交易日收盤價持續上漲，顯示短期強勢。")
        elif recent_closes.is_monotonic_decreasing:
            explanation.append("過去5個交易日收盤價持續下跌，顯示短期弱勢。")

    logger.info(f"Trend analysis completed: {trend_message}")
    return trend_message, "\n".join(explanation) if explanation else "無明確趨勢信號。"

# --- 主應用程式邏輯 ---
st.title("📊 股票趨勢監測系統")

if fetch_button:
    stock_data = get_stock_data(symbol, period, interval)
    if stock_data is not None and isinstance(stock_data, pd.DataFrame) and not stock_data.empty:
        data_with_indicators = calculate_indicators(stock_data)
        if data_with_indicators is not None and isinstance(data_with_indicators, pd.DataFrame) and not data_with_indicators.empty:
            logger.info(f"Data with indicators shape: {data_with_indicators.shape}, columns: {list(data_with_indicators.columns)}")
            
            # 趨勢分析
            trend_message, trend_explanation = analyze_trend(data_with_indicators)
            st.write(f"當前股票：**{symbol}**")
            st.markdown(f"**趨勢判斷：{trend_message}**")
            st.markdown(f"**趨勢解釋：**\n{trend_explanation}")

            # 價格與移動平均線圖
            st.subheader("價格與移動平均線")
            fig_price = go.Figure()
            plot_cols_price = ["Close", "MA20", "EMA20", "Upper", "Lower"]
            colors = ["blue", "orange", "green", "red", "red"]
            plot_added = False
            if isinstance(data_with_indicators, pd.DataFrame):
                for col, color in zip(plot_cols_price, colors):
                    if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                        fig_price.add_trace(go.Scatter(
                            x=data_with_indicators.index,
                            y=data_with_indicators[col],
                            name=col,
                            line=dict(color=color, dash="dash" if col in ["Upper", "Lower"] else "solid")
                        ))
                        plot_added = True
            if plot_added:
                fig_price.update_layout(
                    title=f"{symbol} 價格與移動平均線",
                    xaxis_title="日期",
                    yaxis_title="價格",
                    showlegend=True,
                    hovermode="x unified"
                )
                st.plotly_chart(fig_price, use_container_width=True)
            else:
                logger.warning("No valid data for price plot")
                st.info("沒有足夠的價格或移動平均線數據可供繪製。")

            # MACD 圖
            st.subheader("MACD 指標")
            fig_macd = go.Figure()
            plot_cols_macd = ["MACD", "Signal"]
            plot_added = False
            if isinstance(data_with_indicators, pd.DataFrame):
                for col, color in zip(plot_cols_macd, ["blue", "orange"]):
                    if col in data_with_indicators.columns and data_with_indicators[col].notna().any():
                        fig_macd.add_trace(go.Scatter(
                            x=data_with_indicators.index,
                            y=data_with_indicators[col],
                            name=col,
                            line=dict(color=color)
                        ))
                        plot_added = True
            if plot_added:
                fig_macd.update_layout(
                    title=f"{symbol} MACD 指標",
                    xaxis_title="日期",
                    yaxis_title="MACD",
                    showlegend=True,
                    hovermode="x unified"
                )
                st.plotly_chart(fig_macd, use_container_width=True)
            else:
                logger.warning("No valid data for MACD plot")
                st.info("沒有足夠的MACD數據可供繪製。")

            # 數據概覽
            st.subheader("最新數據概覽")
            num_rows = st.slider("顯示的數據行數", 5, 50, 10)
            st.dataframe(data_with_indicators.tail(num_rows))

            # 數據導出
            csv = data_with_indicators.to_csv(index=True)
            st.download_button(
                label="下載數據為 CSV",
                data=csv,
                file_name=f"{symbol}_data.csv",
                mime="text/csv"
            )
        else:
            logger.warning("Invalid or empty data_with_indicators")
            st.info("無法計算指標，請檢查數據是否足夠或數據格式是否正確。")
    else:
        logger.warning("Invalid or empty stock_data")
        st.info("無法獲取股票數據。請檢查股票代碼或網路連接。")
else:
    st.info("請在左側邊欄輸入股票代碼、選擇數據週期和數據間隔，然後點擊 '獲取數據'。")
