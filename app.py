import subprocess
import sys
import os

# --- Check if streamlit is installed, if not, install it ---
def install_streamlit():
    try:
        import streamlit as st
        print("Streamlit is already installed.")
        return  # Exit the function if already installed
    except ModuleNotFoundError:
        print("Streamlit is not installed. Installing...")
        try:
            # Ensure pip is installed and in the PATH.  Use sys.executable to get the correct pip.
            subprocess.check_call([sys.executable, '-m', 'ensurepip', '--upgrade'])
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'streamlit', '--upgrade'])
            import streamlit as st  # Import after successful installation
            print("Streamlit has been successfully installed.")
            return
        except subprocess.CalledProcessError as e:
            print(f"Error installing Streamlit: {e}")
            print(f"Command output: {e.output}")  # Print the output of the failed command
            print(
                "Please make sure you have a working Python installation with pip.  "
                "You may need to install build tools or other dependencies required to install Streamlit."
            )
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during installation: {e}")
            sys.exit(1)

install_streamlit()  # Ensure Streamlit is installed

import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import time

# --- Function to fetch Nifty 200 stock list ---
@st.cache_data(ttl=600)  # Cache for 10 minutes (600 seconds)
def get_nifty200_stocks():
    nifty200_url = "https://www.nseindia.com/content/indices/ind_nifty200list.csv"
    try:
        df = pd.read_csv(nifty200_url)
        return sorted(df['Symbol'].tolist())
    except Exception as e:
        st.error(f"Error fetching Nifty 200 list: {e}")
        return []

# --- Function to fetch historical data ---
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_stock_data(symbol, period, interval):
    try:
        data = yf.download(symbol + ".NS", period=period, interval=interval)
        return data
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

# --- Function to calculate top gainers and losers ---
def get_top_gainers_losers(df):
    if not df.empty:
        df['Change'] = df['Close'].pct_change() * 100
        gainers = df.nlargest(5, 'Change')
        losers = df.nsmallest(5, 'Change')
        return gainers[['Close', 'Change']].rename(columns={'Close': 'Price'}), losers[['Close', 'Change']].rename(columns={'Close': 'Price'})
    return pd.DataFrame(), pd.DataFrame()

# --- Function to identify stocks in a strong upward trend (simple heuristic) ---
def identify_upward_trend(df):
    if len(df) < 20:
        return False
    # Check if the last 5 closing prices are consistently higher
    for i in range(1, 5):
        if df['Close'].iloc[-i] <= df['Close'].iloc[-(i + 1)]:
            return False
    # Check if the short-term moving average is above the long-term moving average
    df['SMA_5'] = ta.trend.sma_indicator(df['Close'], window=5)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    if df['SMA_5'].iloc[-1] > df['SMA_20'].iloc[-1]:
        return True
    return False

# --- Main Streamlit application ---
st.title("Interactive Nifty 200 Dashboard")

nifty200_stocks = get_nifty200_stocks()
if not nifty200_stocks:
    st.error("Failed to fetch Nifty 200 stocks. Please check your internet connection and try again.")
    st.stop()

