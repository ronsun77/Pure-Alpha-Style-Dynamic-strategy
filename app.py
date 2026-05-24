import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS 外掛注入
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V7.5", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #081028; font-family: 'Segoe UI', Arial, sans-serif; }
    .cyber-card {
        background: #17233a; border-radius: 20px; padding: 24px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.35); border: 1px solid #24334d;
        margin-bottom: 20px; color: #e2e8f0;
    }
    .cyber-card h2 { color: #38bdf8; margin-bottom: 20px; font-size: 20px; border-left: 4px solid #38bdf8; padding-left: 10px; }
    .cyber-card h3 { color: #facc15; font-size: 16px; margin-top: 15px; margin-bottom: 10px; }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #24334d; }
    .metric-row:last-child { border-bottom: none; }
    .m-label { color: #cbd5e1; font-size: 14px; }
    .m-value { color: white; font-weight: bold; font-family: monospace; font-size: 16px; }
    .c-green { color: #22c55e; } .c-red { color: #ef4444; } .c-yellow { color: #facc15; }
    
    .cyber-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
    .cyber-table th, .cyber-table td { padding: 10px 8px; text-align: center; border-bottom: 1px solid #24334d; font-size: 13px; }
    .cyber-table th { background: #1e293b; color: #94a3b8; font-weight: 600; }
    .cyber-table td { color: #e2e8f0; }
    
    .regime-box { margin-top:20px; padding:15px; border-radius:12px; text-align:center; font-size:18px; font-weight:bold; }
    .bull-box { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; }
    .bear-box { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; }
    .neutral-box { background: rgba(250,204,21,0.15); border: 1px solid #facc15; color: #facc15; }
    
    .badge-action { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-buy { background: rgba(34,197,94,0.2); color: #22c55e; }
    .badge-sell { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-hold { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .badge-critical { background: #ef4444; color: white; }
    
    .report-text { line-height: 1.8; color: #cbd5e1; font-size: 15px; }
    .report-text b { color: white; }
    .report-text .highlight-up { color: #22c55e; font-weight: bold; }
    .report-text .highlight-down { color: #ef4444; font-weight: bold; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 核心參數與資料讀取
# ==========================================
CURRENT_WEIGHTS = {"QQQ": 28.71, "QLD": 35.66, "TLT": 7.80, "GLD": 7.65, "UUP": 8.00, "SGOV": 12.18}
BULL_BASE = {"QQQ": 26.0, "QLD": 32.0, "TLT": 7.0, "GLD": 7.0, "UUP": 9.0}
BEAR_BASE = {"QQQ": 13.8, "QLD": 0.0, "TLT": 9.9, "GLD": 10.1, "UUP": 24.5}
ASSET_ROLES = {"QQQ": "核心成長引擎", "QLD": "動能槓桿放大", "TLT": "長債負相關避險", "GLD": "抗通膨終極防禦", "UUP": "美元流動性避險", "SGOV": "流動性海綿池"}

@st.cache_data(ttl=3600)
def load_historical_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
    data_dict = {}
    for t in tickers:
        try:
            df = yf.download(t, period="10y", progress=False)
            if not df.empty:
                data_dict[t] = df['Close'].dropna().squeeze()
        except Exception: pass
    return data_dict

prices_cache = load_historical_data()
df_all = pd.DataFrame(prices_cache).dropna() if len(prices_cache) > 0 else pd.DataFrame()

# ==========================================
# 2. 控制面板 (Sidebar)
# ==========================================
if not df_all.empty and len(df_all) > 200:
    latest_qqq = float(df_all["QQQ"].iloc[-1])
    computed_ma200 = float(df_all["QQQ"].tail(200).mean())
else:
    latest_qqq, computed_ma200 = 717.54, 612.72

st.sidebar.markdown("<h2 style='color:#38bdf8;'>動態參數調控</h2>", unsafe_allow_html=True)
sim_qqq = st.sidebar.slider("QQQ 模擬/現價", 400.0, 900.0, latest_qqq, step=0.01)
sim_ma200 = st.sidebar.slider("QQQ MA200 基準線", 400.0, 800.0, computed_ma200, step=0.01)
k_value = st.sidebar.slider("動態縮放 K 值", 0.500, 1.500, 1.137, step=0.001)
threshold = st.sidebar.slider("最小換倉門檻 (%)", 0.5, 5.0, 2.0, step=0.1)
bench_choice = st.sidebar.selectbox("對標基準 (Benchmark)", ["QQQ", "SPY"])
window_choice = st.sidebar.selectbox("滾動週期 (Window)", [21, 63, 126], index=0)

cutoff_line = sim_ma200 * 0.97
ratio = sim_qqq / sim_ma200 if sim_ma200 > 0 else 1.0

if sim_qqq >= sim_ma200: regime_text, r_class, is_bull = "核心進攻模式", "bull-box", True
elif sim_qqq >= cutoff_line: regime_text, r_class, is_bull = "多頭破位警戒區", "neutral-box", True
else: regime_text, r_class, is_bull = "熊市冬眠啟動", "bear-box", False

# ==========================================
# 3. 優先運算量化矩陣 (取得真實 Beta)
# ==========================================
asset_metrics = {asset: {"vol": 0.0, "corr": 0.0, "beta": 0.0} for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]}
recent_ret = pd.DataFrame()
bench_ret = pd.Series(dtype=float)

if not df_all.empty:
    returns_df = df_all.pct_change().dropna()
    recent_ret = returns_df.tail(window_choice)
    bench_ret = recent_ret[bench_choice]
    bench_var = bench_ret.var()
    
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        a_ret = recent_ret[asset]
        vol = a_ret.std() * np.sqrt(252)
        corr = a_ret.corr(bench_ret) if bench_var > 0 else 0.0
        beta = a_ret.cov(bench_ret) / bench_var if bench_var > 0 else 0.0
        asset_metrics[asset] = {"vol": vol, "corr": corr, "beta": beta}

# ==========================================
# 4. 目標權重分配 (動態結合 Beta 的 K 值縮放)
# ==========================================
base = BULL_BASE if is_bull else BEAR_BASE
targets = {}
for k in ["QQQ", "QLD", "TLT", "GLD", "UUP"]:
    if not is_bull and k == "QLD": targets[k] = 0.0
    else:
        effective_beta = 1.0 if k in ["QQQ", "QLD"] else asset_metrics[k]["beta"]
        targets[k] = base[k] * max(0.0, 1 + (k_value - 1) * effective_beta)
targets["SGOV"] = max(0.0, 100.0 - sum(targets.values()))

# ==========================================
# 5. 前端渲染 (HTML UI 上半部)
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold; font-size:36px; margin-bottom:0;'>Pure Alpha 戰情室 V7.5</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; font-size:14px; margin-bottom:30px;'>Regime Engine × Dynamic Beta Allocation × Advanced Backtest Engine</p>", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])
with col1:
    spy_dd_html = "-9.79%"
    if "SPY" in df_all.columns:
        spy_val = df_all["SPY"].iloc[-1]
        spy_dd_html = f"{((spy_val - df_all['SPY'].max()) / df_all['SPY'].max()) * 100:.2f}%"
    html_card1 = f"""
    <div class="cyber-card">
        <h2>市場 Regime Engine</h2>
        <div class="metric-row"><span class="m-label">QQQ 當前價格</span><span class="m-value c-yellow">{sim_qqq:.2f}</span></div>
        <div class="metric-row"><span class="m-label">QQQ MA200 均線</span><span class="m-value">{sim_ma200:.2f}</span></div>
        <div class="metric-row"><span class="m-label">SPX 當前回撤</span><span class="m-value c-yellow">{spy_dd_html}</span></div>
        <div class="metric-row"><span class="m-label">趨勢強弱比值 (Ratio)</span><span class="m-value c-green">{ratio:.3f}</span></div>
        <div class="regime-box {r_class}">{regime_text}</div>
    </div>
    """
    st.markdown(html_card1.replace('\n', ''), unsafe_allow_html=True)

with col2:
    p_vol, p_beta = 0.1582, 1.08
    if not df_all.empty and not recent_ret.empty:
        w_array = np.array([targets[a] / 100 for a in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]])
        cov_matrix = recent_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].cov() * 252
        p_vol = np.sqrt(np.dot(w_array.T, np.dot(cov_matrix, w_array)))
        port_ret = recent_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].dot(w_array)
        p_beta = (port_ret.cov(bench_ret) * 252) / (bench_ret.var() * 252) if bench_ret.var() > 0 else 0
    risk_status = '<span class="c-green">進攻效能優異 (RISK ON)</span>' if p_beta > 0.7 else '<span class="c-red">避險防禦狀態 (RISK OFF)</span>'
    html_card2 = f"""
    <div class="cyber-card">
        <h2>Portfolio Risk Engine ({window_choice}D)</h2>
        <div class="metric-row"><span class="m-label">預估組合年化波動率</span><span class="m-value c-green">{p_vol*100:.2f}%</span></div>
        <div class="metric-row"><span class="m-label">預估組合 Beta (vs {bench_choice})</span><span class="m-value c-yellow">{p_beta:.2f}</span></div>
        <div class="metric-row"><span class="m-label">斷頭台防禦底線</span><span class="m-value c-red">{cutoff_line:.2f}</span></div>
        <div class="metric-row"><span class="m-label">風控安全評級</span><span class="m-value">{risk_status}</span></div>
    </div>
    """
    st.markdown(html_card2.replace('\n', ''), unsafe_allow_html=True)

table_rows = ""
for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
    cur, tgt = CURRENT_WEIGHTS[asset], targets[asset]
    diff = tgt - cur
    action, act_class = "HOLD", "badge-hold"
    if diff >= threshold: action, act_class = "BUY", "badge-buy"
    elif diff <= -threshold: action, act_class = "SELL", "badge-sell"
    if not is_bull and asset == "QLD" and cur > 0: action, act_class = "CRITICAL SELL", "badge-critical"
    diff_color = "#22c55e" if diff >= 0 else "#ef4444"
    vol_str = f"{asset_metrics[asset]['vol']*100:.1f}%"
    corr = asset_metrics[asset]['corr']
    corr_color = "#22c55e" if corr > 0.4 else ("#ef4444" if corr < -0.1 else "#facc15")
    table_rows += f'<tr style="background: {"rgba(56, 189, 248, 0.05)" if asset=="SGOV" else ""}"><td style="text-align:left; padding-left:15px;"><b>{asset}</b> <span style="color:#64748b; font-size:11px;">{ASSET_ROLES[asset]}</span></td><td style="font-family:monospace;">{cur:.2f}%</td><td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td><td style="font-family:monospace; color:{diff_color};">{diff:+.2f}%</td><td style="font-family:monospace; color:#38bdf8;">{vol_str}</td><td style="font-family:monospace; color:{corr_color};">{corr:.2f}</td><td style="font-family:monospace;">{asset_metrics[asset]['beta']:.2f}</td><td><span class="badge-action {act_class}">{action}</span></td></tr>'

st.markdown(f'<div class="cyber-card"><h2>Dynamic Allocation & Correlation Matrix</h2><table class="cyber-table"><thead><tr><th>資產代碼</th><th>目前實倉</th><th>目標權重</th><th>部位落差</th><th>波動率({window_choice}D)</th><th>相關係數</th><th>Rolling Beta</th><th>執行指令</th></tr></thead><tbody>{table_rows}</tbody></table></div>'.replace('\n', ''), unsafe_allow_html=True)

# ==========================================
# 6. 歷史回測引擎
# ==========================================
st.markdown("<div class='cyber-card' style='padding-bottom:10px;'><h2>歷史回測與分析引擎</h2>", unsafe_allow_html=True)
if not df_all.empty and len(df_all) > 200:
    min_date, max_date = df_all.index.min().date(), df_all.index.max().date()
    col_d1, col_d2 = st.columns(2)
    with col_d1: start_date = st.date_input("回測起始日", min_date, min_value=min_date, max_value=max_date)
    with col_d2: end_date = st.date_input("回測結束日", max_date, min_value=min_date, max_value=max_date)
    bt_df = df_all.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]
    if len(bt_df) > 10:
        bt_ret = bt_df.pct_change().dropna()
        is_bt_bull = bt_df['QQQ'] >= (bt_df['QQQ'].rolling(200).mean() * 0.97)
        w_qqq = np.where(is_bt_bull, BULL_BASE["QQQ"] * k_value, BEAR_BASE["QQQ"] * k_value)
        w_qld = np.where(is_bt_bull, BULL_BASE["QLD"] * k_value, BEAR_BASE["QLD"] * k_value)
        w_tlt = np.where(is_bt_bull, BULL_BASE["TLT"] * k_value, BEAR_BASE["TLT"] * k_value)
        w_gld = np.where(is_bt_bull, BULL_BASE["GLD"] * k_value, BEAR_BASE["GLD"] * k_value)
        w_uup = np.where(is_bt_bull, BULL_BASE["UUP"] * k_value, BEAR_BASE["UUP"] * k_value)
        w_sgov = np.maximum(0, 100.0 - (w_qqq + w_qld + w_tlt + w_gld + w_uup))
        port_ret = (w_qqq * bt_ret['QQQ'] + w_qld * bt_ret['QLD'] + w_tlt * bt_ret['TLT'] + w_gld * bt_ret['GLD'] + w_uup * bt_ret['UUP'] + w_sgov * bt_ret['SGOV']) / 100.0
        cum_port = (1 + port_ret).cumprod()
        cum_bench = (1 + bt_ret[bench_choice]).cumprod()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port.values, name='Pure Alpha', line=dict(color='#38bdf8', width=2)))
        fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench.values, name='Benchmark', line=dict(color='#64748b', width=1.5)))
        fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=40, r=20, t=30, b=40), height=300, yaxis_title="淨值 (Initial=1.0)")
        st.plotly_chart(fig, use_container_width=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("年化報酬 (CAGR)", f"{((cum_port.iloc[-1]**(252/len(cum_port)))-1)*100:.2f}%")
        c2.metric("最大回撤 (MDD)", f"{((cum_port/cum_port.cummax())-1).min()*100:.2f}%")
        c3.metric("年化波動率 (Vol)", f"{port_ret.std()*np.sqrt(252)*100:.2f}%")
        c4.metric("交易日數", len(cum_port))
st.markdown("</div>", unsafe_allow_html=True)
