import streamlit as st
import yfinance as yf
from fredapi import Fred
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIGURATION & SECRETS ---
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
        # A. FX & LOGIC
        usd_php = float(market_df['USDPHP=X'].iloc[-1])
        usd_inr = float(market_df['USDINR=X'].iloc[-1])
        xlf_close = market_df[XLF_TICKER].dropna()
        ma200 = xlf_close.rolling(window=200).mean()
        curr_xlf = float(xlf_close.iloc[-1])
        curr_ma200 = float(ma200.iloc[-1])
        
        # B. METRICS
        m1, m2, m3 = st.columns(3)
        m1.metric("Financials (XLF)", f"${curr_xlf:.2f}", f"{((curr_xlf/xlf_close.iloc[-6])-1)*100:+.2f}%")
        
        if spread_series is not None:
            curr_spread = float(spread_series.iloc[-1]) * 100
            m2.metric("Credit Spread", f"{curr_spread:.0f} bps")
        
        # C. ACTION BANNER
        st.divider()
        if curr_xlf < curr_ma200:
            st.warning("### ⚠️ WARNING: STRUCTURAL STRESS DETECTED")
        else:
            st.success("### ✅ STATUS: BUBBLE INTACT")

        # --- 4. CHARTS (FIXED WIDTH) ---
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("XLF Trend Analysis")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xlf_close.index, y=xlf_close, name='Price', line=dict(color='#00d4ff')))
            fig.add_trace(go.Scatter(x=ma200.index, y=ma200, name='200D MA', line=dict(dash='dash', color='red')))
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,t=10,b=10))
            # FIX: width="stretch" goes HERE
            st.plotly_chart(fig, width="stretch")
            
        with c2:
            st.subheader("Credit Fear (Trailing 90D)")
            if spread_series is not None:
                fig_spread = go.Figure(go.Scatter(x=spread_series.tail(90).index, y=spread_series.tail(90)*100, line=dict(color='#ff4b4b')))
                fig_spread.update_layout(template="plotly_dark", height=400, margin=dict(l=10,r=10,t=10,b=10))
                # FIX: width="stretch" goes HERE
                st.plotly_chart(fig_spread, width="stretch")

        # --- 5. HEDGE PERFORMANCE ---
        st.divider()
        st.subheader("🛡️ Hedge Execution: Short Financials (SEF)")
        hedge_df = market_df['SEF'].ffill()
        fig_sef = go.Figure(go.Scatter(x=hedge_df.index, y=hedge_df, name="SEF Price", line=dict(color='#ffcc00')))
        fig_sef.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10))
        # FIX: width="stretch" goes HERE
        st.plotly_chart(fig_sef, width="stretch")

        # --- 6. CURRENCY SIDEBAR ---
        st.sidebar.divider()
        amount = st.sidebar.number_input("Enter USD", value=100.0)
        st.sidebar.info(f"₱{amount * usd_php:,.2f} | ₹{amount * usd_inr:,.2f}")

except Exception as e:
    st.error(f"Dashboard Error: {e}")
