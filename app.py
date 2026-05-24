import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS 外掛注入
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V7", layout="wide")

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
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 核心參數與資料讀取 (擴展至 3 年供回測用)
# ==========================================
CURRENT_WEIGHTS = {"QQQ": 28.71, "QLD": 35.66, "TLT": 7.80, "GLD": 7.65, "UUP": 8.00, "SGOV": 12.18}
BULL_BASE = {"QQQ": 26.0, "QLD": 32.0, "TLT": 7.0, "GLD": 7.0, "UUP": 9.0}
BEAR_BASE = {"QQQ": 13.8, "QLD": 0.0, "TLT": 9.9, "GLD": 10.1, "UUP": 24.5}
ASSET_ROLES = {"QQQ": "核心成長引擎", "QLD": "動能槓桿放大", "TLT": "長債負相關避險", "GLD": "抗通膨終極防禦", "UUP": "美元流動性避險", "SGOV": "流動性海綿池"}

@st.cache_data(ttl=3600)
def load_historical_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 3)
    data_dict = {}
    for t in tickers:
        try:
            df = yf.download(t, start=start_date, end=end_date, progress=False)
            if not df.empty:
                data_dict[t] = df['Close'].dropna().squeeze()
        except Exception:
            pass
    return data_dict

prices_cache = load_historical_data()

if len(prices_cache) > 0:
    df_all = pd.DataFrame(prices_cache).dropna()
else:
    df_all = pd.DataFrame()

# ==========================================
# 2. 控制面板與演算法 (Sidebar & Logic)
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

if sim_qqq >= sim_ma200:
    regime_text, r_class, is_bull = "核心進攻模式", "bull-box", True
elif sim_qqq >= cutoff_line:
    regime_text, r_class, is_bull = "多頭破位警戒區", "neutral-box", True
else:
    regime_text, r_class, is_bull = "熊市冬眠啟動", "bear-box", False

base = BULL_BASE if is_bull else BEAR_BASE
targets = {k: base[k] * k_value if k != "QLD" or is_bull else 0.0 for k in ["QQQ", "QLD", "TLT", "GLD", "UUP"]}
targets["SGOV"] = max(0.0, 100.0 - sum(targets.values()))

# ==========================================
# 3. 量化指標矩陣預算 (Volatility, Correlation, Beta)
# ==========================================
asset_metrics = {}
for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
    asset_metrics[asset] = {"vol": 0.0, "corr": 0.0, "beta": 0.0}

if not df_all.empty:
    returns_df = df_all.pct_change().dropna()
    recent_ret = returns_df.tail(window_choice)
    bench_ret = recent_ret[bench_choice]
    bench_var = bench_ret.var()
    
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        a_ret = recent_ret[asset]
        vol = a_ret.std() * np.sqrt(252)
        corr = a_ret.corr(bench_ret) if bench_var > 0 else 0.0
        cov = a_ret.cov(bench_ret)
        beta = cov / bench_var if bench_var > 0 else 0.0
        asset_metrics[asset] = {"vol": vol, "corr": corr, "beta": beta}

# ==========================================
# 4. 前端渲染 (HTML UI)
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold; font-size:36px; margin-bottom:0;'>Pure Alpha 戰情室 V7</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; font-size:14px; margin-bottom:30px;'>Regime Engine × Asset Matrix × Backtest Engine</p>", unsafe_allow_html=True)

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
    if not df_all.empty:
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
    bg_color = "background: rgba(56, 189, 248, 0.05);" if asset == "SGOV" else ""
    
    vol_str = f"{asset_metrics[asset]['vol']*100:.1f}%"
    corr = asset_metrics[asset]['corr']
    corr_color = "#22c55e" if corr > 0.4 else ("#ef4444" if corr < -0.1 else "#facc15")
    beta_str = f"{asset_metrics[asset]['beta']:.2f}"

    table_rows += f'<tr style="{bg_color}"><td style="text-align:left; padding-left:15px;"><b>{asset}</b> <span style="color:#64748b; font-size:11px;">{ASSET_ROLES[asset]}</span></td><td style="font-family:monospace;">{cur:.2f}%</td><td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td><td style="font-family:monospace; color:{diff_color};">{diff:+.2f}%</td><td style="font-family:monospace; color:#38bdf8;">{vol_str}</td><td style="font-family:monospace; color:{corr_color};">{corr:.2f}</td><td style="font-family:monospace;">{beta_str}</td><td><span class="badge-action {act_class}">{action}</span></td></tr>'

