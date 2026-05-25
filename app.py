import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 0. 網頁基礎設定與 CSS
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V9.0", layout="wide")
st.markdown("""
<style>
    .stApp { background-color: #081028; }
    .cyber-card { background: #17233a; border-radius: 15px; padding: 20px; border: 1px solid #24334d; margin-bottom: 20px; color: #e2e8f0; }
    .cyber-card h2 { color: #38bdf8; font-size: 18px; border-left: 3px solid #38bdf8; padding-left: 10px; }
    .metric-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #24334d; }
    .m-value { font-family: monospace; font-weight: bold; }
    .regime-box { padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 數據引擎：防呆下載
# ==========================================
@st.cache_data(ttl=3600)
def load_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, period="10y", progress=False)
            if 'Close' in df.columns:
                data[t] = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        except: pass
    return pd.concat(data, axis=1).dropna()

df_raw = load_data()
spx_col = '^GSPC' if '^GSPC' in df_raw.columns else 'SPY'

# ==========================================
# 2. 控制面板
# ==========================================
k_value = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
d1 = st.sidebar.slider("抄底 Lv1 (%)", 10.0, 25.0, 19.0, 0.1)
d2 = st.sidebar.slider("抄底 Lv2 (%)", 20.0, 40.0, 30.0, 0.1)

# ==========================================
# 3. 核心邏輯：記憶狀態機與權重分配
# ==========================================
df = df_raw.copy()
df['MA200'] = df['QQQ'].rolling(200).mean()
df['SPX_DD'] = df[spx_col] / df[spx_col].cummax() - 1

regime = []
curr = 1 # 1:牛, 0:熊, 19:Lv1, 30:Lv2
for i in range(len(df)):
    q, ma, dd = df['QQQ'].iloc[i], df['MA200'].iloc[i], df['SPX_DD'].iloc[i]
    if pd.isna(ma): regime.append(1); continue
    if q >= ma * 1.04: curr = 1
    elif dd <= -d2/100: curr = 30
    elif dd <= -d1/100 and curr != 30: curr = 19
    elif curr == 1 and q < ma * 0.97 and dd > -d1/100: curr = 0
    regime.append(curr)
df['Regime'] = regime

# 目標權重矩陣
w_q = np.where(df['Regime'] == 0, 13.8, 26.0 * k_value)
w_qld = np.where(df['Regime'] == 30, 25.0 * k_value, np.where(df['Regime'] == 19, 15.0 * k_value, np.where(df['Regime'] == 1, 32.0 * k_value, 0.0)))
w_t = np.where(df['Regime'] == 0, 9.9, 7.0 * (1+(k_value-1)*0.525))
w_g = np.where(df['Regime'] == 0, 10.1, 7.0 * (1+(k_value-1)*0.525))
w_u = np.where(df['Regime'] == 0, 24.5, 9.0 * (2.0-k_value))
w_s = np.maximum(0, 100 - (w_q+w_qld+w_t+w_g+w_u))
weights = pd.DataFrame({"QQQ":w_q, "QLD":w_qld, "TLT":w_t, "GLD":w_g, "UUP":w_u, "SGOV":w_s}, index=df.index)/100

# ==========================================
# 4. 回測引擎 (路徑依賴)
# ==========================================
ret = df[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].pct_change().dropna()
nav = [1.0]
curr_w = weights.iloc[0].values
for i in range(len(ret)):
    ret_day = ret.iloc[i].values
    nav.append(nav[-1] * (1 + np.dot(curr_w, ret_day)))
    drift = curr_w * (1 + ret_day) / (1 + np.dot(curr_w, ret_day))
    if i < len(ret) - 1 and np.max(np.abs(drift - weights.iloc[i+1].values)) >= threshold/100:
        curr_w = weights.iloc[i+1].values
    else: curr_w = drift

# ==========================================
# 5. UI 渲染
# ==========================================
st.title("Pure Alpha 戰情室 V9.0")
# 這裡放入原本的 Dashboard 渲染邏輯即可
st.success("系統已完成路徑依賴重構與雙門檻邏輯同步")
st.line_chart(pd.Series(nav, index=df.index[:len(nav)]))
