# EquityOS

What this project is

EquityOS is an interactive, AI-assisted stock analysis system built as a Streamlit application.

It combines:

market data

company fundamentals

historical financial ratios

news and retail sentiment

LLM-based qualitative analysis

into a single, structured analysis flow.

This is not an automated trading system.

It is a decision-support tool designed to reduce noise and surface context.

What problem it solves

Retail investors typically analyze stocks across disconnected sources:

price charts

financial websites

news articles

social media sentiment

EquityOS pulls these signals together and:

structures them 

separates raw data from AI interpretation

makes assumptions and limitations visible

System overview:

1. Data ingestion:

For a given ticker:

Price & company data via Yahoo Finance

News headlines via Finnhub

Historical financial ratios via Finnhub (ROE, margins, liquidity, etc.)

Retail discussion from Reddit (multiple finance subreddits)

3. Quantitative layer
 
The system generates:

Candlestick price chart

Multi-year financial ratio charts

A price-vs-target (user-defined reference point)

These are rendered as interactive Plotly charts inside Streamlit.

6. AI analysis layer
 
Using Google Gemini:

News sentiment & theme analysis

Financial overview and valuation commentary

Buffett-style qualitative business assessment

Retail market pulse synthesis from Reddit discussions

LLMs are used only after data collection, not as a data source.

What this system does not do

No price forecasting or return prediction

No portfolio optimization

No buy/sell recommendations

Target price is treated as a user reference, not a model output.

Limitations:

Financial ratios depend on Finnhub availability and quality

Reddit sentiment is noisy and not statistically representative

LLM outputs can reflect framing bias in prompts

Qualitative analysis should not be treated as ground truth

This tool supports thinking — it does not replace judgment.

Intended audience:

Retail investors who want structured context

Analysts experimenting with AI-assisted workflows

Developers exploring LLM integration in financial tools

-This is an exploratory MVP focused on integration and reasoning flow.
Accuracy, evaluation, and robustness would be the next step






