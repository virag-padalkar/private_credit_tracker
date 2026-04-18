import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Private Credit Bubble Monitor", layout="wide")

# Safe secret handling
try:
    FRED_API_KEY = st.secrets["FRED_API_KEY"]
except:
    st.error("Missing FRED_API_KEY in Streamlit Secrets.")
    st.stop()

XLF_TICKER = 'XLF'

# --- 2. DATA FETCHING (FIXED FOR RATE LIMITS & MULTI-INDEX) ---
@st.cache_data(ttl=3600)
def get_all_market_data(tickers):
    # Added SEF to the primary fetch list
    all_tickers = [XLF_TICKER, 'SEF'] + tickers + ['USDPHP=X', 'USDINR=X']
    
    try:
        # auto_adjust=True helps avoid some rate limit triggers on overhead
        data = yf.download(all_tickers, period='2y', auto_adjust=True)
        
        # Handle MultiIndex: If multiple tickers, yfinance returns (Attribute, Ticker)
        # We only want the price data (Close or Price)
        if isinstance(data.columns, pd.MultiIndex):
            df = data['Close'] if 'Close' in data.columns else data['Price']
        else:
            df = data
            
        # Clean weekend gaps
        df = df.ffill().dropna(how='all')
    except Exception as e:
        st.error(f"YFinance Rate Limit or Connection Error: {e}")
        return None, None
    
    spread = None
    try:
        fred = Fred(api_key=FRED_API_KEY)
        spread = fred.get_series('BAMLH0A0HYM2').dropna()
    except Exception as e:
        st.warning(f"FRED API Error: {e}")
            
    return df, spread

# --- 3. MAIN DASHBOARD ---
st.title("🚨 Private Credit Bubble & FINDX Monitor")
st.markdown(f"**Date:** April 18, 2026 | **Status:** Market Weekend | **Location:** Pasay City, PH")

# Sidebar Configuration
st.sidebar.header("⚙️ Settings")
pc_options = ['ARES', 'APO', 'BX', 'KKR', 'OWL', 'CG']
user_tickers = st.sidebar.multiselect("Track Managers", options=pc_options, default=['ARES', 'APO', 'BX'])

try:
    market_df, spread_series = get_all_market_data(user_tickers)
    
    if market_df is not None:
        # A. EXTRACT LIVE FX RATES
        usd_php = float(market_df['USDPHP=X'].iloc[-1])
        usd_inr = float(market_df['USDINR=X'].iloc[-1])

        # B. XLF LOGIC
        xlf_close = market_df[XLF_TICKER].dropna()
        ma200 = xlf_close.rolling(window=200).mean()
        curr_xlf = float(xlf_close.iloc[-1])
        curr_ma200 = float(ma200.iloc[-1])
        
        xlf_delta = ((curr_xlf / xlf_close.iloc[-6]) - 1) * 100 if len(xlf_close) > 6 else 0.0
        xlf_trigger = curr_xlf < curr_ma200

        # C. FINDX STRESS LOGIC (Drawdown %)
        pc_close = market_df[user_tickers].ffill().dropna()
        if not pc_close.empty:
            norm_prices = pc_close / pc_close.iloc[0]
            stress_val = (1 - norm_prices.mean(axis=1).iloc[-1]) * 100
            prev_week_stress = (1 - norm_prices.mean(axis=1).iloc[-6]) * 100 if len(norm_prices) > 6 else stress_val
        else:
            stress_val = 0.0
            prev_week_stress = 0.0
        
        stress_trigger = (stress_val - prev_week_stress) > 10.0

        # D. SPREAD LOGIC (Converting % to bps)
        spread_trigger = False
        curr_spread_bps = 0.0
        spread_delta = 0.0
        if spread_series is not None and not spread_series.empty:
            curr_spread_bps = float(spread_series.iloc[-1]) * 100
            prev_spread_bps = float(spread_series.iloc[-6]) * 100 if len(spread_series) > 6 else curr_spread_bps
            spread_delta = curr_spread_bps - prev_spread_bps
            spread_trigger = curr_spread_bps > 450.0

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

        # --- 6. CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("XLF Trend Analysis")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xlf_close.index, y=xlf_close, name='Price', line=dict(color='#00d4ff')))
            fig.add_trace(go.Scatter(x=ma200.index, y=ma200, name='200D MA', line=dict(dash='dash', color='red')))
            fig.update_layout(template="plotly_dark", height=400, width="stretch", margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig)
            
        with c2:
            st.subheader("Credit Fear (Trailing 90D)")
            if spread_series is not None:
                fig_spread = go.Figure(go.Scatter(x=spread_series.tail(90).index, y=spread_series.tail(90)*100, line=dict(color='#ff4b4b')))
                fig_spread.update_layout(template="plotly_dark", height=400, width="stretch", margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig_spread)
            else:
                st.info("Check FRED API Key.")

        # --- 7. HEDGE PERFORMANCE (SEF) ---
        st.divider()
        st.subheader("🛡️ Hedge Execution: Short Financials (SEF)")
        hedge_df = market_df['SEF'].ffill()
        
        fig_sef = go.Figure()
        fig_sef.add_trace(go.Scatter(x=hedge_df.index, y=hedge_df, name="SEF Price", line=dict(color='#ffcc00', width=2)))
        fig_sef.update_layout(template="plotly_dark", height=350, width="stretch", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_sef)
        st.info("💡 **Strategy:** If XLF breaks its 200D MA, look for SEF to break upward.")

        # --- 8. LIVE CURRENCY TOOL ---
        st.sidebar.divider()
        st.sidebar.subheader("💱 Live Currency Tool")
        st.sidebar.caption(f"Rates: **PHP {usd_php:.2f}** | **INR {usd_inr:.2f}**")
        amount = st.sidebar.number_input("Enter USD Amount", value=100.0)
        col_a, col_b = st.sidebar.columns(2)
        col_a.info(f"₱{amount * usd_php:,.2f}")
        col_b.info(f"₹{amount * usd_inr:,.2f}")

except Exception as e:
    st.error(f"Dashboard Update Error: {e}")
