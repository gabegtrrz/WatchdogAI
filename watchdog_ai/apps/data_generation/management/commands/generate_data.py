import os
import uuid
import datetime
import yaml
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from apps.data_generation.anomaly_definitions import ANOMALY_BLUEPRINTS
from apps.data_augmentation.models import ItemAveragePrice
from django.utils import timezone 

class Command(BaseCommand):
    """
    A Django management command to generate simulated RAW procurement transaction data.

    This command reads a YAML configuration file to produce realistic transaction
    data suitable for database population and for training a separate feature
    engineering component. It does NOT perform feature engineering itself.

    -----------------
    Usage:
    python manage.py generate_data <path_to_config.yml>
    -----------------

    """
    help = 'Generates simulated raw procurement transaction data from a YAML configuration file.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.faker = Faker() # Initialize a single Faker instance for reuse

    def add_arguments(self, parser):
        """Adds command-line arguments: a required config path."""
        parser.add_argument(
            'config_path',
            type=str,
            help='The path to the YAML configuration file for data generation.'
        )

    def handle(self, *args, **options):
        """Main execution logic for the command."""
        config_path = options['config_path']
        self.config_path = config_path  # Store for use in scrape mode

        # --- 1. Load Configuration & Items ---
        self.stdout.write(self.style.SUCCESS("Loading configuration..."))  # type: ignore
        config, items = self._load_config_and_items(config_path)

        # --- 2. Initialize & Generate ---
        n_samples = config['n_samples']
        random_state = config.get('random_state')
        if random_state:
            np.random.seed(random_state) # setting the starting point (the seed) for NumPy's internal pseudo-random number generator.


            Faker.seed(random_state)

        self.stdout.write(self.style.SUCCESS("Generating raw transaction data..."))  # type: ignore
        df = self._generate_raw_transactions(config, items, n_samples)

        # --- 3. Inject Anomalies ---
        self.stdout.write(self.style.SUCCESS("Injecting anomalies..."))  # type: ignore
        df_with_labels = self._inject_anomalies(df.copy(), config)

        # --- 4. Save Outputs ---
        self._save_output_files(df, df_with_labels, config_path, config)

    def _load_config_and_items(self, config_path):
        """Loads the main YAML config and the item list from its source file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)['data_generator']
        except (FileNotFoundError, KeyError) as e:
            raise CommandError(f"Could not load or parse configuration file: {e}")

        try:
            with open(config['item_source_file'], 'r', encoding='utf-8') as f:
                items = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise CommandError(f"Item source file not found at: {config['item_source_file']}")
        except UnicodeDecodeError as e:
            raise CommandError(f"Error reading item source file encoding: {e}. Please ensure the file is UTF-8 encoded.")
        
        return config, items

    def _generate_raw_transactions(self, config, items, n_samples):
        """Generates a DataFrame of raw transaction data based on config rules."""
        data = {}
        field_rules = config['field_rules']

        # Pre-generate choices for fields that use it to avoid redundant Faker calls
        pre_generated_choices = {}
        
        for field, rule in field_rules.items():
            rule_type = rule.get('type')
            try:
                if rule_type == 'faker':
                    # Use the faker instance directly with the provider method
                    provider_method = getattr(self.faker, rule['provider'])
                    data[field] = [provider_method() for _ in range(n_samples)]
                elif rule_type == 'faker_choice':
                    # Pre-generate choices for faker_choice type
                    provider_method = getattr(self.faker, rule['provider'])
                    pre_generated_choices[field] = [provider_method() for _ in range(rule['n_choices'])]
                    data[field] = np.random.choice(pre_generated_choices[field], size=n_samples)
                elif rule_type == 'categorical':
                    data[field] = np.random.choice(rule['values'], size=n_samples, p=rule.get('weights'))
                elif rule_type == 'normal':
                    data[field] = np.random.normal(loc=rule['mean'], scale=rule['std_dev'], size=n_samples)
                elif rule_type == 'log-normal':
                    data[field] = np.random.lognormal(mean=rule['mean'], sigma=rule['std_dev'], size=n_samples)
                elif rule_type == 'date_range':
                    start = datetime.date.fromisoformat(rule['start_date'])
                    end = datetime.date.fromisoformat(rule['end_date'])
                    # Generate office day dates (Monday to Friday) for normal transactions
                    data[field] = self._generate_office_day_dates(start, end, n_samples)
                elif rule_type == 'fixed':
                    # For fields that should have the same value for all records
                    data[field] = [rule['value'] for _ in range(n_samples)]
                else:
                    self.stdout.write(f"WARNING: Unknown rule type '{rule_type}' for field '{field}'. Skipping.")
                    continue
            except Exception as e:
                self.stdout.write(f"WARNING: Error generating data for field '{field}': {e}. Skipping.")
                continue

        df = pd.DataFrame(data)

        # --- Generate fields that are not based on simple rules ---
        df['item_name'] = np.random.choice(items, size=n_samples)
        df['invoice_number'] = [f"INV-{uuid.uuid4().hex[:8].upper()}" for _ in range(n_samples)]
        df['payment_receipt_number'] = [f"RCPT-{uuid.uuid4().hex[:10].upper()}" for _ in range(n_samples)]

        # --- Generate Procedural Procurement Timeline Dates ---
        # These are generated based on the transaction_date and legal timelines.
        timeline = {
            'invitation_to_bid_posting_date': [],
            'bid_submission_deadline': [],
            'bid_opening_date': [],
            'notice_of_award_date': [],
            'contract_signing_date': [],
        }

        for date in df['transaction_date']:
            # Work backwards from the transaction_date to ensure a logical sequence.
            contract_signing_date = date - datetime.timedelta(days=np.random.randint(1, 15))
            notice_of_award_date = contract_signing_date - datetime.timedelta(days=np.random.randint(1, 10))
            bid_opening_date = notice_of_award_date - datetime.timedelta(days=np.random.randint(1, 7))
            bid_submission_deadline = bid_opening_date - datetime.timedelta(days=np.random.randint(0, 2)) # Can be same day or shortly before
            invitation_to_bid_posting_date = bid_submission_deadline - datetime.timedelta(days=np.random.randint(7, 21)) # Must be at least 7 days prior

            timeline['contract_signing_date'].append(contract_signing_date)
            timeline['notice_of_award_date'].append(notice_of_award_date)
            timeline['bid_opening_date'].append(bid_opening_date)
            timeline['bid_submission_deadline'].append(bid_submission_deadline)
            timeline['invitation_to_bid_posting_date'].append(invitation_to_bid_posting_date)

        # Add the new date columns to the DataFrame
        for col, dates in timeline.items():
            df[col] = dates

        # --- Data Cleaning & Type Enforcement (BEFORE derived calculations) ---
        # Convert negative values to positive for price fields
        df['unit_purchase_price'] = df['unit_purchase_price'].round(4).abs()
        df['quantity'] = df['quantity'].round().abs().clip(lower=1).astype(int)

        # --- Calculate total_purchase_price ---
        df['total_purchase_price'] = (df['quantity'] * df['unit_purchase_price']).round(4)

        # --- Handle average_price based on configuration ---
        average_price_config = config.get('average_price', {})
        average_price_mode = average_price_config.get('mode', 'none')
        
        if average_price_mode == 'none':
            # Remove average_price column if it exists
            if 'average_price' in df.columns:
                df = df.drop('average_price', axis=1)
        elif average_price_mode == 'yaml':
            # Use YAML configuration rules (existing behavior)
            if 'average_price' in df.columns:
                # Allow some records to have empty average_price (randomly set ~25% to NaN for normal data)
                empty_fraction = 0.20  # Increased from 0.1 to 0.25 for more realistic normal data
                empty_indices = np.random.choice(df.index, size=int(n_samples * empty_fraction), replace=False)
                df.loc[empty_indices, 'average_price'] = np.nan
                
                # For non-empty values, ensure they are positive and rounded
                non_empty_mask = df['average_price'].notna()
                if non_empty_mask.sum() > 0:
                    df.loc[non_empty_mask, 'average_price'] = df.loc[non_empty_mask, 'average_price'].round(2).abs()
            
            # Derive unit_purchase_price from average_price for yaml mode
            df = self._derive_unit_price_from_average_price(df, average_price_config)
        elif average_price_mode == 'scrape':
            # Automatically run scraping if needed, then get average prices and derive unit_purchase_price
            # Note: unit_purchase_price should still be defined in field_rules as fallback
            df = self._handle_scrape_mode(df, items, average_price_config)
        else:
            self.stdout.write(f"WARNING: Unknown average_price mode '{average_price_mode}'. Skipping average_price generation.")
            if 'average_price' in df.columns:
                df = df.drop('average_price', axis=1)

        # --- Calculate approved_budget with fallback to unit_purchase_price ---
        budget_markup = np.random.uniform(0.15, 0.22, size=n_samples)
        df['approved_budget'] = np.nan

        # Primary source: average_price, if it exists and is not null
        if 'average_price' in df.columns:
            primary_mask = df['average_price'].notna()
            if primary_mask.sum() > 0:
                df.loc[primary_mask, 'approved_budget'] = (df.loc[primary_mask, 'average_price'] * df.loc[primary_mask, 'quantity'] * (1 + budget_markup[primary_mask])).round(2)

        # Backup source: unit_purchase_price, for all records where approved_budget is still NaN
        backup_mask = df['approved_budget'].isna()
        if backup_mask.sum() > 0 and 'unit_purchase_price' in df.columns:
            unit_price_mask = df['unit_purchase_price'].notna()
            valid_backup_mask = backup_mask & unit_price_mask
            if valid_backup_mask.sum() > 0:
                df.loc[valid_backup_mask, 'approved_budget'] = (df.loc[valid_backup_mask, 'unit_purchase_price'] * df.loc[valid_backup_mask, 'quantity'] * (1 + budget_markup[valid_backup_mask])).round(2)
        
        # If still no approved_budget values, set to NaN
        if bool(df['approved_budget'].isna().all()):
            self.stdout.write(self.style.WARNING("WARNING: No valid average_price or unit_purchase_price found. approved_budget will be blank.")) # type: ignore

        # --- Final safety check: ensure all price fields are positive (only for non-empty values) ---
        price_fields = ['unit_purchase_price', 'average_price', 'approved_budget']
        for field in price_fields:
            if field in df.columns:
                non_empty_mask = df[field].notna()
                if non_empty_mask.sum() > 0:
                    df.loc[non_empty_mask, field] = df.loc[non_empty_mask, field].abs()
            else:
                # If field doesn't exist, create it as NaN (for scrape mode)
                df[field] = np.nan

        df = self._rearrange_columns(df)

        return df

    def _generate_office_day_dates(self, start_date, end_date, n_samples):
        """
        Generates random dates that fall on office days (Monday to Friday).
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            n_samples: Number of dates to generate
            
        Returns:
            List of datetime.date objects that fall on weekdays
        """
        # Generate all possible dates in the range
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            # Check if it's a weekday (Monday=0, Sunday=6)
            if current_date.weekday() < 5:  # Monday to Friday
                all_dates.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        if not all_dates:
            # Fallback: if no weekdays in range, use any date
            current_date = start_date
            while current_date <= end_date:
                all_dates.append(current_date)
                current_date += datetime.timedelta(days=1)
        
        # Randomly select from available office days
        return np.random.choice(all_dates, size=n_samples, replace=True)

    def _handle_scrape_mode(self, df, items, average_price_config):
        """
        Handles scrape mode by automatically running scraping if needed and processing results.
        Robustly handles cases where scraping returns no results.
        """
        self.stdout.write("Handling scrape mode...")
        
        # Get today's date for caching
        today = timezone.now().date()
        
        # Check if we already have scraped prices for today
        existing_prices = ItemAveragePrice.objects.filter(date=today).count() # type: ignore
        
        if existing_prices == 0:
            self.stdout.write("No scraped prices found for today. Running scraping command...")
            
            # Import the scrape command
            from django.core.management import call_command
            from io import StringIO
            
            try:
                # Capture the output of the scrape command
                out = StringIO()
                call_command('scrape_average_prices', self.config_path, stdout=out, stderr=out)
                
                # Check if scraping was successful
                output = out.getvalue()
                self.stdout.write("Scraping completed. Output:")
                self.stdout.write(output)
                
                # Check if any prices were actually scraped
                scraped_count = ItemAveragePrice.objects.filter(date=today).count() # type: ignore
                if scraped_count == 0:
                    self.stdout.write(self.style.WARNING( # type: ignore
                        "WARNING: Scraping completed but no prices were found. "
                        "This could be due to network issues, API limits, or items not found on the platform. "
                        "Proceeding with blank average_price values."
                    ))
                else:
                    self.stdout.write(f"Successfully scraped {scraped_count} prices.")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR( # type: ignore
                    f"ERROR: Failed to run scraping command: {e}. "
                    "Proceeding with blank average_price values."
                ))
        else:
            self.stdout.write(f"Found {existing_prices} existing scraped prices for today.")
        
        # Get average prices from scraped data (handles cases with no results)
        df = self._get_average_prices_from_scraped_data(df, items)
        
        # Derive unit_purchase_price from average_price
        df = self._derive_unit_price_from_average_price(df, average_price_config)
        
        return df

    def _get_average_prices_from_scraped_data(self, df, items):
        """
        Gets average prices from the ItemAveragePrice model for items in the DataFrame.
        Sets average_price to NaN (blank) if no scraped price is available.
        Robustly handles cases where no scraped prices exist.
        """
        self.stdout.write("Getting average prices from scraped data...")
        
        # Get today's date for caching
        today = timezone.now().date()
        
        # Create a mapping of item names to their scraped prices
        item_price_map = {}
        
        # Get all unique items in the DataFrame
        unique_items = df['item_name'].unique()
        
        # Query the database for scraped prices (case-insensitive matching)
        # Create a case-insensitive mapping for matching
        scraped_prices = ItemAveragePrice.objects.filter( # type: ignore
            date=today
        ).values('item_name', 'average_price')
        
        # Create the mapping with case-insensitive keys
        item_price_map = {}
        for price_record in scraped_prices:
            # Store with uppercase key for case-insensitive matching
            item_price_map[price_record['item_name'].upper()] = price_record['average_price']
        
        # Track statistics
        found_count = 0
        missing_count = 0
        
        # Apply prices to the DataFrame
        average_prices = []
        for item_name in df['item_name']:
            # Convert to uppercase for case-insensitive matching
            item_name_upper = item_name.upper()
            if item_name_upper in item_price_map:
                average_prices.append(float(item_price_map[item_name_upper]))
                found_count += 1
            else:
                # Set to NaN (blank) if no scraped price is available
                average_prices.append(np.nan)
                missing_count += 1
        
        # Ensure average_price column exists and set values
        df['average_price'] = average_prices
        
        if found_count > 0:
            # Get indices of records with found prices
            found_indices = [i for i, price in enumerate(average_prices) if not pd.isna(price)]
            if found_indices:
                blank_count = int(len(found_indices) * 0.10)
                if blank_count > 0:
                    blank_indices = np.random.choice(found_indices, size=blank_count, replace=False)
                    for idx in blank_indices:
                        df.loc[idx, 'average_price'] = np.nan
                        found_count -= 1
                        missing_count += 1
        
        self.stdout.write(f"  - Found scraped prices: {found_count}")
        self.stdout.write(f"  - Missing prices (set to blank): {missing_count}")
        
        if found_count == 0:
            self.stdout.write(self.style.WARNING( # type: ignore
                "WARNING: No scraped prices found for any items. "
                "All average_price values will be blank. "
                "This is normal if scraping failed or items are not available on the platform."
            ))
        elif missing_count > 0:
            self.stdout.write(self.style.WARNING( # type: ignore
                f"WARNING: {missing_count} items had no scraped prices and will be blank. "
                "This is normal for some items that may not be available on the platform."
            ))
        
        return df

    def _derive_unit_price_from_average_price(self, df, average_price_config):
        """
        Derives unit_purchase_price from average_price with configurable variation.
        Uses field_rules fallback when average_price is not available.
        """
        self.stdout.write("Deriving unit_purchase_price from average_price...")
        
        # Get variation configuration from YAML
        variation_config = average_price_config.get('unit_price_variation', {})
        min_factor = variation_config.get('min_factor', 0.85)  # Default ±15%
        max_factor = variation_config.get('max_factor', 1.15)
        
        # Ensure unit_purchase_price column exists (from field_rules fallback)
        if 'unit_purchase_price' not in df.columns:
            self.stdout.write("  - ERROR: unit_purchase_price not found in field_rules. This is required for fallback.")
            df['unit_purchase_price'] = np.nan
            return df
        
        # Only process records that have average_price
        valid_mask = df['average_price'].notna()
        
        if valid_mask.sum() == 0:
            self.stdout.write("  - No valid average_price found. Using field_rules fallback for unit_purchase_price.")
            # Keep the existing unit_purchase_price from field_rules as fallback
            return df
        
        # Generate unit prices based on average_price with configurable variation
        variation_factor = np.random.uniform(min_factor, max_factor, size=valid_mask.sum())
        
        # Get the average prices for valid records
        valid_average_prices = df.loc[valid_mask, 'average_price'].values
        
        # Calculate unit prices with variation
        unit_prices = valid_average_prices * variation_factor
        
        # Update unit_purchase_price for valid records (derived from average_price)
        df.loc[valid_mask, 'unit_purchase_price'] = unit_prices.round(4)
        
        # For records without average_price, keep the field_rules fallback
        # (unit_purchase_price already exists from field_rules)
        
        variation_percent = int((max_factor - min_factor) * 50)  # Calculate percentage for display
        self.stdout.write(f"  - Derived unit_purchase_price from average_price for {valid_mask.sum()} records")
        self.stdout.write(f"  - Used field_rules fallback for {len(df) - valid_mask.sum()} records (no average_price)")
        self.stdout.write(f"  - Variation range: ±{variation_percent}% from average_price (min: {min_factor}, max: {max_factor})")
        
        return df

    def _rearrange_columns(self, df):
        """
        Arranges DataFrame columns in a logical, readable order.
        Follows the natural flow of a procurement transaction.
        """
        # Define the desired column order
        column_order = [
            # --- Transaction Identification ---
            'transaction_id',
            'transaction_date',
            'invoice_number',
            'payment_receipt_number',
            
            # --- Project Information ---
            'project_name',
            'end_user_unit', 
            'project_description',
            
            # --- Item Details ---
            'item_name',
            'quantity',
            
            # --- Pricing ---
            'unit_purchase_price',
            # 'total_purchase_price',
            'average_price',
            'approved_budget',
            
            
            # --- Procurement Process ---
            'procurement_method_name',
            'supplier',
            'procurement_officer',
            
            # --- Procurement Timeline (Chronological) ---
            'invitation_to_bid_posting_date',
            'bid_opening_date',
            'bid_submission_deadline',
            'notice_of_award_date',
            'contract_signing_date',
            
            # --- System Fields ---
            'created_at',
            'blockchain_status',
            'blockchain_error',
            'blockchain_retry_count',
            'last_blockchain_attempt'
        ]
        
        # Get existing columns that are actually in the DataFrame
        existing_columns = [col for col in column_order if col in df.columns]
        
        # Add any remaining columns that weren't in the predefined order
        remaining_columns = [col for col in df.columns if col not in existing_columns]
        
        # Combine and reorder
        final_column_order = existing_columns + remaining_columns
        
        return df[final_column_order]

    def _inject_anomalies(self, df, config):
        """Applies anomaly blueprints to a fraction of the DataFrame."""
        df['is_anomaly'] = 0
        n_anomalies = int(len(df) * config['anomaly_fraction'])
        if n_anomalies == 0:
            self.stdout.write("Anomaly fraction is zero; no anomalies will be injected.")
            return df

        # --- Filter to only use blueprints listed in the YAML config ---
        active_blueprint_names = config.get('active_anomalies', [])
        active_blueprints = [bp for bp in ANOMALY_BLUEPRINTS if bp.name in active_blueprint_names]
        
        if not active_blueprints:
            self.stdout.write("No active anomaly blueprints found in config. Skipping injection.")
            return df

        # --- Normalize weights of active blueprints so they sum to 1 ---
        total_weight = sum(bp.weight for bp in active_blueprints)
        probabilities = [bp.weight / total_weight for bp in active_blueprints]

        # --- Select anomaly indices and apply blueprints ---
        anomaly_indices = np.random.choice(df.index, size=n_anomalies, replace=False)
        df.loc[anomaly_indices, 'is_anomaly'] = 1

        # For each selected anomaly, randomly choose a blueprint and apply it
        for idx in anomaly_indices:
            # Choose a blueprint based on the normalized weights
            chosen_blueprint = np.random.choice(active_blueprints, p=probabilities)
            
            # Apply the logic from the chosen blueprint's class
            # Get the record as a copy, modify it, then assign back
            record = df.loc[idx].copy()
            modified_record = chosen_blueprint.apply(record)
            df.loc[idx] = modified_record

        return df

    def _save_output_files(self, df_raw, df_labeled, config_path, config):
        """Saves the two required CSV files to the specified output folder."""
        # Determine output directory
        output_folder_path = config.get('output_folder_path', 'generated_data')
        
        # Create timestamp for unique subfolder
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = os.path.join(output_folder_path, str(timestamp))
        os.makedirs(output_dir, exist_ok=True)

        # Define file paths
        raw_path = os.path.join(output_dir, 'transactions.csv')
        labeled_path = os.path.join(output_dir, 'transactions_with_labels.csv')

        # Save raw data (without the is_anomaly column)
        df_raw.to_csv(raw_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Successfully saved raw data to: {raw_path}"))  # type: ignore

        # Save labeled data
        df_labeled.to_csv(labeled_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Successfully saved labeled data to: {labeled_path}"))  # type: ignore 