from django.urls import path
from . import views
from .views import LiveTradeView

app_name = 'tradesignal'
urlpatterns = [
    path('', views.home, name='home'),
    path('live-trade/', LiveTradeView.as_view(), name='live_trade'),
    path('fetch-data/', views.fetch_data_view, name='fetch_data'),
    path('apply-strategy/<str:symbol>/', views.apply_strategy_view, name='apply_strategy'),
    path('plot-graph/<str:symbol>/', views.plot_graph_view_minute, name='plot_graph'),
    path('export_to_excel/<str:symbol>/', views.export_to_excel, name='export_to_excel'),
]
