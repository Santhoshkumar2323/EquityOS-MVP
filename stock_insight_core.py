import math # For calculating grid dimensions for plots
import yfinance as yf
import pandas as pd
import datetime
import google.generativeai as genai
import os # Added for directory handling
import finnhub
import matplotlib.pyplot as plt # Added for plotting
import mplfinance as mpf # Added for financial plotting
import numpy as np # Added for gauge chart calculations
from matplotlib.patches import Wedge # IMPORTANT FIX: Added for the gauge chart!

# --- Configuration for Gemini API ---
# !!! IMPORTANT: Replace 'YOUR_ACTUAL_GEMINI_API_KEY' with your real API key !!!
genai.configure(api_key='AIzaSyDyFbmgs7mKgN32aoiUpmhEAeEZFbMDQfY') 
print("AI Configuration: SUCCESS - Gemini API key directly loaded for testing.")

# --- Configuration for Finnhub API ---
# !!! IMPORTANT: Replace 'YOUR_ACTUAL_FINNHUB_API_KEY' with your real API key !!!
FINNHUB_API_KEY = 'd1sh0qhr01qkbods98fgd1sh0qhr01qkbods98g0' 
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
print("Finnhub Configuration: Finnhub client initialized.")

# Initialize the Gemini generative model
model = genai.GenerativeModel('gemini-1.5-flash')
print("AI Configuration: Gemini 1.5 Flash model initialized.")

# --- Function to Fetch Stock Data (using yfinance - for info & historical) ---
def fetch_stock_data(ticker_symbol, period="1y"):
    """
    Fetches historical stock data and basic company info for a given ticker symbol using yfinance.
    Note: This function no longer fetches news, news is handled by Finnhub.
    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., "AAPL", "GOOGL").
        period (str): The period for historical data.
    Returns:
        dict: A dictionary containing stock info and historical data, or None if an error occurs.
    """
    print(f"\nData Fetch (yfinance): Attempting to fetch data for {ticker_symbol}...")
    ticker = yf.Ticker(ticker_symbol)

    try:
        info = ticker.info
        if not info:
            print(f"Data Fetch (yfinance): WARNING - Could not retrieve company info for {ticker_symbol}.")
            info_data = {}
        else:
            info_data = {
                "currentPrice": info.get("currentPrice"),
                "previousClose": info.get("previousClose"),
                "peRatio": info.get("trailingPE"),
                "bookValue": info.get("bookValue"),
                "earningsPerShare": info.get("trailingEps"),
                "longBusinessSummary": info.get("longBusinessSummary", "No business summary available."),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "currency": info.get("currency", "$") # Get currency, default to '$'
            }
            print(f"Data Fetch (yfinance): Company info retrieved for {ticker_symbol}.")

        hist_data = ticker.history(period=period)
        if hist_data.empty:
            print(f"Data Fetch (yfinance): No historical data found for {ticker_symbol} for period {period}.")
            hist_data = pd.DataFrame() # CORRECTED: Ensure it's an empty DataFrame, not None
        else:
            print(f"Data Fetch (yfinance): Fetched {len(hist_data)} rows of historical data.")

        if not info_data and hist_data.empty: # Check if both info is empty AND hist_data is empty
            print(f"Data Fetch (yfinance): ERROR - No data of any kind retrieved for {ticker_symbol}.")
            return None

        return {
            "info": info_data,
            "historical_data": hist_data,
        }

    except Exception as e:
        print(f"Data Fetch (yfinance): CRITICAL ERROR fetching data for {ticker_symbol}: {e}")
        print("Please check the ticker symbol, your internet connection, or if Yahoo Finance is temporarily unavailable.")
        print(f"TIP: For Indian stocks, remember to add '.NS' or '.BO' suffix (e.g., ITC.NS).")
        return None

