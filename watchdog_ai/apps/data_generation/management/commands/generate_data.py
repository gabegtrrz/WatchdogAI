import os
import uuid
import datetime
import yaml
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from data_generation.anomaly_definitions import ANOMALY_BLUEPRINTS # Import the blueprints

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

        # --- 1. Load Configuration & Items ---
        self.stdout.write(self.style.SUCCESS("Loading configuration..."))
        config, items = self._load_config_and_items(config_path)

        # --- 2. Initialize & Generate ---
        n_samples = config['n_samples']
        random_state = config.get('random_state')
        if random_state:
            np.random.seed(random_state) # setting the starting point (the seed) for NumPy's internal pseudo-random number generator.


            Faker.seed(random_state)

        self.stdout.write(self.style.SUCCESS("Generating raw transaction data..."))
        df = self._generate_raw_transactions(config, items, n_samples)

        # --- 3. Inject Anomalies ---
        self.stdout.write(self.style.SUCCESS("Injecting anomalies..."))
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
            with open(config['item_source_file'], 'r') as f:
                items = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            raise CommandError(f"Item source file not found at: {config['item_source_file']}")
        
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
                    data[field] = [self.faker.date_between(start_date=start, end_date=end) for _ in range(n_samples)]
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

        # --- Calculate approved_budget as 15-22% above average_price ---
        if 'average_price' in df.columns:
            # Generate random percentage between 15% and 22%
            budget_markup = np.random.uniform(0.15, 0.22, size=n_samples)
            df['approved_budget'] = (df['average_price'] * (1 + budget_markup)).round(2)

        # --- Data Cleaning & Type Enforcement ---
        df['approved_budget'] = df['approved_budget'].clip(lower=0)
        df['unit_purchase_price'] = df['unit_purchase_price'].round(2).clip(lower=0)
        df['average_price'] = df['average_price'].round(2).clip(lower=0)
        df['quantity'] = df['quantity'].round().clip(lower=1).astype(int)

        return df

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
            df.loc[idx] = chosen_blueprint.apply(df.loc[idx])

        return df

    def _save_output_files(self, df_raw, df_labeled, config_path, config):
        """Saves the two required CSV files to the specified output folder."""
        # Determine output directory
        config_dir = os.path.dirname(os.path.abspath(config_path))
        output_folder_name = config.get('output_folder', 'generated_data')
        output_dir = os.path.join(config_dir, output_folder_name)
        os.makedirs(output_dir, exist_ok=True)

        # Define file paths
        raw_path = os.path.join(output_dir, 'transactions.csv')
        labeled_path = os.path.join(output_dir, 'transactions_with_labels.csv')

        # Save raw data (without the is_anomaly column)
        df_raw.to_csv(raw_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Successfully saved raw data to: {raw_path}"))

        # Save labeled data
        df_labeled.to_csv(labeled_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Successfully saved labeled data to: {labeled_path}")) 