import streamlit as st
import stock_insight_core
import os # Import os module for path manipulation
import pandas as pd # Import pandas for DataFrame display

# Set page configuration for better aesthetics
# The page_title appears in the browser tab, while st.title is the main visible title.
st.set_page_config(layout="wide", page_title="Equity OS - Elite Stock Insights AI")

# --- Define the directory for charts relative to streamlit_app.py ---
current_script_dir = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(current_script_dir, "charts")

# Ensure the charts directory exists
# This line will create the 'charts' folder if it doesn't exist.
# If it does exist, 'exist_ok=True' prevents an error.
os.makedirs(CHARTS_DIR, exist_ok=True)
print(f"Ensured charts directory exists at: {CHARTS_DIR}")

# --- Streamlit UI ---
st.title("💡 Equity OS") # Main visible title - changed from "Elite Stock Insights AI"
st.markdown("Enter a stock ticker symbol and an optional target price to get comprehensive AI-driven analysis, news, and financial data.")

# Input fields for ticker and target price
col1, col2 = st.columns(2)
with col1:
    ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, GOOGL, RELIANCE.NS for Indian stocks)", "").strip().upper()
with col2:
    target_price_input = st.text_input("Enter Your Target Price (Optional, e.g., 180.00)", "").strip()

# Initialize analysis_outputs and chart_paths in session state
# This helps retain data when Streamlit reruns the script
if 'analysis_outputs' not in st.session_state:
    st.session_state.analysis_outputs = {}
if 'chart_paths' not in st.session_state:
    st.session_state.chart_paths = []

# Button to trigger analysis
if st.button("No Noise"): # Button text changed from "Get Elite Insights"
    if not ticker_input:
        st.warning("Please enter a stock ticker symbol.")
    else:
        target_price = None
        if target_price_input:
            try:
                target_price = float(target_price_input)
            except ValueError:
                st.error("Invalid target price. Please enter a numerical value.")
                target_price = None # Reset target_price to None on error

        st.info(f"Fetching and analyzing data for {ticker_input}...")
        
        # Call the core logic to generate insights and get chart paths
        outputs, paths = stock_insight_core.generate_stock_insights(ticker_input, target_price, CHARTS_DIR)
        
        # Store results in session state
        st.session_state.analysis_outputs = outputs
        st.session_state.chart_paths = paths
        
        if "Error" in st.session_state.analysis_outputs:
            st.error(st.session_state.analysis_outputs["Error"])
        else:
            st.success("Analysis complete! See results below.")

# --- Display Results Section ---
# This section only runs if there are analysis outputs in session state
if st.session_state.analysis_outputs:
    st.subheader(f"Analysis for {ticker_input}")

    # Display Key Financial Info in a neat table
    if "Key Financial Info" in st.session_state.analysis_outputs:
        st.markdown("### Key Financial Information")
        # Ensure the content is a dict before trying to create a DataFrame
        if isinstance(st.session_state.analysis_outputs["Key Financial Info"], dict):
            # Transpose the dictionary to display metrics as rows and values as columns
            st.dataframe(pd.DataFrame([st.session_state.analysis_outputs["Key Financial Info"]]).T.rename(columns={0: "Value"}))
        else:
            st.write(st.session_state.analysis_outputs["Key Financial Info"]) # Fallback if it's just a string error message

    # Display Charts if available
    if st.session_state.chart_paths:
        st.markdown("### Visual Insights")
        for chart_path in st.session_state.chart_paths:
            # Check if the chart file actually exists on disk before trying to display it
            if os.path.exists(chart_path):
                # Display the image using the updated parameter
                st.image(chart_path, use_container_width=True) # Changed from use_column_width=True
            else:
                st.warning(f"Chart file not found at: {chart_path}. It might not have been generated correctly.")
    else:
        # This block executes if chart_paths is empty or None, indicating no charts were returned
        if "Error" not in st.session_state.analysis_outputs: # Don't show this if there's a general error already
            st.info("No charts were generated or found for display. Please check terminal for errors during chart generation.")


    # Display AI Analysis sections
    if "AI News Analysis (Headlines)" in st.session_state.analysis_outputs:
        st.markdown("### AI-Powered News Analysis")
        st.write(st.session_state.analysis_outputs["AI News Analysis (Headlines)"])

    if "AI Financial Analysis (Company & Valuation)" in st.session_state.analysis_outputs:
        st.markdown("### AI-Powered Company & Valuation Analysis")
        st.write(st.session_state.analysis_outputs["AI Financial Analysis (Company & Valuation)"])

    if "AI Warren Buffett Framework Assessment" in st.session_state.analysis_outputs:
        st.markdown("### AI Warren Buffett Framework Assessment")
        st.write(st.session_state.analysis_outputs["AI Warren Buffett Framework Assessment"])
    
    if "Basic Valuation Insight (Numerical Comparison)" in st.session_state.analysis_outputs:
        st.markdown("### Basic Valuation Insight (Numerical Comparison)")
        st.write(st.session_state.analysis_outputs["Basic Valuation Insight (Numerical Comparison)"])

# --- Sidebar Elements ---
# Placeholder for the "Elite" section (Critical Thinking, Problem-Solving, etc.)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧠 Elite Edge Training")
st.sidebar.info(
    "After each module, I will provide exercises to enhance your critical thinking, problem-solving, analytical skills, and real-world acumen. Stay tuned for these challenges!"
)

# Disclaimer
st.sidebar.markdown("---")
st.sidebar.warning(
    "**Disclaimer:** This tool provides AI-generated insights and financial data for informational purposes only. It is not financial advice. Always conduct your own research and consult with a qualified financial advisor before making any investment decisions."
)