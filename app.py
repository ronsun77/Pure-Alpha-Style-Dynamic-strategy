import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS 外掛注入
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V7.12", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #081028; font-family: 'Segoe UI', Arial, sans-serif; }
    .cyber-card {
        background: #17233a; border-radius: 20px; padding: 24px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.35); border: 1px solid #24334d;
        margin-bottom: 20px; color: #e2e8f0; height: 100%;
    }
    .cyber-card h2 { color: #38bdf8; margin-bottom: 20px; font-size: 20px; border-left: 4px solid #38bdf8; padding-left: 10px; }
    .cyber-card h3 { color: #facc15; font-size: 16px; margin-top: 15px; margin-bottom: 10px; }
    .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #24334d; }
    .metric-row:last-child { border-bottom: none; }
    .m-label { color: #cbd5e1; font-size: 14px; }
    .m-value { color: white; font-weight: bold; font-family: monospace; font-size: 16px; }
    .c-green { color: #22c55e; } .c-red { color: #ef4444; } .c-yellow { color: #facc15; }
    
    .cyber-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
    .cyber-table th, .cyber-table td { padding: 14px 10px; text-align: center; border-bottom: 1px solid #24334d; font-size: 16px; }
    .cyber-table th { background: #1e293b; color: #94a3b8; font-weight: 600; font-size: 15px; }
    .cyber-table td { color: #e2e8f0; }
    
    .regime-box { margin-top:20px; padding:15px; border-radius:12px; text-align:center; font-size:18px; font-weight:bold; }
    .bull-box { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; }
    .bear-box { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; }
    .neutral-box { background: rgba(250,204,21,0.15); border: 1px solid #facc15; color: #facc15; }
    
    .badge-action { padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }
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
CHART_COLORS = {"QQQ": "#38bdf8", "QLD": "#818cf8", "TLT": "#f472b6", "GLD": "#facc15", "UUP": "#ef4444", "SGOV": "#94a3b8"}

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
# 3. 優先運算量化矩陣
# ==========================================
asset_metrics = {asset: {"vol": 0.0, "corr": 0.0, "beta": 0.0} for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]}
recent_ret = pd.DataFrame()
bench_ret = pd.Series(dtype=float)
returns_df_full = pd.DataFrame()

if not df_all.empty:
    returns_df_full = df_all.pct_change().dropna()
    recent_ret = returns_df_full.tail(window_choice)
    bench_ret = recent_ret[bench_choice]
    bench_var = bench_ret.var()
    
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        a_ret = recent_ret[asset]
        vol = a_ret.std() * np.sqrt(252)
        corr = a_ret.corr(bench_ret) if bench_var > 0 else 0.0
        beta = a_ret.cov(bench_ret) / bench_var if bench_var > 0 else 0.0
        asset_metrics[asset] = {"vol": vol, "corr": corr, "beta": beta}

# ==========================================
# 4. 目標權重分配
# ==========================================
base = BULL_BASE if is_bull else BEAR_BASE
targets = {}
for k in ["QQQ", "QLD", "TLT", "GLD", "UUP"]:
    if not is_bull and k == "QLD": 
        targets[k] = 0.0
    else:
        if k in ["QQQ", "QLD"]: multiplier = k_value
        elif k == "UUP": multiplier = 2.0 - k_value
        elif k in ["TLT", "GLD"]: multiplier = 1.0 + (k_value - 1) * 0.525
        targets[k] = base[k] * multiplier
targets["SGOV"] = max(0.0, 100.0 - sum(targets.values()))

# ==========================================
# 5. 前端渲染 (HTML UI 上半部)
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold; font-size:36px; margin-bottom:0;'>Pure Alpha 戰情室 V7.12</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; font-size:14px; margin-bottom:30px;'>Regime Engine × Excel Logic Allocation × Path-Dependent Backtest</p>", unsafe_allow_html=True)

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
    bg_color = "background: rgba(56, 189, 248, 0.05);" if asset == "SGOV" else ""
    
    vol_str = f"{asset_metrics[asset]['vol']*100:.1f}%"
    corr = asset_metrics[asset]['corr']
    corr_color = "#22c55e" if corr > 0.4 else ("#ef4444" if corr < -0.1 else "#facc15")
    beta_str = f"{asset_metrics[asset]['beta']:.2f}"

    table_rows += f'<tr style="{bg_color}"><td style="text-align:left; padding-left:15px;"><b>{asset}</b> <span style="color:#64748b; font-size:13px;">{ASSET_ROLES[asset]}</span></td><td style="font-family:monospace;">{cur:.2f}%</td><td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td><td style="font-family:monospace; color:{diff_color};">{diff:+.2f}%</td><td style="font-family:monospace; color:#38bdf8;">{vol_str}</td><td style="font-family:monospace; color:{corr_color};">{corr:.2f}</td><td style="font-family:monospace;">{beta_str}</td><td><span class="badge-action {act_class}">{action}</span></td></tr>'

html_card3 = f"""
<div class="cyber-card" style="margin-bottom:30px;">
    <h2>Dynamic Allocation & Correlation Matrix</h2>
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
# 6. 動態視覺化圖表區塊
# ==========================================
col_pie, col_beta = st.columns([1, 2.2])

with col_pie:
    st.markdown("<h2 style='color: #38bdf8; font-size: 18px; border-left: 4px solid #38bdf8; padding-left: 10px; margin-bottom: 10px;'>目前實倉資產配比</h2>", unsafe_allow_html=True)
    pie_labels = list(CURRENT_WEIGHTS.keys())
    pie_values = list(CURRENT_WEIGHTS.values())
    pie_colors = [CHART_COLORS[l] for l in pie_labels]
    fig_pie = go.Figure(data=[go.Pie(labels=pie_labels, values=pie_values, hole=.45, textinfo='label+percent', textposition='outside', marker=dict(colors=pie_colors, line=dict(color='#081028', width=2)))])
    fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=20), height=320, showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_beta:
    st.markdown(f"<h2 style='color: #38bdf8; font-size: 18px; border-left: 4px solid #38bdf8; padding-left: 10px; margin-bottom: 10px;'>各資產 Rolling Beta 趨勢 (近2年)</h2>", unsafe_allow_html=True)
    fig_beta = go.Figure()
    if not returns_df_full.empty:
        roll_cov = returns_df_full.rolling(window=window_choice).cov(returns_df_full[bench_choice])
        roll_var = returns_df_full[bench_choice].rolling(window=window_choice).var()
        roll_beta = roll_cov.div(roll_var, axis=0).dropna().tail(504)
        for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
            fig_beta.add_trace(go.Scatter(x=roll_beta.index, y=roll_beta[asset], mode='lines', name=asset, line=dict(color=CHART_COLORS[asset], width=2 if asset in ["QQQ","QLD"] else 1.5)))
        port_weights = [CURRENT_WEIGHTS[a]/100 for a in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]]
        port_beta = (roll_beta[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]] * port_weights).sum(axis=1)
        fig_beta.add_trace(go.Scatter(x=port_beta.index, y=port_beta, mode='lines', name='實倉組合 (Portfolio)', line=dict(color='#22c55e', width=3, dash='dash')))
        fig_beta.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=20, t=10, b=10), height=320, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_beta, use_container_width=True)
    else:
        st.warning("資料量不足以繪製趨勢圖...")

st.markdown("---")

# ==========================================
# 7. 終極路徑依賴回測引擎 (含換倉門檻機制)
# ==========================================
st.markdown("<h2 style='color: #38bdf8; font-size: 22px; border-left: 5px solid #38bdf8; padding-left: 10px; margin-bottom: 20px;'>歷史回測與分析引擎 (Backtest Engine)</h2>", unsafe_allow_html=True)

if not df_all.empty and len(df_all) > 200:
    bt_df_full = df_all.copy()
    bt_df_full['MA200'] = bt_df_full['QQQ'].rolling(200).mean()
    bt_df_full = bt_df_full.dropna()
    
    min_date = bt_df_full.index.min().date()
    max_date = bt_df_full.index.max().date()
    
    col_d1, col_d2, col_d3 = st.columns([1, 1, 2])
    with col_d1: start_date = st.date_input("回測起始日", min_date, min_value=min_date, max_value=max_date)
    with col_d2: end_date = st.date_input("回測結束日", max_date, min_value=min_date, max_value=max_date)
    
    bt_df = bt_df_full.loc[pd.to_datetime(start_date):pd.to_datetime(end_date)]
    
    if len(bt_df) > 10:
        bt_ret = bt_df.pct_change().dropna()
        bt_df = bt_df.loc[bt_ret.index]
        n_days = len(bt_ret)
        
        # 1. 計算每日的「目標」權重矩陣
        is_bt_bull = bt_df['QQQ'] >= (bt_df['MA200'] * 0.97)
        w_qqq_tgt = np.where(is_bt_bull, BULL_BASE["QQQ"] * k_value, BEAR_BASE["QQQ"] * k_value)
        w_qld_tgt = np.where(is_bt_bull, BULL_BASE["QLD"] * k_value, BEAR_BASE["QLD"] * k_value)
        w_tlt_tgt = np.where(is_bt_bull, BULL_BASE["TLT"] * (1.0 + (k_value - 1) * 0.525), BEAR_BASE["TLT"] * (1.0 + (k_value - 1) * 0.525))
        w_gld_tgt = np.where(is_bt_bull, BULL_BASE["GLD"] * (1.0 + (k_value - 1) * 0.525), BEAR_BASE["GLD"] * (1.0 + (k_value - 1) * 0.525))
        w_uup_tgt = np.where(is_bt_bull, BULL_BASE["UUP"] * (2.0 - k_value), BEAR_BASE["UUP"] * (2.0 - k_value))
        sum_5_tgt = w_qqq_tgt + w_qld_tgt + w_tlt_tgt + w_gld_tgt + w_uup_tgt
        w_sgov_tgt = np.maximum(0, 100.0 - sum_5_tgt)
        
        tgt_weights = np.column_stack((w_qqq_tgt, w_qld_tgt, w_tlt_tgt, w_gld_tgt, w_uup_tgt, w_sgov_tgt)) / 100.0
        ret_array = bt_ret[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]].values
        
        # 2. 執行路徑依賴迭代回測 (模擬資金權重漂移與門檻觸發)
        port_nav = np.zeros(n_days)
        current_w = tgt_weights[0].copy()
        threshold_frac = threshold / 100.0
        rebalance_count = 0
        
        for i in range(n_days):
            day_ret = ret_array[i]
            daily_p_ret = np.dot(current_w, day_ret) # 當日組合報酬
            
            # 更新淨值
            if i == 0:
                port_nav[i] = 1.0 * (1 + daily_p_ret)
            else:
                port_nav[i] = port_nav[i-1] * (1 + daily_p_ret)
            
            # 結算後權重發生漂移 (Drift)
            drifted_w = current_w * (1 + day_ret) / (1 + daily_p_ret)
            
            # 檢查是否需要執行換倉 (最後一天不需換倉)
            if i < n_days - 1:
                tgt_w = tgt_weights[i+1]
                deviations = np.abs(drifted_w - tgt_w)
                if np.max(deviations) >= threshold_frac:
                    current_w = tgt_w.copy() # 觸發門檻，重置為目標權重
                    rebalance_count += 1
                else:
                    current_w = drifted_w.copy() # 繼續漂移
                    
        cum_port = pd.Series(port_nav, index=bt_ret.index)
        cum_bench = (1 + bt_ret[bench_choice]).cumprod()
        port_daily_ret_series = cum_port.pct_change().dropna()
        
        total_ret = cum_port.iloc[-1] - 1
        bench_total_ret = cum_bench.iloc[-1] - 1
        cagr = (cum_port.iloc[-1] ** (252 / total_days)) - 1
        bench_cagr = (cum_bench.iloc[-1] ** (252 / total_days)) - 1
        mdd = ((cum_port / cum_port.cummax()) - 1).min()
        bench_mdd = ((cum_bench / cum_bench.cummax()) - 1).min()
        bt_vol = port_daily_ret_series.std() * np.sqrt(252)
        bench_vol = bt_ret[bench_choice].std() * np.sqrt(252)
        
        rf = 0.04
        sharpe = (cagr - rf) / bt_vol if bt_vol > 0 else 0
        bench_sharpe = (bench_cagr - rf) / bench_vol if bench_vol > 0 else 0
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port.values, mode='lines', name='Pure Alpha (策略)', line=dict(color='#38bdf8', width=2)))
        fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench.values, mode='lines', name=f'{bench_choice} (大盤基準)', line=dict(color='#64748b', width=1.5)))
        
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=60, r=20, t=20, b=40), height=350,
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            yaxis_title="累積資金淨值 (Initial = 1.0)",
            xaxis_title="回測時間軸"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("總報酬率 (Total Ret)", f"{total_ret*100:.2f}%", f"大盤 {bench_total_ret*100:.2f}%")
        c2.metric("年化報酬 (CAGR)", f"{cagr*100:.2f}%", f"大盤 {bench_cagr*100:.2f}%")
        c3.metric("最大回撤 (MDD)", f"{mdd*100:.2f}%", f"大盤回撤 {bench_mdd*100:.2f}%", delta_color="inverse")
        c4.metric("年化波動率 (Vol)", f"{bt_vol*100:.2f}%", f"大盤波動 {bench_vol*100:.2f}%", delta_color="inverse")
        c5.metric("夏普指標 (Sharpe)", f"{sharpe:.2f}", f"大盤夏普 {bench_sharpe:.2f}")
        
        # ==========================================
        # 動態文字分析報告
        # ==========================================
        bull_days = np.sum(is_bt_bull)
        bear_days = total_days - bull_days
        bull_ratio = (bull_days / total_days) * 100
        avg_reb_days = total_days // max(1, rebalance_count)
        
        ret_text = f"<span class='{'highlight-up' if total_ret > bench_total_ret else 'highlight-down'}'>{'擊敗' if total_ret > bench_total_ret else '落後'}大盤基準</span>"
        mdd_text = f"<span class='{'highlight-up' if mdd > bench_mdd else 'highlight-down'}'>{'優於' if mdd > bench_mdd else '弱於'}大盤 ({bench_mdd*100:.2f}%)</span>"
        sharpe_text = f"代表策略在承擔相同風險下，具備<span class='{'highlight-up' if sharpe > bench_sharpe else 'highlight-down'}'>{'更強' if sharpe > bench_sharpe else '較弱'}的超額報酬獲取能力</span>。"
        conclusion = "策略成功發揮了「漲時跟隨、跌時抗跌」的 Pure Alpha 核心精神，展現了頂級的風控能力。" if (total_ret > bench_total_ret and mdd > bench_mdd) else "在這段區間內，策略呈現了不同的風險特徵，請觀察特定市場事件對資產相關性的影響。"
        
        report_html = f"""
        <div style="background: rgba(23, 35, 58, 0.5); padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 5px solid #38bdf8;">
            <h3 style="color: #38bdf8; margin-top: 0; font-size: 18px;">📊 策略深度分析報告 (總交易日: {total_days} 天)</h3>
            <div class="report-text">
                <p>在選定的 <b>{total_days}</b> 個交易日中，市場環境判定為多頭進攻 (Bull) 共 <b>{bull_days}</b> 天 ({bull_ratio:.1f}%)，觸發空頭冬眠防禦 (Bear) 共 <b>{bear_days}</b> 天。</p>
                <ul style="margin-top: 10px; margin-bottom: 10px;">
                    <li><b>交易頻率與換倉：</b>在此 <b>{threshold:.1f}%</b> 的換倉門檻設定下，共觸發真實換倉 <b>{rebalance_count}</b> 次 (平均每 {avg_reb_days} 天換倉一次)。</li>
                    <li><b>整體報酬與抗震：</b>策略創造了 <b>{total_ret*100:.2f}%</b> 的總報酬率，{ret_text}。在下檔風險控制上，最大回撤鎖定在 <b>{mdd*100:.2f}%</b>，防禦表現{mdd_text}。</li>
                    <li><b>波動率特徵：</b>策略年化波動率為 <b>{bt_vol*100:.2f}%</b>，相較於大盤的 {bench_vol*100:.2f}%，顯示策略具有{'更佳的' if bt_vol < bench_vol else '較高的'}波動控制特性。</li>
                    <li><b>風險調整後績效：</b>在無風險利率 4% 的假設下，策略夏普值達到 <b>{sharpe:.2f}</b> (大盤為 {bench_sharpe:.2f})，{sharpe_text}</li>
                </ul>
                <p style="margin-bottom: 0;"><b>系統結語：</b>{conclusion}</p>
            </div>
        </div>
        """
        st.markdown(report_html.replace('\n', ''), unsafe_allow_html=True)
    else:
        st.warning("所選日期區間過短，無法進行有效回測計算。")
else:
    st.warning("資料載入中，或歷史資料不足 200 天無法啟動回測引擎...")
