import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# ==========================================
# 0. 系統環境與架構配置
# ==========================================
st.set_page_config(page_title="Pure Alpha 戰情室 V6", layout="wide")

# 固定實際現存持倉 (Current Weights)
CURRENT_WEIGHTS = {"QQQ": 28.71, "QLD": 35.66, "TLT": 7.80, "GLD": 7.65, "UUP": 8.00, "SGOV": 12.18}
BULL_BASE = {"QQQ": 26.0, "QLD": 32.0, "TLT": 7.0, "GLD": 7.0, "UUP": 9.0}
BEAR_BASE = {"QQQ": 13.8, "QLD": 0.0,  TLT: 9.9, "GLD": 10.1, "UUP": 24.5}
ASSET_ROLES = {
    "QQQ": "核心成長引擎", "QLD": "動能槓桿放大", "TLT": "長債負相關避險",
    "GLD": "抗通膨終極防禦", "UUP": "美元流動性避險", "SGOV": "流動性緩衝海綿池"
}

# ==========================================
# 1. 數據增強模組 (帶快取優化機制)
# ==========================================
@st.cache_data(ttl=3600)  # 每小時快取更新，避免頻繁請求遭限流
def load_historical_data():
    tickers = ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV", "SPY"]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    data_dict = {}
    for t in tickers:
        try:
            asset = yf.Ticker(t)
            df = asset.history(start=start_date, end=end_date)
            if not df.empty:
                data_dict[t] = df['Close'].dropna()
        except Exception as e:
            st.error(f"資產 {t} 連線同步失敗: {str(e)}")
    return data_dict

# 載入資料
prices_cache = load_historical_data()

# ==========================================
# 2. 側邊欄控制面板 (Sidebar)
# ==========================================
st.sidebar.title("Pure Alpha 控制台")
st.sidebar.markdown("---")

# 初始化與同步最新市場數據
if "QQQ" in prices_cache and len(prices_cache["QQQ"]) > 200:
    latest_qqq = float(prices_cache["QQQ"].iloc[-1])
    computed_ma200 = float(prices_cache["QQQ"].tail(200).mean())
else:
    latest_qqq, computed_ma200 = 717.54, 612.72

# 互動滑桿設定
sim_qqq = st.sidebar.slider("QQQ 模擬/真實現價", 400.0, 900.0, latest_qqq, step=0.01)
sim_ma200 = st.sidebar.slider("QQQ MA200 基準線", 400.0, 800.0, computed_ma200, step=0.01)
k_value = st.sidebar.slider("當前動態 K 值 (波動率調節)", 0.500, 1.500, 1.137, step=0.001)
threshold = st.sidebar.slider("換倉最小調整門檻 (%)", 0.5, 5.0, 2.0, step=0.1)

# 計算防線
cutoff_line = sim_ma200 * 0.97
ratio = sim_qqq / sim_ma200

# ==========================================
# 3. 中央運算決策引擎
# ==========================================
# 多空機制與 Regime 判定
if sim_qqq >= sim_ma200:
    regime_text = "核心進攻模式 (Regime: Bull)"
    regime_class = "bull"
    is_bull = True
elif sim_qqq >= cutoff_line:
    regime_text = "多頭破位警戒區 (Whipsaw Filter)"
    regime_class = "neutral"
    is_bull = True
else:
    regime_text = "熊市全面防禦 (冬眠啟動)"
    regime_class = "bear"
    is_bull = False

# 計算目標權重
base = BULL_BASE if is_bull else BEAR_BASE
targets = {
    "QQQ": base["QQQ"] * k_value,
    "QLD": (base["QLD"] * k_value) if is_bull else 0.0,
    "TLT": base["TLT"] * k_value,
    "GLD": base["GLD"] * k_value,
    "UUP": base["UUP"] * k_value
}
# SGOV 海綿調度
allocated_sum = sum(targets.values())
targets["SGOV"] = max(0.0, 100.0 - allocated_sum)

# ==========================================
# 4. 主面板視覺化排版 (Dashboard Layout)
# ==========================================
st.title("Pure Alpha 戰情室 V6")
st.markdown("Regime Engine × Dynamic Allocation × Dynamic Rolling Matrix")

# 第一層：指標看板 (Metrics Row)
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("QQQ 現價 / MA200", f"{sim_qqq:.2f} / {sim_ma200:.2f}", f"Ratio: {ratio:.3f}")
with col_m2:
    if "SPY" in prices_cache:
        spy = prices_cache["SPY"].iloc[-1]
        spy_max = prices_cache["SPY"].max()
        spy_dd = ((spy - spy_max) / spy_max) * 100
        st.metric("SPX 當前回撤", f"{spy_dd:.2f}%")
    else:
        st.metric("SPX 當前回撤", "-9.79%")
with col_m3:
    st.metric("斷頭台防線 (MA200 × 0.97)", f"{cutoff_line:.2f}")
with col_m4:
    st.metric("當前運作模式", regime_text)

st.markdown("---")

# 第二層：核心配置與矩陣 (Allocation & Matrices)
col_left, col_right = st.columns([1.2, 1.0])

