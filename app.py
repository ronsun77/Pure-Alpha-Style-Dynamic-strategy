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
st.set_page_config(page_title="Pure Alpha 多資產對沖策略戰情室", layout="wide")

custom_css = """
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} 
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
    .version-footer { text-align: center; color: #64748b; font-size: 12px; margin-top: 50px; padding: 20px 0; border-top: 1px solid #24334d; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 1. 側邊欄：動態資產代碼自訂
# ==========================================
st.sidebar.markdown("<h2 style='color:#38bdf8;'>動態參數調控</h2>", unsafe_allow_html=True)
with st.sidebar.expander("⚙️ 自訂資產代碼 (ETF Tickers)", expanded=False):
    tk_core = st.text_input("核心成長引擎 (預設 QQQ)", "QQQ").upper()
    tk_lev  = st.text_input("動能槓桿放大 (預設 QLD)", "QLD").upper()
    tk_bond = st.text_input("長債負相關避險 (預設 TLT)", "TLT").upper()
    tk_gold = st.text_input("抗通膨終極防禦 (預設 GLD)", "GLD").upper()
    tk_usd  = st.text_input("美元流動性避險 (預設 UUP)", "UUP").upper()
    tk_safe = st.text_input("流動性海綿池 (預設 SGOV)", "SGOV").upper()

PORTFOLIO_ASSETS = [tk_core, tk_lev, tk_bond, tk_gold, tk_usd, tk_safe]

BULL_BASE = {tk_core: 26.0, tk_lev: 32.0, tk_bond: 7.0, tk_gold: 7.0, tk_usd: 9.0}
BEAR_BASE = {tk_core: 20.0, tk_lev: 20.0, tk_bond: 10.0, tk_gold: 10.0, tk_usd: 20.0}
ASSET_ROLES = {tk_core: "核心成長引擎", tk_lev: "動能槓桿放大", tk_bond: "長債負相關避險", tk_gold: "抗通膨終極防禦", tk_usd: "美元流動性避險", tk_safe: "流動性海綿池"}
CHART_COLORS = {tk_core: "#38bdf8", tk_lev: "#818cf8", tk_bond: "#f472b6", tk_gold: "#facc15", tk_usd: "#ef4444", tk_safe: "#94a3b8"}

# ==========================================
# 2. 核心資料下載引擎 
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(tickers_tuple):
    data_dict = {}
    for t in tickers_tuple:
        try:
            for _ in range(3):
                df = yf.download(t, period="max", progress=False)
                if not df.empty and 'Close' in df.columns:
                    data_dict[t] = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
                    if t == "SPY":
                        data_dict["SPY_High"] = df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High']
                        data_dict["SPY_Low"] = df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low']
                    break
                time.sleep(1)
        except Exception: 
            pass
    
    for _ in range(3):
        try:
            spx_df = yf.download("^GSPC", period="max", progress=False)
            if not spx_df.empty and 'Close' in spx_df.columns:
                data_dict["^GSPC"] = spx_df['Close'].iloc[:, 0] if isinstance(spx_df['Close'], pd.DataFrame) else spx_df['Close']
                data_dict["SPX_High"] = spx_df['High'].iloc[:, 0] if isinstance(spx_df['High'], pd.DataFrame) else spx_df['High']
                data_dict["SPX_Low"] = spx_df['Low'].iloc[:, 0] if isinstance(spx_df['Low'], pd.DataFrame) else spx_df['Low']
                break
        except Exception:
            time.sleep(1)

    if data_dict: 
        return pd.concat(data_dict, axis=1)
    return pd.DataFrame()

fetch_list = tuple(set(PORTFOLIO_ASSETS + ["SPY", "QQQ"]))

with st.spinner('正在從 Yahoo Finance 同步長期歷史市場數據...'):
    raw_df_all = load_data(fetch_list)

missing_assets = [a for a in PORTFOLIO
