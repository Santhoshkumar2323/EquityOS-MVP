# stock_insight_core.py

import os
import yfinance as yf
import finnhub
import praw
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration & Initialization ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    print("ERROR: FINNHUB_API_KEY not found in .env file. Finnhub features will be unavailable.")
    finnhub_client = None
else:
    try:
        finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
        print("Finnhub Configuration: Finnhub client initialized.")
    except Exception as e:
        print(f"ERROR: Finnhub client initialization failed: {e}. Finnhub features will be unavailable.")
        finnhub_client = None


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env file. AI features will be unavailable.")
    gemini_model = None
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        print("AI Configuration: Gemini 1.5 Flash model initialized.")
    except Exception as e:
        print(f"ERROR: Gemini API initialization failed: {e}. AI features will be unavailable.")
        gemini_model = None

# Reddit credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

reddit_client = None
if all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_USER_AGENT]):
    try:
        # PRAW handles authentication on first use, ensure read-only if no posting needed
        reddit_client = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            username=REDDIT_USERNAME,
            password=REDDIT_PASSWORD,
            user_agent=REDDIT_USER_AGENT
        )
        # Verify read-only access by trying to access something simple
        # This helps catch credential issues early
        print(f"Reddit client read-only: {reddit_client.read_only}")
        if not reddit_client.read_only: # If it's not read-only, it means it authenticated with username/password
             print("Reddit Configuration: SUCCESS - PRAW client initialized (user authenticated).")
        else: # If read-only is true, it means it's an unauthenticated script instance
             print("Reddit Configuration: SUCCESS - PRAW client initialized (read-only script).")

    except Exception as e:
        print(f"Reddit Configuration: ERROR - PRAW client initialization failed: {e}")
else:
    print("Reddit Configuration: WARNING - Missing one or more Reddit credentials in .env file. Reddit features will be unavailable.")


# --- Data Fetching Functions ---

def fetch_yfinance_data(ticker):
    """Fetches historical data and company info from Yahoo Finance."""
    print(f"Data Fetch (yfinance): Attempting to fetch data for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y", interval="1d") # 1 year daily data

        if hist.empty:
            print(f"Data Fetch (yfinance): No historical data found for {ticker}.")
            return None, None
        
        print(f"Data Fetch (yfinance): Company info retrieved for {ticker}.")
        print(f"Data Fetch (yfinance): Fetched {len(hist)} rows of historical data.")
        return info, hist
    except Exception as e:
        print(f"Data Fetch (yfinance): Error fetching data for {ticker}: {e}")
        return None, None

def fetch_finnhub_news(ticker, limit=250):
    """Fetches news headlines from Finnhub."""
    print(f"Data Fetch (Finnhub): Attempting to fetch news for {ticker}...")
    if not finnhub_client:
        return []
    try:
        # Finnhub news API requires 'from' and 'to' dates
        from_date = (pd.Timestamp.now() - pd.DateOffset(months=1)).strftime('%Y-%m-%d')
        to_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        news = finnhub_client.company_news(ticker, _from=from_date, to=to_date)
        news_headlines = [article['headline'] for article in news if 'headline' in article]
        print(f"Data Fetch (Finnhub): Fetched {len(news_headlines)} news articles.")
        return news_headlines[:limit] # Limit to avoid excessive AI token usage
    except Exception as e:
        print(f"Data Fetch (Finnhub): Error fetching news for {ticker}: {e}")
        return []

