import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# 0. 網頁基礎設定與終極 CSS 外掛注入
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V6", layout="wide")

# 將你原本漂亮的 CSS 樣式直接注入 Streamlit
custom_css = """
<style>
    /* 隱藏 Streamlit 預設的頂部與底部雜訊 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 強制改變全域背景與字體 */
    .stApp {
        background-color: #081028;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    
    /* 你的專屬 Card UI 設計 */
    .cyber-card {
        background: #17233a;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.35);
        border: 1px solid #24334d;
        margin-bottom: 20px;
        color: #e2e8f0;
    }
    .cyber-card h2 {
        color: #38bdf8;
        margin-bottom: 20px;
        font-size: 20px;
        border-left: 4px solid #38bdf8;
        padding-left: 10px;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #24334d;
    }
    .metric-row:last-child { border-bottom: none; }
    .m-label { color: #cbd5e1; font-size: 14px; }
    .m-value { color: white; font-weight: bold; font-family: monospace; font-size: 16px; }
    .c-green { color: #22c55e; }
    .c-red { color: #ef4444; }
    .c-yellow { color: #facc15; }
    
    /* 客製化表格 */
    .cyber-table { width: 100%; border-collapse: collapse; margin-top: 5px; }
    .cyber-table th, .cyber-table td { padding: 12px 10px; text-align: center; border-bottom: 1px solid #24334d; font-size: 14px; }
    .cyber-table th { background: #1e293b; color: #94a3b8; font-weight: 600; }
    .cyber-table td { color: #e2e8f0; }
    
    /* 狀態燈號 Box */
    .regime-box { margin-top:20px; padding:18px; border-radius:12px; text-align:center; font-size:20px; font-weight:bold; }
    .bull-box { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #22c55e; }
    .bear-box { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #ef4444; }
    .neutral-box { background: rgba(250,204,21,0.15); border: 1px solid #facc15; color: #facc15; }
    
    /* 交易指令標籤 */
    .badge-action { padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-buy { background: rgba(34,197,94,0.2); color: #22c55e; }
    .badge-sell { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-hold { background: rgba(148,163,184,0.15); color: #94a3b8; }
    .badge-critical { background: #ef4444; color: white; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 核心參數與資料讀取 (Python Engine)
# ==========================================
CURRENT_WEIGHTS = {"QQQ": 28.71, "QLD": 35.66, "TLT": 7.80, "GLD": 7.65, "UUP": 8.00, "SGOV": 12.18}
BULL_BASE = {"QQQ": 26.0, "QLD": 32.0, "TLT": 7.0, "GLD": 7.0, "UUP": 9.0}
BEAR_BASE = {"QQQ": 13.8, "QLD": 0.0, "TLT": 9.9, "GLD": 10.1, "UUP": 24.5}
ASSET_ROLES = {"QQQ": "核心成長引擎", "QLD": "動能槓桿放大", "TLT": "長債負相關避險", "GLD": "抗通膨終極防禦", "UUP": "美元流動性避險", "SGOV": "流動性海綿池"}

@st.cache_data(ttl=3600)
def load_historical_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
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

# ==========================================
# 2. 控制面板與演算法 (Sidebar & Logic)
# ==========================================
if "QQQ" in prices_cache and len(prices_cache["QQQ"]) > 200:
    latest_qqq = float(prices_cache["QQQ"].iloc[-1])
    computed_ma200 = float(prices_cache["QQQ"].tail(200).mean())
else:
    latest_qqq, computed_ma200 = 717.54, 612.72

st.sidebar.markdown("<h2 style='color:#38bdf8;'>環境參數模擬</h2>", unsafe_allow_html=True)
sim_qqq = st.sidebar.slider("QQQ 模擬/現價", 400.0, 900.0, latest_qqq, step=0.01)
sim_ma200 = st.sidebar.slider("QQQ MA200 基準線", 400.0, 800.0, computed_ma200, step=0.01)
k_value = st.sidebar.slider("動態縮放 K 值", 0.500, 1.500, 1.137, step=0.001)
threshold = st.sidebar.slider("最小換倉門檻 (%)", 0.5, 5.0, 2.0, step=0.1)

bench_choice = st.sidebar.selectbox("對標商品 (Benchmark)", ["QQQ", "SPY"])
window_choice = st.sidebar.selectbox("統計週期 (Window)", [21, 63, 126], index=0)

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
# 3. 網頁渲染 (將 Python 數據寫入 HTML)
# ==========================================
st.markdown("<h1 style='color:white; font-weight:bold; font-size:36px; margin-bottom:0;'>Pure Alpha 戰情室 V6</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8; font-size:14px; margin-bottom:30px;'>Regime Engine × Dynamic Allocation × Matrix Engine (Python Powered)</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

# 卡片 1: 市場狀態
with col1:
    spy_dd_html = "-9.79%"
    if "SPY" in prices_cache:
        spy_val = prices_cache["SPY"].iloc[-1]
        spy_dd_html = f"{((spy_val - prices_cache['SPY'].max()) / prices_cache['SPY'].max()) * 100:.2f}%"
        
    html_card1 = f"""
    <div class="cyber-card">
        <h2>市場 Regime Engine</h2>
        <div class="metric-row"><span class="m-label">QQQ 當前價格</span><span class="m-value c-yellow">{sim_qqq:.2f}</span></div>
        <div class="metric-row"><span class="m-label">QQQ MA200 均線</span><span class="m-value">{sim_ma200:.2f}</span></div>
        <div class="metric-row"><span class="m-label">SPX 當前回撤</span><span class="m-value c-yellow">{spy_dd_html}</span></div>
        <div class="metric-row"><span class="m-label">趨勢多空比值 (Ratio)</span><span class="m-value c-green">{ratio:.3f}</span></div>
        <div class="regime-box {r_class}">{regime_text}</div>
    </div>
    """
    st.markdown(html_card1, unsafe_allow_html=True)

# 卡片 2: 風險引擎
with col2:
    p_vol, p_beta = 0.1582, 1.08
    if bench_choice in prices_cache and "QQQ" in prices_cache:
        try:
            # 矩陣運算核心
            returns_df = pd.DataFrame({k: v.pct_change() for k, v in prices_cache.items() if k in targets}).dropna()
            recent_ret = returns_df.tail(window_choice)
            cov_matrix = recent_ret.cov() * 252
            w_array = np.array([targets[a] / 100 for a in returns_df.columns])
            p_vol = np.sqrt(np.dot(w_array.T, np.dot(cov_matrix, w_array)))
            
            bench_ret = prices_cache[bench_choice].pct_change().dropna().tail(window_choice)
            bench_var = bench_ret.var() * 252
            port_ret = recent_ret.dot(w_array)
            p_beta = (port_ret.cov(bench_ret) * 252) / bench_var if bench_var != 0 else 0
        except: pass

    risk_status = '<span class="c-green">進攻效能優異 (RISK ON)</span>' if p_beta > 0.7 else '<span class="c-red">避險防禦狀態 (RISK OFF)</span>'
    html_card2 = f"""
    <div class="cyber-card">
        <h2>Portfolio Risk Engine ({window_choice}D)</h2>
        <div class="metric-row"><span class="m-label">組合預估年化波動率</span><span class="m-value c-green">{p_vol*100:.2f}%</span></div>
        <div class="metric-row"><span class="m-label">組合總體 Beta (vs {bench_choice})</span><span class="m-value c-yellow">{p_beta:.2f}</span></div>
        <div class="metric-row"><span class="m-label">風控安全評級</span><span class="m-value">{risk_status}</span></div>
        <div class="metric-row"><span class="m-label">斷頭台防禦底線</span><span class="m-value c-red">{cutoff_line:.2f}</span></div>
    </div>
    """
    st.markdown(html_card2, unsafe_allow_html=True)

# 卡片 3: 配置與交易明細 (跨欄)
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
    
    table_rows += f"""
    <tr style="{bg_color}">
        <td style="text-align:left; padding-left:20px;"><b>{asset}</b> <span style="color:#64748b; font-size:12px;">{ASSET_ROLES[asset]}</span></td>
        <td style="font-family:monospace;">{cur:.2f}%</td>
        <td style="font-family:monospace; font-weight:bold; color:white;">{tgt:.2f}%</td>
        <td style="font-family:monospace; color:{diff_color};">{diff:+.2f}%</td>
        <td><span class="badge-action {act_class}">{action}</span></td>
    </tr>
    """

html_card3 = f"""
<div class="cyber-card">
    <h2>Dynamic Allocation & Trade Action</h2>
    <table class="cyber-table">
        <thead>
            <tr><th>資產代碼</th><th>目前實倉</th><th>目標權重</th><th>部位落差</th><th>執行指令</th></tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>
"""
st.markdown(html_card3, unsafe_allow_html=True)
