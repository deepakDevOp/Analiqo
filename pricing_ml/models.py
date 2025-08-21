"""
Models for machine learning pricing components.
"""

from django.db import models
from core.models import BaseModel
import uuid


class MLModel(BaseModel):
    """Machine learning model for pricing optimization."""
    
    MODEL_TYPES = [
        ('demand_forecasting', 'Demand Forecasting'),
        ('price_elasticity', 'Price Elasticity'),
        ('buy_box_prediction', 'Buy Box Prediction'),
        ('competitor_analysis', 'Competitor Analysis'),
        ('seasonal_adjustment', 'Seasonal Adjustment'),
        ('margin_optimization', 'Margin Optimization'),
    ]
    
    STATUS_CHOICES = [
        ('training', 'Training'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('failed', 'Failed'),
        ('deprecated', 'Deprecated'),
    ]
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='ml_models'
    )
    name = models.CharField(max_length=255)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    version = models.CharField(max_length=20, default='1.0.0')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='training')
    
    # Model metadata
    algorithm = models.CharField(max_length=100, help_text='ML algorithm used (e.g., RandomForest, XGBoost)')
    hyperparameters = models.JSONField(default=dict, help_text='Model hyperparameters')
    features = models.JSONField(default=list, help_text='Feature names used by the model')
    target_variable = models.CharField(max_length=100, help_text='Target variable being predicted')
    
    # Performance metrics
    accuracy_score = models.FloatField(null=True, blank=True)
    precision_score = models.FloatField(null=True, blank=True)
    recall_score = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    mse_score = models.FloatField(null=True, blank=True, help_text='Mean Squared Error')
    mae_score = models.FloatField(null=True, blank=True, help_text='Mean Absolute Error')
    r2_score = models.FloatField(null=True, blank=True, help_text='R-squared score')
    
    # Training information
    training_started_at = models.DateTimeField(null=True, blank=True)
    training_completed_at = models.DateTimeField(null=True, blank=True)
    training_duration = models.DurationField(null=True, blank=True)
    training_samples = models.IntegerField(null=True, blank=True)
    validation_samples = models.IntegerField(null=True, blank=True)
    
    # Model artifacts
    model_file_path = models.CharField(max_length=500, null=True, blank=True)
    model_size_bytes = models.BigIntegerField(null=True, blank=True)
    
    # Deployment information
    deployed_at = models.DateTimeField(null=True, blank=True)
    last_prediction_at = models.DateTimeField(null=True, blank=True)
    prediction_count = models.BigIntegerField(default=0)
    
    # Configuration
    is_default = models.BooleanField(default=False, help_text='Default model for this type')
    retrain_frequency_days = models.IntegerField(default=7, help_text='Days between retraining')
    min_training_samples = models.IntegerField(default=1000, help_text='Minimum samples required for training')
    
    # Metadata and notes
    description = models.TextField(blank=True)
    training_notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'model_type', 'status']),
            models.Index(fields=['status', 'is_default']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'model_type', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_model_per_type'
            )
        ]
    
    def __str__(self):
        return f"{self.name} ({self.model_type}) v{self.version}"


