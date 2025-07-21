from django import forms

class AnalysisConfigurationForm(forms.Form):
    """
    Validates the contamination parameter for the Isolation Forest model.
    """
    contamination = forms.FloatField(
        min_value=1,
        max_value=50,
        required=True,
        label='Sensitivity',
        help_text='Select a sensitivity level between 1% and 50%.'
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