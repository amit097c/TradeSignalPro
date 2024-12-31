import requests

import os
import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime
import pytz

#os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets/v2'
os.environ['APCA_API_BASE_URL'] = 'https://data.alpaca.markets/v2'
API_KEY = 'PKMXFOXOMDPMNUMB3TXR'
API_SECRET = '64LdMS9gQnAf4bm8el3NIhNkuuj3slpG3lfvde6p'
BASE_URL = os.environ['APCA_API_BASE_URL']


def convert_to_utc1(ny_time_str: str) -> str:
    """
    Convert a New York time string to UTC in the format required by the Alpaca API.

    :param ny_time_str: The date and time string in New York time (format: 'YYYY-MM-DD HH:MM:SS').
    :return: The corresponding UTC time string (format: 'YYYY-MM-DDTHH:MM:SSZ').
    """
    ny_tz = pytz.timezone('America/New_York')
    utc_tz = pytz.timezone('UTC')
    #ny_time_str = ny_time_str.replace('T', ' ') + ':00'
    print(' ny_time_str ', ny_time_str)

    ny_time = ny_tz.localize(datetime.strptime(ny_time_str, '%Y-%m-%d %H:%M:%S'))
    utc_time = ny_time.astimezone(utc_tz)
    return utc_time.strftime('%Y-%m-%dT%H:%M:%SZ')

def convert_to_ny_time(utc_time_str: str) -> str:
    """
    Convert a UTC time string to New York time in the format required.

    :param utc_time_str: The date and time string in UTC (format: 'YYYY-MM-DDTHH:MM:SSZ').
    :return: The corresponding New York time string (format: 'YYYY-MM-DD HH:MM:SS').
    """
    utc_tz = pytz.timezone('UTC')
    ny_tz = pytz.timezone('America/New_York')
    utc_time = utc_tz.localize(datetime.strptime(utc_time_str, '%Y-%m-%dT%H:%M:%SZ'))
    ny_time = utc_time.astimezone(ny_tz)
    return ny_time.strftime('%Y-%m-%d %H:%M:%S')

def convert_bars_to_ny_time(bars: pd.DataFrame) -> pd.DataFrame:
    """
    Convert the datetime index of the bars DataFrame from UTC to New York time.

    :param bars: DataFrame with the historical data.
    :return: DataFrame with the datetime index converted to New York time.
    """
    ny_tz = pytz.timezone('America/New_York')
    bars.index = bars.index.tz_convert(ny_tz)
    return bars

def fetch_historical_data(symbol: str, start_date: str, end_date: str, timeframe: str) -> pd.DataFrame:
    """
    Fetch historical data from Alpaca for a given symbol.


    :param symbol: The ticker symbol for the stock (e.g., 'AAPL').
    :param start_date: The start date for historical data (format: 'YYYY-MM-DD').
    :param end_date: The end date for historical data (format: 'YYYY-MM-DD').
    :param timeframe: The timeframe for the data ('minute', 'hour', 'day').
    :return: A list of historical data for the given symbol.
    """
    # Ensure BASE_URL is a string and valid
    if not isinstance(BASE_URL, str):
        raise ValueError("BASE_URL must be a string")

    # Create an API object
    api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')
    # Fetch historical data

    bars = api.get_bars(
        symbol,
        timeframe,
        start=convert_to_utc1(start_date),
        end=convert_to_utc1(end_date)
    ).df  # Convert to pandas DataFrame

    bars = convert_bars_to_ny_time(bars)
    print('bars: ', bars)
    return bars


def execute_strategy(stock):
    # Example of 50-day moving average strategy
    historical_data = stock.historicaldata_set.order_by('date')
    print(historical_data.count())
    signals = []
    active_buys = 0
    for i in range(50, len(historical_data)):  # since it is 50 day ma, i will start from 50
        avg_price = sum(
            [entry.close_price for entry in historical_data[i - 50:i]]) / 50  #calculated the avg of 50 entires back from i and divide by 50
        # Previous and current close prices
        previous_close = historical_data[i - 1].close_price
        current_close = historical_data[i].close_price

        # Buy signal: previous close below avg and current close above avg
        if previous_close < avg_price and current_close > avg_price:
            print('buy', 'previous: ', previous_close, 'avg ', avg_price, 'current ', current_close)
            signals.append({'date': historical_data[i].date, 'type': 'BUY', 'price': current_close})
            active_buys += 1
            # Sell signal: previous close above avg and current close below avg
        elif previous_close > avg_price and current_close < avg_price:
            if active_buys > 0:
                print('sell', 'previous: ', previous_close, 'avg ', avg_price, 'current ', current_close)
                signals.append({'date': historical_data[i].date, 'type': 'SELL', 'price': current_close})
                active_buys -= 1
    print(signals)
    return signals
