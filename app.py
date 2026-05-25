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
st.set_page_config(
    page_title="Pure Alpha 多資產對沖策略戰情室",
    layout="wide"
)

custom_css = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #081028;
        font-family: 'Segoe UI', Arial, sans-serif;
    }

    .cyber-card {
        background: #17233a;
        border-radius: 20px;
        padding: 24px;
        box-shadow: 0 4px 25px rgba(0,0,0,0.35);
        border: 1px solid #24334d;
        margin-bottom: 20px;
        color: #e2e8f0;
        height: 100%;
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

    .metric-row:last-child {
        border-bottom: none;
    }

    .m-label {
        color: #cbd5e1;
        font-size: 14px;
    }

    .m-value {
        color: white;
        font-weight: bold;
        font-family: monospace;
        font-size: 16px;
    }

    .c-green { color: #22c55e; }
    .c-red { color: #ef4444; }
    .c-yellow { color: #facc15; }

    .cyber-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 5px;
    }

    .cyber-table th,
    .cyber-table td {
        padding: 14px 10px;
        text-align: center;
        border-bottom: 1px solid #24334d;
        font-size: 16px;
    }

    .cyber-table th {
        background: #1e293b;
        color: #94a3b8;
        font-weight: 600;
        font-size: 15px;
    }

    .cyber-table td {
        color: #e2e8f0;
    }

    .badge-action {
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 14px;
    }

    .badge-buy {
        background: rgba(34,197,94,0.2);
        color: #22c55e;
    }

    .badge-sell {
        background: rgba(239,68,68,0.2);
        color: #ef4444;
    }

    .badge-hold {
        background: rgba(148,163,184,0.15);
        color: #94a3b8;
    }

    .badge-critical {
        background: #ef4444;
        color: white;
    }

    .regime-box {
        margin-top:20px;
        padding:15px;
        border-radius:12px;
        text-align:center;
        font-size:18px;
        font-weight:bold;
    }

    .bull-box {
        background: rgba(34,197,94,0.15);
        border: 1px solid #22c55e;
        color: #22c55e;
    }

    .bear-box {
        background: rgba(239,68,68,0.15);
        border: 1px solid #ef4444;
        color: #ef4444;
    }

    .dip-box {
        background: rgba(56,189,248,0.15);
        border: 1px solid #38bdf8;
        color: #38bdf8;
    }

    .version-footer {
        text-align: center;
        color: #64748b;
        font-size: 12px;
        margin-top: 50px;
        padding: 20px 0;
        border-top: 1px solid #24334d;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# Robust Utility Functions
# ==========================================
def unique_cols(cols):
    return list(dict.fromkeys(cols))

# ==========================================
# 1. 側邊欄：動態資產代碼自訂
# ==========================================
st.sidebar.markdown(
    "<h2 style='color:#38bdf8;'>動態參數調控</h2>",
    unsafe_allow_html=True
)

with st.sidebar.expander(
    "⚙️ 自訂資產代碼 (ETF Tickers)",
    expanded=False
):

    tk_core = st.text_input(
        "核心成長引擎 (預設 QQQ)",
        "QQQ"
    ).upper()

    tk_lev = st.text_input(
        "動能槓桿放大 (預設 QLD)",
        "QLD"
    ).upper()

    tk_bond = st.text_input(
        "長債負相關避險 (預設 TLT)",
        "TLT"
    ).upper()

    tk_gold = st.text_input(
        "抗通膨終極防禦 (預設 GLD)",
        "GLD"
    ).upper()

    tk_usd = st.text_input(
        "美元流動性避險 (預設 UUP)",
        "UUP"
    ).upper()

    tk_safe = st.text_input(
        "流動性海綿池 (預設 SGOV)",
        "SGOV"
    ).upper()

PORTFOLIO_ASSETS = [
    tk_core,
    tk_lev,
    tk_bond,
    tk_gold,
    tk_usd,
    tk_safe
]

CURRENT_WEIGHTS = {
    tk_core: 28.71,
    tk_lev: 35.66,
    tk_bond: 7.80,
    tk_gold: 7.65,
    tk_usd: 8.00,
    tk_safe: 12.18
}

BULL_BASE = {
    tk_core: 26.0,
    tk_lev: 32.0,
    tk_bond: 7.0,
    tk_gold: 7.0,
    tk_usd: 9.0
}

BEAR_BASE = {
    tk_core: 20.0,
    tk_lev: 20.0,
    tk_bond: 10.0,
    tk_gold: 10.0,
    tk_usd: 20.0
}

ASSET_ROLES = {
    tk_core: "核心成長引擎",
    tk_lev: "動能槓桿放大",
    tk_bond: "長債負相關避險",
    tk_gold: "抗通膨終極防禦",
    tk_usd: "美元流動性避險",
    tk_safe: "流動性海綿池"
}

CHART_COLORS = {
    tk_core: "#38bdf8",
    tk_lev: "#818cf8",
    tk_bond: "#f472b6",
    tk_gold: "#facc15",
    tk_usd: "#ef4444",
    tk_safe: "#94a3b8"
}

# ==========================================
# 2. 核心資料下載引擎
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_data(tickers_tuple):

    data_dict = {}

    for t in tickers_tuple:

        try:

            for _ in range(3):

                df = yf.download(
                    t,
                    period="max",
                    progress=False
                )

                if not df.empty and 'Close' in df.columns:

                    data_dict[t] = (
                        df['Close'].iloc[:, 0]
                        if isinstance(df['Close'], pd.DataFrame)
                        else df['Close']
                    )

                    if t == "SPY":

                        data_dict["SPY_High"] = (
                            df['High'].iloc[:, 0]
                            if isinstance(df['High'], pd.DataFrame)
                            else df['High']
                        )

                        data_dict["SPY_Low"] = (
                            df['Low'].iloc[:, 0]
                            if isinstance(df['Low'], pd.DataFrame)
                            else df['Low']
                        )

                    break

                time.sleep(1)

        except Exception:
            pass

    for _ in range(3):

        try:

            spx_df = yf.download(
                "^GSPC",
                period="max",
                progress=False
            )

            if not spx_df.empty and 'Close' in spx_df.columns:

                data_dict["^GSPC"] = (
                    spx_df['Close'].iloc[:, 0]
                    if isinstance(spx_df['Close'], pd.DataFrame)
                    else spx_df['Close']
                )

                data_dict["SPX_High"] = (
                    spx_df['High'].iloc[:, 0]
                    if isinstance(spx_df['High'], pd.DataFrame)
                    else spx_df['High']
                )

                data_dict["SPX_Low"] = (
                    spx_df['Low'].iloc[:, 0]
                    if isinstance(spx_df['Low'], pd.DataFrame)
                    else spx_df['Low']
                )

                break

        except Exception:
            time.sleep(1)

    if data_dict:
        return pd.concat(data_dict, axis=1)

    return pd.DataFrame()

fetch_list = tuple(set(PORTFOLIO_ASSETS + ["SPY"]))

with st.spinner('正在從 Yahoo Finance 同步長期歷史市場數據...'):
    raw_df_all = load_data(fetch_list)

missing_assets = [
    a for a in PORTFOLIO_ASSETS
    if a not in raw_df_all.columns
]

if raw_df_all.empty:
    st.error("🚨 無法連接至 Yahoo Finance 獲取任何市場數據")
    st.stop()

if tk_core not in raw_df_all.columns:
    st.error(f"🚨 核心標的 '{tk_core}' 下載失敗")
    st.stop()

spx_col = '^GSPC' if '^GSPC' in raw_df_all.columns else 'SPY'

if spx_col == '^GSPC':

    h_col = 'SPX_High'
    l_col = 'SPX_Low'

else:

    h_col = 'SPY_High'
    l_col = 'SPY_Low'

AVAILABLE_ASSETS = [
    c for c in PORTFOLIO_ASSETS
    if c in raw_df_all.columns
]

inception_dates = raw_df_all.apply(lambda x: x.first_valid_index())

df_all = raw_df_all.ffill().bfill()

# ==========================================
# 3. 滑桿參數
# ==========================================
latest_core = float(df_all[tk_core].iloc[-1])

computed_ma200 = (
    float(df_all[tk_core].rolling(200).mean().iloc[-1])
    if len(df_all) >= 200
    else latest_core
)

sim_core = st.sidebar.slider(
    f"{tk_core} 模擬/現價",
    100.0,
    900.0,
    latest_core,
    step=0.01
)

sim_ma200 = st.sidebar.slider(
    f"{tk_core} MA200 基準線",
    100.0,
    800.0,
    computed_ma200,
    step=0.01
)

k_value = st.sidebar.slider(
    "動態縮放 K 值",
    0.500,
    1.500,
    1.137,
    step=0.001
)

threshold = st.sidebar.slider(
    "最小換倉門檻 (%)",
    0.5,
    5.0,
    2.0,
    step=0.1
)

st.sidebar.markdown(
    "<h3 style='color:#facc15;'>左側抄底門檻設定</h3>",
    unsafe_allow_html=True
)

dip_lv1 = st.sidebar.slider(
    "Lv1 抄底門檻 (%)",
    10.0,
    25.0,
    19.0,
    step=0.1
)

dip_lv2 = st.sidebar.slider(
    "Lv2 恐慌門檻 (%)",
    20.0,
    40.0,
    30.0,
    step=0.1
)

bench_options = [tk_core, "SPY"]

if "^GSPC" in df_all.columns:
    bench_options.append("^GSPC")

bench_options = unique_cols(bench_options)

bench_choice = st.sidebar.selectbox(
    "對標基準",
    bench_options,
    index=0
)

window_choice = st.sidebar.selectbox(
    "滾動週期",
    [21, 63, 126],
    index=0
)

dip_lv1_frac = dip_lv1 / 100.0
dip_lv2_frac = dip_lv2 / 100.0

# ==========================================
# 4. 狀態機
# ==========================================
df_all['MA200'] = df_all[tk_core].rolling(200).mean()

df_all['SPX_Max'] = df_all[h_col].cummax()

df_all['SPX_DD'] = (
    df_all[l_col] / df_all['SPX_Max'] - 1
)

regime_states = []
current_state = 1

qqq_vals = df_all[tk_core].values
ma200_vals = df_all['MA200'].values
spx_dd_vals = df_all['SPX_DD'].values

for i in range(len(df_all)):

    q = qqq_vals[i]
    ma = ma200_vals[i]
    spx_dd = spx_dd_vals[i]

    if pd.isna(ma):
        regime_states.append(1)
        continue

    if q >= ma * 1.04:
        current_state = 1

    elif spx_dd <= -dip_lv2_frac:
        current_state = 30

    elif spx_dd <= -dip_lv1_frac and current_state != 30:
        current_state = 19

    elif current_state == 1 and q < ma * 0.97:
        current_state = 0

    regime_states.append(current_state)

df_all['Regime'] = regime_states

# ==========================================
# 5. 目標權重
# ==========================================
mult_core_lev = k_value
mult_bond_gold = 1.0 + (k_value - 1) * 0.525
mult_usd = 2.0 - k_value

tgt_weights_df = pd.DataFrame(index=df_all.index)

tgt_weights_df[tk_core] = np.where(
    df_all['Regime'] == 0,
    BEAR_BASE[tk_core]/100.0,
    (BULL_BASE[tk_core]/100.0) * mult_core_lev
)

tgt_weights_df[tk_bond] = np.where(
    df_all['Regime'] == 0,
    BEAR_BASE[tk_bond]/100.0,
    (BULL_BASE[tk_bond]/100.0) * mult_bond_gold
)

tgt_weights_df[tk_gold] = np.where(
    df_all['Regime'] == 0,
    BEAR_BASE[tk_gold]/100.0,
    (BULL_BASE[tk_gold]/100.0) * mult_bond_gold
)

tgt_weights_df[tk_usd] = np.where(
    df_all['Regime'] == 0,
    BEAR_BASE[tk_usd]/100.0,
    (BULL_BASE[tk_usd]/100.0) * mult_usd
)

tgt_weights_df[tk_lev] = 0.0

tgt_weights_df.loc[
    df_all['Regime'] == 1,
    tk_lev
] = (BULL_BASE[tk_lev]/100.0) * mult_core_lev

tgt_weights_df.loc[
    df_all['Regime'] == 19,
    tk_lev
] = 0.15 * mult_core_lev

tgt_weights_df.loc[
    df_all['Regime'] == 30,
    tk_lev
] = 0.25 * mult_core_lev

tgt_weights_df[tk_safe] = np.maximum(
    0,
    1.0 - tgt_weights_df[
        [tk_core, tk_lev, tk_bond, tk_gold, tk_usd]
    ].sum(axis=1)
)

targets = (
    tgt_weights_df.loc[df_all.index[-1]] * 100
).to_dict()

# ==========================================
# 6. Rolling Beta Engine (FIXED)
# ==========================================
st.markdown(
    "<h1 style='color:white;'>Pure Alpha 多資產對沖策略戰情室</h1>",
    unsafe_allow_html=True
)

col_pie, col_beta = st.columns([1, 2.2])

with col_pie:

    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=AVAILABLE_ASSETS,
                values=[
                    CURRENT_WEIGHTS.get(a, 0)
                    for a in AVAILABLE_ASSETS
                ],
                hole=.45
            )
        ]
    )

    fig_pie.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=320
    )

    st.plotly_chart(fig_pie, use_container_width=True)

