import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 1. 資料引擎
# ==========================================
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
spx_col = '^GSPC' if '^GSPC' in df_raw.columns else 'SPY'

# ==========================================
# 2. 側邊欄控制
# ==========================================
st.sidebar.markdown("## Pure Alpha 控制台")
k_val = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
d1 = st.sidebar.slider("抄底 Lv1 (%)", 10.0, 25.0, 19.0, 0.1)
d2 = st.sidebar.slider("抄底 Lv2 (%)", 20.0, 40.0, 30.0, 0.1)

# ==========================================
# 3. 核心邏輯引擎
# ==========================================
df = df_raw.copy()
df['MA200'] = df['QQQ'].rolling(200).mean()
df['SPX_DD'] = df[spx_col] / df[spx_col].cummax() - 1

# 狀態機
states = []
curr = 1
for i in range(len(df)):
    q, ma, dd = df['QQQ'].iloc[i], df['MA200'].iloc[i], df['SPX_DD'].iloc[i]
    if pd.isna(ma): states.append(1); continue
    if q >= ma * 1.04: curr = 1
    elif dd <= -d2/100: curr = 30
    elif dd <= -d1/100 and curr != 30: curr = 19
    elif curr == 1 and q < ma * 0.97 and dd > -d1/100: curr = 0
    states.append(curr)
df['Regime'] = states

# 權重矩陣
w = pd.DataFrame(index=df.index)
w['QQQ'] = np.where(df['Regime'] == 0, 0.138, 0.260 * k_val)
w['QLD'] = np.select([df['Regime']==30, df['Regime']==19, df['Regime']==1], [0.25*k_val, 0.15*k_val, 0.32*k_val], default=0.0)
w['TLT'] = np.where(df['Regime'] == 0, 0.099, 0.07 * (1+(k_val-1)*0.525))
w['GLD'] = np.where(df['Regime'] == 0, 0.101, 0.07 * (1+(k_val-1)*0.525))
w['UUP'] = np.where(df['Regime'] == 0, 0.245, 0.09 * (2.0-k_val))
w['SGOV'] = 1.0 - w.sum(axis=1)

# ==========================================
# 4. 回測引擎
# ==========================================
ret = df[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].pct_change().dropna()
nav, curr_w, rebal = [1.0], w.iloc[0].values, 0
for i in range(len(ret)):
    daily_ret = np.dot(curr_w, ret.iloc[i].values)
    nav.append(nav[-1] * (1 + daily_ret))
    drift = curr_w * (1 + ret.iloc[i].values) / (1 + daily_ret)
    if i < len(ret) - 1 and np.max(np.abs(drift - w.iloc[i+1].values)) >= threshold/100:
        curr_w = w.iloc[i+1].values; rebal += 1
    else: curr_w = drift

# ==========================================
# 5. V8.8 完整儀表板渲染
# ==========================================
st.title("Pure Alpha 戰情室 V8.8 重構版")

# KPI 面板
c1, c2, c3 = st.columns(3)
c1.metric("當前 Regime", df['Regime'].iloc[-1])
c2.metric("累計換倉", rebal)
c3.metric("最終淨值", f"{nav[-1]:.2f}")

# 圖表區
col_l, col_r = st.columns(2)
with col_l:
    st.subheader("策略淨值")
    st.line_chart(pd.Series(nav, index=df.index[:len(nav)]))
with col_r:
    st.subheader("資產配比")
    fig = go.Figure(data=[go.Pie(labels=w.columns, values=w.iloc[-1].values)])
    st.plotly_chart(fig, use_container_width=True)

# Rolling Beta
st.subheader("Rolling Beta 趨勢")
beta_series = ret.rolling(21).corr(ret[spx_col]).mean(axis=1)
st.line_chart(beta_series.tail(252))

# 透視鏡
st.subheader("除錯透視鏡 (最近 5 日)")
st.dataframe(pd.concat([df['Regime'], w], axis=1).tail(5))
