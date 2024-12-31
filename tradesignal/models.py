from django.db import models

# Create your models here.
from django.db import models


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.symbol


'''To store the historical data fetched from external sources like Alpaca. This allows you to save, query, 
and manage large amounts of data efficiently, which is crucial for backtesting strategies or reviewing past trade'''


class HistoricalData(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    date = models.DateTimeField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()

    class Meta:
        unique_together = ('stock', 'date')

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"


'''To store trading signals, including buy and sell actions, along with relevant timestamps. This data can be later 
used for performance analysis or generating reports'''


class TradingSignal(models.Model):
    SIGNAL_CHOICES = (
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    )

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    signal_type = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    date = models.DateTimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.signal_type} - {self.stock.symbol} on {self.date} at {self.price}"


'''If you plan to extend the project to handle multiple users, models can manage user portfolios, track holdings, 
and record trade history'''