selected_stock = st.sidebar.selectbox("Select Stock", nifty200_stocks)
timeframe = st.sidebar.selectbox("Select Timeframe", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = st.sidebar.selectbox("Select Interval", ["1d", "1wk", "1mo"], index=0)

# Fetch data for all Nifty 200 stocks for current day to calculate gainers/losers
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")
nifty200_latest_data = {}
progress_bar = st.progress(0)
for i, stock in enumerate(nifty200_stocks):
    try:
        data = yf.download(stock + ".NS", start=today_str, end=today_str, interval="5m", progress=False) # Changed to 5m interval
        if not data.empty:
            nifty200_latest_data[stock] = data
    except Exception as e:
        print(f"Error fetching data for {stock}: {e}")
    progress_bar.progress((i + 1) / len(nifty200_stocks))

latest_prices_df = pd.DataFrame()
for stock, data in nifty200_latest_data.items():
    if not data.empty:
        latest_prices_df.loc[stock, 'Close'] = data['Close'].iloc[-1]

# Calculate and display top 5 gainers and losers
st.subheader("Top 5 Gainers (Intraday)")
gainers_df = pd.DataFrame(columns=['Price', 'Change (%)'])
losers_df = pd.DataFrame(columns=['Price', 'Change (%)'])

if nifty200_latest_data:
    latest_prices = {stock: data['Close'].iloc[-1] for stock, data in nifty200_latest_data.items() if not data.empty}
    if len(nifty200_latest_data) > 1: #Need atleast 2 data points.
        previous_prices = {stock: data['Close'].iloc[-2] for stock, data in nifty200_latest_data.items() if not data.empty and len(data['Close']) > 1}
        if latest_prices and previous_prices:
            changes = {stock: ((latest_prices[stock] - previous_prices[stock]) / previous_prices[stock]) * 100 for stock in latest_prices if stock in previous_prices}
            sorted_changes = sorted(changes.items(), key=lambda item: item[1], reverse=True)
            top_gainers = sorted_changes[:5]
            top_losers = sorted(changes.items(), key=lambda item: item[1])[:5]
            for stock, change in top_gainers:
                gainers_df.loc[stock] = [latest_prices[stock],  f"{change:.2f}"]
            for stock, change in top_losers:
                losers_df.loc[stock] = [latest_prices[stock], f"{change:.2f}"]
        else:
             st.warning("Insufficient data to calculate gainers/losers.  May need to wait for more market data.")
    else:
        st.warning("Insufficient data to calculate gainers/losers.  May need to wait for more market data.")

else:
    st.warning("Could not fetch Nifty 200 latest data.")
st.dataframe(gainers_df)
st.subheader("Top 5 Losers (Intraday)")
st.dataframe(losers_df)

# Identify and display stocks in a strong upward trend
st.subheader("Stocks in Strong Upward Trend (Recent)")
trending_stocks = []
# Fetch historical data for trend analysis (adjust period as needed)
historical_data_trend = yf.download([stock + ".NS" for stock in nifty200_stocks], period="1mo", interval="1d", progress=False)
if isinstance(historical_data_trend, pd.DataFrame):
    for stock in nifty200_stocks:
        if stock in historical_data_trend.columns.levels[1]:
            stock_data = historical_data_trend['Close'][stock].dropna()
            if identify_upward_trend(stock_data.to_frame()):
                trending_stocks.append(stock)
    if trending_stocks:
        st.write(", ".join(trending_stocks))
    else:
        st.write("No stocks currently showing a strong upward trend based on the criteria.")
else:
    st.warning("Could not fetch data to identify upward trending stocks.")

# Display data and charts for the selected stock
if selected_stock:
    stock_data = fetch_stock_data(selected_stock, timeframe, interval)
    if not stock_data.empty:
        st.subheader(f"{selected_stock} - Open, High, Low, Close")
        latest_data = stock_data.iloc[-1]
        ohlc_52wk = pd.DataFrame({
            'Open': [latest_data['Open']],
            'High': [latest_data['High']],
            'Low': [latest_data['Low']],
            'Close': [latest_data['Close']],
            '52 Week High': [stock_data['High'].max()],
            '52 Week Low': [stock_data['Low'].min()]
        })
        st.dataframe(ohlc_52wk)

        # Candlestick Chart
        st.subheader(f"{selected_stock} - Candlestick Chart ({timeframe}, {interval})")
        fig_candlestick = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                                     open=stock_data['Open'],
                                                     high=stock_data['High'],
                                                     low=stock_data['Low'],
                                                     close=stock_data['Close'])])
        st.plotly_chart(fig_candlestick, use_container_width=True)

        # Technical Indicators
        st.subheader(f"{selected_stock} - Technical Indicators ({timeframe}, {interval})")
        stock_data['SMA_20'] = ta.trend.sma_indicator(stock_data['Close'], window=20)
        stock_data['RSI'] = ta.momentum.rsi(stock_data['Close'], window=14)
        stock_data.dropna(inplace=True)

        fig_indicators = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                       vertical_spacing=0.1,
                                       row_heights=[0.7, 0.3])

        fig_indicators.add_trace(go.Candlestick(x=stock_data.index,
                                                open=stock_data['Open'],
                                                high=stock_data['High'],
                                                low=stock_data['Low'],
                                                close=stock_data['Close'],
                                                name='Candlestick'), row=1, col=1)

        fig_indicators.add_trace(go.Scatter(x=stock_data.index, y=stock_data['SMA_20'],
                                             line=dict(color='blue'), name='SMA 20'), row=1, col=1)

        fig_indicators.add_trace(go.Scatter(x=stock_data.index, y=stock_data['RSI'],
                                             line=dict(color='purple'), name='RSI'), row=2, col=1)

        fig_indicators.add_hline(y=70, line=dict(color='red', dash='dash'), row=2, col=1)
        fig_indicators.add_hline(y=30, line=dict(color='green', dash='dash'), row=2, col=1)

        fig_indicators.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_indicators, use_container_width=True)
    else:
        st.warning(f"Could not fetch data for {selected_stock} with the selected timeframe and interval.")
