from datetime import datetime, timedelta

import pytz

from django.shortcuts import render, redirect
from datetime import datetime, timezone
from django.shortcuts import render
from django.http import JsonResponse
from . import services
from .forms import FetchDataRange
from .models import Stock, HistoricalData, TradingSignal
from .services import fetch_historical_data, execute_strategy
import plotly.graph_objs as go
import pandas as pd
from django.http import HttpResponse
import io
import os
from django.views import View
import plotly.express as px
from .tasks import fetch_data_task, apply_strategy_task


def home(request):
    return render(request, 'home.html')


def export_to_excel(request, symbol):
    data = TradingSignal.objects.filter(stock__symbol=symbol).values()
    if not data:
        # Handle empty data case
        return HttpResponse("No data found for the specified symbol.", content_type="text/plain")

    df = pd.DataFrame(list(data))
    print("DataFrame:\n", df)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

    buffer.seek(0)
    print("Buffer Size:", len(buffer.getvalue()))
    # Use openpyxl or xlsxwriter as the engine to write to Excel
    response = HttpResponse(buffer.getvalue(),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="model_data.xlsx"'

    return response


def convert_to_ny(utc_time_str: str) -> str:
    """
    Convert a UTC time string to New York time.

    :param utc_time_str: The date and time string in UTC (format: 'YYYY-MM-DDTHH:MM:SSZ').
    :return: The corresponding New York time string (format: 'YYYY-MM-DD HH:MM:SS').
    """
    # Define timezones
    utc_tz = pytz.timezone('UTC')
    ny_tz = pytz.timezone('America/New_York')

    # Parse UTC time string
    utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')  # Change format here
    utc_time = utc_tz.localize(utc_time)

    # Convert to New York time
    ny_time = utc_time.astimezone(ny_tz)

    # Format to 'YYYY-MM-DD HH:MM:SS'
    return ny_time.strftime('%Y-%m-%d %H:%M:%S')


def convert_utc_to_local(utc_dt_str):
    # Parse the datetime string including the timezone info
    utc_dt = datetime.fromisoformat(utc_dt_str)
    # Convert UTC time to local time
    local_dt = utc_dt.astimezone()  # Converts to local time zone automatically
    local_dt_str = local_dt.strftime('%Y-%m-%d %H:%M:%S')
    return local_dt_str


def fetch_data_view(request):
    print(request)
    if request.method == 'POST':
        form = FetchDataRange(request.POST)
        print('this is post method')
        if form.is_valid():
            symbol = form.cleaned_data['symbol']
            start_date = form.cleaned_data['start_date'].strftime('%Y-%m-%d %H:%M:%S')
            end_date = form.cleaned_data['end_date'].strftime('%Y-%m-%d %H:%M:%S')
            timestamp = form.cleaned_data['timeframe']
            stock, created = Stock.objects.get_or_create(symbol=symbol)
            # Delete any existing historical data for this stock symbol, to maintain the consistency
            HistoricalData.objects.filter(stock=stock).delete()
            data = fetch_historical_data(symbol, start_date, end_date, timestamp)
            print(data)
            for time, entry in data.iterrows():
                print('time: ', convert_utc_to_local(str(time)))  # -4:00 meaning local time is 4 hours behind from utc

                # Convert to a timezone-aware datetime
                local_tz = pytz.timezone('America/New_York')
                naive_datetime = datetime.strptime(convert_utc_to_local(str(time)), '%Y-%m-%d %H:%M:%S')
                aware_datetime = local_tz.localize(naive_datetime)
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
            return plot_graph_view_minute(request, symbol)
        return render(request, 'fetch_data.html', {'form': form, 'success': "Form is invalid. Please check the input."})

    else:
        form = FetchDataRange()
        return render(request, 'fetch_data.html', {'form': form, 'success': "progress"})


def apply_strategy_view(request, symbol):
    stock = Stock.objects.get(symbol=symbol)
    signals = execute_strategy(stock)
    local_tz = pytz.timezone('America/New_York')  # Replace with your desired timezone
    for signal in signals:
        if 'date' in signal and signal['date'] is not None:
            print(signal['date'])  #this is utc time
            utc_date = signal['date']
            local_date = utc_date.astimezone(local_tz)
            date = local_date.strftime('%Y-%m-%d %H:%M:%S')
            print("local date", date)  #this is in ny/america timezone
            TradingSignal.objects.update_or_create(
                stock=stock,
                date=date,  #signal['date'],
                defaults={
                    'signal_type': signal['type'],
                    'price': signal['price'],
                }
            )

    return plot_graph_view_minute(request, symbol)  #JsonResponse({'status': 'Strategy applied successfully'})


def plot_graph_view_minute(request, symbol):
    try:
        stock = Stock.objects.get(symbol=symbol)
    except Stock.DoesNotExist:
        print("stock not found")
        return render(request, 'graph.html',
                      {'message': f"Stock with symbol '{symbol}' not found.", 'symbol': 'not found'})

    # Filter historical data for 1-minute granularity
    historical_data = HistoricalData.objects.filter(stock=stock).order_by('date')

    if not historical_data.exists():
        return render(request, 'graph.html',
                      {'message': f"No historical data found for stock symbol '{symbol}'.", 'symbol': 'not found'})

    print("plot graph data: ", historical_data)
    # dates = [data.date.strftime('%H:%M') for data in historical_data]
    # open_prices = [data.open_price for data in historical_data]
    # high_prices = [data.high_price for data in historical_data]
    # low_prices = [data.low_price for data in historical_data]
    # close_prices = [data.close_price for data in historical_data]
    local_tz = pytz.timezone('America/New_York')  # Replace with your desired timezone

    dates = []
    open_prices = []
    high_prices = []
    low_prices = []
    close_prices = []
    for data in historical_data:
        utc_date = data.date
        local_date = utc_date.astimezone(local_tz)  # Convert UTC to local timezone
        dates.append(local_date.strftime('%Y-%m-%d %H:%M:%S'))  # Format as needed
        open_prices.append(data.open_price)
        high_prices.append(data.high_price)
        low_prices.append(data.low_price)
        close_prices.append(data.close_price)
    # Create candlestick chart for 1-minute data
    candlestick = go.Candlestick(
        x=dates,
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        name='Candlestick'
    )

    # Plot the signals as scatter points
    fig = go.Figure(data=[candlestick])

    # Calculate the moving average for 1-minute data (e.g., 50-minute MA)
    df = pd.DataFrame({
        'date': dates,
        'close': close_prices
    })
    df['50_min_ma'] = df['close'].rolling(window=50).mean()

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['50_min_ma'],
        mode='lines',
        name='50-Minute Moving Average',
        line=dict(color='orange', width=2)
    ))

    signals_exist = TradingSignal.objects.filter(stock=stock).exists()
    if signals_exist:
        signals = TradingSignal.objects.filter(stock=stock).order_by('date')
        buy_signals = [signal for signal in signals if signal.signal_type == 'BUY']
        sell_signals = [signal for signal in signals if signal.signal_type == 'SELL']
        print(buy_signals, " --- ", sell_signals)
        buy_scatter = go.Scatter(
            x=[signal.date for signal in buy_signals],
            y=[signal.price for signal in buy_signals],
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            name='Buy Signal'
        )

        sell_scatter = go.Scatter(
            x=[signal.date for signal in sell_signals],
            y=[signal.price for signal in sell_signals],
            mode='markers',
            marker=dict(color='red', size=10, symbol='triangle-down'),
            name='Sell Signal'
        )
        # Add signals to the figure
        fig.add_trace(buy_scatter)
        fig.add_trace(sell_scatter)

    fig.update_layout(title=f"{stock.symbol} 1-Minute Price Chart", xaxis_title='Date', yaxis_title='Price',
                      height=1500)

    # Set the x-axis range to zoom in on a specific part of the chart (optional)
    fig.update_xaxes(range=[df['date'].min(), df['date'].max()])

    graph_html = fig.to_html(full_html=False)
    return render(request, 'graph.html', {'graph': graph_html, 'symbol': symbol})


