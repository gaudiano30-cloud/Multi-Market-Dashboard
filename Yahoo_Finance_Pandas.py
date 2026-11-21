import requests # Library to communicate with Website (Allow Python to do requeste HTTP vi a Internet Server.)
import pandas as pd # Library to Handle Data and Tables (Structure row-line as excel - Tables)
import numpy as np # Scientific Computing
import time # Library to Handle Time (In our program, it is used to avoid making consecutive requests to Yahoo Finance too quickly, especially when a download fails.)
from datetime import datetime, timezone # Handle time
import matplotlib.pyplot as plt  # Library for data visualization

# datetime: Allows you to represent and manipulate dates and times.

# timezone: Allows you to specify the time zone.


# ==========================================
# 1. EUROPEAN STOCKS
# ==========================================

tickers = {
    "Enel": "ENEL.MI",
    "ENI": "ENI.MI",
    "BASF": "BAS.DE",
    "Airbus": "AIR.PA",
    "Volkswagen": "VOW3.DE"
}

# I use a dictionary to directly associate ticker code with company name. Ticker?

# They are codes used to identify securities on financial markets.


# ==========================================
# 2. YAHOO FINANCE DOWNLOAD FUNCTION
# ==========================================

def scarica_yahoo(ticker, start, end):

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}" # Specify the address to which we send the request f-string is used to pass the ticker provided as argument
    )

    # We have to specify the time interval for which we want the data
    start_timestamp = int(
        datetime.strptime(start, "%Y-%m-%d") # The strptime function transforms a date written as text into a Python date object.
        .replace(tzinfo=timezone.utc) # Here, we assign the date to the UTC time zone. UTC is the international reference for measuring time. Yahoo Finance uses Unix timestamps, so we must specify the time reference.
        .timestamp() # It transforms the data into a number called a Unix timestamp. A Unix timestamp represents the number of seconds that have passed since January 1, 1970, at 00:00 UTC.
    ) # Int transform the result into an integer number
    # Result: 1420070400 -> timestamp for 1° gennaio 2015 at 00:00 UTC.

    end_timestamp = int(
        datetime.strptime(end, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc).timestamp()
    ) # Same procedure for final data

    # Prepare the parameters for the request and we organize them into a dictionary
    # These are the data that yahoo finance need to download the data
    params = {
        "period1": start_timestamp, # Starting time
        "period2": end_timestamp, # Ending time
        "interval": "1d", # Data frequence (1d, 1wk, 1mo, 1h, 5m)
        "events": "div,splits" # Corporate events to include in your response
    }

    # Info about internet request:
    headers = {
        "User-Agent": "Mozilla/5.0" # User-Agent identifies the type of client making the request. # We use a generic identifier that resembles the one used by a browser. # Why do we do this? # Some servers may handle requests differently based on the client making them. # This header can improve the compatibility of the request with Yahoo Finance, although it does not guarantee that the server will always accept the download.
    }

    # The loop will attempt to download data up to three times.
    # Why is this useful?
    # Imagine that Yahoo Finance doesn't respond to the first request due to a temporary connection issue.
    # Rather than immediately aborting the program, Python will try again.
    # This makes the program more robust.
    for tentativo in range(3):
        
        # try to handle exceptions: 1) No connection; 2) Server unavailable; 3) Ticker missing; 4) Incomplete response; 5) Data unavailable.
        try:

            # requests.get -> sends an HTTP GET request to the server.
            response = requests.get(
                url, # Yahoo Finance web address
                params=params, # 	Data and frequency of data
                headers=headers, # Identifier of client
                timeout=30 # Maximum waiting time
            ) # The answer of the server is stored in response
            # response does not contains the data, but an object
            # that represents the HTTP answer of the server

            response.raise_for_status() # ceck if the HTTP request is accomplished

            # HTTP Code Meaning: 200 Request Successful; 400 Bad Request; 401 Unauthorized Access; 404 Resource Not Found; 429 Too Many Requests; 500 Server Error
            # If the server returns an HTTP error code, raise_for_status() throws an exception.
            # This exception will be handled by our except.


            dati = response.json()["chart"]
            # Yahoo Finance returns data in JSON format.
            # JSON is a format used to transmit information between applications.
            # With: response.json(), we transform the response into a Python data structure, typically composed of dictionaries and lists.
            # With ["chart"], we select the section called chart, which contains financial data
            # Not extracting price yet: just entering in the section that contains the data.

            if dati.get("error"): # Control if there is a key in the data diction call error
                raise ValueError(dati["error"]) # In that case, the related message is raised

            risultato = dati["result"] # Extract data

            if not risultato: # Check that the list is not empty
                raise ValueError("Nessun dato disponibile")

            risultato = risultato[0] # It is a list, and index 0 contains the data of the element request

            indicatori = risultato["indicators"] # This instruction enters the indicators section, which contains the indicators and the stock quotes.

            # Search the section adjusted
            adjclose = indicatori.get("adjclose")

            # If suitable prices are available, use them. Otherwise, use the normal closing prices.
            if adjclose and adjclose[0].get("adjclose") is not None:
                valori = adjclose[0]["adjclose"]
            else:
                valori = indicatori["quote"][0]["close"]
            # It will therefore contain the price series that we will use to build the DataFrame.


            date = pd.to_datetime(
                risultato["timestamp"],
                unit="s",
                utc=True
            )
            # Yahoo Finance doesn't directly return dates in human-readable format.
            # It returns Unix timestamps.
            # To convert them to dates, we use:
            # Let's look at the parameters:
                # - result["timestamp"]: Contains the timestamps received from Yahoo.
                # - unit="s": Specifies that timestamps are expressed in seconds.
                # - utc=True: Interprets dates as referring to the UTC time zone.


            # At this point we need to convert the time zone.
            date = (
                date.tz_convert("Europe/Rome") # Converts dates from UTC to Rome time.
                .tz_localize(None)
            )
            # Removes time zone information, keeping the converted date and time.
            # Why do we do this?
            # To have a simple time index, without additional time zone information, more convenient to use with Pandas.


            # Finally we have data:
            # This statement creates a Pandas DataFrame.
            # Let's look at the two elements:
                # - {"Close": values}: Creates a column called Close containing the prices.
                # - index=date: Uses dates as the row index.
            df = pd.DataFrame(
                {"Close": valori},
                index=date
            )

            df.index.name = "Date" # We assign the name Data to the DataFrame index. This improves the readability of the table and exported files.

            return df.dropna() # dropna(), Removes rows containing missing values ​​(NaN). return, Returns the DataFrame to the part of the program that called the function.

        except Exception as e: # Error handling: except
                # This statement traps errors that may occur during the execution of the try block.
                    # Let's look at the components:
                    # - except: handles an error.
                    # - Exception: indicates a general category of Python errors.
                    # - as e: assigns the error to the variable e.
                    # For example, if Yahoo Finance isn't responding, e might contain a timeout message.

            print(
                f"Tentativo {tentativo + 1}/3 "
                f"fallito per {ticker}: {e}"
            ) # Print Error Message

            time.sleep(2) # Python waits two seconds before trying again. This avoids immediately sending another request to the server.

    # Outside the loop if all attempts were empty - Return nothing
    print(f"ATTENZIONE: impossibile scaricare {ticker}")

    return None


