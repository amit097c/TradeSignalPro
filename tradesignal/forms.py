from django import forms


class FetchDataRange(forms.Form):
    start_date = forms.DateTimeField(label="Start Date", widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    end_date = forms.DateTimeField(label="End Date", widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    symbol = forms.CharField(label="stock symbol", widget=forms.TextInput(attrs={'class': 'form-control'}))
    timeframe = forms.ChoiceField(
        label="Timeframe",
        choices=[
            ('1Min', '1 Minute'),   # Minute-level data
            ('5Min', '5 Minutes'),  # Example additional timeframe
            ('15Min', '15 Minutes'),# Example additional timeframe
            ('1D', '1 Day')         # Daily data
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
