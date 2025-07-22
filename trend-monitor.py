import streamlit as st
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# ⏱ 页面每 5 分钟刷新
st_autorefresh(interval=300000, key="datarefresh")

st.title("📈 股票趋势实时监控工具")

# 📝 输入股票代码，默认 AAPL
symbol = st.sidebar.text_input("请输入股票代码（例如 AAPL 或 0700.HK）", value="AAPL")

@st.cache_data(ttl=300)
def get_data(symbol):
    df = yf.download(tickers=symbol, interval='5m', period='1d')
    df.dropna(inplace=True)

    # 技术指标计算
    df['MA20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

    return df

df = get_data(symbol)
latest = df.iloc[-1]

# 🔍 趋势建议逻辑
advice = "🔍 当前趋势模糊，建议观望"
if latest['MACD'] > latest['MACD_signal'] and latest['Close'] > latest['MA20'] and latest['RSI'] < 70:
    advice = "🟢 MACD、均线与 RSI 皆看涨，可考虑买入"
elif latest['MACD'] < latest['MACD_signal'] and latest['Close'] < latest['MA20'] and latest['RSI'] > 30:
    advice = "🔴 指标偏弱，可能为卖出信号"

# 📊 显示指标和建议
st.subheader(f"📍 {symbol} 最新技术分析")
st.metric(label="收盘价", value=f"{latest['Close']:.2f}")
st.metric(label="MACD 差值", value=f"{(latest['MACD'] - latest['MACD_signal']):.2f}")
st.metric(label="RSI", value=f"{latest['RSI']:.2f}")
st.success(advice)

# 📈 收盘价与 MA20 趋势图（最近 50 条数据）
st.line_chart(df[['Close', 'MA20']].tail(50))
