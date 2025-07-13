from django.db import models
from django.utils import timezone
from apps.core.models import Transaction


class AnomalyReport(models.Model):
    """
    Stores anomaly detection results for procurement transactions.
    
    This model captures the output of the Isolation Forest model and stores
    information needed for SHAP-based explanations of why a transaction
    was flagged as anomalous.
    """
    
    # --- Core Relationship ---
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        related_name='anomaly_report',
        null=True,
        blank=True,
        help_text="The transaction that was analyzed for anomalies. Can be null if transaction was deleted."
    )
    
    # Store transaction_id separately to preserve reference even if transaction is deleted
    transaction_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Transaction ID for reference, preserved even if transaction is deleted."
    )
    
    # --- Anomaly Detection Results ---
    is_anomaly = models.BooleanField(
        default=False,
        help_text="Whether the transaction was flagged as anomalous by the model."
    )
    
    anomaly_score = models.FloatField(
        null=True,
        blank=True,
        help_text="The anomaly score from the Isolation Forest model. Lower values indicate more anomalous behavior."
    )
    
    confidence_level = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence level of the anomaly detection (0.0 to 1.0)."
    )
    
    # --- Feature Values (for SHAP explanations) ---
    feature_values = models.JSONField(
        null=True,
        blank=True,
        help_text="The feature values used for anomaly detection (stored for SHAP explanations)."
    )
    
    # --- Explanation Data ---
    shap_values = models.JSONField(
        null=True,
        blank=True,
        help_text="SHAP values explaining which features contributed to the anomaly score."
    )
    
    top_contributing_features = models.JSONField(
        null=True,
        blank=True,
        help_text="Top 5 features that most contributed to the anomaly detection, with their importance scores."
    )
    
    # --- Model Metadata ---
    model_version = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Version of the anomaly detection model used for this analysis."
    )
    
    model_training_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when the model used for this analysis was trained."
    )
    
    # --- Processing Metadata ---
    detection_timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this anomaly analysis was performed."
    )
    
    processing_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to process this transaction (in milliseconds)."
    )
    
    # --- Error Handling ---
    processing_error = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if anomaly detection failed for this transaction."
    )
    
    # --- Status Tracking ---
    STATUS_CHOICES = [
        ('pending', 'Pending Analysis'),
        ('processing', 'Processing'),
        ('completed', 'Analysis Completed'),
        ('failed', 'Analysis Failed'),
        ('explained', 'Explanation Generated'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the anomaly analysis."
    )
    
    # --- Explanation Status ---
    explanation_generated = models.BooleanField(
        default=False,
        help_text="Whether SHAP explanation has been generated for this report."
    )
    
    explanation_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the SHAP explanation was generated."
    )
    
    class Meta:
        ordering = ['-detection_timestamp']
        verbose_name = "Anomaly Report"
        verbose_name_plural = "Anomaly Reports"
        indexes = [
            models.Index(fields=['is_anomaly']),
            models.Index(fields=['status']),
            models.Index(fields=['detection_timestamp']),
            models.Index(fields=['transaction_id']),
        ]
    
    def __str__(self):
        return f"Anomaly Report for {self.transaction_id} ({'Anomalous' if self.is_anomaly else 'Normal'})"
    
    def save(self, *args, **kwargs):
        """Ensure transaction_id is set from the related transaction if available."""
        if self.transaction and not self.transaction_id:
            self.transaction_id = str(self.transaction_id)
        super().save(*args, **kwargs)
    
    @property
    def anomaly_severity(self):
        """
        Returns a human-readable severity level based on the anomaly score.
        """
        if self.anomaly_score is None:
            return "Unknown"
        
        if self.anomaly_score < 0.3:
            return "High"
        elif self.anomaly_score < 0.5:
            return "Medium"
        elif self.anomaly_score < 0.7:
            return "Low"
        else:
            return "Normal"
    
    @property
    def is_high_priority(self):
        """
        Returns True if this anomaly should be prioritized for review.
        """
        return (
            self.is_anomaly and 
            self.anomaly_score is not None and 
            self.anomaly_score < 0.4 and
            self.confidence_level is not None and
            self.confidence_level > 0.7
        )
    
    def generate_explanation_summary(self):
        """
        Returns a human-readable summary of why this transaction was flagged.
        """
        if not self.is_anomaly or not self.top_contributing_features:
            return "No explanation available."
        
        # Handle JSONField properly - it might be a list or dict
        features = self.top_contributing_features
        if isinstance(features, list):
            features = features[:3]  # Top 3 features
        else:
            return "Anomaly detected but no specific features identified."
        
        explanations = []
        
        for feature_data in features:
            if isinstance(feature_data, (list, tuple)) and len(feature_data) >= 2:
                feature_name, importance = feature_data[0], feature_data[1]
                if isinstance(importance, (int, float)) and importance > 0.1:
                    explanations.append(f"{feature_name} (impact: {importance:.2f})")
            elif isinstance(feature_data, dict):
                feature_name = feature_data.get('feature_name', 'Unknown')
                importance = feature_data.get('importance', 0)
                if isinstance(importance, (int, float)) and importance > 0.1:
                    explanations.append(f"{feature_name} (impact: {importance:.2f})")
        
        if explanations:
            return f"Flagged due to: {', '.join(explanations)}"
        else:
            return "Anomaly detected but no specific features identified."
    
    def mark_as_explained(self):
        """
        Marks this report as having an explanation generated.
        """
        self.explanation_generated = True
        self.explanation_timestamp = timezone.now()
        self.status = 'explained'
        self.save(update_fields=['explanation_generated', 'explanation_timestamp', 'status'])