html_card3 = f"""
<div class="cyber-card">
    <h2>Dynamic Allocation & Correlation Matrix (即時整合表)</h2>
    <table class="cyber-table">
        <thead>
            <tr><th>資產代碼</th><th>目前實倉</th><th>目標權重</th><th>部位落差</th><th>波動率({window_choice}D)</th><th>相關係數</th><th>Rolling Beta</th><th>執行指令</th></tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>
"""
st.markdown(html_card3.replace('\n', ''), unsafe_allow_html=True)

# ==========================================
# 5. 歷史回測引擎 (Vectorized Backtest)
# ==========================================
st.markdown("<div class='cyber-card' style='padding-bottom:10px;'><h2>歷史回測引擎 (Backtest Engine)</h2>", unsafe_allow_html=True)

if not df_all.empty and len(df_all) > 200:
    bt_df = df_all.copy()
    bt_df['MA200'] = bt_df['QQQ'].rolling(200).mean()
    bt_df = bt_df.dropna()
    bt_ret = bt_df.pct_change().dropna()
    bt_df = bt_df.loc[bt_ret.index]
    
    is_bt_bull = bt_df['QQQ'] >= (bt_df['MA200'] * 0.97)
    
    w_qqq = np.where(is_bt_bull, BULL_BASE["QQQ"] * k_value, BEAR_BASE["QQQ"] * k_value)
    w_qld = np.where(is_bt_bull, BULL_BASE["QLD"] * k_value, BEAR_BASE["QLD"] * k_value)
    w_tlt = np.where(is_bt_bull, BULL_BASE["TLT"] * k_value, BEAR_BASE["TLT"] * k_value)
    w_gld = np.where(is_bt_bull, BULL_BASE["GLD"] * k_value, BEAR_BASE["GLD"] * k_value)
    w_uup = np.where(is_bt_bull, BULL_BASE["UUP"] * k_value, BEAR_BASE["UUP"] * k_value)
    
    sum_5 = w_qqq + w_qld + w_tlt + w_gld + w_uup
    w_sgov = np.maximum(0, 100.0 - sum_5)
    
    port_daily_ret = (w_qqq * bt_ret['QQQ'] + w_qld * bt_ret['QLD'] + w_tlt * bt_ret['TLT'] + 
                      w_gld * bt_ret['GLD'] + w_uup * bt_ret['UUP'] + w_sgov * bt_ret['SGOV']) / 100.0
    
    cum_port = (1 + port_daily_ret).cumprod()
    cum_bench = (1 + bt_ret[bench_choice]).cumprod()
    
    total_days = len(cum_port)
    cagr = (cum_port.iloc[-1] ** (252 / total_days)) - 1
    mdd = ((cum_port / cum_port.cummax()) - 1).min()
    bt_vol = port_daily_ret.std() * np.sqrt(252)
    
    bench_cagr = (cum_bench.iloc[-1] ** (252 / total_days)) - 1
    bench_mdd = ((cum_bench / cum_bench.cummax()) - 1).min()
    bench_vol = bt_ret[bench_choice].std() * np.sqrt(252)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port.values, mode='lines', name='Pure Alpha (策略)', line=dict(color='#38bdf8', width=2)))
    fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench.values, mode='lines', name=f'{bench_choice} (大盤基準)', line=dict(color='#64748b', width=1.5)))
    
    # 圖表排版更新：加入 Y軸與X軸 標籤設定，並加寬邊距
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=60, r=20, t=30, b=40), height=380,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        yaxis_title="累積資金淨值 (Initial = 1.0)",
        xaxis_title="回測時間軸"
    )
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("策略年化報酬 (CAGR)", f"{cagr*100:.2f}%", f"勝過大盤 {(cagr - bench_cagr)*100:.2f}%")
    c2.metric("策略最大回撤 (MDD)", f"{mdd*100:.2f}%", f"大盤回撤 {bench_mdd*100:.2f}%", delta_color="inverse")
    c3.metric("策略年化波動率 (Vol)", f"{bt_vol*100:.2f}%", f"大盤波動 {bench_vol*100:.2f}%", delta_color="inverse")
    c4.metric("回測交易總日數", f"{total_days} 天")
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("※ 註：此回測為向量化簡化模型，套用「當前設定之 K 值」與 0.97 斷頭台機制進行歷史軌跡推演，未計入手續費與滑價摩擦。Y 軸代表資金從 1.0 開始成長的倍數淨值。")
else:
    st.warning("資料載入中，或歷史資料不足 200 天無法啟動回測引擎...")

st.markdown("</div>", unsafe_allow_html=True)
