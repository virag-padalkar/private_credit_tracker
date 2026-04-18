import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Private Credit Bubble Monitor", layout="wide")

try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except:
    st.error("Missing FRED_API_KEY in Streamlit Secrets.")
    st.stop()

XLF_TICKER = 'XLF'

# --- 2. DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_all_market_data(tickers):
    all_tickers = [XLF_TICKER, 'SEF'] + tickers + ['USDPHP=X', 'USDINR=X']
    try:
        data = yf.download(all_tickers, period='2y', auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'] if 'Close' in data.columns else data['Price']
        else:
            df = data
        df = df.ffill().dropna(how='all')
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return None, None
    
    spread = None
    try:
        fred = Fred(api_key=FRED_API_KEY)
        spread = fred.get_series('BAMLH0A0HYM2').dropna()
    except:
        pass
    return df, spread

# --- 3. MAIN DASHBOARD ---
st.title("🚨 Private Credit Bubble & FINDX Monitor")
st.sidebar.header("⚙️ Settings")
pc_options = ['ARES', 'APO', 'BX', 'KKR', 'OWL', 'CG']
user_tickers = st.sidebar.multiselect("Track Managers", options=pc_options, default=['ARES', 'APO', 'BX'])

try:
    market_df, spread_series = get_all_market_data(user_tickers)
    
    if market_df is not None:
        # --- A. CALCULATIONS ---
        usd_php = float(market_df['USDPHP=X'].iloc[-1])
        usd_inr = float(market_df['USDINR=X'].iloc[-1])
        
        xlf_close = market_df[XLF_TICKER].dropna()
        ma200 = xlf_close.rolling(window=200).mean()
        curr_xlf = float(xlf_close.iloc[-1])
        curr_ma200 = float(ma200.iloc[-1])
        xlf_trigger = curr_xlf < curr_ma200
        
        spread_trigger = False
        curr_spread_bps = 0.0
        if spread_series is not None and not spread_series.empty:
            curr_spread_bps = float(spread_series.iloc[-1]) * 100
            spread_trigger = curr_spread_bps > 450.0

        pc_close = market_df[user_tickers].ffill().dropna()
        stress_val, stress_delta = 0.0, 0.0
        stress_trigger = False
        if not pc_close.empty:
            norm_prices = pc_close / pc_close.iloc[0]
            stress_val = (1 - norm_prices.mean(axis=1).iloc[-1]) * 100
            prev_week_stress = (1 - norm_prices.mean(axis=1).iloc[-6]) * 100 if len(norm_prices) > 6 else stress_val
            stress_delta = stress_val - prev_week_stress
            stress_trigger = stress_delta > 10.0

        # --- B. TOP METRICS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Financials (XLF)", f"${curr_xlf:.2f}", f"{((curr_xlf/xlf_close.iloc[-6])-1)*100:+.2f}%")
        m1.caption(f"200D MA: **${curr_ma200:.2f}**")
        
        if spread_series is not None:
            m2.metric("Credit Spread", f"{curr_spread_bps:.0f} bps")
            m2.caption("Threshold: 450 bps")
        
        m3.metric("FINDX Stress %", f"{stress_val:.2f}%", f"{stress_delta:+.2f}%", delta_color="inverse")
        m3.caption("Weekly Δ Target: < 10%")

        # --- C. STATUS UPDATE ---
        st.divider()
        active_triggers = sum([xlf_trigger, spread_trigger, stress_trigger])
        
        if active_triggers >= 2:
            st.error(f"### 🔥 SYSTEMIC SHORT SIGNAL ({active_triggers}/3 Triggers Active)")
        elif active_triggers == 1:
            st.warning(f"### ⚠️ WARNING: STRUCTURAL STRESS DETECTED ({active_triggers}/3 Triggers Active)")
        else:
            st.success(f"### ✅ STATUS: BUBBLE INTACT ({active_triggers}/3 Triggers Active)")

        # --- D. ACTION MATRIX ---
        with st.expander("📚 Institutional Action Matrix & Trigger Legend", expanded=False):
            st.markdown("""
| Active Triggers | Market Regime | Portfolio Action |
| :---: | :--- | :--- |
| **0** | ✅ **Expansion** | Risk-on. Leverage is safe. |
| **1** | ⚠️ **Warning** | Tighten stops. Monitor manager outflows. |
| **2** | ⚡ **Unwind** | **Short Signal.** Raise cash; Buy SEF. |
| **3** | 🔥 **Collapse** | Liquidation event. Full defensive posture. |

**Trigger Definitions:**
1. **XLF < 200D MA:** Trend reversal from accumulation to distribution.
2. **Spread > 450bps:** Lenders demanding high premiums; credit freeze risk.
3. **Stress Δ > 10%:** Sharp sell-off in Private Credit managers (FINDX).
            """)

        # --- E. CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("XLF Trend Analysis")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xlf_close.index, y=xlf_close, name='Price', line=dict(color='#00d4ff')))
            fig.add_trace(go.Scatter(x=ma200.index, y=ma200, name='200D MA', line=dict(dash='dash', color='red')))
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig, width="stretch")
            
        with c2:
            st.subheader("Credit Fear (Trailing 90D)")
            if spread_series is not None:
                fig_spread = go.Figure(go.Scatter(x=spread_series.tail(90).index, y=spread_series.tail(90)*100, line=dict(color='#ff4b4b')))
                fig_spread.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig_spread, width="stretch")

        # --- F. HEDGE PERFORMANCE ---
        st.divider()
        st.subheader("🛡️ Hedge Execution: Short Financials (SEF)")
        hedge_df = market_df['SEF'].ffill()
        fig_sef = go.Figure(go.Scatter(x=hedge_df.index, y=hedge_df, name="SEF Price", line=dict(color='#ffcc00')))
        fig_sef.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_sef, width="stretch")

        # --- G. CURRENCY TOOL ---
        st.sidebar.divider()
        st.sidebar.caption(f"PHP: {usd_php:.2f} | INR: {usd_inr:.2f}")
        amount = st.sidebar.number_input("Enter USD", value=100.0)
        st.sidebar.info(f"₱{amount * usd_php:,.2f} | ₹{amount * usd_inr:,.2f}")

except Exception as e:
    st.error(f"Logic Processing Error: {e}")
