# streamlit_app.py

import streamlit as st
import pandas as pd
import sys
import os
import time

# Add the directory containing stock_insight_core.py to the Python path
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)

# Now, import functions from stock_insight_core.py
try:
    from stock_insight_core import perform_comprehensive_analysis
except ImportError as e:
    st.error(f"FATAL ERROR: Could not load 'stock_insight_core.py'. Please ensure it's in the same directory and all dependencies are installed.")
    st.exception(e) # Display the full exception for debugging
    st.stop() # Stop the app if the core module can't be loaded

# --- Streamlit App Configuration ---
st.set_page_config(layout="wide", page_title="EquityOS: AI-Powered Stock Analysis")

# --- Custom CSS for Sidebar (Dark Background) and Input Fields (White) ---
st.markdown(
    """
    <style>
    /* Target the sidebar container by its data-testid */
    section[data-testid="stSidebar"] {
        background-color: #1a1a1a; /* Very dark grey, almost black */
        color: white; /* Text color for sidebar */
    }
    /* Ensure text within markdown in sidebar is also white */
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    /* Ensure headers in sidebar are also white */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5,
    section[data-testid="stSidebar"] h6,
    section[data-testid="stSidebar"] .st-emotion-cache-10ohe8r { /* Target specific Streamlit header class if direct h-tag isn't enough */
        color: white !important;
    }
    /* Adjust expander header colors in sidebar */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        color: #f0f2f6; /* Lighter color for expander headers */
        background-color: #333333; /* Slightly lighter dark grey for expander headers */
        border-radius: 5px;
        padding: 10px;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    /* Adjust expander content text */
    section[data-testid="stSidebar"] .streamlit-expanderContent {
        color: #d1d1d1; /* A bit lighter than pure white for readability */
    }

    /* --- Input Field Styling (Ticker and Target Price) --- */
    /* Target st.text_input fields and set their background to white */
    /* This targets the actual input element */
    div.stTextInput > div > div > input {
        background-color: white !important;
        color: black !important; /* Ensure text is readable on white background */
    }
    /* This targets the overall container of the text input for consistency */
    [data-testid="stTextInput"] {
        background-color: white !important;
    }

    /* --- Button Styling (Default) --- */
    /* Removed specific background-color or color styles for buttons to make them default. */
    /* If your config.toml makes secondary buttons black, you will need to adjust that file. */

    </style>
    """,
    unsafe_allow_html=True
)


# --- Main Title ---
st.title("💡 EquityOS")

# --- Inputs moved from sidebar to main area ---
col_input1, col_input2 = st.columns([1, 1])

with col_input1:
    ticker_symbol = st.text_input(
        "Enter Stock Ticker (e.g., AAPL, GOOGL, RELIANCE.NS)",
        value="",
        key="ticker_input"
    ).upper()

with col_input2:
    target_price_input = st.text_input(
        "Enter Your Target Price (e.g., 180.00)",
        value="",
        key="target_price_input"
    )

# Validate inputs
target_price = None
input_error_message = ""

if not ticker_symbol:
    input_error_message = "Please enter a stock ticker symbol to proceed."
elif not target_price_input:
    input_error_message = "Please enter a target price to proceed."
else:
    try:
        target_price = float(target_price_input)
        if target_price <= 0:
            input_error_message = "Target price must be a positive number."
    except ValueError:
        input_error_message = "Invalid target price. Please enter a numerical value (e.g., 180.00)."

# Display error message or the button
if input_error_message:
    st.info(input_error_message)
    run_analysis_button = False # Disable button if there's an error message
else:
    # --- The "NO NOISE" button ---
    # Set to default Streamlit button appearance (not black)
    run_analysis_button = st.button("NO NOISE", use_container_width=True)


st.markdown("---") # Visual separator

