import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Private Credit Bubble Tracker", layout="wide")
FRED_API_KEY = 'd513e8c5050452fc2c895cb81aec41ee' # Replace with your key
fred = Fred(api_key=FRED_API_KEY)

# Conversion Rates (April 2026)
USD_TO_PHP = 59
USD_TO_INR = 93

# Tickers
XLF_TICKER = 'XLF'
PC_MANAGERS = ['ARES', 'APO', 'BX']

# --- DATA FETCHING ---
@st.cache_data(ttl=3600)
def get_data():
    # Step 1: XLF Data
    xlf = yf.download(XLF_TICKER, period='1y')
    
    # Step 2: Credit Spread (FRED)
    spread = fred.get_series('BAMLH0A0HYM2')
    
    # Step 3: PC Managers Equity
    pc_equity = yf.download(PC_MANAGERS, period='1y')['Close']
    
    return xlf, spread, pc_equity

# --- UI LAYOUT ---
st.title("🚨 Private Credit Bubble & FINDX Monitor")
st.markdown(f"**Date:** April 14, 2026 | **Location:** Pasay City, PH")
st.divider()

try:
    xlf_df, spread_series, pc_df = get_data()

    # --- ROBUST DATA SELECTION ---
    # yfinance sometimes returns a MultiIndex. This ensures we get the single 'Close' column.
    if isinstance(xlf_df.columns, pd.MultiIndex):
        xlf_close_series = xlf_df['Close'][XLF_TICKER]
    else:
        xlf_close_series = xlf_df['Close']

    # --- CALCULATIONS ---
    # Step 1: XLF MA Analysis
    ma200_series = xlf_close_series.rolling(window=200).mean()
    
    # We use .item() to ensure we are comparing single float values, not Series
    current_xlf = float(xlf_close_series.iloc[-1])
    ma200_xlf = float(ma200_series.iloc[-1])
    
    xlf_status = "CRACKED" if current_xlf < ma200_xlf else "INTACT"

    # Step 2: Spread Analysis (FRED data is usually a simple Series)
    current_spread = float(spread_series.iloc[-1])
    prev_5d_spread = float(spread_series.iloc[-6])
    spread_change = ((current_spread - prev_5d_spread) / prev_5d_spread) * 100
    spread_status = "SPIKING" if spread_change >= 20 else "STABLE"

    # --- TOP METRICS ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Use inverse delta if price is below MA (Red is bad for the sector, good for our short)
        st.metric("XLF vs 200-Day MA", f"${current_xlf:.2f}", 
                  f"{((current_xlf/ma200_xlf)-1)*100:.2f}%", delta_color="inverse")
        st.caption(f"Status: **Trend {xlf_status}**")

    with col2:
        st.metric("FRED HY Spread", f"{current_spread:.2f} bps", f"{spread_change:+.2f}%", delta_color="inverse")
        st.caption(f"Status: **Credit {spread_status}**")

    with col3:
        # Handling MultiIndex for Private Credit Managers too
        if isinstance(pc_df.columns, pd.MultiIndex):
            pc_close = pc_df['Close']
        else:
            pc_close = pc_df
            
        avg_pc_change = pc_close.pct_change(periods=5).iloc[-1].mean() * 100
        st.metric("PC Manager Equity (5D)", "Avg Stress", f"{avg_pc_change:+.2f}%", delta_color="inverse")
        st.caption("Ares, Apollo, Blackstone")

    # --- STRATEGY ACTION BOX ---
    st.divider()
    if xlf_status == "CRACKED" and spread_status == "SPIKING":
        st.error("### ⚠️ ACTION: SELL/SHORT SIGNAL TRIGGERED")
        st.write("Both technical and credit signals confirm the bubble is deflating. Consider entry into **SEF**.")
    elif xlf_status == "CRACKED" or spread_status == "SPIKING":
        st.warning("### ⚠️ WARNING: SYSTEM STRESS DETECTED")
        st.write("One of two major triggers has fired. Prepare 'Dry Powder' (Cash/SGOV).")
    else:
        st.success("### ✅ STATUS: BUBBLE INTACT")
        st.write("Market remains above key support levels. Monitoring FINDX for movement.")

# --- VISUALIZATIONS ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("XLF Trend Analysis")
        fig = go.Figure()
        
        # We use the xlf_close_series and ma200_series variables we defined earlier
        fig.add_trace(go.Scatter(x=xlf_close_series.index, y=xlf_close_series, name='XLF Price'))
        fig.add_trace(go.Scatter(x=ma200_series.index, y=ma200_series, name='200D MA', line=dict(dash='dash')))
        
        fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Credit Spread (Fear Gauge)")
        # FRED data is a simple series, so this remains direct
        st.line_chart(spread_series.tail(90))
        st.caption("Trailing 90 days of ICE BofA High Yield Spread")
        
        # --- CURRENCY TOOL (In Sidebar) ---
    st.sidebar.header("Currency Converter")
    usd_val = st.sidebar.number_input("Enter USD Amount", value=current_xlf)
    st.sidebar.write(f"**PHP:** ₱{usd_val * USD_TO_PHP:,.2f}")
    st.sidebar.write(f"**INR:** ₹{usd_val * USD_TO_INR:,.2f}")

except Exception as e:
    st.error(f"Dashboard Error: {e}")
    st.info("Check your FRED API key or internet connection.")
