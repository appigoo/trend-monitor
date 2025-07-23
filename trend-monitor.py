import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import time

REFRESH_INTERVAL = 300  # 每 5 分钟自动刷新

# 时间范围与间隔选项
period_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y"]
interval_options = ["1m", "5m", "15m", "1h", "1d"]

st.title("📊 股票监控儀表板（含异动排行分析）")

# 使用者输入股票代号
input_tickers = st.text_input("请输入股票代号（用英文逗号分隔，例如：AAPL, MSFT, TSLA）", value="AAPL, MSFT, TSLA, GOOGL, AMZN")
selected_tickers = [ticker.strip().upper() for ticker in input_tickers.split(",") if ticker.strip()]

selected_period = st.selectbox("选择时间范围 (period)", period_options, index=1)
selected_interval = st.selectbox("选择间隔时间 (interval)", interval_options, index=1)

placeholder = st.empty()

while True:
    all_data = []  # 用于异动分析的暂存资料

    with placeholder.container():
        st.subheader(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not selected_tickers:
            st.warning("⚠️ 请输入至少一个有效的股票代号。")
        else:
            for ticker in selected_tickers:
                stock = yf.Ticker(ticker)
                try:
                    data = stock.history(period=selected_period, interval=selected_interval)
                    current_price = data["Close"].iloc[-1]
                    previous_close = stock.info.get('previousClose', current_price)
                    change = current_price - previous_close
                    pct_change = (change / previous_close) * 100

                    last_volume = data["Volume"].iloc[-1]
                    prev_volume = data["Volume"].iloc[-2] if len(data) > 1 else last_volume
                    volume_change = last_volume - prev_volume
                    volume_pct_change = (volume_change / prev_volume) * 100 if prev_volume != 0 else 0

                    st.metric(label=f"{ticker} 股价", value=f"${current_price:.2f}",
                              delta=f"{change:.2f} ({pct_change:.2f}%)")
                    st.metric(label=f"{ticker} 成交量", value=f"{last_volume:,}",
                              delta=f"{volume_change:,} ({volume_pct_change:.2f}%)")
                    st.dataframe(data.tail(5))

                    # 收集异动分析数据
                    all_data.append({
                        "Ticker": ticker,
                        "Price %": pct_change,
                        "Volume %": volume_pct_change,
                        "背离": "✅" if (pct_change > 0 and volume_pct_change < 0) or (pct_change < 0 and volume_pct_change > 0) else ""
                    })

                except Exception as e:
                    st.warning(f"🚫 无法取得 {ticker} 的资料：{e}")

        # 成交量异动排行
        if all_data:
            df_analysis = pd.DataFrame(all_data)
            st.subheader("🔥 成交量异动排行（按幅度排序）")
            st.dataframe(df_analysis.sort_values(by="Volume %", ascending=False).reset_index(drop=True))

            # 背离分析
            st.subheader("🧭 价格/成交量背离分析")
            df_divergence = df_analysis[df_analysis["背离"] == "✅"]
            if not df_divergence.empty:
                st.dataframe(df_divergence.reset_index(drop=True))
            else:
                st.info("✅ 当前没有检测到明显的价格/成交量背离股票")

        st.markdown("---")
        st.info("页面将在 5 分钟后自动刷新...")

    time.sleep(REFRESH_INTERVAL)
    placeholder.empty()