# --- Main Content Area - Analysis Trigger ---
if run_analysis_button:
    # Custom loading messages for sequential display
    loading_messages = [
        f"Fetching {ticker_symbol} data from Yahoo Finance...",
        f"Retrieving recent news for {ticker_symbol} from Finnhub...",
        f"Gathering historical financial statements and calculating ratios for {ticker_symbol}...",
        f"Scanning Reddit for market pulse and discussions related to {ticker_symbol}...",
        "Sending collected data to Google Gemini for AI-powered insights...",
        "Generating interactive charts...",
        f"Compiling your comprehensive analysis for {ticker_symbol}..."
    ]

    # Use st.status if available (Streamlit >= 1.25) for a nicer progress UI
    if hasattr(st, 'status'):
        with st.status("Initiating Analysis...", expanded=True) as status_container:
            for i, msg in enumerate(loading_messages):
                st.write(msg)
                time.sleep(0.5) # Simulate processing time for each step

            results = perform_comprehensive_analysis(ticker_symbol, target_price)

            if "error" in results:
                status_container.error(f"Analysis failed: {results['error']}")
            else:
                status_container.success("Analysis complete!")
    else: # Fallback for older Streamlit versions using st.spinner
        detailed_status_message_placeholder = st.empty()
        with st.spinner("Analyzing... Please wait."):
            for i, msg in enumerate(loading_messages):
                detailed_status_message_placeholder.info(msg)
                time.sleep(0.5) # Simulate work for each step

            results = perform_comprehensive_analysis(ticker_symbol, target_price)
        detailed_status_message_placeholder.empty() # Clear detailed message after spinner is done


    if "error" in results:
        st.error(results["error"])
    else:
        st.success(f"Comprehensive analysis for {ticker_symbol} completed!")

        # --- Display Key Financial Info ---
        st.header(f"📊 Key Financial Information for {ticker_symbol}")
        col1, col2, col3 = st.columns(3)
        key_info = results.get('key_financial_info', {})
        with col1:
            st.metric("Current Price", key_info.get("Current Price (Prev Close)", "N/A"))
            st.metric("P/E Ratio", key_info.get("P/E Ratio", "N/A"))
        with col2:
            st.metric("Book Value", key_info.get("Book Value", "N/A"))
            st.metric("EPS", key_info.get("EPS", "N/A"))
        with col3:
            st.metric("Sector", key_info.get("Sector", "N/A"))
            st.metric("Industry", key_info.get("Industry", "N/A"))

        st.markdown("---")

        # --- Display Charts (Interactive) ---
        st.header("📈 Interactive Charts")
        charts = results.get('charts', {})
        if charts:
            st.subheader("Candlestick Chart")
            st.plotly_chart(charts.get('candlestick_chart'), use_container_width=True)

            st.subheader("Historical Financial Ratios")
            st.plotly_chart(charts.get('financial_ratios_chart'), use_container_width=True)

            st.subheader("Current Price vs. Target Price")
            st.plotly_chart(charts.get('price_gauge_chart'), use_container_width=True)
        else:
            st.warning("No charts generated.")

        st.markdown("---")

        # --- Display AI Analysis ---
        st.header("🧠 AI-Powered Insights")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📰 News Analysis",
            "💰 Financial Analysis",
            "👴 Warren Buffett Framework",
            "💬 Reddit Market Pulse"
        ])

        with tab1:
            st.subheader("AI News Analysis (Headlines)")
            st.markdown(results.get('ai_news_analysis', "AI news analysis not available."))

        with tab2:
            st.subheader("AI Financial Analysis (Company & Valuation)")
            st.markdown(results.get('ai_financial_analysis', "AI financial analysis not available."))

        with tab3:
            st.subheader("AI Warren Buffett Framework Assessment")
            st.markdown(results.get('ai_buffett_analysis', "AI Buffett framework analysis not available."))

        with tab4:
            st.subheader("AI Reddit Market Pulse")
            st.markdown(results.get('ai_reddit_market_pulse', "AI Reddit market pulse analysis not available."))

        st.markdown("---")

        # --- Basic Valuation Insight ---
        st.header("🎯 Basic Valuation Insight")
        basic_val = results.get('basic_valuation_insight', {})
        if basic_val:
            st.write(f"**Your Target Price:** {basic_val.get('Your Target Price', 'N/A')}")
            st.write(f"**Current Price:** {basic_val.get('Current Price', 'N/A')}")
            st.markdown(f"**Insight:** {basic_val.get('Insight', 'N/A')}")
        else:
            st.info("Basic valuation insight not available.")

# --- Sidebar Content ---
with st.sidebar:
    st.header("💡 Wisdom Corner")

    with st.expander("🧠 Behavioral Finance Tips", expanded=True):
        st.markdown("""
        * **Overconfidence Bias:** *Don't overestimate your insights.* Always consider alternative viewpoints and potential downsides to your investment decisions.
        * **Confirmation Bias:** *Actively seek opposing views.* Challenge your own beliefs by looking for information that disproves your initial assumptions.
        * **Herd Mentality:** *Think independently.* Avoid making investment decisions solely because "everyone else is doing it." Do your own thorough due diligence.
        * **Loss Aversion:** *Cut your losses decisively.* Don't hold onto losing investments hoping they'll recover, simply because you don't want to realize a loss. Be objective.
        * **Anchoring:** *Don't fixate on past prices.* Evaluate a stock based on its current fundamentals and future prospects, not just historical highs or lows you remember.
        * **Sunk Cost Fallacy:** *Past investments are irrelevant to future decisions.* Don't commit more capital to a failing investment just because you've already invested heavily.
        """)

    with st.expander("⚠️ Stock Market Risk Advice", expanded=True):
        st.markdown("""
        * **Diversify Broadly:** *Don't put all your eggs in one basket.* Spread your investments across different asset classes (stocks, bonds), industries, and geographical regions.
        * **Adopt a Long-Term View:** *Time in the market beats timing the market.* Short-term volatility is normal; focus on your long-term financial goals and stay disciplined.
        * **Invest Only Disposable Income:** *Never invest money you might need soon.* Ensure you have an adequate emergency fund before entering the market.
        * **Conduct Thorough Due Diligence:** *Research before you invest.* Understand the companies you own, their business models, financial health, and competitive landscape.
        * **Manage Emotions:** *Avoid impulsive decisions driven by fear or greed.* Stick to your predefined investment plan and avoid reacting emotionally to market swings.
        * **Understand Your Risk Tolerance:** *Know your comfort level with loss.* Tailor your investment strategy to your personal capacity and willingness to take on risk.
        """)