def fetch_historical_financials(ticker):
    """Fetches historical financial statements and calculates ratios."""
    print(f"--- Fetching Historical Financial Data for {ticker} ---")
    if not finnhub_client:
        return pd.DataFrame()

    try:
        financials = finnhub_client.company_basic_financials(ticker, 'all')
        if not financials or 'metric' not in financials:
            print(f"Finnhub: No basic financials found for {ticker}.")
            return pd.DataFrame()

        metrics_data_by_year = {}
        for metric_item in financials['metric']:
            if 'date' in metric_item and 'value' in metric_item and 'concept' in metric_item:
                date = pd.to_datetime(metric_item['date'])
                year = date.year
                if year not in metrics_data_by_year:
                    metrics_data_by_year[year] = {}
                metrics_data_by_year[year][metric_item['concept']] = metric_item['value']

        df_financials = pd.DataFrame.from_dict(metrics_data_by_year, orient='index')
        df_financials.index.name = 'Date'
        df_financials = df_financials.sort_index(ascending=True)

        ratios_df = pd.DataFrame(index=df_financials.index)
        
        # Mapping Finnhub raw metric names to display names
        # Check for both 'MetricNameAnnual' and 'MetricName' from Finnhub's basic financials
        # Print concepts found for debugging
        print(f"  Finnhub concepts found for {ticker}: {df_financials.columns.tolist()}")

        ratio_mapping = {
            'grossProfitMargin': 'Gross Profit Margin',
            'ebitMargin': 'Operating Profit Margin', # EBIT Margin
            'netProfitMargin': 'Net Profit Margin',
            'roe': 'Return on Equity',
            'roa': 'Return on Assets',
            'currentRatio': 'Current Ratio',
            'quickRatio': 'Quick Ratio',
            'eps': 'EPS Growth' # Added EPS growth for completeness, though it's usually calculated from historical EPS
        }

        for finnhub_metric, display_name in ratio_mapping.items():
            if f'{finnhub_metric}Annual' in df_financials.columns:
                ratios_df[display_name] = df_financials[f'{finnhub_metric}Annual']
                print(f"  Found '{finnhub_metric}Annual' as '{display_name}'.")
            elif finnhub_metric in df_financials.columns:
                ratios_df[display_name] = df_financials[finnhub_metric]
                print(f"  Found '{finnhub_metric}' as '{display_name}'.")
            else:
                print(f"  Warning: Metric '{finnhub_metric}' (or its annual version) not found for {ticker}.")
        
        if ratios_df.empty:
            print(f"  No relevant financial ratios could be extracted for {ticker} from Finnhub for charting.")
            return pd.DataFrame()

        print("Calculated Historical Ratios (Annual):")
        print(ratios_df)
        return ratios_df.tail(5) # Show last 5 years
    except Exception as e:
        print(f"Finnhub: Error fetching or processing financial data for {ticker}: {e}")
        return pd.DataFrame()

def fetch_reddit_market_pulse(ticker, limit_posts_per_subreddit=15, limit_comments_per_post=3):
    """Fetches relevant Reddit posts and comments for broader market sentiment."""
    print(f"--- Starting AI-Powered Reddit Market Pulse Analysis ---")
    if not reddit_client:
        print("Reddit Market Pulse: PRAW client not initialized or credentials missing. Skipping Reddit data fetch.")
        return []

    subreddits = ['investing', 'stocks', 'wallstreetbets', 'stockmarket', 'finance', 'economy']
    reddit_content_for_ai = []
    print(f"Reddit Market Pulse: Attempting to fetch market pulse from {len(subreddits)} subreddits...")

    try:
        for subreddit_name in subreddits:
            subreddit = reddit_client.subreddit(subreddit_name)
            print(f"Fetching top {limit_posts_per_subreddit} posts from r/{subreddit_name} (hot posts)...")
            
            for i, submission in enumerate(subreddit.hot(limit=limit_posts_per_subreddit)):
                if i >= limit_posts_per_subreddit: # Ensure we don't exceed the limit
                    break
                if submission.stickied:
                    continue # Skip pinned posts

                # Collect post title and body
                post_text = f"Title: {submission.title}\n"
                if submission.selftext:
                    post_text += f"Body: {submission.selftext}\n"

                # Fetch top comments for broader context
                comments_added = []
                try:
                    # Replace_more loads more comments, limit=0 loads top-level comments
                    submission.comments.replace_more(limit=0) 
                    # Use a list comprehension and slice to get top N comments
                    for k, top_comment in enumerate(submission.comments.list()):
                        if k >= limit_comments_per_post:
                            break
                        if hasattr(top_comment, 'body') and top_comment.body.strip(): # Ensure body exists and isn't empty
                            comments_added.append(f"Comment: {top_comment.body}")
                except Exception as comment_err:
                    print(f"  Warning: Could not fetch comments for post {submission.id}: {comment_err}")

                if comments_added:
                    post_text += "\n".join(comments_added) + "\n"
                
                reddit_content_for_ai.append(post_text)
                time.sleep(0.1) # Small delay to be respectful of Reddit API limits

        print(f"Reddit Market Pulse: Fetched {len(reddit_content_for_ai)} pieces of content for market pulse.")
        return reddit_content_for_ai
    except Exception as e:
        print(f"Reddit Market Pulse: Error fetching Reddit data: {e}. Check API limits or credentials.")
        return []

# --- Charting Functions ---

def create_candlestick_chart(df_hist, ticker):
    """Creates an interactive candlestick chart."""
    fig = go.Figure(data=[go.Candlestick(
        x=df_hist.index,
        open=df_hist['Open'],
        high=df_hist['High'],
        low=df_hist['Low'],
        close=df_hist['Close']
    )])
    fig.update_layout(
        title=f'{ticker} Candlestick Chart',
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        height=500
    )
    return fig

