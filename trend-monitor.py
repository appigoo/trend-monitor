import streamlit as st                       # Streamlit 主模块
import yfinance as yf                        # 获取股票数据
import pandas as pd                          # 数据处理
import ta                                    # 技术指标计算
from streamlit_autorefresh import st_autorefresh  # 页面自动刷新

# 设置自动刷新：300000 毫秒 = 5 分钟
st_autorefresh(interval=300000, key="refresh")

st.title("📊 实时股票趋势监测器")

# 输入股票代码（如：AAPL、TSLA、0700.HK）
symbol = st.sidebar.text_input("请输入股票代码", value="AAPL")

# 获取数据函数，使用 Streamlit 缓存避免重复计算，有效期 5 分钟
@st.cache_data(ttl=300)
def get_data(symbol):
    df = yf.download(tickers=symbol, interval='5m', period='1d')
    df.dropna(inplace=True)

    # 确保使用 Series 格式（避免二维问题）
    close_series = df['Close']

    # 计算 MA20（20周期简单移动平均）
    df['MA20'] = ta.trend.sma_indicator(close_series, window=20)

    # 计算 MACD 与信号线
    macd = ta.trend.macd(close_series)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    # 计算 RSI（相对强弱指标）
    df['RSI'] = ta.momentum.rsi(close_series, window=14)

    return df

# 调用函数取得数据
df = get_data(symbol)

# 选取最新一条数据进行分析
latest = df.iloc[-1]

# 趋势判断逻辑
advice = '🔍 当前趋势模糊，建议观望'
if latest['MACD'] > latest['MACD_signal'] and latest['RSI'] < 70 and latest['Close'] > latest['MA20']:
    advice = '🟢 趋势向上，可能是买入机会'
elif latest['MACD'] < latest['MACD_signal'] and latest['RSI'] > 30 and latest['Close'] < latest['MA20']:
    advice = '🔴 趋势向下，可能是卖出信号'

# 显示关键指标和建议
st.subheader(f"📍 {symbol} 最新趋势分析")
st.metric("收盘价", f"{latest['Close']:.2f}")
st.metric("RSI", f"{latest['RSI']:.2f}")
st.metric("MACD 差值", f"{(latest['MACD'] - latest['MACD_signal']):.2f}")
st.success(advice)

# 走势图（最近 50 个周期）
st.line_chart(df[['Close', 'MA20']].tail(50))
