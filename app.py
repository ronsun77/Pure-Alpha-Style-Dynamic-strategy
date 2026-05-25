import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 0. 基礎設定
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V9.2", layout="wide")

# ==========================================
# 1. 強力數據讀取 (含備份機制)
# ==========================================
@st.cache_data(ttl=3600)
def get_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
    data_dict = {}
    for t in tickers:
        try:
            # 獲取五年數據，保證回測足夠長且不會崩潰
            df = yf.download(t, period="5y", progress=False)
            if 'Close' in df.columns:
                data_dict[t] = df['Close'].iloc[:, 0]
        except: continue
    return pd.concat(data_dict, axis=1).dropna()

df_all = get_data()
if df_all.empty:
    st.error("數據下載失敗，請檢查網路連線。")
    st.stop()

# ==========================================
# 2. 控制面板 (定義參數)
# ==========================================
st.sidebar.markdown("## 策略參數控制")
k_val = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
d1 = st.sidebar.slider("抄底 Lv1 (%)", 10.0, 25.0, 19.0, 0.1)
d2 = st.sidebar.slider("抄底 Lv2 (%)", 20.0, 40.0, 30.0, 0.1)

# ==========================================
# 3. 狀態機核心邏輯 (與 Excel 對齊)
# ==========================================
df = df_all.copy()
df['MA200'] = df['QQQ'].rolling(200).mean()
spx = '^GSPC' if '^GSPC' in df.columns else 'SPY'
df['SPX_DD'] = df[spx] / df[spx].cummax() - 1

regime = []
curr = 1 
for i in range(len(df)):
    q, ma, dd = df['QQQ'].iloc[i], df['MA200'].iloc[i], df['SPX_DD'].iloc[i]
    if pd.isna(ma): regime.append(1); continue
    
    # 狀態機邏輯：牛(1), 熊(0), Lv1(19), Lv2(30)
    if q >= ma * 1.04: curr = 1
    elif dd <= -d2/100: curr = 30
    elif dd <= -d1/100 and curr != 30: curr = 19
    elif curr == 1 and q < ma * 0.97 and dd > -d1/100: curr = 0
    regime.append(curr)
df['Regime'] = regime

# 權重矩陣計算
weights = pd.DataFrame(index=df.index)
weights['QQQ'] = np.where(df['Regime'] == 0, 0.138, 0.260 * k_val)
weights['QLD'] = np.select([df['Regime']==30, df['Regime']==19, df['Regime']==1], 
                           [0.25*k_val, 0.15*k_val, 0.32*k_val], default=0.0)
weights['TLT'] = np.where(df['Regime'] == 0, 0.099, 0.07 * (1+(k_val-1)*0.525))
weights['GLD'] = np.where(df['Regime'] == 0, 0.101, 0.07 * (1+(k_val-1)*0.525))
weights['UUP'] = np.where(df['Regime'] == 0, 0.245, 0.09 * (2.0-k_val))
weights['SGOV'] = 1.0 - weights.sum(axis=1)

# ==========================================
# 4. 路徑依賴回測引擎
# ==========================================
returns = df[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].pct_change().dropna()
nav = [1.0]
curr_w = weights.iloc[0].values
rebal_count = 0

for i in range(len(returns)):
    daily_ret = np.dot(curr_w, returns.iloc[i].values)
    nav.append(nav[-1] * (1 + daily_ret))
    
    # 漂移修正 (Drift Calculation)
    drift = curr_w * (1 + returns.iloc[i].values) / (1 + daily_ret)
    if i < len(returns) - 1:
        if np.max(np.abs(drift - weights.iloc[i+1].values)) >= threshold/100:
            curr_w = weights.iloc[i+1].values
            rebal_count += 1
        else:
            curr_w = drift

# ==========================================
# 5. UI 渲染 (Dashboard)
# ==========================================
st.title("Pure Alpha 戰情室 V9.2")

col1, col2 = st.columns([1, 2])
with col1:
    st.metric("當前 regime 狀態", df['Regime'].iloc[-1])
    st.metric("歷史累計換倉次數", rebal_count)
with col2:
    st.subheader("策略淨值走勢")
    st.line_chart(pd.Series(nav, index=df.index[:len(nav)]))

st.subheader("目標權重透視")
st.dataframe(weights.tail(10))
