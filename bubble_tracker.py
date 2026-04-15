import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Private Credit Bubble Monitor", layout="wide")

XLF_TICKER = 'XLF'

# --- 2. SIDEBAR INPUTS ---
st.sidebar.header("⚙️ Settings")

# Key input moves here. It remains blank until the user types it in.
user_fred_key = st.sidebar.text_input(
    "Enter FRED API Key", 
    type="password", 
    help="Get a free key at fred.stlouisfed.org"
)

default_pc = ['ARES', 'APO', 'BX']
user_tickers = st.sidebar.multiselect("Track Managers", options=['ARES', 'APO', 'BX', 'KKR', 'OWL', 'CG'], default=default_pc)

# --- 3. DATA FETCHING FUNCTION ---
@st.cache_data(ttl=3600)
def get_all_market_data(tickers, api_key):
    all_tickers = [XLF_TICKER] + tickers + ['USDPHP=X', 'USDINR=X']
    data = yf.download(all_tickers, period='2y') 
    
    spread = None
    if api_key: # Only attempts to fetch if a key is provided
        try:
            fred = Fred(api_key=api_key)
            spread = fred.get_series('BAMLH0A0HYM2').dropna()
        except Exception as e:
            st.error(f"FRED API Error: {e}")
            
    return data, spread

# --- 4. MAIN DASHBOARD LOGIC ---
st.title("🚨 Private Credit Bubble & FINDX Monitor")

if not user_fred_key:
    st.info("👈 Enter your FRED API Key in the sidebar to activate the Credit Fear Gauge.")

try:
    market_df, spread_series = get_all_market_data(user_tickers)

    # A. EXTRACT LIVE FX RATES
    usd_php = float(market_df['Close']['USDPHP=X'].dropna().iloc[-1])
    usd_inr = float(market_df['Close']['USDINR=X'].dropna().iloc[-1])

    # B. XLF LOGIC
    xlf_close = market_df['Close'][XLF_TICKER].dropna()
    ma200 = xlf_close.rolling(window=200).mean()
    curr_xlf = float(xlf_close.iloc[-1])
    curr_ma200 = float(ma200.iloc[-1])
    
    # Calculate XLF Delta %
    xlf_delta = ((curr_xlf / xlf_close.iloc[-6]) - 1) * 100 if len(xlf_close) > 6 else 0.0
    xlf_trigger = curr_xlf < curr_ma200

    # C. FINDX STRESS LOGIC (Drawdown %)
    pc_close = market_df['Close'][user_tickers].ffill().dropna()
    if len(pc_close) > 6:
        # Calculate drawdown from the start of the 2y period
        norm_prices = pc_close / pc_close.iloc[0]
        stress_val = (1 - norm_prices.mean(axis=1).iloc[-1]) * 100
        prev_week_stress = (1 - norm_prices.mean(axis=1).iloc[-6]) * 100
    else:
        stress_val = 0.0
        prev_week_stress = 0.0
    
    stress_trigger = (stress_val - prev_week_stress) > 10.0

    # D. SPREAD LOGIC (Converting % to bps)
    spread_trigger = False
    curr_spread_bps = 0.0
    spread_delta = 0.0
    if spread_series is not None and not spread_series.empty:
        # FRED returns 2.95 for 2.95%, which is 295 bps
        curr_spread_bps = float(spread_series.iloc[-1]) * 100
        prev_spread_bps = float(spread_series.iloc[-6]) * 100
        spread_delta = curr_spread_bps - prev_spread_bps
        spread_trigger = curr_spread_bps > 450.0 or (curr_spread_bps / prev_spread_bps > 1.20)

    # --- 4. TOP METRICS ---
    m1, m2, m3 = st.columns(3)
    
    m1.metric("Financials (XLF)", f"${curr_xlf:.2f}", f"{xlf_delta:+.2f}%", delta_color="inverse")
    m1.caption(f"200D MA: **${curr_ma200:.2f}**")
    
    m2.metric("Credit Spread", f"{curr_spread_bps:.0f} bps", f"{spread_delta:+.0f} bps", delta_color="inverse")
    m2.caption("Target: < 450 bps")
    
    m3.metric("FINDX Stress %", f"{stress_val:.2f}%", f"{stress_val - prev_week_stress:+.2f}%", delta_color="inverse")
    m3.caption("Weekly Δ Target: < 10%")

    # --- 5. ACTION BANNER ---
    st.divider()
    active_triggers = sum([xlf_trigger, spread_trigger, stress_trigger])
    
    if active_triggers >= 2:
        st.error(f"### ⚡ SYSTEMIC SHORT SIGNAL: {active_triggers}/3 Triggers Fired")
    elif active_triggers == 1:
        st.warning("### ⚠️ WARNING: STRUCTURAL STRESS DETECTED")
    else:
        st.success("### ✅ STATUS: BUBBLE INTACT")

    # Legend
    with st.expander("📚 View Trigger Legend & Logic"):
        st.markdown("""
        | Trigger | Logic | Critical Threshold |
        | :--- | :--- | :--- |
        | **Trend Pivot** | XLF Price < 200-Day MA | Confirms the long-term trend reversal. |
        | **Credit Panic** | Spread > 450bps or +20%/week | Institutional rush for default insurance. |
        | **Liquidity Crack** | Stress Index +10% in a week | Major sell-off in Private Credit Managers. |
        """)

    # --- 6. CHARTS ---
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("XLF Trend Analysis")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=xlf_close.index, y=xlf_close, name='Price'))
        fig.add_trace(go.Scatter(x=ma200.index, y=ma200, name='200D MA', line=dict(dash='dash')))
        fig.update_layout(template="plotly_dark", margin=dict(l=20,r=20,t=20,b=20))
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("Credit Fear (Trailing 90D)")
        if spread_series is not None:
            # Re-scale for the chart display
            st.line_chart(spread_series.tail(90) * 100)
        else:
            st.info("Check FRED API Key.")

    # --- 7. LIVE CURRENCY TOOL ---
    st.sidebar.divider()
    st.sidebar.subheader("💱 Live Currency Tool")
    st.sidebar.caption(f"Rates: **PHP {usd_php:.2f}** | **INR {usd_inr:.2f}**")
    
    amount = st.sidebar.number_input("Enter USD Amount", value=100.0)
    col_a, col_b = st.sidebar.columns(2)
    col_a.info(f"₱{amount * usd_php:,.2f}")
    col_b.info(f"₹{amount * usd_inr:,.2f}")

except Exception as e:
    st.error(f"Dashboard Update Error: {e}")
