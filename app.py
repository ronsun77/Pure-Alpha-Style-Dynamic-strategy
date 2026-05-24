import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V8.2", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #081028; font-family: 'Segoe UI', Arial, sans-serif; }
    .cyber-card { background: #17233a; border-radius: 20px; padding: 24px; box-shadow: 0 4px 25px rgba(0,0,0,0.35); border: 1px solid #24334d; margin-bottom: 20px; color: #e2e8f0; height: 100%; }
    .cyber-card h2 { color: #38bdf8; margin-bottom: 20px; font-size: 20px; border-left: 4px solid #38bdf8; padding-left: 10px; }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #24334d; }
    .m-label { color: #cbd5e1; font-size: 14px; }
    .m-value { color: white; font-weight: bold; font-family: monospace; font-size: 16px; }
    .c-green { color: #22c55e; } .c-red { color: #ef4444; } .c-yellow { color: #facc15; }
    .cyber-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
    .cyber-table th, .cyber-table td { padding: 14px 10px; text-align: center; border-bottom: 1px solid #24334d; font-size: 16px; }
    .cyber-table th { background: #1e293b; color: #94a3b8; font-weight: 600; font-size: 15px; }
    .badge-action { padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }
    .badge-buy { background: rgba(34,197,94,0.2); color: #22c55e; }
    .badge-sell { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-hold { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .badge-critical { background: #ef4444; color: white; }
    .regime-box { margin-top:20px; padding:15px; border-radius:12px; text-align:center; font-size:18px; font-weight:bold; }
    .bull-box { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; }
    .bear-box { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; }
    .neutral-box { background: rgba(250,204,21,0.15); border: 1px solid #facc15; color: #facc15; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 核心參數與資料下載
# ==========================================
PRICE_COLS = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
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

# ==========================================
# 2. 雙門檻狀態機 (Hysteresis Regime Engine)
# ==========================================
df_all['MA200'] = df_all['QQQ'].rolling(200).mean()
df_all['SPY_Max'] = df_all['SPY'].cummax()
df_all['SPY_DD'] = df_all['SPY'] / df_all['SPY_Max'] - 1

bull_states = []
current_bull = True 

for i in range(len(df_all)):
    q = df_all['QQQ'].iloc[i]
    ma = df_all['MA200'].iloc[i]
    if pd.isna(ma):
        bull_states.append(True)
        continue
    if current_bull:
        if q < ma * 0.97: current_bull = False
    else:
        if q >= ma * 1.04: current_bull = True
    bull_states.append(current_bull)

df_all['is_bull'] = bull_states
is_bull_hist = df_all['is_bull']

# ==========================================
# 3. 控制面板與即時狀態判定
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

last_state = is_bull_hist.iloc[-2] if len(is_bull_hist) > 1 else True

if last_state: 
    if sim_qqq < sim_ma200 * 0.97:
        regime_text, r_class, is_bull = "熊市冬眠啟動 (跌破 0.97 斷頭台)", "bear-box", False
    else:
        regime_text, r_class, is_bull = "核心進攻模式", "bull-box", True
else: 
    if sim_qqq >= sim_ma200 * 1.04:
        regime_text, r_class, is_bull = "重返牛市 (強勢突破 1.04)", "bull-box", True
    else:
        regime_text, r_class, is_bull = "熊市冬眠中 (須突破 1.04 方可買回)", "bear-box", False

ratio = sim_qqq / sim_ma200 if sim_ma200 > 0 else 1.0

mult_qqq_qld = k_value
mult_tlt_gld = 1.0 + (k_value - 1) * 0.525
mult_uup = 2.0 - k_value

w_qqq_tgt = np.where(is_bull_hist, BULL_BASE["QQQ"] * mult_qqq_qld, BEAR_BASE["QQQ"])
w_tlt_tgt = np.where(is_bull_hist, BULL_BASE["TLT"] * mult_tlt_gld, BEAR_BASE["TLT"])
w_gld_tgt = np.where(is_bull_hist, BULL_BASE["GLD"] * mult_tlt_gld, BEAR_BASE["GLD"])
w_uup_tgt = np.where(is_bull_hist, BULL_BASE["UUP"] * mult_uup, BEAR_BASE["UUP"])
w_qld_tgt = np.where(is_bull_hist, BULL_BASE["QLD"] * mult_qqq_qld, BEAR_BASE["QLD"]) 
w_sgov_tgt = np.maximum(0, 100.0 - (w_qqq_tgt + w_qld_tgt + w_tlt_tgt + w_gld_tgt + w_uup_tgt))

tgt_weights_df = pd.DataFrame({
    "QQQ": w_qqq_tgt, "QLD": w_qld_tgt, "TLT": w_tlt_tgt, 
    "GLD": w_gld_tgt, "UUP": w_uup_tgt, "SGOV": w_sgov_tgt
}, index=df_all.index) / 100.0

targets = (tgt_weights_df.loc[df_all.index[-1]] * 100).to_dict()

# ==========================================
# 4. 儀表板 UI 渲染
# ==========================================
st.markdown("<h1 style='color:white;'>Pure Alpha 戰情室 V8.2</h1>", unsafe_allow_html=True)
col1, col2 = st.columns([1, 1])
with col1:
    spy_dd_html = f"{df_all['SPY_DD'].iloc[-1] * 100:.2f}%" if not df_all.empty else "-9.79%"
    html_card1 = f"""
    <div class="cyber-card">
        <h2>市場 Regime Engine (雙門檻系統)</h2>
        <div class="metric-row"><span class="m-label">QQQ 當前價格</span><span class="m-value c-yellow">{sim_qqq:.2f}</span></div>
        <div class="metric-row"><span class="m-label">QQQ MA200 均線</span><span class="m-value">{sim_ma200:.2f}</span></div>
        <div class="metric-row"><span class="m-label">SPX 當前回撤</span><span class="m-value c-yellow">{spy_dd_html}</span></div>
        <div class="metric-row"><span class="m-label">趨勢強弱比值 (Ratio)</span><span class="m-value c-green">{ratio:.3f}</span></div>
        <div class="regime-box {r_class}">{regime_text}</div>
    </div>
    """
    st.markdown(html_card1.replace('\n', ''), unsafe_allow_html=True)

with col2:
    # 修正點 1：只對 PRICE_COLS 計算漲跌幅
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
        <div class="metric-row"><span class="m-label">預估組合 Beta (vs {bench_choice})</span><span class="m-value c-yellow">{p_beta:.2f}</span></div>
        <div class="metric-row"><span class="m-label">遲滯上緣 (牛市買回線)</span><span class="m-value c-green">{sim_ma200 * 1.04:.2f}</span></div>
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
    
    vol_str = f"{recent_ret[asset].std() * np.sqrt(252) * 100:.1f}%"
    corr = recent_ret[asset].corr(recent_ret[bench_choice])
    beta_str = f"{recent_ret[asset].cov(recent_ret[bench_choice]) / recent_ret[bench_choice].var():.2f}"
    bg_color = "background: rgba(56, 189, 248, 0.05);" if asset == "SGOV" else ""
    table_rows += f'<tr style="{bg_color}"><td style="text-align:left; padding-left:15px;"><b>{asset}</b> <span style="color:#64748b; font-size:13px;">{ASSET_ROLES[asset]}</span></td><td style="font-family:monospace;">{cur:.2f}%</td><td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td><td style="font-family:monospace; color:{"#22c55e" if diff>=0 else "#ef4444"};">{diff:+.2f}%</td><td style="font-family:monospace; color:#38bdf8;">{vol_str}</td><td style="font-family:monospace; color:{"#22c55e" if corr>0.4 else "#ef4444" if corr<-0.1 else "#facc15"};">{corr:.2f}</td><td style="font-family:monospace;">{beta_str}</td><td><span class="badge-action {act_class}">{action}</span></td></tr>'

st.markdown(f"""
<div class="cyber-card" style="margin-bottom:30px;">
    <h2>Dynamic Allocation & Correlation Matrix</h2>
    <table class="cyber-table"><thead><tr><th>資產代碼</th><th>目前實倉</th><th>目標權重</th><th>部位落差</th><th>波動率({window_choice}D)</th><th>相關係數</th><th>Rolling Beta</th><th>執行指令</th></tr></thead><tbody>{table_rows}</tbody></table>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 5. 視覺化圖表區塊
# ==========================================
col_pie, col_beta = st.columns([1, 2.2])

with col_pie:
    st.markdown("<h2 style='color: #38bdf8; font-size: 18px; border-left: 4px solid #38bdf8; padding-left: 10px; margin-bottom: 10px;'>目前實倉資產配比</h2>", unsafe_allow_html=True)
    fig_pie = go.Figure(data=[go.Pie(labels=list(CURRENT_WEIGHTS.keys()), values=list(CURRENT_WEIGHTS.values()), hole=.45, textinfo='label+percent', marker=dict(colors=[CHART_COLORS[l] for l in CURRENT_WEIGHTS.keys()], line=dict(color='#081028', width=2)))])
    fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=20), height=320, showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_beta:
    st.markdown(f"<h2 style='color: #38bdf8; font-size: 18px; border-left: 4px solid #38bdf8; padding-left: 10px; margin-bottom: 10px;'>動態 Beta 趨勢 (即時還原歷史狀態)</h2>", unsafe_allow_html=True)
    fig_beta = go.Figure()
    
    # 修正點 2：只對 PRICE_COLS 計算漲跌幅
    ret_all = df_all[PRICE_COLS].pct_change().dropna()
    roll_cov = ret_all.rolling(window=window_choice).cov(ret_all[bench_choice])
    roll_var = ret_all[bench_choice].rolling(window=window_choice).var()
    roll_beta = roll_cov.div(roll_var, axis=0).dropna().tail(504)
    
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        fig_beta.add_trace(go.Scatter(x=roll_beta.index, y=roll_beta[asset], mode='lines', name=asset, line=dict(color=CHART_COLORS[asset], width=1.5, dash='dot')))
    
    w_hist_aligned = tgt_weights_df.loc[roll_beta.index]
    port_beta_dynamic = (roll_beta[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]] * w_hist_aligned).sum(axis=1)
    
    fig_beta.add_trace(go.Scatter(x=port_beta_dynamic.index, y=port_beta_dynamic, mode='lines', name='策略組合 (Dynamic)', line=dict(color='#22c55e', width=3.5)))
    fig_beta.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=20, t=10, b=10), height=320, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_beta, use_container_width=True)

st.markdown("---")

# ==========================================
# 6. 路徑依賴回測引擎 
# ==========================================
st.markdown("<h2 style='color: #38bdf8; font-size: 22px; border-left: 5px solid #38bdf8; padding-left: 10px; margin-bottom: 20px;'>歷史回測與分析引擎 (Path-Dependent)</h2>", unsafe_allow_html=True)

df_all = df_all.dropna()
min_date, max_date = df_all.index.min().date(), df_all.index.max().date()
col_d1, col_d2, _ = st.columns([1, 1, 2])
start_date = col_d1.date_input("回測起始日", min_date, min_value=min_date, max_value=max_date)
end_date = col_d2.date_input("回測結束日", max_date, min_value=min_date, max_value=max_date)

bt_mask = (df_all.index.date >= start_date) & (df_all.index.date <= end_date)
bt_df = df_all.loc[bt_mask]

if len(bt_df) > 10:
    # 修正點 3：只對 PRICE_COLS 計算漲跌幅
    bt_ret = bt_df[PRICE_COLS].pct_change().dropna()
    tgt_weights_sub = tgt_weights_df.loc[bt_ret.index]
    
    n_days = len(bt_ret)
    port_nav = np.zeros(n_days)
    
    ret_array = bt_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].values
    tgt_array = tgt_weights_sub[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].values
    
    current_w = tgt_array[0].copy()
    threshold_frac = threshold / 100.0
    rebalance_count = 0
    
    for i in range(n_days):
        day_ret = ret_array[i]
        daily_p_ret = np.dot(current_w, day_ret)
        port_nav[i] = (1.0 * (1 + daily_p_ret)) if i == 0 else (port_nav[i-1] * (1 + daily_p_ret))
        drifted_w = current_w * (1 + day_ret) / (1 + daily_p_ret)
        
        if i < n_days - 1:
            tgt_w = tgt_array[i+1]
            deviations = np.abs(drifted_w - tgt_w)
            if np.max(deviations) >= threshold_frac:
                current_w = tgt_w.copy()
                rebalance_count += 1
            else:
                current_w = drifted_w.copy()
                
    cum_port = pd.Series(port_nav, index=bt_ret.index)
    cum_bench = (1 + bt_ret[bench_choice]).cumprod()
    
    total_days = len(cum_port)
    total_ret = cum_port.iloc[-1] - 1
    bench_total_ret = cum_bench.iloc[-1] - 1
    cagr = (cum_port.iloc[-1] ** (252 / total_days)) - 1 if total_days > 0 else 0
    bench_cagr = (cum_bench.iloc[-1] ** (252 / total_days)) - 1 if total_days > 0 else 0
    mdd = ((cum_port / cum_port.cummax()) - 1).min()
    bench_mdd = ((cum_bench / cum_bench.cummax()) - 1).min()
    
    port_daily_ret_series = cum_port.pct_change().dropna()
    bt_vol = port_daily_ret_series.std() * np.sqrt(252)
    bench_vol = bt_ret[bench_choice].std() * np.sqrt(252)
    sharpe = (cagr - 0.04) / bt_vol if bt_vol > 0 else 0
    bench_sharpe = (bench_cagr - 0.04) / bench_vol if bench_vol > 0 else 0
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port.values, mode='lines', name='Pure Alpha (策略)', line=dict(color='#38bdf8', width=2)))
    fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench.values, mode='lines', name=f'{bench_choice} (大盤基準)', line=dict(color='#64748b', width=1.5)))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=60, r=20, t=20, b=40), height=350, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01), yaxis_title="累積資金淨值 (Initial = 1.0)")
    st.plotly_chart(fig, use_container_width=True)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("總報酬率 (Total Ret)", f"{total_ret*100:.2f}%", f"大盤 {bench_total_ret*100:.2f}%")
    c2.metric("年化報酬 (CAGR)", f"{cagr*100:.2f}%", f"大盤 {bench_cagr*100:.2f}%")
    c3.metric("最大回撤 (MDD)", f"{mdd*100:.2f}%", f"大盤回撤 {bench_mdd*100:.2f}%", delta_color="inverse")
    c4.metric("年化波動率 (Vol)", f"{bt_vol*100:.2f}%", f"大盤波動 {bench_vol*100:.2f}%", delta_color="inverse")
    c5.metric("夏普指標 (Sharpe)", f"{sharpe:.2f}", f"大盤夏普 {bench_sharpe:.2f}")
    
    bull_days = np.sum(tgt_weights_sub["QLD"] > 0)
    bear_days = total_days - bull_days
    avg_reb_days = total_days // max(1, rebalance_count)
    
    report_html = f"""
    <div style="background: rgba(23, 35, 58, 0.5); padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 5px solid #38bdf8;">
        <h3 style="color: #38bdf8; margin-top: 0; font-size: 18px;">📊 策略深度分析報告 (總交易日: {total_days} 天)</h3>
        <div class="report-text">
            <p>雙門檻狀態機發揮作用：多頭進攻期共 <b>{bull_days}</b> 天，觸發空頭冬眠防禦共 <b>{bear_days}</b> 天。</p>
            <ul style="margin-top: 10px; margin-bottom: 10px;">
                <li><b>交易頻率與換倉：</b>在此 <b>{threshold:.1f}%</b> 的換倉門檻設定下，共觸發真實換倉 <b>{rebalance_count}</b> 次 (平均每 {avg_reb_days} 天換倉一次)。</li>
                <li><b>整體報酬與抗震：</b>創造了 <b>{total_ret*100:.2f}%</b> 的總報酬率。下檔風險控制上，最大回撤鎖定在 <b>{mdd*100:.2f}%</b> (大盤為 {bench_mdd*100:.2f}%)。</li>
                <li><b>波動率特徵：</b>年化波動率為 <b>{bt_vol*100:.2f}%</b> (大盤為 {bench_vol*100:.2f}%)，夏普值達到 <b>{sharpe:.2f}</b>。</li>
            </ul>
        </div>
    </div>
    """
    st.markdown(report_html.replace('\n', ''), unsafe_allow_html=True)
else:
    st.warning("所選日期區間資料不足。")
