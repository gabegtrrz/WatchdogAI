import os
import datetime
import yaml
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    """
    A Django management command to generate simulated procurement data.

    This command creates a realistic dataset for training and testing an Isolation
    Forest anomaly detection model. It performs feature engineering to transform
    raw data attributes into features meaningful for machine learning, based on
    a provided YAML configuration file.
    """
    help = 'Generates simulated procurement data for anomaly detection modeling from a YAML configuration file.'

    def add_arguments(self, parser):
        """
        Defines the command-line arguments for the management command.
        
        It requires a single positional argument: the path to the YAML config file.
        """
        parser.add_argument(
            'config_path',
            type=str,
            help='The path to the YAML configuration file for data generation.'
        )

    def handle(self, *args, **options):
        """
        The main execution logic for the management command.

        This method orchestrates the data generation process:
        1. Loads the YAML configuration.
        2. Initializes the generator.
        3. Generates baseline features.
        4. Engineers additional features (date-based, calculated).
        5. Injects a specified fraction of anomalies.
        6. Saves the final dataset to a uniquely named CSV file.
        """
        config_path = options['config_path']

        # --- 1. Load Configuration ---
        self.stdout.write(self.style.HTTP_INFO("Loading configuration..."))
        try:
            with open(config_path, 'r') as f:
                # Safely load the YAML and extract the main configuration dictionary
                config = yaml.safe_load(f)['data_generator']
        except FileNotFoundError:
            raise CommandError(f"Configuration file not found at: {config_path}")
        except (yaml.YAMLError, KeyError) as e:
            raise CommandError(f"Error parsing YAML configuration file: {e}")

        # --- 2. Setup & Initialization ---
        n_samples = config['n_samples']
        random_state = config.get('random_state') # random_state is optional
        anomaly_fraction = config['anomaly_fraction']
        feature_rules = config['feature_rules']
        anomaly_rules = config['anomaly_rules']

        # Seed the random number generator for reproducibility if a state is provided
        if random_state is not None:
            np.random.seed(random_state)

        # --- 3. Generate and Engineer Features ---
        self.stdout.write(self.style.HTTP_INFO("Generating and engineering features..."))
        df = self._generate_all_features(feature_rules, n_samples)
        
        # --- 4. Anomaly Injection ---
        self.stdout.write(self.style.HTTP_INFO("Injecting anomalies..."))
        df = self._inject_anomalies(df, anomaly_fraction, anomaly_rules)

        # --- 5. Save Output ---
        output_path = self._get_output_path(config_path)
        # Ensure the output directory exists before saving
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save the final DataFrame to a CSV file, without the pandas index
        df.to_csv(output_path, index=False)
        self.stdout.write(self.style.SUCCESS(f"Data generation complete. File saved to: {output_path}"))

    def _generate_all_features(self, feature_rules, n_samples):
        """
        Generates a complete DataFrame with baseline, engineered, and calculated features.
        """
        data = {}
        # First, generate baseline features from the configuration rules
        for feature, rule in feature_rules.items():
            rule_type = rule.get('type')
            
            # Generate numerical data from normal (Gaussian) distribution
            if rule_type == 'normal':
                data[feature] = np.random.normal(loc=rule['mean'], scale=rule['std_dev'], size=n_samples)
            
            # Generate numerical data from log-normal distribution
            elif rule_type == 'log-normal':
                # Note: np.random.lognormal's mean and sigma are for the underlying normal distribution
                data[feature] = np.random.lognormal(mean=rule['mean'], sigma=rule['std_dev'], size=n_samples)
            
            # Generate categorical data based on a list of values and optional weights
            elif rule_type == 'categorical':
                data[feature] = np.random.choice(rule['values'], size=n_samples, p=rule.get('weights'))

            # Generate binary (0 or 1) data based on a given probability for '1'
            elif rule_type == 'binary':
                prob_one = rule['probability_of_one']
                data[feature] = np.random.choice([0, 1], size=n_samples, p=[1 - prob_one, prob_one])
        
        df = pd.DataFrame(data)

        # --- Data Cleaning and Type Enforcement ---
        # Ensure that financial values and quantities are non-negative
        if 'unit_price' in df.columns:
            df['unit_price'] = df['unit_price'].clip(lower=0)
        if 'average_price' in df.columns:
            df['average_price'] = df['average_price'].clip(lower=0)
        # Quantities should be whole numbers (integers) and at least 1
        if 'quantity' in df.columns:
            df['quantity'] = df['quantity'].round().clip(lower=1).astype(int)

        # --- Engineer Date-Based Features ---
        # Generate random transaction dates within the last 3 years for realism
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=3 * 365)
        
        # Create random dates by adding a random number of seconds from the start date
        random_seconds = np.random.randint(0, int((end_date - start_date).total_seconds()), n_samples)
        transaction_dates = [start_date + datetime.timedelta(seconds=int(s)) for s in random_seconds]
        
        df['transaction_date'] = pd.to_datetime(transaction_dates)
        
        # Extract day of the week (Monday=0, Sunday=6)
        df['day_of_week'] = df['transaction_date'].dt.dayofweek
        # Create a binary flag for weekend transactions
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # The raw transaction_date is no longer needed for the model
        df = df.drop(columns=['transaction_date'])

        # --- Engineer Calculated Features ---
        # Calculate the price deviation ratio, a key feature for anomaly detection
        # Use .get() to avoid KeyErrors if 'average_price' isn't in the dataframe
        average_price = df.get('average_price')
        unit_price = df.get('unit_price')

        if average_price is not None and unit_price is not None:
            # Handle division by zero: replace with a large number or 1.0, depending on context.
            # Here, we replace with 1.0, assuming no deviation if average is zero.
            df['price_deviation_ratio'] = unit_price.divide(average_price.replace(0, np.nan)).fillna(1.0)
        
        return df

    def _inject_anomalies(self, df, anomaly_fraction, anomaly_rules):
        """
        Selects a fraction of records and modifies them to be anomalous.
        """
        # Add the ground truth column, initialized to 0 (normal)
        df['is_anomaly'] = 0
        
        # Determine the number of anomalies to create
        n_anomalies = int(len(df) * anomaly_fraction)
        if n_anomalies == 0:
            self.stdout.write(self.style.WARNING("Anomaly fraction is too low, no anomalies will be injected."))
            return df

        # Randomly select indices to turn into anomalies, without replacement
        anomaly_indices = np.random.choice(df.index, size=n_anomalies, replace=False)

        # Set the ground truth label for these anomalies
        df.loc[anomaly_indices, 'is_anomaly'] = 1

        # Apply each anomaly rule to the selected records
        for rule in anomaly_rules:
            feature = rule['feature']
            rule_type = rule['type']
            
            if feature not in df.columns:
                self.stdout.write(self.style.WARNING(f"Feature '{feature}' from anomaly rules not in generated data. Skipping."))
                continue

            if rule_type == 'extreme_value':
                # Multiply the feature's current value by a factor to create an outlier
                factor = rule['factor']
                df.loc[anomaly_indices, feature] *= factor
            
            elif rule_type == 'fixed_value':
                # Set the feature to a specific, often unusual, value
                value = rule['value']
                df.loc[anomaly_indices, feature] = value
        
        return df

    def _get_output_path(self, config_path):
        """
        Constructs a unique, informative output filename for the generated data.
        """
        # Get the base name of the config file (e.g., 'train_config' from '.../train_config.yml')
        config_basename = os.path.splitext(os.path.basename(config_path))[0]
        
        # Create a timestamp string in YYYY-MM-DD_HH-MM-SS format
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        # Define the output directory at the project root
        output_dir = os.path.join(os.getcwd(), 'data')
        
        # Combine parts to create the full, unique path
        return os.path.join(output_dir, f"{config_basename}_{timestamp}.csv") 