# ==========================================
# 3. DOWNLOAD OF THE FIVE STOCKS
# ==========================================

prices_dict = {} # Create Empty Dictionary 

for nome, ticker in tickers.items(): # Metodo iterm restituisce sia la chiave che il valore

    print(f"Download {nome} ({ticker})...") # Messaggio di avanzamento

    dati = scarica_yahoo(
        ticker,
        start="2015-01-01",
        end="2026-01-01"
    )

    if dati is not None and not dati.empty:

        prices_dict[nome] = dati["Close"] # Save dati into the dictionary

        print(
            f"{nome}: {len(dati)} osservazioni scaricate"
        )

    else:

        print(f"{nome}: dati non disponibili")


# ==========================================
# 4. PRICE DATAFRAME CREATION
# ==========================================

if not prices_dict: # Check that the download of the data is not ok
    raise RuntimeError(
        "Nessun titolo scaricato. "
        "Controllare la connessione a Yahoo Finance."
    )

# In our case, it takes all the time series contained in Prices_dict and the combinations into a single DataFrame.
stock_prices = pd.concat( # pd.concat is used to concatenate pandas objects
    prices_dict,
    axis=1 # Tells Pandas to concatenate the data horizontally, that is, by placing the series side by side as columns. To understand the difference: axis=0: vertical concatenation (one below the other);  axis=1: horizontal concatenation (one next to the other).
)

