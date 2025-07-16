from django import forms

class AnalysisConfigurationForm(forms.Form):
    """
    Validates the contamination parameter for the Isolation Forest model.
    """
    contamination = forms.FloatField(
    min_value=0.01,
    max_value=0.5,
    required=True,
    widget=forms.NumberInput(attrs={
        'class': 'form-control form-control-lg',
        'step': '0.01',
        'placeholder': 'e.g., 0.05 for 5% anomalies'
    }),
    label="Expected Anomaly Percentage",
    help_text="For this demo, enter '0.10'. Valid values, representing the expected proportion of anomalies in the dataset, range from 0.01 (1%) to 0.50 (50%)."
    )
    
    transaction_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        help_text="JSON string of transaction IDs"
    )

    def clean_transaction_ids(self):
        """
        Deserializes the transaction_ids from a JSON string into a list of integers.
        """
        import json
        ids_string = self.cleaned_data['transaction_ids']
        try:
            ids = json.loads(ids_string)
            if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
                raise forms.ValidationError("Invalid transaction IDs format.")
            return ids
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for transaction IDs.") 