from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from apps.core.models import Transaction, ProcurementMethod

class SingleTransactionUploadForm(forms.ModelForm):
    """
    Django form for single transaction upload with prefilled values and validation.
    """
    
    # Predefined choices for dropdowns
    END_USER_UNIT_CHOICES = [
        ('', 'Select end user unit...'),
        ('DEPED - Division of City Schools', 'DEPED - Division of City Schools'),
        ('DEPED - Division of Provincial Schools', 'DEPED - Division of Provincial Schools'),
        ('DEPED - Science and Technology Education Center', 'DEPED - Science and Technology Education Center'),
        ('DEPED - Regional Science High School', 'DEPED - Regional Science High School'),
        ('DEPED - National Science High School', 'DEPED - National Science High School'),
        ('DEPED - Special Science Elementary School', 'DEPED - Special Science Elementary School'),
        ('DEPED - Science and Technology School', 'DEPED - Science and Technology School'),
        ('DEPED - Laboratory School', 'DEPED - Laboratory School'),
        ('DEPED - Science Education Center', 'DEPED - Science Education Center'),
        ('DEPED - STEM Learning Center', 'DEPED - STEM Learning Center'),
    ]
    
    ITEM_NAME_CHOICES = [
        ('', 'Select an item...'),
        ('BEAKER – LOW FORM GRIFFIN, 250 ML, BOROSILICATE GLASS 3.3, WITH SPOUT AND PRINTED GRADUATIONS', 'BEAKER – LOW FORM GRIFFIN, 250 ML, BOROSILICATE GLASS 3.3, WITH SPOUT AND PRINTED GRADUATIONS'),
        ('GRADUATED CYLINDER – 100 ML CAPACITY, CLASS B, POLYPROPYLENE, WITH HEXAGONAL BASE AND MOLDED GRADUATIONS', 'GRADUATED CYLINDER – 100 ML CAPACITY, CLASS B, POLYPROPYLENE, WITH HEXAGONAL BASE AND MOLDED GRADUATIONS'),
        ('TEST TUBE – 16 × 150 MM, BOROSILICATE GLASS 3.3, RIMMED, REUSABLE', 'TEST TUBE – 16 × 150 MM, BOROSILICATE GLASS 3.3, RIMMED, REUSABLE'),
        ('ERLENMEYER FLASK – 250 ML, BOROSILICATE GLASS 3.3, NARROW MOUTH, WITH PRINTED GRADUATIONS', 'ERLENMEYER FLASK – 250 ML, BOROSILICATE GLASS 3.3, NARROW MOUTH, WITH PRINTED GRADUATIONS'),
        ('FUNNEL – UTILITY TYPE, POLYPROPYLENE PLASTIC, 100 MM TOP DIAMETER', 'FUNNEL – UTILITY TYPE, POLYPROPYLENE PLASTIC, 100 MM TOP DIAMETER'),
        ('WATCH GLASS – 100 MM DIAMETER, SODA-LIME GLASS, FIRE-POLISHED WITH BEVELED EDGES', 'WATCH GLASS – 100 MM DIAMETER, SODA-LIME GLASS, FIRE-POLISHED WITH BEVELED EDGES'),
        ('TRIPLE BEAM BALANCE – MECHANICAL, 610 G CAPACITY, 0.1 G READABILITY, STAINLESS STEEL PAN', 'TRIPLE BEAM BALANCE – MECHANICAL, 610 G CAPACITY, 0.1 G READABILITY, STAINLESS STEEL PAN'),
        ('ALCOHOL LAMP – 150 ML CAPACITY, GLASS BODY, WITH METAL SHIELD AND ADJUSTABLE WICK CAP', 'ALCOHOL LAMP – 150 ML CAPACITY, GLASS BODY, WITH METAL SHIELD AND ADJUSTABLE WICK CAP'),
        ('METER STICK – 100 CM, HARDWOOD WITH METAL END CAPS, DUAL SCALE IN CM AND INCHES', 'METER STICK – 100 CM, HARDWOOD WITH METAL END CAPS, DUAL SCALE IN CM AND INCHES'),
        ('STOPWATCH – DIGITAL LCD, 1/100TH SECOND PRECISION, WATER-RESISTANT, LAP/SPLIT FUNCTION', 'STOPWATCH – DIGITAL LCD, 1/100TH SECOND PRECISION, WATER-RESISTANT, LAP/SPLIT FUNCTION'),
        ('STIRRING ROD – 200 MM × 7 MM, BOROSILICATE GLASS, ROUNDED ENDS', 'STIRRING ROD – 200 MM × 7 MM, BOROSILICATE GLASS, ROUNDED ENDS'),
        ('TEST TUBE BRUSH – FOR 16–20 MM TUBES, NYLON BRISTLES, GALVANIZED STEEL WIRE HANDLE WITH LOOPED END', 'TEST TUBE BRUSH – FOR 16–20 MM TUBES, NYLON BRISTLES, GALVANIZED STEEL WIRE HANDLE WITH LOOPED END'),
        ('DRY CELL BATTERY – SIZE D, CARBON-ZINC (HEAVY DUTY), 1.5 VOLTS, SHRINK-WRAPPED PACK OF 2', 'DRY CELL BATTERY – SIZE D, CARBON-ZINC (HEAVY DUTY), 1.5 VOLTS, SHRINK-WRAPPED PACK OF 2'),
        ('PH INDICATOR PAPER – UNIVERSAL RANGE (PH 1–14), PLASTIC DISPENSER ROLL, 5 METERS LENGTH', 'PH INDICATOR PAPER – UNIVERSAL RANGE (PH 1–14), PLASTIC DISPENSER ROLL, 5 METERS LENGTH'),
        ('WIRE GAUZE – 125 × 125 MM (5" × 5"), WOVEN STEEL MESH WITH CERAMIC FIBER CENTER', 'WIRE GAUZE – 125 × 125 MM (5" × 5"), WOVEN STEEL MESH WITH CERAMIC FIBER CENTER'),
    ]
    

    PROCUREMENT_METHOD_CHOICES = [
        ('', 'Select procurement method...'),
        ('Competitive Bidding', 'Competitive Bidding'),
        ('Direct Contracting', 'Direct Contracting'),
        ('Limited Source Bidding', 'Limited Source Bidding'),
        ('Negotiated Procurement (Agency-to-Agency)', 'Negotiated Procurement (Agency-to-Agency)'),
        ('Negotiated Procurement (Small Value Procurement)', 'Negotiated Procurement (Small Value Procurement)'),
        ('Negotiated Procurement (Two Failed Biddings)', 'Negotiated Procurement (Two Failed Biddings)'),
        ('Repeat Order', 'Repeat Order'),
    ]

    # Override fields to use choices and add prefilled values
    item_name = forms.ChoiceField(
        choices=ITEM_NAME_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    end_user_unit = forms.ChoiceField(
        choices=END_USER_UNIT_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    procurement_method = forms.ChoiceField(
        choices=PROCUREMENT_METHOD_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Add prefilled values for demo
    project_name = forms.CharField(
        max_length=255,
        required=False,
        initial="AghamYaman Labs Project",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    project_description = forms.CharField(
        required=False,
        initial="Enhanced laboratory equipment procurement for science education modernization and student learning enhancement.",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        initial=25,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    unit_purchase_price = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        initial=Decimal('850.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    approved_budget = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        min_value=Decimal('0.01'),
        initial=Decimal('23013.46'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    supplier = forms.CharField(
        max_length=100,
        initial="Science Equipment Supplier",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    procurement_officer = forms.CharField(
        max_length=100,
        required=False,
        initial="Shana Lagingtama",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    invoice_number = forms.CharField(
        max_length=100,
        initial="INV-2024-001",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    payment_receipt_number = forms.CharField(
        max_length=100,
        initial="RCPT-2024-001",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    transaction_date = forms.DateField(
        initial=datetime.now().date(),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    # Optional timeline fields - pre-filled with logical procurement timeline
    # Working backwards from transaction_date following procurement process sequence
    invitation_to_bid_posting_date = forms.DateField(
        required=False,
        initial=datetime.now().date() - timedelta(days=45),  # 45 days before transaction
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    bid_submission_deadline = forms.DateField(
        required=False,
        initial=datetime.now().date() - timedelta(days=25),  # 25 days before transaction
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    bid_opening_date = forms.DateField(
        required=False,
        initial=datetime.now().date() - timedelta(days=23),  # 23 days before transaction
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    notice_of_award_date = forms.DateField(
        required=False,
        initial=datetime.now().date() - timedelta(days=15),  # 15 days before transaction
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    contract_signing_date = forms.DateField(
        required=False,
        initial=datetime.now().date() - timedelta(days=8),   # 8 days before transaction
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    class Meta:
        model = Transaction
        fields = [
            'project_name', 'end_user_unit', 'project_description',
            'item_name', 'quantity', 'unit_purchase_price', 'approved_budget',
            'supplier', 'procurement_officer', 'invoice_number', 'payment_receipt_number',
            'transaction_date', 'invitation_to_bid_posting_date', 'bid_submission_deadline',
            'bid_opening_date', 'notice_of_award_date', 'contract_signing_date'
        ]
        exclude = ['procurement_method']  # Exclude since we handle it manually
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for dropdown fields
        self.fields['item_name'].choices = self.ITEM_NAME_CHOICES
        self.fields['end_user_unit'].choices = self.END_USER_UNIT_CHOICES
        self.fields['procurement_method'].choices = self.PROCUREMENT_METHOD_CHOICES
    
    def clean(self):
        """Custom validation for the form."""
        cleaned_data = super().clean()
        
        # Validate that transaction date is not in the future
        transaction_date = cleaned_data.get('transaction_date')
        if transaction_date and transaction_date > datetime.now().date():
            raise ValidationError('Transaction date cannot be in the future.')
        
        # Validate that unit price is reasonable (not too high)
        unit_price = cleaned_data.get('unit_purchase_price')
        if unit_price and unit_price > Decimal('1000000'):
            raise ValidationError('Unit price seems unreasonably high. Please check the value.')
        
        # Validate that quantity is reasonable
        quantity = cleaned_data.get('quantity')
        if quantity and quantity > 10000:
            raise ValidationError('Quantity seems unreasonably high. Please check the value.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Override save to handle procurement method creation."""
        instance = super().save(commit=False)
        
        # Get or create procurement method
        procurement_method_name = self.cleaned_data.get('procurement_method')
        if procurement_method_name:
            procurement_method, created = ProcurementMethod.objects.get_or_create(
                name=procurement_method_name
            )
            instance.procurement_method = procurement_method
        
        if commit:
            instance.save()
        return instance 