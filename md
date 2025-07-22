# 股票趋势监测系统 📈

这是一个使用 Python 和 Streamlit 构建的实时股票趋势分析工具，支持 MA、MACD 和布林带等经典技术指标，并每 5 分钟更新趋势判断。

## 功能
- 支持多种股票数据源（通过 Yahoo Finance）
- 每 5 分钟自动更新数据
- 支持 MACD 金叉/死叉判断
- 布林带突破识别
- Streamlit 可视化界面

## 快速启动
```bash
pip install -r requirements.txt
streamlit run trend_monitor.py