class TrainingJob(BaseModel):
    """Training job for ML models."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='training_jobs'
    )
    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name='training_jobs',
        null=True,
        blank=True
    )
    
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    model_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Job configuration
    algorithm = models.CharField(max_length=100)
    hyperparameters = models.JSONField(default=dict)
    data_source = models.CharField(max_length=200, help_text='Source of training data')
    feature_config = models.JSONField(default=dict, help_text='Feature engineering configuration')
    
    # Execution details
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    worker_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Results
    training_samples = models.IntegerField(null=True, blank=True)
    validation_samples = models.IntegerField(null=True, blank=True)
    test_samples = models.IntegerField(null=True, blank=True)
    
    # Performance metrics
    final_metrics = models.JSONField(default=dict)
    training_loss = models.FloatField(null=True, blank=True)
    validation_loss = models.FloatField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(null=True, blank=True)
    error_traceback = models.TextField(null=True, blank=True)
    
    # Output
    model_artifacts_path = models.CharField(max_length=500, null=True, blank=True)
    logs_path = models.CharField(max_length=500, null=True, blank=True)
    
    # Configuration and metadata
    config = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['model_type', 'status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"Training Job {self.job_id} ({self.model_type})"


class ModelPrediction(BaseModel):
    """Record of model predictions for audit and analysis."""
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='model_predictions'
    )
    model = models.ForeignKey(
        MLModel,
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    
    # Prediction input
    product_id = models.CharField(max_length=100)
    marketplace = models.CharField(max_length=50)
    input_features = models.JSONField(default=dict, help_text='Features used for prediction')
    
    # Prediction output
    prediction_value = models.FloatField()
    confidence_score = models.FloatField(null=True, blank=True)
    prediction_probabilities = models.JSONField(default=dict, help_text='Class probabilities for classification')
    
    # Context
    model_version = models.CharField(max_length=20)
    prediction_timestamp = models.DateTimeField(auto_now_add=True)
    request_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Performance tracking
    actual_value = models.FloatField(null=True, blank=True, help_text='Actual value for validation')
    prediction_error = models.FloatField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-prediction_timestamp']
        indexes = [
            models.Index(fields=['organization', 'model', 'prediction_timestamp']),
            models.Index(fields=['product_id', 'marketplace']),
            models.Index(fields=['prediction_timestamp']),
        ]
    
    def __str__(self):
        return f"Prediction {self.id} ({self.model.model_type})"


class FeatureStore(BaseModel):
    """Feature store for ML models."""
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='features'
    )
    
    # Feature identification
    feature_name = models.CharField(max_length=100)
    feature_group = models.CharField(max_length=50, help_text='Logical grouping of features')
    data_type = models.CharField(max_length=20, default='float')
    
    # Feature metadata
    description = models.TextField(blank=True)
    calculation_logic = models.TextField(help_text='How the feature is calculated')
    update_frequency = models.CharField(max_length=50, default='daily')
    
    # Data quality
    null_percentage = models.FloatField(null=True, blank=True)
    unique_values = models.IntegerField(null=True, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    mean_value = models.FloatField(null=True, blank=True)
    std_value = models.FloatField(null=True, blank=True)
    
    # Feature importance
    importance_score = models.FloatField(null=True, blank=True)
    correlation_with_target = models.FloatField(null=True, blank=True)
    
    # Operational
    is_active = models.BooleanField(default=True)
    last_computed_at = models.DateTimeField(null=True, blank=True)
    computation_time_seconds = models.FloatField(null=True, blank=True)
    
    # Configuration
    computation_config = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['feature_group', 'feature_name']
        indexes = [
            models.Index(fields=['organization', 'feature_group']),
            models.Index(fields=['is_active', 'last_computed_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'feature_name'],
                name='unique_feature_per_organization'
            )
        ]
    
    def __str__(self):
        return f"{self.feature_group}.{self.feature_name}"


class ModelExperiment(BaseModel):
    """Experiment tracking for ML model development."""
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    organization = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='experiments'
    )
    
    # Experiment identification
    experiment_name = models.CharField(max_length=200)
    experiment_id = models.UUIDField(default=uuid.uuid4, unique=True)
    model_type = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    
    # Experiment configuration
    hypothesis = models.TextField(help_text='What you are testing')
    algorithm = models.CharField(max_length=100)
    hyperparameters = models.JSONField(default=dict)
    feature_set = models.JSONField(default=list)
    data_split_config = models.JSONField(default=dict)
    
    # Execution details
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    # Results
    metrics = models.JSONField(default=dict)
    model_artifacts_path = models.CharField(max_length=500, null=True, blank=True)
    logs_path = models.CharField(max_length=500, null=True, blank=True)
    
    # Analysis
    conclusion = models.TextField(null=True, blank=True, help_text='Experiment conclusions')
    next_steps = models.TextField(null=True, blank=True)
    
    # Metadata
    tags = models.JSONField(default=list, help_text='Tags for categorizing experiments')
    metadata = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'model_type']),
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self):
        return f"Experiment: {self.experiment_name}"