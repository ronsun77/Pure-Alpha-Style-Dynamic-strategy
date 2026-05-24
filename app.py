import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定 (V7.11 穩定版)
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室", layout="wide")

# (CSS 注入部分維持不變，確保介面風格一致)
st.markdown("""<style>...css設定...</style>""", unsafe_allow_html=True)

# ==========================================
# 1. 數據引擎：嚴格控制資料來源
# ==========================================
@st.cache_data(ttl=3600)
def load_data():
    # 確保抓取足夠長度以支撐 MA200
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
    data = {t: yf.download(t, period="10y", progress=False)['Close'] for t in tickers}
    return pd.DataFrame(data).dropna()

df_all = load_data()

# ==========================================
# 2. 核心權重決策區 (嚴格對齊 Excel 公式)
# ==========================================
# 請確保這裡的參數與你的 Excel 完全對應
def get_target_weights(is_bull, k):
    targets = {}
    if is_bull:
        # 牛市：套用 K 值縮放
        targets["QQQ"] = 26.0 * k
        targets["QLD"] = 32.0 * k
        targets["TLT"] = 7.0 * (1.0 + (k-1)*0.525)
        targets["GLD"] = 7.0 * (1.0 + (k-1)*0.525)
        targets["UUP"] = 9.0 * (2.0 - k)
    else:
        # 熊市：直接採用 Base，無縮放
        targets["QQQ"] = 13.8
        targets["QLD"] = 0.0
        targets["TLT"] = 9.9
        targets["GLD"] = 10.1
        targets["UUP"] = 24.5
    
    targets["SGOV"] = max(0.0, 100.0 - sum(targets.values()))
    return targets

# ==========================================
# 3. 執行介面渲染
# ==========================================
# (在此處放入你的表格顯示與圖表繪製邏輯)
# 確保 Rolling Beta 趨勢圖引用的是與回測一致的權重序列