# --- START OF NEW FUNCTION: get_historical_financial_ratios ---
def get_historical_financial_ratios(ticker_symbol):
    print(f"\n--- Fetching Historical Financial Data for {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)

    try:
        # Get annual income statement
        income_statement = ticker.financials
        if income_statement.empty:
            print("Warning: Annual Income Statement data not available.")
            return pd.DataFrame() # Return empty if no data

        # Get annual balance sheet
        balance_sheet = ticker.balance_sheet
        if balance_sheet.empty:
            print("Warning: Annual Balance Sheet data not available.")
            return pd.DataFrame() # Return empty if no data

        # Transpose DataFrames so dates are rows
        income_statement = income_statement.T
        balance_sheet = balance_sheet.T

        # Rename index to 'Date' for consistency
        income_statement.index.name = 'Date'
        balance_sheet.index.name = 'Date'

        # Ensure index is datetime for proper merging/sorting
        income_statement.index = pd.to_datetime(income_statement.index)
        balance_sheet.index = pd.to_datetime(balance_sheet.index)

        # Merge financial data on Date index
        financial_data = pd.merge(income_statement, balance_sheet, left_index=True, right_index=True, how='outer')

        # --- Calculate Ratios ---
        ratios_df = pd.DataFrame(index=financial_data.index)

        # Profitability Ratios
        if 'Total Revenue' in financial_data.columns and 'Gross Profit' in financial_data.columns:
            ratios_df['Gross Profit Margin'] = (financial_data['Gross Profit'] / financial_data['Total Revenue']) * 100
        if 'Total Revenue' in financial_data.columns and 'Operating Income' in financial_data.columns:
            ratios_df['Operating Profit Margin'] = (financial_data['Operating Income'] / financial_data['Total Revenue']) * 100
        if 'Total Revenue' in financial_data.columns and 'Net Income' in financial_data.columns:
            ratios_df['Net Profit Margin'] = (financial_data['Net Income'] / financial_data['Total Revenue']) * 100

        # Liquidity Ratios
        if 'Total Current Assets' in financial_data.columns and 'Total Current Liabilities' in financial_data.columns:
            # Avoid division by zero by replacing 0 with NaN
            ratios_df['Current Ratio'] = financial_data['Total Current Assets'] / financial_data['Total Current Liabilities'].replace(0, pd.NA)

        # Solvency Ratios
        if 'Total Liabilities' in financial_data.columns and 'Total Stockholder Equity' in financial_data.columns:
            # Avoid division by zero
            ratios_df['Debt to Equity Ratio'] = financial_data['Total Liabilities'] / financial_data['Total Stockholder Equity'].replace(0, pd.NA)

        # Efficiency/Return Ratios
        if 'Net Income' in financial_data.columns and 'Total Stockholder Equity' in financial_data.columns:
            # Avoid division by zero
            ratios_df['Return on Equity (ROE)'] = (financial_data['Net Income'] / financial_data['Total Stockholder Equity'].replace(0, pd.NA)) * 100
        
        # Drop rows where all ratio values are NaN (if a year has no complete data for any ratio)
        ratios_df.dropna(how='all', inplace=True)
        
        # Optional: Round percentage ratios for cleaner display
        for col in ['Gross Profit Margin', 'Operating Profit Margin', 'Net Profit Margin', 'Return on Equity (ROE)']:
            if col in ratios_df.columns:
                ratios_df[col] = ratios_df[col].round(2)

        # Sort by date in ascending order (oldest to newest) for trend analysis
        ratios_df.sort_index(ascending=True, inplace=True)

        print("\nCalculated Historical Ratios (Annual):")
        print(ratios_df)
        return ratios_df

    except Exception as e:
        print(f"Error fetching historical financial data for {ticker_symbol}: {e}")
        return pd.DataFrame() # Return empty DataFrame on error
# --- END OF NEW FUNCTION: get_historical_financial_ratios ---


# --- New Function to Fetch News Data (using Finnhub) ---
def fetch_finnhub_news(ticker_symbol, days_back=7):
    """
    Fetches news headlines for a given ticker symbol using Finnhub.
    Args:
        ticker_symbol (str): The stock ticker symbol.
        days_back (int): Number of days back to fetch news.
    Returns:
        list: A list of dictionaries, where each dict has 'title' and 'link'.
    """
    print(f"\nData Fetch (Finnhub): Attempting to fetch news for {ticker_symbol}...")
    try:
        # Calculate start and end dates
        to_date = datetime.date.today()
        from_date = to_date - datetime.timedelta(days=days_back)

        # Finnhub requires dates as strings in 'YYYY-MM-DD' format
        finnhub_news = finnhub_client.company_news(
            symbol=ticker_symbol,
            _from=from_date.strftime('%Y-%m-%d'),
            to=to_date.strftime('%Y-%m-%d')
        )

        if not finnhub_news:
            print(f"Data Fetch (Finnhub): No recent news found for {ticker_symbol}.")
            return {"articles": [], "error": None}
        else:
            # Filter out articles with no titles and format them
            news_data = []
            for n in finnhub_news:
                title = n.get('headline') # Finnhub uses 'headline' for title
                url = n.get('url')
                if title and url: # Only include if both title and URL exist
                    news_data.append({"title": title, "link": url})
            print(f"Data Fetch (Finnhub): Fetched {len(news_data)} news articles.")
            return {"articles": news_data, "error": None}

    except finnhub.FinnhubAPIException as e:
        error_msg = f"Finnhub API ERROR - {e}. TIP: Check your Finnhub API key or if you've exceeded your rate limit or if your plan covers this stock's news."
        print(f"Data Fetch (Finnhub): {error_msg}")
        return {"articles": [], "error": error_msg}
    except Exception as e:
        error_msg = f"CRITICAL ERROR fetching news for {ticker_symbol}: {e}"
        print(f"Data Fetch (Finnhub): {error_msg}")
        return {"articles": [], "error": error_msg}

# --- Function for AI News Analysis (using Gemini) ---
def analyze_news_with_gemini(news_articles):
    """
    Uses the Gemini AI model to identify key themes, sentiment, and potential implications from news headlines.
    Args:
        news_articles (list): A list of dictionaries, where each dict has 'title' and 'link'.
    Returns:
        dict: A dictionary containing 'themes', 'sentiment', 'implications', or default values if an error occurs.
    """
    if not news_articles:
        return {
            "themes": "No recent news available for theme analysis.",
            "sentiment": "Neutral",
            "implications": "No news implications to assess."
        }

    news_titles = "\n".join([article['title'] if article.get('title') else '' for article in news_articles])

    if not news_titles.strip():
        return {
            "themes": "No meaningful headlines were available from the news.",
            "sentiment": "Neutral",
            "implications": "No news implications to assess due to lack of headlines."
        }

    prompt = f"""
    Analyze the following stock news headlines for a company.
    Identify 2-3 key themes or narratives emerging from these headlines that are relevant to an investor.
    Determine the overall sentiment (Positive, Negative, Neutral, or Mixed) based on the headlines.
    Suggest potential short-term implications (e.g., "The news suggests potential for increased volatility", "positive news could support a price rally", "negative news might lead to downward pressure") for the stock based only on these news headlines.

    Headlines:
    {news_titles}

    Format your response as follows:
    Themes: [List 2-3 themes, separated by semicolons]
    Sentiment: [Positive/Negative/Neutral/Mixed]
    Implications: [Short-term implications statement]
    """

    print("\nAI Analysis: Sending news headlines to Gemini for detailed analysis...")
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            ai_response = response.text.strip()
            print("AI Analysis: Received response from Gemini.")

            themes = "Could not extract themes."
            sentiment = "Could not extract sentiment."
            implications = "Could not extract implications."

            # Use splitlines() to handle different newline characters consistently
            lines = ai_response.splitlines()
            for line in lines:
                # Use .find() for more robust matching and extraction
                if "Themes:" in line:
                    themes = line[line.find("Themes:") + len("Themes:"):].strip()
                elif "Sentiment:" in line:
                    sentiment = line[line.find("Sentiment:") + len("Sentiment:"):].strip()
                elif "Implications:" in line:
                    implications = line[line.find("Implications:") + len("Implications:"):].strip()

            return {"themes": themes, "sentiment": sentiment, "implications": implications}
        else:
            print("AI Analysis: Gemini generated an empty or unreadable response for news.")
            return {
                "themes": "Gemini could not generate themes for the news.",
                "sentiment": "Unknown",
                "implications": "Gemini could not generate implications for the news."
            }

    except Exception as e:
        print(f"AI Analysis: ERROR during Gemini API call for news analysis: {e}")
        if "Quota exceeded" in str(e) or "Rate Limit" in str(e):
            print("TIP: You might have hit a Gemini API quota or rate limit. Please try again in a few minutes or hours.")
        return {
            "themes": "AI news analysis failed due to an error.",
            "sentiment": "Error",
            "implications": "AI news analysis failed due to an error."
        }

# --- Function for AI Financial Data Analysis (using Gemini) ---
def analyze_financials_with_gemini(info_data):
    """
    Uses the Gemini AI model to analyze core financial data and business summary.
    Args:
        info_data (dict): A dictionary containing financial info like P/E, EPS, Book Value, etc.
    Returns:
        dict: A dictionary containing 'company_overview', 'valuation_insight', 'strategic_context',
              or default values if an error occurs.
    """
    if not info_data:
        return {
            "company_overview": "No financial data available for company overview.",
            "valuation_insight": "No financial data for valuation insight.",
            "strategic_context": "No financial data for strategic context."
        }

    # Prepare financial data for the prompt, handling missing values gracefully
    long_business_summary = info_data.get('longBusinessSummary', 'No business summary available.')
    # Ensure numerical values are formatted only if they exist and are numbers
    pe_ratio = info_data.get('peRatio')
    pe_ratio_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else 'N/A'
    
    book_value = info_data.get('bookValue')
    book_value_str = f"{book_value:.2f}" if isinstance(book_value, (int, float)) else 'N/A'
    
    eps = info_data.get('earningsPerShare')
    eps_str = f"{eps:.2f}" if isinstance(eps, (int, float)) else 'N/A'
    
    sector = info_data.get('sector', 'N/A')
    industry = info_data.get('industry', 'N/A')

    prompt = f"""
    Analyze the following financial data and business summary for a company.
    Please generate the response for the following fields. If a field cannot be determined, state "Not ascertainable from data provided".
    Do not add any additional text or introductory/concluding remarks outside of the specified format.

    Company Overview:
    Valuation Insight:
    Strategic Context:

    Financial Data:
    Business Summary: {long_business_summary}
    P/E Ratio: {pe_ratio_str}
    Book Value: {book_value_str}
    EPS: {eps_str}
    Sector: {sector}
    Industry: {industry}
    """

    print("\nAI Analysis: Sending financial data to Gemini for analysis...")
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            ai_response = response.text.strip()
            print("AI Analysis: Received response from Gemini.")

            company_overview = "Could not extract company overview."
            valuation_insight = "Could not extract valuation insight."
            strategic_context = "Could not extract strategic context."

            # Parse based on expected labels, now that the prompt tries to enforce structure more.
            response_lines = ai_response.splitlines()
            
            for line in response_lines:
                if line.strip().startswith("Company Overview:"):
                    company_overview = line.strip()[len("Company Overview:"):].strip()
                elif line.strip().startswith("Valuation Insight:"):
                    valuation_insight = line.strip()[len("Valuation Insight:"):].strip()
                elif line.strip().startswith("Strategic Context:"):
                    strategic_context = line.strip()[len("Strategic Context:"):].strip()

            # Fallback if direct parsing doesn't work and AI might have provided a single block
            if company_overview == "Could not extract company overview." and \
               valuation_insight == "Could not extract valuation insight." and \
               strategic_context == "Could not extract strategic context." and \
               len(response_lines) > 0:
                company_overview = ai_response # Capture whole response as overview as a fallback
                valuation_insight = "See Company Overview for combined insight."
                strategic_context = "See Company Overview for combined insight."


            return {
                "company_overview": company_overview,
                "valuation_insight": valuation_insight,
                "strategic_context": strategic_context
            }
        else:
            print("AI Analysis: Gemini generated an empty or unreadable response for financial data.")
            return {
                "company_overview": "Gemini could not generate company overview.",
                "valuation_insight": "Gemini could not generate valuation insight.",
                "strategic_context": "Gemini could not generate strategic context."
            }

    except Exception as e:
        print(f"AI Analysis: ERROR during Gemini API call for financial analysis: {e}")
        if "Quota exceeded" in str(e) or "Rate Limit" in str(e):
            print("TIP: You might have hit a Gemini API quota or rate limit. Please try again in a few minutes or hours.")
        return {
            "company_overview": "AI financial analysis failed due to an error.",
            "valuation_insight": "AI financial analysis failed due to an error.",
            "strategic_context": "AI financial analysis failed due to an error."
        }

# --- NEW FUNCTION: AI Warren Buffett Framework Analysis ---
def analyze_with_buffett_framework(info_data):
    """
    Uses the Gemini AI model to analyze a company against simplified Warren Buffett investment principles.
    Args:
        info_data (dict): A dictionary containing financial info and business summary.
    Returns:
        dict: A dictionary containing 'understandable_business', 'economic_moat', 'management_quality',
              'valuation_comment', or default values if an error occurs.
    """
    if not info_data:
        return {
            "understandable_business": "Not ascertainable due to lack of data.",
            "economic_moat": "Not ascertainable due to lack of data.",
            "consistent_earnings": "Not ascertainable due to lack of data.", # Added this key
            "management_quality": "Not ascertainable due to lack of data.",
            "valuation_comment": "Not ascertainable due to lack of data."
        }

    long_business_summary = info_data.get('longBusinessSummary', 'No business summary available.')
    
    # Ensure numerical values are formatted only if they exist and are numbers
    pe_ratio = info_data.get('peRatio')
    pe_ratio_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else 'N/A'
    
    book_value = info_data.get('bookValue')
    book_value_str = f"{book_value:.2f}" if isinstance(book_value, (int, float)) else 'N/A'
    
    eps = info_data.get('earningsPerShare')
    eps_str = f"{eps:.2f}" if isinstance(eps, (int, float)) else 'N/A'
    
    sector = info_data.get('sector', 'N/A')
    industry = info_data.get('industry', 'N/A')
    
    current_price = info_data.get('currentPrice')
    current_price_str = f"{current_price:.2f}" if isinstance(current_price, (int, float)) else 'N/A'


    prompt = f"""
    Evaluate the following company's characteristics through the lens of a simplified Warren Buffett investment framework.
    Focus on qualitative aspects and use the provided information.

    Consider the following principles:
    1.  *Understandable Business (Circle of Competence):* Is the business easy to comprehend?
    2.  *Durable Competitive Advantage (Economic Moat):* What gives this company a lasting edge over competitors (e.g., brand, patents, network effects, cost advantage)?
    3.  *Consistent Earnings Power/Profitability:* Based on provided financial data and business type, does it suggest stable and growing earnings?
    4.  *Rational and Shareholder-Oriented Management:* Does the business summary hint at sound leadership or focus on long-term shareholder value?
    5.  *Valuation (Qualitative Comment on "Margin of Safety"):* Comment briefly if the current valuation metrics (like P/E) suggest a potential "margin of safety" (undervalued) or if it appears fully valued/overvalued, considering its industry.

    Provided Data:
    Business Summary: {long_business_summary}
    Sector: {sector}
    Industry: {industry}
    P/E Ratio: {pe_ratio_str}
    EPS: {eps_str}
    Book Value: {book_value_str}
    Current Price: {current_price_str}

    Format your response strictly as follows, providing a concise assessment for each point. If a point cannot be assessed from the data, state "Not ascertainable from data provided":
    Understandable Business: [Assessment]
    Economic Moat: [Assessment]
    Consistent Earnings: [Assessment]
    Management Quality: [Assessment]
    Valuation Comment: [Assessment]
    """

    print("\nAI Analysis: Sending data to Gemini for Warren Buffett framework analysis...")
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            ai_response = response.text.strip()
            print("AI Analysis: Received response from Gemini for Buffett analysis.")

            understandable_business = "Could not extract."
            economic_moat = "Could not extract."
            consistent_earnings = "Could not extract."
            management_quality = "Could not extract."
            valuation_comment = "Could not extract."

            lines = ai_response.splitlines()
            for line in lines:
                if "Understandable Business:" in line:
                    understandable_business = line[line.find("Understandable Business:") + len("Understandable Business:"):].strip()
                elif "Economic Moat:" in line:
                    economic_moat = line[line.find("Economic Moat:") + len("Economic Moat:"):].strip()
                elif "Consistent Earnings:" in line:
                    consistent_earnings = line[line.find("Consistent Earnings:") + len("Consistent Earnings:"):].strip()
                elif "Management Quality:" in line:
                    management_quality = line[line.find("Management Quality:") + len("Management Quality:"):].strip()
                elif "Valuation Comment:" in line:
                    valuation_comment = line[line.find("Valuation Comment:") + len("Valuation Comment:"):].strip()
            
            return {
                "understandable_business": understandable_business,
                "economic_moat": economic_moat,
                "consistent_earnings": consistent_earnings,
                "management_quality": management_quality,
                "valuation_comment": valuation_comment
            }
        else:
            print("AI Analysis: Gemini generated an empty or unreadable response for Buffett analysis.")
            return {
                "understandable_business": "AI analysis failed.",
                "economic_moat": "AI analysis failed.",
                "consistent_earnings": "AI analysis failed.", # Added this key here as well
                "management_quality": "AI analysis failed.",
                "valuation_comment": "AI analysis failed."
            }
    except Exception as e:
        print(f"AI Analysis: ERROR during Gemini API call for Buffett framework analysis: {e}")
        if "Quota exceeded" in str(e) or "Rate Limit" in str(e):
            print("TIP: You might have hit a Gemini API quota or rate limit. Please try again in a few minutes or hours.")
        return {
            "understandable_business": "AI analysis failed due to an error.",
            "economic_moat": "AI analysis failed due to an error.",
            "consistent_earnings": "AI analysis failed due to an error.", # Added this key here as well
            "management_quality": "AI analysis failed due to an error.",
            "valuation_comment": "AI analysis failed due to an error."
        }

# --- NEW FUNCTION: plot_candlestick_chart ---
# Modified: chart_dir is now passed as an argument
def plot_candlestick_chart(historical_data, ticker, chart_dir):
    """
    Generates and saves a candlestick chart of historical prices and volume.
    chart_dir: The absolute path to the directory where charts should be saved.
    """
    if historical_data.empty:
        print(f"No historical data available for {ticker} to plot candlestick chart.")
        return None # Return None if no chart is generated

    # Ensure the chart directory exists and is writable
    if not os.path.isdir(chart_dir): # Check if it's a directory (robust)
        try:
            os.makedirs(chart_dir, exist_ok=True) # exist_ok=True prevents error if it already exists
            print(f"Created chart directory: {chart_dir}")
        except PermissionError as pe:
            print(f"ERROR: Permission denied when creating directory {chart_dir}: {pe}")
            print("Please ensure your user account has write permissions to this path.")
            return None
        except OSError as oe: # Catch a broader OS error for directory creation issues
            print(f"ERROR: Failed to create chart directory {chart_dir}: {oe}")
            return None
        except Exception as e:
            print(f"ERROR: Unexpected error during directory creation for {chart_dir}: {e}")
            return None
    
    # Double-check if the directory is valid after creation attempt
    if not os.path.isdir(chart_dir):
        print(f"CRITICAL ERROR: Directory {chart_dir} does not exist or is not a directory immediately after creation attempt.")
        print("This indicates a severe file system or permissions issue.")
        return None

    historical_data.index = pd.to_datetime(historical_data.index)
    
    mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
    s = mpf.make_mpf_style(base_mpf_style='yahoo', marketcolors=mc)

    chart_filename = f'{ticker}_candlestick.png'
    filepath = os.path.join(chart_dir, chart_filename)

    # Plotting and saving with more specific error handling
    try:
        fig, axlist = mpf.plot(
            historical_data,
            type='candle',
            mav=(20, 50), # Add 20 and 50 period Moving Averages
            volume=True,
            show_nontrading=False,
            style=s,
            title=f'{ticker} Candlestick Chart with Volume',
            ylabel='Price',
            ylabel_lower='Volume',
            figscale=1.5, # Adjust figure size for better readability
            returnfig=True # Ensure this is True so we get the figure object back
        )
        
        if fig is not None:
            plt.savefig(filepath, dpi=300, bbox_inches='tight') # This is the saving line
            plt.close(fig) # Close the figure to free up memory
            print(f"Candlestick chart for {ticker} saved to {filepath}")
            return filepath # Return the path of the saved chart
        else:
            print(f"Warning: Figure object was None after mpf.plot for {ticker} candlestick chart.")
            return None

    except Exception as e:
        print(f"CRITICAL PLOTTING/SAVING ERROR for {filepath} for {ticker}: {e}")
        # Add more diagnostic info in case of save error
        print(f"Does chart_dir exist (pre-save check)? {os.path.exists(chart_dir)}")
        print(f"Is chart_dir a directory (pre-save check)? {os.path.isdir(chart_dir)}")
        parent_dir_of_filepath = os.path.dirname(filepath)
        print(f"Does the parent directory of target file ({parent_dir_of_filepath}) exist? {os.path.exists(parent_dir_of_filepath)}")
        print(f"Is the parent directory of target file a directory? {os.path.isdir(parent_dir_of_filepath)}")
        return None

# --- NEW FUNCTION: plot_financial_ratios_multiples ---
# Modified: chart_dir is now passed as an argument
def plot_financial_ratios_multiples(historical_ratios_df, ticker, chart_dir):
    """
    Generates and saves a Small Multiples plot for historical financial ratios.
    chart_dir: The absolute path to the directory where charts should be saved.
    """
    if historical_ratios_df.empty:
        print(f"No historical ratio data available for {ticker} to plot financial ratios multiples.")
        return None

    if not os.path.exists(chart_dir):
        os.makedirs(chart_dir)
        print(f"Created chart directory: {chart_dir}")

    ratios_to_plot = historical_ratios_df.select_dtypes(include=[float, int])
    ratios_to_plot.index = pd.to_datetime(ratios_to_plot.index)

    if ratios_to_plot.empty:
        print(f"No numeric ratio data found for {ticker} to plot financial ratios multiples.")
        return None

    num_ratios = len(ratios_to_plot.columns)
    
    # Calculate grid size (rows, cols) to make it roughly square
    num_cols = math.ceil(math.sqrt(num_ratios))
    num_rows = math.ceil(num_ratios / num_cols)

    fig, axes = plt.subplots(num_rows, num_cols, figsize=(num_cols * 5, num_rows * 4), sharex=True)
    # Flatten axes array for easy iteration, especially for 1-row/1-col cases
    axes = axes.flatten() if num_ratios > 1 else [axes]

    fig.suptitle(f'{ticker} Key Financial Ratios Over Time', fontsize=16, y=1.02) # y adjusts title position

    for i, column in enumerate(ratios_to_plot.columns):
        ax = axes[i]
        ax.plot(ratios_to_plot.index, ratios_to_plot[column], marker='o', linestyle='-', markersize=4)
        ax.set_title(column, fontsize=10)
        ax.set_ylabel('Value')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.tick_params(axis='x', rotation=45) # Rotate x-axis labels for readability

    # Hide any unused subplots
    for j in range(num_ratios, len(axes)):
        fig.delaxes(axes[j])

    plt.tight_layout(rect=[0, 0.03, 1, 0.98]) # Adjust layout to prevent overlap, leaving space for suptitle
    
    chart_filename = f'{ticker}_financial_ratios_multiples.png'
    filepath = os.path.join(chart_dir, chart_filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig) # Close the figure to free up memory

    print(f"Financial ratios multiples chart for {ticker} saved to {filepath}")
    return filepath # Return the path of the saved chart

# --- NEW FUNCTION: plot_gauge_chart ---
# Modified: chart_dir is now passed as an argument
def plot_gauge_chart(value, min_val, max_val, title, filename, chart_dir, target_val=None, units="", current_color='blue', target_color='green'):
    """
    Generates and saves a gauge chart.
    value: The current value to display.
    min_val, max_val: The min and max values for the gauge range.
    title: Title of the chart.
    filename: Name of the file to save (e.g., "price_gauge.png").
    chart_dir: The absolute path to the directory where charts should be saved.
    target_val: Optional target value to highlight.
    units: Units to display (e.g., "$", "%").
    current_color: Color for the current value indicator.
    target_color: Color for the target value indicator.
    """
    if not os.path.exists(chart_dir):
        os.makedirs(chart_dir)

    # Calculate angle for the current value (from 180 to 0 degrees)
    # 0 degrees at right, 180 degrees at left (standard polar coordinates)
    # Gauge goes from 0 to 180, so 0 maps to 180, max maps to 0
    angle_range = 180
    if max_val == min_val: # Avoid division by zero
        angle = 90 # Center if range is zero
    else:
        normalized_value = (value - min_val) / (max_val - min_val)
        angle = 180 - (normalized_value * angle_range) # Scale to 180-0 for visual gauge

    # Calculate angle for target value if present
    target_angle = None
    if target_val is not None:
        if max_val == min_val:
            target_angle = 90
        else:
            normalized_target = (target_val - min_val) / (max_val - min_val)
            target_angle = 180 - (normalized_target * angle_range)

    fig, ax = plt.subplots(figsize=(6, 6))

    # Draw the outer arc of the gauge
    wedge = Wedge((0, 0), 1, 0, 180, width=0.2, fc='lightgray', ec='gray', lw=1)
    ax.add_patch(wedge)

    # Draw the current value indicator (needle)
    # Convert angle from degrees to radians for sin/cos
    x_needle = np.cos(np.radians(angle)) * 0.9 # 0.9 is length of needle
    y_needle = np.sin(np.radians(angle)) * 0.9
    ax.plot([0, x_needle], [0, y_needle], color=current_color, linewidth=3, solid_capstyle='round')

    ax.plot(0, 0, marker='o', color='black', markersize=8) # Center dot
    # Draw target value indicator if present
    if target_angle is not None:
        x_target = np.cos(np.radians(target_angle)) * 1.0 # slightly outside main arc
        y_target = np.sin(np.radians(target_angle)) * 1.0
        ax.plot([x_target], [y_target], marker='^', color=target_color, markersize=12, zorder=5)

    # Add labels for min/max
    ax.text(np.cos(np.radians(180)) * 1.1, np.sin(np.radians(180)) * 1.1, f'{min_val}{units}', ha='center', va='top', fontsize=10)
    ax.text(np.cos(np.radians(0)) * 1.1, np.sin(np.radians(0)) * 1.1, f'{max_val}{units}', ha='center', va='top', fontsize=10)
    # Display current value text
    ax.text(0, -0.1, f'Current: {value:.2f}{units}', ha='center', va='top', fontsize=12, color=current_color)
    if target_val is not None:
        ax.text(0, -0.2, f'Target: {target_val:.2f}{units}', ha='center', va='top', fontsize=12, color=target_color)
    ax.set_title(title, fontsize=14, pad=20)
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.2, 1.2) # Adjusted Y limit to make space for text
    ax.axis('off') # Hide axes
    filepath = os.path.join(chart_dir, filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    plt.close(fig) # Close the figure to free up memory
    print(f"Gauge chart '{title}' saved to {filepath}")
    return filepath # Return the path of the saved chart


# --- Main function to generate all stock insights ---
# Modified: chart_output_dir is a new argument
def generate_stock_insights(ticker_symbol, target_price, chart_output_dir):
    print(f"\n--- Initiating comprehensive analysis for {ticker_symbol} with target price {target_price} ---")
    
    analysis_outputs = {}
    chart_paths = []

    # 1. Fetch yfinance data (info and historical)
    stock_analysis_data = fetch_stock_data(ticker_symbol, period="1y")
    if stock_analysis_data is None:
        analysis_outputs["Error"] = f"Failed to get core data for {ticker_symbol}. Please check the ticker symbol."
        return analysis_outputs, chart_paths
    
    info = stock_analysis_data["info"]
    historical_data = stock_analysis_data["historical_data"]

    # 2. Fetch Finnhub News
    finnhub_news_results = fetch_finnhub_news(ticker_symbol, days_back=7)
    finnhub_news_articles = finnhub_news_results["articles"]
    finnhub_news_error = finnhub_news_results["error"]

    # 3. Fetch Historical Financial Ratios
    historical_ratios = get_historical_financial_ratios(ticker_symbol)

    # Prepare Key Financial Info for display
    current_price_display = info.get('currentPrice') or info.get('previousClose')
    currency_symbol = info.get('currency', '$')

    key_financial_info_output = {
        "Stock": ticker_symbol,
        "Current Price (Prev Close)": f"{currency_symbol}{current_price_display:.2f}" if isinstance(current_price_display, (int, float)) else "N/A",
        "P/E Ratio": f"{info.get('peRatio'):.2f}" if isinstance(info.get('peRatio'), (int, float)) else "N/A",
        "Book Value": f"{currency_symbol}{info.get('bookValue'):.2f}" if isinstance(info.get('bookValue'), (int, float)) else "N/A",
        "EPS": f"{currency_symbol}{info.get('earningsPerShare'):.2f}" if isinstance(info.get('earningsPerShare'), (int, float)) else "N/A",
        "Sector": info.get('sector', 'N/A'),
        "Industry": info.get('industry', 'N/A')
    }
    analysis_outputs["Key Financial Info"] = key_financial_info_output

    # 4. Generate Charts
    print("\n--- Generating Charts ---")
    # Pass chart_output_dir to plotting functions
    candlestick_chart_path = plot_candlestick_chart(historical_data, ticker_symbol, chart_output_dir)
    if candlestick_chart_path:
        chart_paths.append(candlestick_chart_path)
    
    financial_ratios_chart_path = plot_financial_ratios_multiples(historical_ratios, ticker_symbol, chart_output_dir)
    if financial_ratios_chart_path:
        chart_paths.append(financial_ratios_chart_path)

    current_price_for_gauge = info.get('currentPrice') or info.get('previousClose')
    if isinstance(current_price_for_gauge, (int, float)):
        gauge_min = min(current_price_for_gauge, target_price) * 0.8
        gauge_max = max(current_price_for_gauge, target_price) * 1.2
        if gauge_max - gauge_min < 0.01:
            gauge_min = current_price_for_gauge * 0.9
            gauge_max = current_price_for_gauge * 1.1
            if gauge_max - gauge_min < 0.01:
                gauge_min = 0
                gauge_max = max(current_price_for_gauge, target_price, 10) * 1.2
        
        gauge_chart_path = plot_gauge_chart(
            value=current_price_for_gauge,
            min_val=gauge_min,
            max_val=gauge_max,
            title=f'{ticker_symbol} Price vs. Target',
            filename=f'{ticker_symbol}_price_gauge.png',
            chart_dir=chart_output_dir, # Pass the specific directory name
            target_val=target_price,
            units=currency_symbol
        )
        if gauge_chart_path:
            chart_paths.append(gauge_chart_path)
    else:
        print(f"Skipping Gauge Chart for {ticker_symbol}: Current price data not available or invalid.")

    # 5. AI-Powered News Analysis
    print("\n--- Starting AI-Powered News Analysis ---")
    news_analysis_results = analyze_news_with_gemini(finnhub_news_articles)
    news_output = ""
    if finnhub_news_error:
        news_output += f"**Warning: Could not fetch Finnhub news headlines. Reason: {finnhub_news_error}**\n\n"
    news_output += f"**Themes:** {news_analysis_results['themes']}\n\n"
    news_output += f"**Sentiment:** {news_analysis_results['sentiment']}\n\n"
    news_output += f"**Implications:** {news_analysis_results['implications']}"
    analysis_outputs["AI News Analysis (Headlines)"] = news_output

    # 6. AI-Powered Financial Data Analysis
    print("\n--- Starting AI-Powered Financial Data Analysis ---")
    financial_analysis_results = analyze_financials_with_gemini(info)
    financial_output = f"**Company Overview:** {financial_analysis_results['company_overview']}\n\n"
    financial_output += f"**Valuation Insight:** {financial_analysis_results['valuation_insight']}\n\n"
    financial_output += f"**Strategic Context:** {financial_analysis_results['strategic_context']}"
    analysis_outputs["AI Financial Analysis (Company & Valuation)"] = financial_output

    # 7. AI-Powered Warren Buffett Framework Analysis
    print("\n--- Starting AI-Powered Warren Buffett Framework Analysis ---")
    buffett_analysis_results = analyze_with_buffett_framework(info)
    buffett_output = f"**Understandable Business:** {buffett_analysis_results['understandable_business']}\n\n"
    buffett_output += f"**Economic Moat:** {buffett_analysis_results['economic_moat']}\n\n"
    buffett_output += f"**Consistent Earnings:** {buffett_analysis_results['consistent_earnings']}\n\n"
    buffett_output += f"**Management Quality:** {buffett_analysis_results['management_quality']}\n\n"
    buffett_output += f"**Valuation Comment:** {buffett_analysis_results['valuation_comment']}"
    analysis_outputs["AI Warren Buffett Framework Assessment"] = buffett_output

    # 8. Basic Valuation Insight (Numerical Comparison)
    numerical_valuation_output = ""
    current_price_numerical = info.get('currentPrice') or info.get('previousClose')
    if current_price_numerical is not None and isinstance(current_price_numerical, (int, float)):
        numerical_valuation_output += f"Your Target Price: {currency_symbol}{target_price:.2f}\n\n"
        numerical_valuation_output += f"Current Price: {currency_symbol}{current_price_numerical:.2f}\n\n"
        if current_price_numerical > target_price:
            numerical_valuation_output += "Insight: Current price is **ABOVE** your target price. Consider if it's overvalued for your strategy."
        elif current_price_numerical < target_price:
            numerical_valuation_output += "Insight: Current price is **BELOW** your target price. This might be a potential opportunity based on your target."
        else:
            numerical_valuation_output += "Insight: Current price is **AT** your target price."
    else:
        numerical_valuation_output += "Insight: Cannot provide numerical valuation insight, current price not available or invalid."
    analysis_outputs["Basic Valuation Insight (Numerical Comparison)"] = numerical_valuation_output

    print("\n--- Comprehensive analysis complete. ---")
    return analysis_outputs, chart_paths


# --- Main execution block for direct testing of stock_insight_core.py ---
if __name__ == "__main__":
    print("\n--- Running stock_insight_core.py in standalone test mode ---")
    # For standalone testing, we still need a chart directory.
    # We'll use a relative path from the current working directory for simplicity here.
    # In a real app like Streamlit, you'd pass the correct path.
    test_chart_dir = os.path.join(os.getcwd(), 'charts_test')
    if not os.path.exists(test_chart_dir):
        os.makedirs(test_chart_dir)
        print(f"Created temporary chart directory for testing: {test_chart_dir}")

    TICKER_SYMBOL_TEST = input("Enter the stock ticker symbol for testing (e.g., GOOGL, AAPL, RELIANCE.NS): ").strip().upper()
    
    TARGET_PRICE_TEST = 0.0
    while True:
        try:
            TARGET_PRICE_TEST_STR = input(f"Enter a test target price for {TICKER_SYMBOL_TEST} (e.g., 180.00): ").strip()
            TARGET_PRICE_TEST = float(TARGET_PRICE_TEST_STR)
            break
        except ValueError:
            print("Invalid input. Please enter a numerical value for the target price.")

    # Call the main insights generation function with the test chart directory
    full_analysis_results, generated_chart_paths = generate_stock_insights(TICKER_SYMBOL_TEST, TARGET_PRICE_TEST, test_chart_dir)

    # Display results for standalone testing
    print("\n===== FULL ANALYSIS RESULTS (Standalone Test) =====")
    for section_title, content in full_analysis_results.items():
        print(f"\n--- {section_title} ---")
        if isinstance(content, dict):
            for key, value in content.items():
                print(f"  {key}: {value}")
        else:
            print(content)
    
    print("\n--- Generated Chart Paths (Standalone Test) ---")
    if generated_chart_paths:
        for path in generated_chart_paths:
            print(f"- {path}")
    else:
        print("No charts were generated.")

    print("\n--- Standalone testing of stock_insight_core.py finished ---")