def plot_graph_view(request, symbol):
    try:
        stock = Stock.objects.get(symbol='AAPL')
    except Stock.DoesNotExist:
        print("stock not found")
        return render(request, 'graph.html',
                      {'message': f"Stock with symbol '{symbol}' not found.", 'symbol': 'not found'})
    historical_data = HistoricalData.objects.filter(stock=stock).order_by('-date')
    dates = [data.date for data in historical_data]
    open_prices = [data.open_price for data in historical_data]
    high_prices = [data.high_price for data in historical_data]
    low_prices = [data.low_price for data in historical_data]
    close_prices = [data.close_price for data in historical_data]

    # Create candlestick chart
    candlestick = go.Candlestick(
        x=dates,
        open=open_prices,
        high=high_prices,
        low=low_prices,
        close=close_prices,
        name='Candlestick'
    )

    # Plot the signals as scatter points
    fig = go.Figure(data=[candlestick])

    # 50 day moving average line
    dates = [data.date for data in historical_data]
    close_prices = [data.close_price for data in historical_data]
    df = pd.DataFrame({
        'date': dates,
        'close': close_prices
    })
    df['50_day_ma'] = df['close'].rolling(window=50).mean()

    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['50_day_ma'],
        mode='lines',
        name='50-Day Moving Average',
        line=dict(color='orange', width=2)
    ))

    signals_exist = TradingSignal.objects.filter(stock=stock).exists()
    if signals_exist:
        signals = TradingSignal.objects.filter(stock=stock).order_by('date')
        print('signals: ', signals)
        buy_signals = [signal for signal in signals if signal.signal_type == 'BUY']
        sell_signals = [signal for signal in signals if signal.signal_type == 'SELL']

        buy_scatter = go.Scatter(
            x=[signal.date for signal in buy_signals],
            y=[signal.price for signal in buy_signals],
            mode='markers',
            marker=dict(color='green', size=10, symbol='triangle-up'),
            name='Buy Signal'
        )

        sell_scatter = go.Scatter(
            x=[signal.date for signal in sell_signals],
            y=[signal.price for signal in sell_signals],
            mode='markers',
            marker=dict(color='red', size=10, symbol='triangle-down'),
            name='Sell Signal'
        )
        # Add signals to the figure
        fig.add_trace(buy_scatter)
        fig.add_trace(sell_scatter)

    fig.update_layout(title=f"{stock.symbol} Price Chart", xaxis_title='Date', yaxis_title='Price', height=1500)
    # Optionally, set the range of the x-axis to zoom in on a specific part of the chart
    fig.update_xaxes(range=[df['date'].min(), df['date'].max()])

    graph_html = fig.to_html(full_html=False)
    return render(request, 'graph.html', {'graph': graph_html, 'symbol': symbol})


class LiveTradeView(View):
    def get(self, request):
        form = FetchDataRange()
        return render(request, 'live_trade.html', {'form': form, 'success': "progress"})

    def post(self, request):
        print("this is post live-trade request")
        if request.method == 'POST':
            form = FetchDataRange(request.POST)
            print('this is post method')
            if form.is_valid():
                symbol = form.cleaned_data['symbol']
                start_date = form.cleaned_data['start_date'].strftime('%Y-%m-%d %H:%M:%S')
                end_date = form.cleaned_data['end_date'].strftime('%Y-%m-%d %H:%M:%S')
                timestamp = form.cleaned_data['timeframe']
                print("Trigger tasks")
                # Trigger the tasks asynchronously
                fetch_data_task.delay(symbol, start_date, end_date, timestamp)
                apply_strategy_task.delay(symbol)
                return render(request, 'live_trade.html', {'message': 'initiated the request.'})