with col_beta:

    st.markdown(
        f"<h2 style='color:#38bdf8;'>動態 Beta 趨勢</h2>",
        unsafe_allow_html=True
    )

    if (
        len(AVAILABLE_ASSETS) > 0
        and bench_choice in df_all.columns
    ):

        try:

            # =====================================
            # 修正 duplicated columns 問題
            # =====================================
            ret_cols = unique_cols(
                AVAILABLE_ASSETS + [bench_choice]
            )

            ret_all = (
                df_all[ret_cols]
                .pct_change()
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
            )

            # =====================================
            # Robust Rolling Beta
            # =====================================
            roll_beta = pd.DataFrame(
                index=ret_all.index
            )

            bench_var = (
                ret_all[bench_choice]
                .rolling(window_choice)
                .var()
            )

            for asset in AVAILABLE_ASSETS:

                cov = (
                    ret_all[asset]
                    .rolling(window_choice)
                    .cov(ret_all[bench_choice])
                )

                beta_series = cov / bench_var

                roll_beta[asset] = beta_series

            roll_beta = (
                roll_beta
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
                .tail(504)
            )

            fig_beta = go.Figure()

            for asset in AVAILABLE_ASSETS:

                fig_beta.add_trace(
                    go.Scatter(
                        x=roll_beta.index,
                        y=roll_beta[asset],
                        mode='lines',
                        name=asset,
                        line=dict(
                            color=CHART_COLORS.get(asset, "#94a3b8"),
                            width=1.5,
                            dash='dot'
                        )
                    )
                )

            # =====================================
            # Dynamic Portfolio Beta
            # =====================================
            w_hist_aligned = (
                tgt_weights_df
                .loc[roll_beta.index, AVAILABLE_ASSETS]
                .fillna(0)
            )

            port_beta_dynamic = (
                roll_beta[AVAILABLE_ASSETS]
                * w_hist_aligned
            ).sum(axis=1)

            fig_beta.add_trace(
                go.Scatter(
                    x=port_beta_dynamic.index,
                    y=port_beta_dynamic,
                    mode='lines',
                    name='策略組合',
                    line=dict(
                        color='#22c55e',
                        width=3.5
                    )
                )
            )

            fig_beta.add_hline(
                y=0,
                line_dash="dash",
                line_color="gray"
            )

            fig_beta.add_hline(
                y=1,
                line_dash="dot",
                line_color="#facc15"
            )

            fig_beta.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=20, t=10, b=10),
                height=320,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                yaxis_title="Rolling Beta",
                xaxis_title="Date"
            )

            st.plotly_chart(
                fig_beta,
                use_container_width=True
            )

        except Exception as e:

            st.error(
                f"Rolling Beta Engine 發生錯誤：{e}"
            )

    else:

        st.warning(
            "無法計算 Rolling Beta"
        )

# ==========================================
# Footer
# ==========================================
st.markdown(
    '<div class="version-footer">Powered by Pure Alpha Quantitative Engine | Version 8.9 Robust Build</div>',
    unsafe_allow_html=True
)
