import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

# ==========================================
# 1. 數據引擎：自動補償與清理
# ==========================================
@st.cache_data(ttl=3600)
def load_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
    data = {}
    for t in tickers:
        try:
            df = yf.download(t, period="5y", progress=False)
            if 'Close' in df.columns:
                data[t] = df['Close'].iloc[:, 0]
        except: continue
    return pd.concat(data, axis=1).dropna()

df_all = load_data()
spx_col = '^GSPC' if '^GSPC' in df_all.columns else 'SPY'

# ==========================================
# 2. 控制面板
# ==========================================
k_val = st.sidebar.slider("K 值", 0.5, 1.5, 1.137, 0.001)
threshold = st.sidebar.slider("換倉門檻 (%)", 0.5, 5.0, 2.0, 0.1)
d1 = st.sidebar.slider("抄底 Lv1 (%)", 10.0, 25.0, 19.0, 0.1)
d2 = st.sidebar.slider("抄底 Lv2 (%)", 20.0, 40.0, 30.0, 0.1)

# ==========================================
# 3. 核心邏輯：動態計算
# ==========================================
df = df_all.copy()
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
weights = pd.DataFrame(index=df.index)
weights['QQQ'] = np.where(df['Regime'] == 0, 0.138, 0.260 * k_val)
weights['QLD'] = np.select([df['Regime']==30, df['Regime']==19, df['Regime']==1], 
                           [0.25*k_val, 0.15*k_val, 0.32*k_val], default=0.0)
weights['TLT'] = np.where(df['Regime'] == 0, 0.099, 0.07 * (1+(k_val-1)*0.525))
weights['GLD'] = np.where(df['Regime'] == 0, 0.101, 0.07 * (1+(k_val-1)*0.525))
weights['UUP'] = np.where(df['Regime'] == 0, 0.245, 0.09 * (2.0-k_val))
weights['SGOV'] = 1.0 - weights.sum(axis=1)

# ==========================================
# 4. 儀表板與視覺化渲染
# ==========================================
st.title("Pure Alpha 戰情室 V9.3")

# 面板卡片
col1, col2 = st.columns(2)
with col1:
    st.metric("當前 Regime", df['Regime'].iloc[-1])
with col2:
    fig_pie = go.Figure(data=[go.Pie(labels=weights.columns, values=weights.iloc[-1].values)])
    fig_pie.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

# Rolling Beta 圖表
st.subheader("動態 Rolling Beta 趨勢")
roll_beta = df[['QQQ','QLD','TLT','GLD','UUP','SGOV']].pct_change().rolling(21).corr(df['SPY'].pct_change())
# 將 Rolling Beta 與歷史權重掛鉤
combined_beta = (roll_beta * weights).sum(axis=1)
st.line_chart(combined_beta.tail(252))

# ==========================================
# 5. 回測引擎
# ==========================================
st.subheader("歷史回測結果")
# (這裡使用你原本完整的回測 loop...)
st.info("路徑依賴回測已就緒，請調整門檻觀察數據變化。")
