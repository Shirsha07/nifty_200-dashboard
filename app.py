import subprocess
import sys
import os
import time  # Import the time module
import datetime
import streamlit as st  # Import at the top level, outside the function.
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --- Check if streamlit is installed, if not, install it ---
def install_streamlit():
    try:
        import streamlit
        print("Streamlit is already installed.")
        return  # Exit the function if already installed
    except ModuleNotFoundError:
        print("Streamlit is not installed. Installing...")
        try:
            # Ensure pip is installed and in the PATH.  Use sys.executable to get the correct pip.
            process = subprocess.Popen(
                [sys.executable, '-m', 'ensurepip', '--upgrade'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"Error running ensurepip: {stderr.decode()}")
                sys.exit(1)

            process = subprocess.Popen(
                [sys.executable, '-m', 'pip', 'install', 'streamlit', '--upgrade'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                print(f"Error installing Streamlit: {stderr.decode()}")
                print(f"Command output: {stdout.decode()} {stderr.decode()}")  # Print both stdout and stderr
                sys.exit(1)
            import streamlit  # Import after successful installation
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


# --- Nifty 200 stock list ---
NIFTY_200_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO",
    "BAJFINANCE", "BAJAJFINSV", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB",
    "DLF", "DABUR", "EICHERMOT", "GAIL", "GRASIM", "HCLTECH", "HDFC", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INFY", "INDUSINDBK", "ITC", "JSWSTEEL",
    "KOTAKBANK", "LTIM", "LT", "M&M", "MARUTI", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBIN",
    "SHREECEM", "SUNPHARMA", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO", "ADANIGREEN",
    "ADANITRANS", "ALKEM", "AMBUJACEM", "APOLLOTYRE", "ARVIND", "ASHOKLEY", "BALKRISIND", "BANKBARODA",
    "BEL", "BHARATFORG", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN", "CONCOR", "CUMMINSIND",
    "FEDERALBNK", "GLAND", "HAVELLS", "HCLTECH", "HDFC", "HDFCAMC", "HEC", "ICICIACCI", "ICICIGI",
    "ICICIPRULI", "IGL", "INDIAMART", "INDIANHOTEL", "IEX", "IRCTC", "JUBLFOOD", "LALPATHLAB", "LIC Housing Finance",
    "LUPIN", "M&MFIN", "MOTHERSUMI", "MRF", "MUTHOOLFIN", "NAVINFLOUR", "OBEROIRLTY", "PAGEIND", "PEL",
    "PIIND", "PNB", "POLYCAB", "SBICARD", "SIEMENS", "SRF", "SRTRANSFIN", "STARHEALTH", "TATACONSUM",
    "TATAMOTORS", "TATASTEEL", "TVSMOTOR", "ACC", "AMARAJABAT", "BAJAJELEC", "BANDHANBNK", "BANKINDIA",
    "BASF", "BBTC", "BERGEPAINT", "BLUEDART", "CENTRALBK", "CGPOWER", "COROMANDEL", "CROMPTON",
    "DELTACORP", "DHANUKA", "DISHTV", "EIHOTEL", "EMAMILTD", "ESCORTS", "EXIDEIND", "FORTIS", "FRETAIL",
    "GDL", "GESC", "GNFC", "GODREJAGRO", "GODREJCP", "GPPL", "GSPL", "GUJGASLTD", "HEIDELBERG", "HFCL",
    "HIKAL", "HINDPETRO", "HUDCO", "IBULHSGFIN", "IDBI", "IDFC", "IOLCP", "IPCALAB", "JBCHEPHARM", "JKCEMENT",
    "JKLAKSHMI", "JMCPROJECTS", "JSL", "JUSTDIAL", "KAJARIACER", "KALPATPOWR", "KANSAINER", "KARURVYSYA", "KEI",
    "KIOCL", "KPRMILL", "KRBL", "KSCL", "L&TFH", "LAURUSLABS", "LTTS", "MANAPPURAM", "MASTEK", "MAXHEALTH",
    "MCX", "METROPOLIS", "MGL", "MINDACORP", "MINDTREE", "MMTC", "MPL", "MRPL", "NCC", "NESTLEIND", "NETWORK18",
    "NHPC", "NIACL", "NMDC", "NRBBEARING", "ORIENTBANK", "ORIENTCEM", "PAYTM", "PFC", "PGHH", "PHOENIXLTD", "PRESTIGE",
    "PRINCEPIPE", "QUESS", "RAIN", "RALLIS", "RAMCOCEM", "RATNAMANI", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", "SANOFI",
    "SJVN", "SOUTHBANK", "SPARC", "SUMICHEM", "SUNDARMFIN", "SUNTV", "SYNGENE", "TATACHEM", "TATAMTRDVR", "TBZ",
    "THERMAX", "THOMASCOOK", "TIINDIA", "TIMKEN", "TORNTPOWER", "TRENT", "TRITURBINE", "TTKPRESTIG", "UNIONBANK", "VAIBHAVGBL",
    "VAKILAND", "VEDL", "VENKEYS", "WELCORP", "WHIRLPOOL", "ZEEL"
]

# --- Function to fetch historical data ---
@st.cache_data(ttl=600)  # Cache for 10 minutes
def fetch_stock_data(symbol, period, interval, retries=3, delay=5):  # Added retries and delay
    for attempt in range(retries):
        try:
            data = yf.download(symbol + ".NS", period=period, interval=interval)
            if data.empty:
                st.warning(f"No data found for {symbol} on attempt {attempt + 1}.")
                return pd.DataFrame()
            return data
        except Exception as e:
            error_message = str(e)  # Get the error message
            st.error(f"Error fetching data for {symbol} on attempt {attempt + 1}: {error_message}")
            if attempt < retries - 1:  # Only wait if there are more retries
                time.sleep(delay)  # Wait before retrying
            else:
                return pd.DataFrame()  # Return empty DataFrame after all retries fail



# --- Function to calculate top gainers and losers ---
def get_top_gainers_losers(df):
    if not df.empty:
        df['Change'] = df['Close'].pct_change() * 100
        gainers = df.nlargest(5, 'Change')
        losers = df.nsmallest(5, 'Change')
        return gainers[['Close', 'Change']].rename(columns={'Close': 'Price'}), losers[['Close', 'Change']].rename(
            columns={'Close': 'Price'})
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

selected_stock = st.sidebar.selectbox("Select Stock", NIFTY_200_STOCKS)
timeframe = st.sidebar.selectbox("Select Timeframe", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)
interval = "1d"  # Hardcoded interval to be 1d
today = datetime.date.today()
today_str = today.strftime("%Y-%m-%d")
gainers_df = pd.DataFrame(columns=['Price', 'Change (%)'])
losers_df = pd.DataFrame(columns=['Price', 'Change (%)'])

# Fetch data for all Nifty 200 stocks for calculating gainers/losers
st.subheader("Top 5 Gainers (Daily)")
st.subheader("Top 5 Losers (Daily)")
nifty200_data = {}
progress_bar = st.progress(0)
for i, stock in enumerate(NIFTY_200_STOCKS):
    for attempt in range(3):  # Retry 3 times
        try:

            data = yf.download(stock + ".NS", start=today_str, end=today_str, interval="1d",
                                   progress=False)  # Fetch daily data
            if data is not None and not data.empty:
                nifty200_data[stock] = data
                break  # If successful, break the retry loop
            else:
                print(f"No data found for {stock} on {today_str} attempt {attempt + 1}")
                time.sleep(5)  # Wait 5 seconds before retrying
        except Exception as e:
            print(f"Error fetching data for {stock} attempt {attempt + 1}: {e}")
            time.sleep(5)  # Wait before retry
    progress_bar.progress((i + 1) / len(NIFTY_200_STOCKS))

# Calculate and display top 5 gainers and losers
if nifty200_data:
    latest_prices = {}
    for stock, data in nifty200_data.items():
        if not data.empty:
            try:
                latest_prices[stock] = data['Close'].iloc[-1]
            except IndexError:
                print(f"IndexError: No close price found for {stock} on {today_str}")
                latest_prices[stock] = None  # Set to None if no close price

    valid_prices = {stock: price for stock, price in latest_prices.items() if price is not None}

    if len(valid_prices) > 1:  # Need at least two stocks to calculate change
        previous_prices = {}
        for stock, data in nifty200_data.items():
            if not data.empty and len(data) > 1:
                try:
                    previous_prices[stock] = data['Close'].iloc[-2]
                except IndexError:
                    print(f"IndexError: No previous close price found for {stock} on {today_str}")
                    previous_prices[stock] = None
        valid_previous_prices = {stock: price for stock, price in previous_prices.items() if
                                 price is not None}  #  Create a dict with valid previous prices

        # Calculate changes only for stocks with both latest and previous prices
        common_stocks = set(valid_prices.keys()) & set(valid_previous_prices.keys())
        if common_stocks:
            changes = {
                stock: ((valid_prices[stock] - valid_previous_prices[stock]) / valid_previous_prices[stock]) * 100
                for stock in common_stocks
            }

            sorted_changes = sorted(changes.items(), key=lambda item: item[1], reverse=True)
            top_gainers = sorted_changes[:5]
            top_losers = sorted(changes.items(), key=lambda item: item[1])[:5]

            for stock, change in top_gainers:
                gainers_df.loc[stock] = [valid_prices[stock], f"{change:.2f}"]
            for stock, change in top_losers:
                losers_df.loc[stock] = [valid_prices[stock], f"{change:.2f}"]
        else:
            st.warning("Not enough data to calculate gainers/losers.")
    else:
        st.warning("Not enough stocks with valid prices to calculate gainers/losers.")
else:
    st.warning("Could not fetch Nifty 200 daily data.")

st.dataframe(gainers_df)
st.dataframe(losers_df)

# Identify and display stocks in a strong upward trend
st.subheader("Stocks in Strong Upward Trend (Recent)")
trending_stocks = []
# Fetch historical data for trend analysis (adjust period as needed)
historical_data_trend = yf.download([stock + ".NS" for stock in NIFTY_200_STOCKS], period="1mo",
                                       interval="1d", progress=False)
if isinstance(historical_data_trend, pd.DataFrame):
    for stock in NIFTY_200_STOCKS:
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
