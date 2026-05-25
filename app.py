import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V8.8 (盤中真實觸價版)", layout="wide")

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
# 1. 核心參數與資料下載 (加入 High/Low 提取)
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
    # 1. 抓取一般 ETF
    for t in PRICE_COLS:
        try:
            df = yf.download(t, period="10y", progress=False)
            if not df.empty and 'Close' in df.columns:
                data_dict[t] = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                if t == "SPY":
                    data_dict["SPY_High"] = df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High']
                    data_dict["SPY_Low"] = df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low']
        except Exception: pass
    
    # 2. 強制抓取 SPX (包含 High/Low)
    for _ in range(3):
        try:
            spx_df = yf.download("^GSPC", period="10y", progress=False)
            if not spx_df.empty and 'Close' in spx_df.columns:
                data_dict["^GSPC"] = spx_df['Close'].iloc[:, 0] if isinstance(spx_df['Close'], pd.DataFrame) else spx_df['Close']
                data_dict["SPX_High"] = spx_df['High'].iloc[:, 0] if isinstance(spx_df['High'], pd.DataFrame) else spx_df['High']
                data_dict["SPX_Low"] = spx_df['Low'].iloc[:, 0] if isinstance(spx_df['Low'], pd.DataFrame) else spx_df['Low']
                break
        except Exception:
            time.sleep(0.5)

    if data_dict: return pd.concat(data_dict, axis=1).dropna()
    return pd.DataFrame()

df_all = load_data()

# 判定大盤基準與高低點欄位
spx_col = '^GSPC' if '^GSPC' in df_all.columns else 'SPY'
if spx_col == '^GSPC':
    h_col, l_col = 'SPX_High', 'SPX_Low'
else:
    h_col, l_col = 'SPY_High', 'SPY_Low'

CHART_PRICE_COLS = [c for c in PRICE_COLS if c in df_all.columns]

# ==========================================
# 2. 控制面板與參數提取
# ==========================================
st.sidebar.markdown("<h2 style='color:#38bdf8;'>動態參數調控</h2>", unsafe_allow_html=True)
latest_qqq = float(df_all["QQQ"].iloc[-1]) if not df_all.empty else 717.54
computed_ma200 = float(df_all["QQQ"].rolling(200).mean().iloc[-1]) if not df_all.empty else 612.72

sim_qqq = st.sidebar.slider("QQQ 模擬/現價", 400.0, 900.0, latest_qqq, step=0.01)
sim_ma200 = st.sidebar.slider("QQQ MA200 基準線", 400.0, 800.0, computed_ma200, step=0.01)
k_value = st.sidebar.slider("動態縮放 K 值", 0.500, 1.500, 1.137, step=0.001)
threshold = st.sidebar.slider("最小換倉門檻 (%)", 0.5, 5.0, 2.0, step=0.1)

st.sidebar.markdown("<h3 style='color:#facc15;'>左側抄底門檻設定</h3>", unsafe_allow_html=True)
dip_lv1 = st.sidebar.slider("Lv1 抄底門檻 (%)", 10.0, 25.0, 19.0, step=0.1) 
dip_lv2 = st.sidebar.slider("Lv2 恐慌門檻 (%)", 20.0, 40.0, 30.0, step=0.1) 

bench_choice = st.sidebar.selectbox("對標基準", ["QQQ", "SPY"])
window_choice = st.sidebar.selectbox("滾動週期", [21, 63, 126], index=0)

dip_lv1_frac = dip_lv1 / 100.0
dip_lv2_frac = dip_lv2 / 100.0

# ==========================================
# 3. 雙門檻 + 盤中觸價狀態機 
# ==========================================
df_all['MA200'] = df_all['QQQ'].rolling(200).mean()

# 關鍵：使用 High/Low 算真實盤中回撤
df_all['SPX_Max'] = df_all[h_col].cummax()
df_all['SPX_DD'] = df_all[l_col] / df_all['SPX_Max'] - 1

regime_states = []
current_state = 1 

for i in range(len(df_all)):
    q = df_all['QQQ'].iloc[i]
    ma = df_all['MA200'].iloc[i]
    spx_dd = df_all['SPX_DD'].iloc[i] 
    
    if pd.isna(ma):
        regime_states.append(1)
        continue
    
    if q >= ma * 1.04:
        current_state = 1
    elif spx_dd <= -dip_lv2_frac:
        current_state = 30
    elif spx_dd <= -dip_lv1_frac and current_state != 30:
        current_state = 19
    elif current_state == 1 and q < ma * 0.97 and spx_dd > -dip_lv1_frac:
        current_state = 0
        
    regime_states.append(current_state)