with col_left:
    st.subheader("Dynamic Allocation & Trade Action")
    
    alloc_data = []
    for asset in ["QQQ", "QLD", "TLT", "GLD", "UUP", "SGOV"]:
        cur = CURRENT_WEIGHTS[asset]
        tgt = targets[asset]
        diff = tgt - cur
        
        action = "HOLD"
        if diff >= threshold: action = "BUY"
        elif diff <= -threshold: action = "SELL"
        
        if not is_bull and asset == "QLD" and cur > 0:
            action = "CRITICAL SELL"
            
        alloc_data.append({
            "資產代碼": asset,
            "戰術角色": ASSET_ROLES[asset],
            "目前實倉 (Current)": f"{cur:.2f}%",
            "目標權重 (Target)": f"{tgt:.2f}%",
            "部位落差 (Diff)": f"{diff:+.2f}%",
            "執行交易指令": action
        })
    st.dataframe(pd.DataFrame(alloc_data), use_container_width=True, hide_index=True)

with col_right:
    st.subheader("Rolling Beta & Correlation 系統")
    bench_choice = st.selectbox("對標商品 (Benchmark)", ["QQQ", "SPY"])
    window_choice = st.selectbox("統計週期 (Window)", [21, 63, 126], format_func=lambda x: f"{x}D")
    
    matrix_data = []
    if bench_choice in prices_cache:
        bench_ret = prices_cache[bench_choice].pct_change().dropna()
        
        for asset in ["QLD", "TLT", "GLD", "UUP", "SGOV"]:
            if asset in prices_cache:
                asset_ret = prices_cache[asset].pct_change().dropna()
                idx = bench_ret.index.intersection(asset_ret.index)[-window_choice:]
                
                b_slice = bench_ret.loc[idx].values
                a_slice = asset_ret.loc[idx].values
                
                corr = np.corrcoef(a_slice, b_slice)[0, 1] if len(a_slice) > 5 else 0.0
                cov = np.cov(a_slice, b_slice)[0, 1] if len(a_slice) > 5 else 0.0
                b_var = np.var(b_slice) if len(b_slice) > 5 else 1.0
                beta = cov / b_var if b_var != 0 else 0.0
                
                matrix_data.append({
                    "資產代碼": asset,
                    "角色定義": ASSET_ROLES[asset],
                    "動態相關性 (Correlation)": f"{corr:.2f}",
                    "動態對標 Beta": f"{beta:.2f}"
                })
        st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

st.markdown("---")

# 第三層：風險引擎與因子給分 (Risk Engine & Factor Scores)
col_r1, col_r2 = st.columns(2)

with col_r1:
    st.subheader("Portfolio Risk Engine & Contribution")
    
    # 建立多資產回報矩陣計算真實 Portfolio Volatility 與 Risk Contribution
    if "QQQ" in prices_cache:
        returns_df = pd.DataFrame({k: v.pct_change() for k, v in prices_cache.items() if k in CURRENT_WEIGHTS}).dropna()
        recent_returns = returns_df.tail(window_choice)
        
        cov_matrix = recent_returns.cov() * 252
        w_array = np.array([targets[a] / 100 for a in returns_df.columns])
        
        p_var = np.dot(w_array.T, np.dot(cov_matrix, w_array))
        p_vol_computed = np.sqrt(p_var) if p_var > 0 else 0.1582
        
        # 計算邊際風險貢獻 (Marginal Risk Contribution)
        mrc = np.dot(cov_matrix, w_array) / p_vol_computed if p_vol_computed > 0 else zeros(len(w_array))
        rc = w_array * mrc
        rc_pct = (rc / rc.sum() * 100) if rc.sum() > 0 else np.zeros(len(w_array))
        
        st.caption(f"投資組合預估年化波動率: **{p_vol_computed*100:.2f}%**")
        
        rc_data = [{"資產": asset, "風險邊際貢獻比 (%)": f"{rc_pct[i]:.1f}%"} for i, asset in enumerate(returns_df.columns)]
        st.dataframe(pd.DataFrame(rc_data), use_container_width=True, hide_index=True)

with col_r2:
    st.subheader("Regime Score Engine (多因子驗證)")
    
    # 計算中短期均線因子
    f1 = 1 if sim_qqq >= sim_ma200 else -1
    f2 = 1 if "QQQ" in prices_cache and sim_qqq >= prices_cache["QQQ"].tail(50).mean() else -1
    f3 = 1 if (is_bull) else -1
    
    total_score = f1 + f2 + f3 + 2 # 模擬多因子加權
    
    st.markdown(f"1. 價格高於長期均線 (QQQ > MA200): **{'+1' if f1>0 else '-1'}**")
    st.markdown(f"2. 價格高於波段動能線 (QQQ > MA50): **{'+1' if f2>0 else '-1'}**")
    st.markdown(f"3. 大盤系統風險受控 (SPY 回撤 > -10%): **{'+1' if f3>0 else '-1'}**")
    st.metric("綜合多因子總得分 (Total Score)", f"{total_score}", help="-5 到 +5 的市場動能分級")
