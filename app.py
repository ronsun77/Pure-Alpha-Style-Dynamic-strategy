import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 0. 網頁基礎設定
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V8.9", layout="wide")

# ==========================================
# 1. 資料讀取 (防呆版)
# ==========================================
@st.cache_data(ttl=3600)
def load_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
    data_dict = {}
    for t in tickers:
        try:
            df = yf.download(t, period="10y", progress=False)
            if 'Close' in df.columns:
                series = df['Close'].dropna()
                data_dict[t] = series.iloc[:, 0] if isinstance(series, pd.DataFrame) else series
        except Exception: pass
    return pd.concat(data_dict, axis=1).dropna()

df_raw = load_data()
spx_col = '^GSPC' if '^GSPC' in df_raw.columns else 'SPY'

# ==========================================
# 2. 控制面板
# ==========================================
st.sidebar.markdown("## 動態參數調控")
k_value = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("最小換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
dip_lv1 = st.sidebar.slider("Lv1 抄底門檻 (%)", 10.0, 25.0, 19.0, 0.1)
dip_lv2 = st.sidebar.slider("Lv2 恐慌門檻 (%)", 20.0, 40.0, 30.0, 0.1)

# ==========================================
# 3. 核心運算：動態狀態機 (綁定滑桿參數)
# ==========================================
def run_strategy(df, k, d1, d2):
    df = df.copy()
    df['MA200'] = df['QQQ'].rolling(200).mean()
    df['SPX_Max'] = df[spx_col].cummax()
    df['SPX_DD'] = df[spx_col] / df['SPX_Max'] - 1
    
    states = []
    curr = 1 # 1=牛市, 0=熊市, 19=抄底1, 30=抄底2
    
    for i in range(len(df)):
        q, ma, dd = df['QQQ'].iloc[i], df['MA200'].iloc[i], df['SPX_DD'].iloc[i]
        if pd.isna(ma): states.append(1); continue
        
        if q >= ma * 1.04: curr = 1
        elif dd <= - (d2/100.0): curr = 30
        elif dd <= - (d1/100.0) and curr != 30: curr = 19
        elif curr == 1 and q < ma * 0.97 and dd > -(d1/100.0): curr = 0
        states.append(curr)
    
    df['Regime'] = states
    # 計算目標權重矩陣
    mult_q = k
    mult_t = 1.0 + (k - 1) * 0.525
    mult_u = 2.0 - k
    
    w_q = np.where(df['Regime'] == 0, 13.8, 26.0 * mult_q)
    w_qld = np.where(df['Regime'] == 30, 25.0 * mult_q, np.where(df['Regime'] == 19, 15.0 * mult_q, np.where(df['Regime'] == 1, 32.0 * mult_q, 0.0)))
    w_t = np.where(df['Regime'] == 0, 9.9, 7.0 * mult_t)
    w_g = np.where(df['Regime'] == 0, 10.1, 7.0 * mult_t)
    w_u = np.where(df['Regime'] == 0, 24.5, 9.0 * mult_u)
    w_s = np.maximum(0, 100.0 - (w_q + w_qld + w_t + w_g + w_u))
    
    df_weights = pd.DataFrame({"QQQ": w_q, "QLD": w_qld, "TLT": w_t, "GLD": w_g, "UUP": w_u, "SGOV": w_s}, index=df.index) / 100.0
    return df, df_weights

df_all, tgt_weights = run_strategy(df_raw, k_value, dip_lv1, dip_lv2)

# ==========================================
# 4. 回測引擎 (路徑依賴)
# ==========================================
st.markdown("# Pure Alpha 戰情室 V8.9")
price_cols = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]
bt_ret = df_all[price_cols].pct_change().dropna()
tgt_sub = tgt_weights.loc[bt_ret.index]

n = len(bt_ret)
nav = np.zeros(n)
w_curr = tgt_sub.iloc[0].values
rebal = 0

for i in range(n):
    nav[i] = (1.0 * (1 + np.dot(w_curr, bt_ret.iloc[i]))) if i == 0 else (nav[i-1] * (1 + np.dot(w_curr, bt_ret.iloc[i])))
    w_drift = w_curr * (1 + bt_ret.iloc[i].values) / (1 + np.dot(w_curr, bt_ret.iloc[i]))
    if i < n - 1:
        if np.max(np.abs(w_drift - tgt_sub.iloc[i+1].values)) >= (threshold/100.0):
            w_curr = tgt_sub.iloc[i+1].values; rebal += 1
        else: w_curr = w_drift

# ==========================================
# 5. UI 視覺化 (略)
# ==========================================
# (此處保持與前一版相同的繪圖邏輯，即可完整運作)
st.write(f"今日觸發換倉門檻狀態：門檻 {threshold}% | 歷史累計換倉次數: {rebal}")
# ... 其餘圖表與回測報告邏輯直接複製 V8.7 的部分即可 ...