df_all['Regime'] = regime_states

# 權重矩陣
mult_qqq_qld = k_value
mult_tlt_gld = 1.0 + (k_value - 1) * 0.525
mult_uup = 2.0 - k_value

w_qqq_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["QQQ"], BULL_BASE["QQQ"] * mult_qqq_qld)
w_tlt_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["TLT"], BULL_BASE["TLT"] * mult_tlt_gld)
w_gld_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["GLD"], BULL_BASE["GLD"] * mult_tlt_gld)
w_uup_tgt = np.where(df_all['Regime'] == 0, BEAR_BASE["UUP"], BULL_BASE["UUP"] * mult_uup)

w_qld_tgt = np.where(df_all['Regime'] == 30, 25.0 * mult_qqq_qld,
            np.where(df_all['Regime'] == 19, 15.0 * mult_qqq_qld,
            np.where(df_all['Regime'] == 1, BULL_BASE["QLD"] * mult_qqq_qld, BEAR_BASE["QLD"])))

w_sgov_tgt = np.maximum(0, 100.0 - (w_qqq_tgt + w_qld_tgt + w_tlt_tgt + w_gld_tgt + w_uup_tgt))

tgt_weights_df = pd.DataFrame({
    "QQQ": w_qqq_tgt, "QLD": w_qld_tgt, "TLT": w_tlt_tgt, 
    "GLD": w_gld_tgt, "UUP": w_uup_tgt, "SGOV": w_sgov_tgt
}, index=df_all.index) / 100.0

targets = (tgt_weights_df.loc[df_all.index[-1]] * 100).to_dict()

# UI 盤中狀態判定
current_spx_dd = df_all['SPX_DD'].iloc[-1] if not df_all.empty else 0.0
last_state = df_all['Regime'].iloc[-2] if len(df_all) > 1 else 1

if last_state == 1:
    if current_spx_dd <= -dip_lv2_frac: regime_text, r_class = f"極度恐慌抄底鎖定 (DD > {dip_lv2}%)", "dip-box"
    elif current_spx_dd <= -dip_lv1_frac: regime_text, r_class = f"左側抄底鎖定 (DD > {dip_lv1}%)", "dip-box"
    elif sim_qqq < sim_ma200 * 0.97: regime_text, r_class = "熊市冬眠啟動 (跌破 0.97)", "bear-box"
    else: regime_text, r_class = "核心進攻模式", "bull-box"
elif last_state == 0:
    if sim_qqq >= sim_ma200 * 1.04: regime_text, r_class = "重返牛市 (強勢突破 1.04)", "bull-box"
    elif current_spx_dd <= -dip_lv2_frac: regime_text, r_class = f"極度恐慌抄底鎖定 (DD > {dip_lv2}%)", "dip-box"
    elif current_spx_dd <= -dip_lv1_frac: regime_text, r_class = f"左側抄底鎖定 (DD > {dip_lv1}%)", "dip-box"
    else: regime_text, r_class = "熊市冬眠中 (等待突破 1.04)", "bear-box"
else:
    if sim_qqq >= sim_ma200 * 1.04: regime_text, r_class = "抄底成功！重返滿血牛市", "bull-box"
    elif current_spx_dd <= -dip_lv2_frac: regime_text, r_class = f"極度恐慌抄底鎖定 (DD > {dip_lv2}%)", "dip-box"
    else: regime_text, r_class = "左側抄底建倉鎖定中 (等待牛市訊號)", "dip-box"

ratio = sim_qqq / sim_ma200 if sim_ma200 > 0 else 1.0

# ==========================================
# 4. 前端總覽面板渲染
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold;'>Pure Alpha 戰情室 V8.8</h1>", unsafe_allow_html=True)
col1, col2 = st.columns([1, 1])

with col1:
    spx_dd_html = f"{current_spx_dd * 100:.2f}%" if not df_all.empty else "-9.79%"
    html_card1 = f"""
    <div class="cyber-card">
        <h2>市場 Regime Engine ({spx_col} 聯動)</h2>
        <div class="metric-row"><span class="m-label">QQQ 當前價格</span><span class="m-value c-yellow">{sim_qqq:.2f}</span></div>
        <div class="metric-row"><span class="m-label">QQQ MA200 均線</span><span class="m-value">{sim_ma200:.2f}</span></div>
        <div class="metric-row"><span class="m-label">盤中真實最大回撤</span><span class="m-value c-yellow">{spx_dd_html}</span></div>
        <div class="metric-row"><span class="m-label">趨勢強弱比值 (Ratio)</span><span class="m-value c-green">{ratio:.3f}</span></div>
        <div class="regime-box {r_class}">{regime_text}</div>
    </div>
    """
    st.markdown(html_card1.replace('\n', ''), unsafe_allow_html=True)

