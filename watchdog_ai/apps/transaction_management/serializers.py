from rest_framework import serializers

class TransactionCSVUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading a CSV file of transactions.
    It validates that the uploaded file is a CSV.
    """
    csv_file = serializers.FileField()

    def validate_csv_file(self, value):
        """
        Check that the uploaded file is a CSV.
        """
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("The uploaded file must be a CSV.")
        return value