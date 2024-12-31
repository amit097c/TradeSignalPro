import pandas as pd

from datetime import datetime
import pytz
from celery.app import shared_task
from django.shortcuts import render
import plotly.graph_objs as go
from .models import Stock, HistoricalData, TradingSignal
from .services import fetch_historical_data, execute_strategy
from django.core.exceptions import ObjectDoesNotExist

'''def convert_utc_to_local(utc_dt_str):
    # Parse the datetime string including the timezone info
    utc_dt = datetime.fromisoformat(utc_dt_str)
    # Convert UTC time to local time
    local_tz = pytz.timezone('America/New_York')
    local_dt = utc_dt.astimezone(local_tz)  # Converts to local time zone automatically
    local_dt_str = local_dt.strftime('%Y-%m-%d %H:%M:%S')
    return local_dt_str'''


def convert_utc_to_local(utc_dt_str):
    # Parse the datetime string including the timezone info
    utc_dt = datetime.fromisoformat(utc_dt_str)
    # Convert UTC time to local time
    local_dt = utc_dt.astimezone()  # Converts to local time zone automatically
    local_dt_str = local_dt.strftime('%Y-%m-%d %H:%M:%S')
    return local_dt_str


def localize_to_ny(time_str):
    """Convert a naive datetime string to aware datetime in New York timezone."""
    aware_datetime = datetime.fromisoformat(str(time_str))
    local_tz = pytz.timezone('America/New_York')
   # naive_datetime = datetime.strptime(str(time_str), '%Y-%m-%d %H:%M:%S')
  #  aware_datetime = local_tz.localize(naive_datetime)  # Now it's timezone-aware
    if aware_datetime.tzinfo == local_tz:
        return aware_datetime

        # Convert to NY timezone
    return aware_datetime.astimezone(local_tz)



# Task to fetch data asynchronously
@shared_task
def fetch_data_task(symbol, start_date, end_date, timestamp):
    '''print("Fetching data for {}".format(symbol))
    stock, created = Stock.objects.get_or_create(symbol=symbol)
    # Delete any existing historical data for this stock to maintain consistency

    HistoricalData.objects.filter(stock=stock).delete()
    start_date += ":00"
    end_date += ":00"

    start_date_dt = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%S')
    end_date_dt = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S')

    data = fetch_historical_data(symbol, start_date_dt.strftime('%Y-%m-%d %H:%M:%S'),
                                 end_date_dt.strftime('%Y-%m-%d %H:%M:%S'), timestamp)
    print(f"Data fetched for {symbol}: {data}")

    for time, entry in data.iterrows():
        utc_time_str = str(time)

        aware_ny_time = localize_to_ny(utc_time_str)
        print("NY time (aware):", aware_ny_time)
        print('time: ', convert_utc_to_local(str(time)))  # -4:00 meaning local time is 4 hours behind from utc
        local_tz = pytz.timezone('America/New_York')
        naive_datetime = datetime.strptime(convert_utc_to_local(str(time)), '%Y-%m-%d %H:%M:%S')
        aware_datetime = local_tz.localize(naive_datetime)
        print("aware datetime: ", aware_datetime)
        #ny_datetime = datetime.strptime(str(aware_datetime), '%Y-%m-%d %H:%M:%S')
        HistoricalData.objects.update_or_create(
            stock=stock,
            date=aware_ny_time,
            defaults={
                'open_price': entry['open'],
                'close_price': entry['close'],
                'high_price': entry['high'],
                'low_price': entry['low'],
                'volume': entry['volume'],
            }
        )
    '''

    stock, created = Stock.objects.get_or_create(symbol=symbol)
    # Delete any existing historical data for this stock symbol, to maintain the consistency
    HistoricalData.objects.filter(stock=stock).delete()
    data = fetch_historical_data(symbol, start_date, end_date, timestamp)
    print(data)
    for time, entry in data.iterrows():
        print('time: ', convert_utc_to_local(str(time)))  # -4:00 meaning local time is 4 hours behind from utc

        # Convert to a timezone-aware datetime
        local_tz = pytz.timezone('UTC')
        aware_datetime = localize_to_ny(time)
        utc_datetime = aware_datetime.astimezone(pytz.utc)
        naive_datetime = datetime.strptime(convert_utc_to_local(str(time)), '%Y-%m-%d %H:%M:%S')
        #aware_datetime = local_tz.localize(naive_datetime)
        print('aware datetime: ', aware_datetime)
        HistoricalData.objects.update_or_create(
            stock=stock,
            date=aware_datetime,
            defaults={
                'open_price': entry['open'],
                'close_price': entry['close'],
                'high_price': entry['high'],
                'low_price': entry['low'],
                'volume': entry['volume'],
            }
        )
    print(f"Historical data saved for {symbol}")


# Task to apply the strategy asynchronously
@shared_task
def apply_strategy_task(symbol):
    '''try:
        stock = Stock.objects.get(symbol=symbol)
    except ObjectDoesNotExist:
        print(f"Stock {symbol} does not exist.")
        return

    signals = execute_strategy(stock)
    local_tz = pytz.timezone('America/New_York')

    for signal in signals:
        if 'date' in signal and signal['date'] is not None:
            utc_date = signal['date']
            local_date = utc_date.astimezone(local_tz)
            date = local_date.strftime('%Y-%m-%d %H:%M:%S')
            TradingSignal.objects.update_or_create(
                stock=stock,
                date=local_date,
                defaults={
                    'signal_type': signal['type'],
                    'price': signal['price'],
                }
            )
'''
    stock = Stock.objects.get(symbol=symbol)
    signals = execute_strategy(stock)
    local_tz = pytz.timezone('America/New_York')  # Replace with your desired timezone
    for signal in signals:
        if 'date' in signal and signal['date'] is not None:
            print(signal['date'])  # this is utc time
            utc_date = signal['date']
            local_date = utc_date.astimezone(local_tz)
            date = local_date.strftime('%Y-%m-%d %H:%M:%S')
            print("local date", date)  # this is in ny/america timezone
            TradingSignal.objects.update_or_create(
                stock=stock,
                date=date,  # signal['date'],# in above fetch data date is stored in america/new_york therefore directly took the as it is
                defaults={
                    'signal_type': signal['type'],
                    'price': signal['price'],
                }
            )
    print(f"Strategy applied for {symbol}")

# Task to plot graph asynchronously