def create_financial_ratios_chart(df_ratios, ticker):
    """Creates a chart for historical financial ratios."""
    if df_ratios.empty:
        fig = go.Figure()
        fig.update_layout(title=f'{ticker} Key Historical Ratios (Data Not Available)', height=400,
                          annotations=[dict(text="Financial ratio data not available via Finnhub for this ticker or period.",
                                            xref="paper", yref="paper", showarrow=False,
                                            font=dict(size=14, color="grey"))])
        return fig

    fig = go.Figure()
    for col in df_ratios.columns:
        fig.add_trace(go.Scatter(x=df_ratios.index.astype(str), y=df_ratios[col], mode='lines+markers', name=col))

    fig.update_layout(
        title=f'{ticker} Key Historical Ratios',
        xaxis_title='Fiscal Year',
        yaxis_title='Value (e.g., %)', # Changed to generic "Value" as some ratios aren't percentages
        height=500
    )
    return fig

def create_price_gauge_chart(current_price, target_price, ticker):
    """Creates a gauge chart for current price vs. target price."""
    # Ensure a reasonable range for the gauge
    gauge_min_val = min(current_price, target_price) * 0.9 if min(current_price, target_price) * 0.9 > 0 else 0
    gauge_max_val = max(current_price, target_price) * 1.1

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=current_price,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"<b>{ticker}</b> Price vs. Target"},
        gauge={
            'axis': {'range': [gauge_min_val, gauge_max_val], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [gauge_min_val, target_price * 0.95], 'color': "lightcoral", 'name': 'Below Target'},
                {'range': [target_price * 0.95, target_price * 1.05], 'color': "lightgreen", 'name': 'Near Target'},
                {'range': [target_price * 1.05, gauge_max_val], 'color': "lightblue", 'name': 'Above Target'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': target_price
            }
        }
    ))
    fig.update_layout(height=400)
    return fig


# --- AI Analysis Functions ---

def ai_news_analysis(news_headlines):
    """Uses Gemini to analyze news headlines."""
    print("AI Analysis: Sending news headlines to Gemini for detailed analysis...")
    if not gemini_model:
        return "AI news analysis unavailable due to API configuration issues."

    if not news_headlines:
        return "No recent news headlines available for analysis."

    prompt = f"""
    Analyze the sentiment and key themes from the following news headlines related to a company.
    Provide:
    1.  **Themes:** List the main recurring subjects or categories in bullet points.
    2.  **Sentiment:** Overall sentiment (e.g., Bullish, Bearish, Mixed, Neutral).
    3.  **Implications:** What are the potential short-term or long-term impacts of these themes and sentiment on the stock?

    News Headlines:
    {chr(10).join(news_headlines)}
    """
    try:
        response = gemini_model.generate_content(prompt)
        print("AI Analysis: Received response from Gemini.")
        return response.text
    except Exception as e:
        print(f"AI Analysis: Error with Gemini news analysis: {e}. Check Gemini API key or rate limits.")
        return f"AI news analysis failed: {e}"

def ai_financial_analysis(stock_info, df_ratios):
    """Uses Gemini to analyze financial data and company overview."""
    print("AI Analysis: Sending financial data to Gemini for analysis...")
    if not gemini_model:
        return "AI financial analysis unavailable due to API configuration issues."

    # Extract relevant info from stock_info
    pe_ratio = stock_info.get('trailingPE')
    book_value = stock_info.get('bookValue')
    eps = stock_info.get('trailingEps')
    sector = stock_info.get('sector')
    industry = stock_info.get('industry')
    summary = stock_info.get('longBusinessSummary', 'No business summary available.')

    financial_data_str = f"""
    P/E Ratio: {pe_ratio if pe_ratio else 'N/A'}
    Book Value: {book_value if book_value else 'N/A'}
    EPS: {eps if eps else 'N/A'}
    Sector: {sector if sector else 'N/A'}
    Industry: {industry if industry else 'N/A'}
    Historical Ratios (last 5 years, percentages/values):
    {df_ratios.to_string() if not df_ratios.empty else 'No historical ratios available.'}
    """

    prompt = f"""
    Analyze the following financial data and company information for a stock.
    Provide a concise analysis including:
    1.  **Company Overview:** A brief summary of what the company does.
    2.  **Valuation Insight:** Comment on the P/E ratio, book value, and other relevant metrics. Does it appear overvalued, undervalued, or fairly valued based on these metrics?
    3.  **Strategic Context:** Briefly describe the company's business model, competitive advantages, and market position based on the summary.
    4.  **Key Financial Metrics:** Re-state the provided P/E, Book Value, EPS, Sector, Industry.
    5.  **Business Summary:** Provide the full business summary if available.

    Financial Data and Company Summary:
    {financial_data_str}
    Business Summary: {summary}
    """
    try:
        response = gemini_model.generate_content(prompt)
        print("AI Analysis: Received response from Gemini.")
        return response.text
    except Exception as e:
        print(f"AI Analysis: Error with Gemini financial analysis: {e}. Check Gemini API key or rate limits.")
        return f"AI financial analysis failed: {e}"

