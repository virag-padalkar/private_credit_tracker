# private_credit_tracker
A personal macroeconomic dashboard using Python and Streamlit to track credit market health and interest rate benchmarks. The program will visualize specific FRED data series, such as high-yield credit spreads, to analyze their correlation with financial sector volatility for personal research and potential future investments. 

Key Features
Trend Pivot Detection: Tracks the XLF (S&P Financial Select Sector) against its 200-day Moving Average to identify long-term trend reversals.

Credit Fear Gauge: Integrates with the FRED API to monitor the ICE BofA High Yield Spread as a proxy for private credit insurance costs.

Sector Stress Monitoring: Real-time equity tracking for the "Big Three" private credit managers: Ares (ARES), Apollo (APO), and Blackstone (BX).

Integrated Action Logic: A dynamic alert system that signals when to shift to "Dry Powder" (Cash) or execute a hedge via inverse ETFs like SEF.

The Macro Thesis
As the "Maturity Wall" of 2026 approaches, mid-market companies face a critical refinancing period at significantly higher interest rates. This dashboard identifies the specific "cracks" in the financial system that mirror the early stages of the 2008 crisis, focusing on the shift of risk from traditional banks to "Shadow Banks."

Technical Stack
Language: Python 3.x

Framework: Streamlit

Data Sources: Yahoo Finance (yfinance), St. Louis Fed (FRED API)

Visualization: Plotly Graph Objects

Getting Started
Obtain a free API key from FRED.

Input the key into the application sidebar.

Monitor the Action Signal banner for high-conviction entry points.

Disclaimer: This tool is for educational and economic research purposes only. It does not constitute financial advice. Inverse ETFs (like SEF) carry significant risk and are not intended for long-term holding.

Final Deployment Tip
Once you are on the Streamlit deployment page:

Repository: Select your bubble-tracker-repo.

Main file path: Ensure it says bubble_tracker.py.

URL: You can customize the URL to something like private-credit-monitor-2026.streamlit.app.

Your dashboard is now ready for the world. Good luck with the "Maturity Wall" watch!
