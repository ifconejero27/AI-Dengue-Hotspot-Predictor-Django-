from django import forms

class DengueDataImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Select CSV file',
        help_text='File should have columns: BARANGAY, WEEK 1, WEEK 2, ... WEEK 52'
    )
    year = forms.IntegerField(
        label='Year',
        min_value=2000,
        max_value=2100,
        help_text='Year the data was reported (e.g., 2021)'
    )