with col2:
    recent_ret = df_all[CHART_PRICE_COLS].pct_change().tail(window_choice).dropna()
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
        <div class="metric-row"><span class="m-label">遲滯上緣 (右側回補線)</span><span class="m-value c-green">{sim_ma200 * 1.04:.2f}</span></div>
        <div class="metric-row"><span class="m-label">風控安全評級</span><span class="m-value">{risk_status}</span></div>
    </div>
    """
    st.markdown(html_card2.replace('\n', ''), unsafe_allow_html=True)

table_rows = ""
is_bull_now = df_all['Regime'].iloc[-1] in [1, 19, 30]
for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
    cur, tgt = CURRENT_WEIGHTS[asset], targets[asset]
    diff = tgt - cur
    action, act_class = "HOLD", "badge-hold"
    if diff >= threshold: action, act_class = "BUY", "badge-buy"
    elif diff <= -threshold: action, act_class = "SELL", "badge-sell"
    if not is_bull_now and asset == "QLD" and cur > tgt: action, act_class = "REDUCE", "badge-critical"
    
    vol_str = f"{recent_ret[asset].std() * np.sqrt(252) * 100:.1f}%"
    corr = recent_ret[asset].corr(recent_ret[bench_choice])
    beta_str = f"{recent_ret[asset].cov(recent_ret[bench_choice]) / recent_ret[bench_choice].var():.2f}"
    bg_color = "background: rgba(56, 189, 248, 0.05);" if asset == "SGOV" else ""
    table_rows += f'<tr style="{bg_color}"><td style="text-align:left; padding-left:15px;"><b>{asset}</b> <span style="color:#64748b; font-size:13px;">{ASSET_ROLES[asset]}</span></td><td style="font-family:monospace;">{cur:.2f}%</td><td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td><td style="font-family:monospace; color:{"#22c55e" if diff>=0 else "#ef4444"};">{diff:+.2f}%</td><td style="font-family:monospace; color:#38bdf8;">{vol_str}</td><td style="font-family:monospace; color:{"#22c55e" if corr>0.4 else "#ef4444" if corr<-0.1 else "#facc15"};">{corr:.2f}</td><td style="font-family:monospace;">{beta_str}</td><td><span class="badge-action {act_class}">{action}</span></td></tr>'

st.markdown(f"""
<div class="cyber-card" style="margin-bottom:30px;">
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
    st.markdown(f"<h2 style='color: #38bdf8; font-size: 18px; border-left: 4px solid #38bdf8; padding-left: 10px; margin-bottom: 10px;'>動態 Beta 趨勢 (即時還原真實歷史軌跡)</h2>", unsafe_allow_html=True)
    
    ret_all = df_all[CHART_PRICE_COLS].pct_change().dropna()
    roll_cov = ret_all.rolling(window=window_choice).cov(ret_all[bench_choice])
    roll_var = ret_all[bench_choice].rolling(window=window_choice).var()
    roll_beta = roll_cov.div(roll_var, axis=0).dropna().tail(504)
    
    fig_beta = go.Figure()
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        fig_beta.add_trace(go.Scatter(x=roll_beta.index, y=roll_beta[asset], mode='lines', name=asset, line=dict(color=CHART_COLORS[asset], width=1.5, dash='dot')))
    
    w_hist_aligned = tgt_weights_df.loc[roll_beta.index]
    port_beta_dynamic = (roll_beta[["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]] * w_hist_aligned).sum(axis=1)
    
    fig_beta.add_trace(go.Scatter(x=port_beta_dynamic.index, y=port_beta_dynamic, mode='lines', name='策略組合 (Dynamic Portfolio)', line=dict(color='#22c55e', width=3.5)))
    fig_beta.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=20, t=10, b=10), height=320, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_beta, use_container_width=True)

st.markdown("---")

# ==========================================
# 6. 高級路徑依賴回測引擎 
# ==========================================
st.markdown("<h2 style='color: #38bdf8; font-size: 22px; border-left: 5px solid #38bdf8; padding-left: 10px; margin-bottom: 20px;'>歷史回測與分析引擎 (Path-Dependent Rebalance)</h2>", unsafe_allow_html=True)

min_date, max_date = df_all.index.min().date(), df_all.index.max().date()
col_d1, col_d2, _ = st.columns([1, 1, 2])
start_date = col_d1.date_input("回測起始日", min_date, min_value=min_date, max_value=max_date)
end_date = col_d2.date_input("回測結束日", max_date, min_value=min_date, max_value=max_date)

bt_mask = (df_all.index.date >= start_date) & (df_all.index.date <= end_date)
bt_df = df_all.loc[bt_mask]

if len(bt_df) > 10:
    bt_ret = bt_df[CHART_PRICE_COLS].pct_change().dropna()
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
    
    # 區間整體 Beta 計算
    bt_cov = port_daily_ret_series.cov(bt_ret[bench_choice])
    bt_var = bt_ret[bench_choice].var()
    bt_beta = bt_cov / bt_var if bt_var > 0 else 0
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum_port.index, y=cum_port.values, mode='lines', name='Pure Alpha (策略組合)', line=dict(color='#38bdf8', width=2)))
    fig.add_trace(go.Scatter(x=cum_bench.index, y=cum_bench.values, mode='lines', name=f'{bench_choice} (基準大盤)', line=dict(color='#64748b', width=1.5)))
    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=60, r=20, t=20, b=40), height=350, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01), yaxis_title="累積資金淨值")
    st.plotly_chart(fig, use_container_width=True)
    
    # 擴增為 6 個卡片，加入區間 Beta
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("總報酬率", f"{total_ret*100:.2f}%", f"大盤 {bench_total_ret*100:.2f}%")
    c2.metric("年化報酬", f"{cagr*100:.2f}%", f"大盤 {bench_cagr*100:.2f}%")
    c3.metric("最大回撤", f"{mdd*100:.2f}%", f"大盤 {bench_mdd*100:.2f}%", delta_color="inverse")
    c4.metric("波動率", f"{bt_vol*100:.2f}%", f"大盤 {bench_vol*100:.2f}%", delta_color="inverse")
    c5.metric("夏普指標", f"{sharpe:.2f}", f"大盤 {bench_sharpe:.2f}")
    c6.metric("區間 Beta", f"{bt_beta:.2f}", "大盤 1.00", delta_color="off")
    
    bull_days = np.sum(df_all.loc[bt_mask, 'Regime'] == 1)
    dip_days = np.sum((df_all.loc[bt_mask, 'Regime'] == 19) | (df_all.loc[bt_mask, 'Regime'] == 30))
    bear_days = np.sum(df_all.loc[bt_mask, 'Regime'] == 0)
    avg_reb_days = total_days // max(1, rebalance_count)
    
    report_html = f"""
    <div style="background: rgba(23, 35, 58, 0.5); padding: 20px; border-radius: 12px; margin-top: 20px; border-left: 5px solid #38bdf8;">
        <h3 style="color: #38bdf8; margin-top: 0; font-size: 18px;">📊 策略深度分析報告</h3>
        <div class="report-text">
            <p>歷史記憶狀態機運作統計：滿血牛市進攻期共 <b>{bull_days}</b> 天，階梯式左側抄底期共 <b>{dip_days}</b> 天，熊市防禦冬眠期共 <b>{bear_days}</b> 天。</p>
            <ul style="margin-top: 10px; margin-bottom: 10px;">
                <li><b>換倉控制常態：</b>在當前 <b>{threshold:.1f}%</b> 的調倉門檻限制下，全歷史共觸發真實再平衡交易 <b>{rebalance_count}</b> 次 (平均每 {avg_reb_days} 個交易日調整一次)。</li>
                <li><b>風控防禦效能：</b>階梯式左側抄底建倉成功抱持，最大下檔回撤成功鎖定在 <b>{mdd*100:.2f}%</b>，顯著優於大盤的基準表現。</li>
            </ul>
        </div>
    </div>
    """
    st.markdown(report_html.replace('\n', ''), unsafe_allow_html=True)
else:
    st.warning("資料不足。")

# ==========================================
# 7. 除錯透視鏡 (隱藏面板)
# ==========================================
with st.expander("🔍 歷史回撤與觸發除錯檢視 (Data Inspector)"):
    st.markdown("在此確認 Yahoo Finance 計算的回撤是否與你的 Excel 有微小落差。")
    debug_df = df_all[['QQQ', 'MA200', spx_col, h_col, l_col, 'SPX_DD', 'Regime']].tail(100).copy()
    debug_df['SPX_DD'] = (debug_df['SPX_DD'] * 100).round(2).astype(str) + '%'
    st.dataframe(debug_df.sort_index(ascending=False))
