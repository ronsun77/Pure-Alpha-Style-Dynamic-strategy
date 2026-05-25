import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS 外掛注入
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V8.7", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #081028; font-family: 'Segoe UI', Arial, sans-serif; }
    .cyber-card { background: #17233a; border-radius: 20px; padding: 24px; box-shadow: 0 4px 25px rgba(0,0,0,0.35); border: 1px solid #24334d; margin-bottom: 20px; color: #e2e8f0; height: 100%; }
    .cyber-card h2 { color: #38bdf8; margin-bottom: 20px; font-size: 20px; border-left: 4px solid #38bdf8; padding-left: 10px; }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #24334d; }
    .metric-row:last-child { border-bottom: none; }
    .m-label { color: #cbd5e1; font-size: 14px; }
    .m-value { color: white; font-weight: bold; font-family: monospace; font-size: 16px; }
    .c-green { color: #22c55e; } .c-red { color: #ef4444; } .c-yellow { color: #facc15; }
    .cyber-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
    .cyber-table th, .cyber-table td { padding: 14px 10px; text-align: center; border-bottom: 1px solid #24334d; font-size: 16px; }
    .cyber-table th { background: #1e293b; color: #94a3b8; font-weight: 600; font-size: 15px; }
    .cyber-table td { color: #e2e8f0; }
    .badge-action { padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }
    .badge-buy { background: rgba(34,197,94,0.2); color: #22c55e; }
    .badge-sell { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-hold { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .badge-critical { background: #ef4444; color: white; }
    .regime-box { margin-top:20px; padding:15px; border-radius:12px; text-align:center; font-size:18px; font-weight:bold; }
    .bull-box { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; }
    .bear-box { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; }
    .dip-box { background: rgba(56,189,248,0.15); border: 1px solid #38bdf8; color: #38bdf8; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 核心參數與資料下載 (納入真實指數 ^GSPC)
# ==========================================
PRICE_COLS = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY", "^GSPC"]
CURRENT_WEIGHTS = {"QQQ": 28.71, "QLD": 35.66, "TLT": 7.80, "GLD": 7.65, "UUP": 8.00, "SGOV": 12.18}
BULL_BASE = {"QQQ": 26.0, "QLD": 32.0, "TLT": 7.0, "GLD": 7.0, "UUP": 9.0}
BEAR_BASE = {"QQQ": 13.8, "QLD": 0.0, "TLT": 9.9, "GLD": 10.1, "UUP": 24.5}
ASSET_ROLES = {"QQQ": "核心成長引擎", "QLD": "動能槓桿放大", "TLT": "長債負相關避險", "GLD": "抗通膨終極防禦", "UUP": "美元流動性避險", "SGOV": "流動性海綿池"}
CHART_COLORS = {"QQQ": "#38bdf8", "QLD": "#818cf8", "TLT": "#f472b6", "GLD": "#facc15", "UUP": "#ef4444", "SGOV": "#94a3b8"}

@st.cache_data(ttl=3600)
def load_data():
    data_dict = {}
    for t in PRICE_COLS:
        try:
            df = yf.download(t, period="10y", progress=False)
            if 'Close' in df.columns:
                series = df['Close'].dropna()
                if isinstance(series, pd.DataFrame): series = series.iloc[:, 0]
                data_dict[t] = series
        except Exception: pass
    if data_dict: return pd.concat(data_dict, axis=1).dropna()
    return pd.DataFrame()

df_all = load_data()
# 動態過濾：只保留真正下載成功的欄位，防呆機制
PRICE_COLS = [c for c in PRICE_COLS if c in df_all.columns]

# ==========================================
# 2. 雙門檻 + 階梯抄底記憶狀態機
# ==========================================
df_all['MA200'] = df_all['QQQ'].rolling(200).mean()

# 關鍵防呆：如果 ^GSPC 遭 Yahoo 阻擋，自動無縫降級使用 SPY
spx_col = '^GSPC' if '^GSPC' in df_all.columns else 'SPY'
df_all['SPX_Max'] = df_all[spx_col].cummax()
df_all['SPX_DD'] = df_all[spx_col] / df_all['SPX_Max'] - 1

regime_states = [] # 狀態映射：0=熊市防禦, 1=常態牛市, 19=19%抄底鎖定, 30=30%極度抄底鎖定
current_state = 1 

for i in range(len(df_all)):
    q = df_all['QQQ'].iloc[i]
    ma = df_all['MA200'].iloc[i]
    spx_dd = df_all['SPX_DD'].iloc[i]
    
    if pd.isna(ma):
        regime_states.append(1)
        continue
    
    # 規則 1：右側確認大反轉，強制回歸滿血牛市
    if q >= ma * 1.04:
        current_state = 1
    # 規則 2：左側階梯式抄底判定 (一旦鎖定，反彈不輕易平倉，直到滿足規則 1)
    elif spx_dd <= -0.30:
        current_state = 30
    elif spx_dd <= -0.19 and current_state != 30:
        current_state = 19
    # 規則 3：常態牛市跌破均線防禦線，切換為熊市
    elif current_state == 1 and q < ma * 0.97 and spx_dd > -0.19:
        current_state = 0
        
    regime_states.append(current_state)

df_all['Regime'] = regime_states

# ==========================================
# 3. 控制面板與全歷史目標權重矩陣
# ==========================================
st.sidebar.markdown("<h2 style='color:#38bdf8;'>動態參數調控</h2>", unsafe_allow_html=True)
latest_qqq = float(df_all["QQQ"].iloc[-1]) if not df_all.empty else 717.54
computed_ma200 = float(df_all["MA200"].iloc[-1]) if not df_all.empty else 612.72

sim_qqq = st.sidebar.slider("QQQ 模擬/現價", 400.0, 900.0, latest_qqq, step=0.01)
sim_ma200 = st.sidebar.slider("QQQ MA200 基準線", 400.0, 800.0, computed_ma200, step=0.01)
k_value = st.sidebar.slider("動態縮放 K 值", 0.500, 1.500, 1.137, step=0.001)
threshold = st.sidebar.slider("最小換倉門檻 (%)", 0.5, 5.0, 2.0, step=0.1)
bench_choice = st.sidebar.selectbox("對標基準", ["QQQ", "SPY"])
window_choice = st.sidebar.selectbox("滾動週期", [21, 63, 126], index=0)

# K 值邏輯
mult_qqq_qld = k_value
mult_tlt_gld = 1.0 + (k_value - 1) * 0.525
mult_uup = 2.0 - k_value

# 生成全歷史動態目標矩陣
w_qqq_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["QQQ"], BULL_BASE["QQQ"] * mult_qqq_qld)
w_tlt_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["TLT"], BULL_BASE["TLT"] * mult_tlt_gld)
w_gld_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["GLD"], BULL_BASE["GLD"] * mult_tlt_gld)
w_uup_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["UUP"], BULL_BASE["UUP"] * mult_uup)

# 精準寫入階梯式抄底 QLD 權重邏輯
w_qld_tgt = np.where(df_all['Regime'] == 30, 25.0 * mult_qqq_qld,
            np.where(df_all['Regime'] == 19, 15.0 * mult_qqq_qld,
            np.where(df_all['Regime'] == 1, BULL_BASE["QLD"] * mult_qqq_qld, BEAR_BASE["QLD"])))

w_sgov_tgt = np.maximum(0, 100.0 - (w_qqq_tgt + w_qld_tgt + w_tlt_tgt + w_gld_tgt + w_uup_tgt))

tgt_weights_df = pd.DataFrame({
    "QQQ": w_qqq_tgt, "QLD": w_qld_tgt, "TLT": w_tlt_tgt, 
    "GLD": w_gld_tgt, "UUP": w_uup_tgt, "SGOV": w_sgov_tgt
}, index=df_all.index) / 100.0

targets = (tgt_weights_df.loc[df_all.index[-1]] * 100).to_dict()

# UI 盤中即時狀態模擬顯示
current_spx_dd = df_all['SPX_DD'].iloc[-1] if not df_all.empty else 0.0
last_state = df_all['Regime'].iloc[-2] if len(df_all) > 1 else 1

if last_state == 1:
    if current_spx_dd <= -0.30: regime_text, r_class = "極度恐慌抄底鎖定 (SPX DD > 30%)", "dip-box"
    elif current_spx_dd <= -0.19: regime_text, r_class = "左側抄底鎖定 (SPX DD > 19%)", "dip-box"
    elif sim_qqq < sim_ma200 * 0.97: regime_text, r_class = "熊市冬眠啟動 (跌破 0.97)", "bear-box"
    else: regime_text, r_class = "核心進攻模式", "bull-box"
elif last_state == 0:
    if sim_qqq >= sim_ma200 * 1.04: regime_text, r_class = "重返牛市 (強勢突破 1.04)", "bull-box"
    elif current_spx_dd <= -0.30: regime_text, r_class = "極度恐慌抄底鎖定 (SPX DD > 30%)", "dip-box"
    elif current_spx_dd <= -0.19: regime_text, r_class = "左側抄底鎖定 (SPX DD > 19%)", "dip-box"
    else: regime_text, r_class = "熊市冬眠中 (等待突破 1.04)", "bear-box"
else:
    if sim_qqq >= sim_ma200 * 1.04: regime_text, r_class = "抄底成功！重返滿血牛市", "bull-box"
    elif current_spx_dd <= -0.30: regime_text, r_class = "極度恐慌抄底鎖定 (SPX DD > 30%)", "dip-box"
    else: regime_text, r_class = "左側抄底建倉鎖定中 (等待牛市訊號)", "dip-box"

ratio = sim_qqq / sim_ma200 if sim_ma200 > 0 else 1.0

# ==========================================
# 4. 前端總覽面板渲染
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold;'>Pure Alpha 戰情室 V8.7</h1>", unsafe_allow_html=True)
col1, col2 = st.columns([1, 1])

with col1:
    spx_dd_html = f"{current_spx_dd * 100:.2f}%" if not df_all.empty else "-9.79%"
    html_card1 = f"""
    <div class="cyber-card">
        <h2>市場 Regime Engine (防呆保護版)</h2>
        <div class="metric-row"><span class="m-label">QQQ 當前價格</span><span class="m-value c-yellow">{sim_qqq:.2f}</span></div>
        <div class="metric-row"><span class="m-label">QQQ MA200 均線</span><span class="m-value">{sim_ma200:.2f}</span></div>
        <div class="metric-row"><span class="m-label">SPX 真實回撤</span><span class="m-value c-yellow">{spx_dd_html}</span></div>
        <div class="metric-row"><span class="m-label">趨勢強弱比值 (Ratio)</span><span class="m-value c-green">{ratio:.3f}</span></div>
        <div class="regime-box {r_class}">{regime_text}</div>
    </div>
    """
    st.markdown(html_card1.replace('\n', ''), unsafe_allow_html=True)

with col2:
    recent_ret = df_all[PRICE_COLS].pct_change().tail(window_choice).dropna()
    w_array = np.array([targets[a] / 100 for a in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]])
    cov_matrix = recent_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].cov() * 252
    p_vol = np.sqrt(np.dot(w_array.T, np.dot(cov_matrix, w_array)))
    p_beta = (recent_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].dot(w_array).cov(recent_ret[bench_choice]) * 252) / (recent_ret[bench_choice].var() * 252)
    risk_status = '<span class="c-green">進攻效能優異 (RISK ON)</span>' if p_beta > 0.7 else '<span class="c-red">避險防禦狀態 (RISK OFF)</span>'
    html_card2 = f"""
    <div class="cyber-card">
        <h2>Portfolio Risk Engine ({window_choice}D)</h2>
        <div class="metric-row"><span class="m-label">預估組合年化波動率</span><span class="m-value c-green">{p_vol*100:.2f}%</span></div>
        <div class="metric-row"><span class="m-label">預估組合 Beta (vs {bench_choice})</span><span class="m-va
