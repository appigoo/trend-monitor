import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from streamlit_autorefresh import st_autorefresh

# 页面自动刷新每 300 秒（5 分钟）
st_autorefresh(interval=300000, key="auto_refresh")

st.title("📊 实时股票趋势分析")
symbol = st.sidebar.text_input("输入股票代码（如：AAPL）", value="AAPL")

@st.cache_data(ttl=300)
def get_data(symbol):
    df = yf.download(tickers=symbol, interval='5m', period='1d')
    df.dropna(inplace=True)
    df['MA20'] = ta.trend.sma_indicator(df['Close'], window=20)
    macd = ta.trend.macd(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    return df

df = get_data(symbol)
latest = df.iloc[-1]

# 趋势判断逻辑
advice = '🔍 观望中'
if latest['MACD'] > latest['MACD_signal'] and latest['RSI'] < 70 and latest['Close'] > latest['MA20']:
    advice = '🟢 买入机会可能出现'
elif latest['MACD'] < latest['MACD_signal'] and latest['RSI'] > 30 and latest['Close'] < latest['MA20']:
    advice = '🔴 卖出信号可能产生'

st.subheader(f"最新分析：{symbol}")
st.metric("收盘价", f"{latest['Close']:.2f}")
st.metric("RSI", f"{latest['RSI']:.2f}")
st.metric("MACD差值", f"{latest['MACD'] - latest['MACD_signal']:.2f}")
st.success(advice)

# 可视化收盘价与 MA20
st.line_chart(df[['Close', 'MA20']].tail(50))