def ai_buffett_framework_analysis(stock_info):
    """Uses Gemini to assess a stock based on Warren Buffett's investment framework."""
    print("AI Analysis: Sending data to Gemini for Warren Buffett framework analysis...")
    if not gemini_model:
        return "AI Buffett framework analysis unavailable due to API configuration issues."

    pe_ratio = stock_info.get('trailingPE')
    business_summary = stock_info.get('longBusinessSummary', 'No business summary available.')
    eps = stock_info.get('trailingEps')
    
    prompt = f"""
    Assess the following stock based on Warren Buffett's investment framework. Focus on these aspects:
    1.  **Understandable Business:** Is the business easy to comprehend?
    2.  **Economic Moat:** Does the company have a sustainable competitive advantage (brand, patents, network effects, cost advantage, etc.)?
    3.  **Consistent Earnings:** Based on available data (like EPS), does it suggest consistent earnings power? (Note if more historical data is needed).
    4.  **Management Quality:** While not directly available, what can be inferred about management based on business summary and market position? (Note if more data is needed).
    5.  **Valuation Comment:** Given the P/E ratio and overall profile, does the stock appear to offer a "margin of safety" (i.e., is it undervalued or fairly valued for its quality)?

    Stock Information:
    Business Summary: {business_summary}
    P/E Ratio: {pe_ratio if pe_ratio else 'N/A'}
    EPS: {eps if eps else 'N/A'}
    """
    try:
        response = gemini_model.generate_content(prompt)
        print("AI Analysis: Received response from Gemini for Buffett analysis.")
        return response.text
    except Exception as e:
        print(f"AI Analysis: Error with Gemini Buffett analysis: {e}. Check Gemini API key or rate limits.")
        return f"AI Buffett framework analysis failed: {e}"

def ai_reddit_market_pulse_analysis(reddit_content):
    """Uses Gemini to analyze Reddit content for market pulse."""
    print("AI Analysis: Sending Reddit market pulse content to Gemini for analysis...")
    if not gemini_model:
        return "AI Reddit market pulse analysis unavailable due to API configuration issues."
    if not reddit_content:
        return """
**Overall Retail Market Sentiment:** Not enough relevant Reddit content found for comprehensive analysis.
**Prevailing Retail Investment Themes/Sectors:** Not ascertainable.
**Key Bullish Drivers (Retail Perspective):** Not ascertainable.
**Key Bearish Concerns (Retail Perspective):** Not ascertainable.
**Implied Retail Positioning/Strategy:** Not ascertainable.
        """

    combined_reddit_text = "\n\n---\n\n".join(reddit_content)

    prompt = f"""
    Analyze the following collection of Reddit post titles, bodies, and top comments related to stock market and specific stock trends.
    Extract the overall sentiment and key investment themes and drivers from the retail investor perspective.
    Be specific in identifying themes, and try to discern bullish/bearish drivers even if not explicitly stated, or if sentiment is ambiguous, state "Mixed" or "Neutral" with justification.

    Provide the analysis in the following structured format:
    1.  **Overall Retail Market Sentiment:** [Your assessment: Bullish/Bearish/Mixed/Neutral with brief justification]
    2.  **Prevailing Retail Investment Themes/Sectors:** [List specific themes, stocks, or sectors discussed in bullet points]
    3.  **Key Bullish Drivers (Retail Perspective):** [List reasons for optimism in bullet points]
    4.  **Key Bearish Concerns (Retail Perspective):** [List reasons for pessimism/risks in bullet points]
    5.  **Implied Retail Positioning/Strategy:** [Are they looking to buy, sell, hold, or is it speculative? Justify briefly.]

    Reddit Content for Analysis:
    {combined_reddit_text}
    """
    try:
        response = gemini_model.generate_content(prompt)
        print("AI Analysis: Received response from Gemini for Reddit market pulse.")
        return response.text
    except Exception as e:
        print(f"AI Analysis: Error with Gemini Reddit analysis: {e}. Check Gemini API key or rate limits.")
        return f"AI Reddit market pulse analysis failed: {e}"