stock_prices = stock_prices.sort_index() # This statement sorts the DataFrame by its index. In our case, the index is dates. Then the prices are sorted chronologically, from oldest to newest.

print("\nPrezzi adjusted:")
print(stock_prices.tail()) # Print only the last data


# ==========================================
# 5. DAILY LOG RETURNS
# ==========================================

# This is where the np.log() function from the NumPy library comes into play.
stock_returns = np.log(
    stock_prices / stock_prices.shift(1) # The .shift(1) method shifts all values ​​in the DataFrame down one row.
) 

# ==========================================
# 6. MONTHLY AGGREGATION
# ==========================================

# The Pandas .resample() method is used to change the time frequency of the data.
# In our case:
# - stock_prices contains daily prices.
# - "ME" stands for Month End.

monthly_prices = stock_prices.resample("ME").last() # .resmaple("ME"), gather data for month; .last() take lasto observation in the mountly group data

# Rendimenti logaritmici mensili

monthly_returns = np.log(
    monthly_prices / monthly_prices.shift(1)
)

# ==========================================
# 7. RESULTS EXPORT
# ==========================================

# .to_csv(): is a Pandas method that allows you to export a DataFrame in CSV format
# encoding="utf-8-sig": Specifies the file encoding, useful for improving compatibility with Excel, especially with accented characters.
monthly_returns.to_csv(
    "european_stock_returns.csv",
    encoding="utf-8-sig"
)

stock_prices.to_csv(
    "european_stock_prices.csv",
    encoding="utf-8-sig"
)

stock_returns.to_csv(
    "european_daily_returns.csv",
    encoding="utf-8-sig"
)

print("\n================================")
print("DOWNLOAD COMPLETATO")
print("================================")

print("\nTitoli scaricati:")
print(list(prices_dict.keys()))

print("\nRendimenti mensili:")
print(monthly_returns.tail())

print("\nFile CSV creati:")
print("- european_stock_returns.csv")
print("- european_stock_prices.csv")
print("- european_daily_returns.csv")


# ==========================================
# 7. DATA VISUALIZATION
# ==========================================

# GRAPH 1: NORMALIZED STOCK PRICES

# Normalize prices to a base value of 100
normalized_prices = (
    stock_prices.div(stock_prices.iloc[0]) * 100
) # .iloc Allows you to select rows and columns by their position. [0] selects the first row of the DataFrame.
# div() method divides each value in the column by the initial value of the same column.


plt.figure(figsize=(14, 7)) # plt.figure() creates a new figure, which is the space in which the graph will be drawn.
# figsize=(14, 7) defines the figure's dimensions in inches: - 14 inches wide; - 7 inches tall.


# The normalized_prices.columns table contains the names of the DataFrame columns.
# The "Title" field takes the name of each stock, one at a time.
for titolo in normalized_prices.columns:
    plt.plot(
        normalized_prices.index,
        normalized_prices[titolo],
        label=titolo
    ) # plt.plot() draws a line on the chart. Its arguments are:
        # - normalized_prices.index: represents the horizontal (X) axis, i.e., the dates.
        # - normalized_prices[stock]: represents the vertical (Y) axis, i.e., the normalized prices of the selected stock.
        # - label=stock: assigns the stock name to the line.

plt.title("European Stocks - Historical Performance")
plt.xlabel("Date")
plt.ylabel("Normalized Price (Base = 100)")

plt.legend() # Add legend
plt.grid(True) # Grid activated
plt.tight_layout() # Automatically adjusts the spaces between chart elements, preventing titles and labels from overlapping or being cut off.
plt.show() # View the graph on the screen.


# GRAPH 2: MONTHLY LOG RETURNS

plt.figure(figsize=(14, 7))

for titolo in monthly_returns.columns:
    plt.plot(
        monthly_returns.index,
        monthly_returns[titolo] * 100,
        label=titolo
    )

plt.title("European Stocks - Monthly Log Returns")
plt.xlabel("Date")
plt.ylabel("Monthly Log Returns (%)")

plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()






