import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# 設定版面
st.set_page_config(page_title="Pure Alpha 戰情室 V9.5", layout="wide")

# 1. 資料引擎
@st.cache_data(ttl=3600)
def load_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, period="5y", progress=False)
            if 'Close' in df.columns: data[t] = df['Close'].iloc[:, 0]
        except: continue
    return pd.concat(data, axis=1).dropna()

df_raw = load_data()
spx = '^GSPC' if '^GSPC' in df_raw.columns else 'SPY'

# 2. 側邊控制列
st.sidebar.title("🛠 策略參數")
k_val = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
d1 = st.sidebar.slider("抄底 Lv1 (%)", 10.0, 25.0, 19.0, 0.1)
d2 = st.sidebar.slider("抄底 Lv2 (%)", 20.0, 40.0, 30.0, 0.1)

# 3. 核心邏輯
df = df_raw.copy()
df['MA200'] = df['QQQ'].rolling(200).mean()
df['SPX_DD'] = df[spx] / df[spx].cummax() - 1

regime = []
curr = 1 
for i in range(len(df)):
    q, ma, dd = df['QQQ'].iloc[i], df['MA200'].iloc[i], df['SPX_DD'].iloc[i]
    if pd.isna(ma): regime.append(1); continue
    if q >= ma * 1.04: curr = 1
    elif dd <= -d2/100: curr = 30
    elif dd <= -d1/100 and curr != 30: curr = 19
    elif curr == 1 and q < ma * 0.97 and dd > -d1/100: curr = 0
    regime.append(curr)
df['Regime'] = regime

weights = pd.DataFrame(index=df.index)
weights['QQQ'] = np.where(df['Regime'] == 0, 0.138, 0.260 * k_val)
weights['QLD'] = np.select([df['Regime']==30, df['Regime']==19, df['Regime']==1], 
                           [0.25*k_val, 0.15*k_val, 0.32*k_val], default=0.0)
weights['TLT'] = np.where(df['Regime'] == 0, 0.099, 0.07 * (1+(k_val-1)*0.525))
weights['GLD'] = np.where(df['Regime'] == 0, 0.101, 0.07 * (1+(k_val-1)*0.525))
weights['UUP'] = np.where(df['Regime'] == 0, 0.245, 0.09 * (2.0-k_val))
weights['SGOV'] = 1.0 - weights.sum(axis=1)

# 4. 回測引擎
returns = df[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].pct_change().dropna()
nav = [1.0]
curr_w = weights.loc[returns.index[0]].values
for i in range(len(returns)):
    daily_ret = np.dot(curr_w, returns.iloc[i].values)
    nav.append(nav[-1] * (1 + daily_ret))
    drift = curr_w * (1 + returns.iloc[i].values) / (1 + daily_ret)
    if i < len(returns) - 1:
        if np.max(np.abs(drift - weights.loc[returns.index[i+1]].values)) >= threshold/100:
            curr_w = weights.loc[returns.index[i+1]].values
        else: curr_w = drift

# 5. UI 視覺還原
st.title("📈 Pure Alpha 戰情室 V9.5")
c1, c2, c3 = st.columns(3)
c1.metric("當前 Regime", df['Regime'].iloc[-1])
c2.metric("最新 QQQ 目標", f"{weights['QQQ'].iloc[-1]*100:.1f}%")
c3.metric("最新 QLD 目標", f"{weights['QLD'].iloc[-1]*100:.1f}%")

st.subheader("策略淨值 vs 大盤基準")
st.line_chart(pd.DataFrame({"策略": pd.Series(nav, index=df.index[:len(nav)]), "SPY": df[spx]}))

st.subheader("當前資產配比")
fig = go.Figure(data=[go.Pie(labels=weights.columns, values=weights.iloc[-1].values, hole=.4)])
st.plotly_chart(fig, use_container_width=True)

st.subheader("權重配置明細")
st.dataframe(weights.tail(10), use_container_width=True)