# --- Main Analysis Function ---

def perform_comprehensive_analysis(ticker, target_price):
    """
    Performs a comprehensive stock analysis, fetches data, runs AI analysis,
    and generates chart figures.
    Returns a dictionary of results for the Streamlit app.
    """
    print(f"\n--- Initiating comprehensive analysis for {ticker} with target price {target_price} ---")

    results = {}
    
    # 1. Fetch Data
    stock_info, df_hist = fetch_yfinance_data(ticker)
    if stock_info is None or df_hist is None or df_hist.empty:
        return {"error": f"Could not fetch basic stock data for {ticker}. Please check the ticker symbol, your internet connection, or try a different ticker."}

    current_price = df_hist['Close'].iloc[-1]
    results['key_financial_info'] = {
        "Stock": ticker,
        "Current Price (Prev Close)": f"USD{current_price:.2f}",
        "P/E Ratio": f"{stock_info.get('trailingPE'):.2f}" if stock_info.get('trailingPE') else "N/A",
        "Book Value": f"USD{stock_info.get('bookValue'):.2f}" if stock_info.get('bookValue') else "N/A",
        "EPS": f"USD{stock_info.get('trailingEps'):.2f}" if stock_info.get('trailingEps') else "N/A",
        "Sector": stock_info.get('sector', "N/A"),
        "Industry": stock_info.get('industry', "N/A")
    }

    news_headlines = fetch_finnhub_news(ticker)
    df_ratios = fetch_historical_financials(ticker)
    reddit_content = fetch_reddit_market_pulse(ticker)

    # 2. Generate Charts (Plotly Figures)
    print("--- Generating Charts ---")
    results['charts'] = {
        'candlestick_chart': create_candlestick_chart(df_hist, ticker),
        'financial_ratios_chart': create_financial_ratios_chart(df_ratios, ticker),
        'price_gauge_chart': create_price_gauge_chart(current_price, target_price, ticker)
    }

    # 3. AI Analysis
    print("--- Starting AI-Powered News Analysis ---")
    results['ai_news_analysis'] = ai_news_analysis(news_headlines)

    print("--- Starting AI-Powered Financial Data Analysis ---")
    results['ai_financial_analysis'] = ai_financial_analysis(stock_info, df_ratios)

    print("--- Starting AI-Powered Warren Buffett Framework Analysis ---")
    results['ai_buffett_analysis'] = ai_buffett_framework_analysis(stock_info)

    print("--- Starting AI-Powered Reddit Market Pulse Analysis ---")
    results['ai_reddit_market_pulse'] = ai_reddit_market_pulse_analysis(reddit_content)

    # 4. Basic Valuation Insight
    results['basic_valuation_insight'] = {
        "Your Target Price": f"USD{target_price:.2f}",
        "Current Price": f"USD{current_price:.2f}",
        "Insight": "Current price is **BELOW** your target price. This might be a potential opportunity based on your target." if current_price < target_price else \
                   "Current price is **ABOVE** your target price. Consider if it's overvalued for your strategy." if current_price > target_price else \
                   "Current price is **AT** your target price."
    }

    print("\n--- Comprehensive analysis complete. ---")
    return results

# This part is for standalone testing if you run stock_insight_core.py directly
if __name__ == "__main__":
    print("--- Running stock_insight_core.py in standalone test mode ---")
    
    test_ticker = input("Enter the stock ticker symbol for testing (e.g., GOOGL, AAPL, RELIANCE.NS): ").upper()
    try:
        test_target_price = float(input(f"Enter a test target price for {test_ticker} (e.g., 180.00): "))
    except ValueError:
        print("Invalid price entered. Using default target of 200.00.")
        test_target_price = 200.00

    analysis_results = perform_comprehensive_analysis(test_ticker, test_target_price)

    # Print full results for standalone mode
    print("\n===== FULL ANALYSIS RESULTS (Standalone Test) =====")
    if "error" in analysis_results:
        print(f"Error: {analysis_results['error']}")
    else:
        for key, value in analysis_results.items():
            if key == 'charts':
                print(f"--- Generated Chart Figures (will be interactive in Streamlit) ---")
                print("Charts are Plotly Figure objects, displayable in a web app.")
                continue
            
            print(f"\n--- {key.replace('_', ' ').title()} ---")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
            else:
                print(value)

    print("\n--- Standalone testing of stock_insight_core.py finished ---")