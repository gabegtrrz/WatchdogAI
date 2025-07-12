# watchdog_ai/apps/data_generation/anomaly_definitions.py
import numpy as np

# ---------------------------------------------------
# Anomaly Blueprint Definitions
# ---------------------------------------------------
# Each class in this file represents a blueprint for an anomaly scenario.

    # `name`: The user-facing name, used in the YAML config.

    # `weight`: The probability of this anomaly type being chosen. Weights across all active blueprints will be normalized.
    
    # `apply(record)`: A static method that takes a single transaction record (a pandas Series) and modifies it in place to be anomalous.
# ---------------------------------------------------

class SuspiciousOverpricing:
    """
    Scenario: An item is grossly overpriced, and the transaction is pushed
    through a non-competitive procurement method with a specific supplier.
    """
    name = "Suspicious Overpricing"
    weight = 0.4  # 40% chance

    @staticmethod
    def apply(record):
        # Modify the record (a pandas Series) to make it anomalous.
        # Use np.random for more realistic, non-uniform anomalies.
        record['unit_purchase_price'] *= np.random.uniform(7.5, 12.5)
        record['supplier'] = 'Premium Imports LLC'
        record['procurement_method'] = 'Direct Contracting' # Avoids competitive bidding
        return record

class UnusualBulkOrder:
    """
    Scenario: A very large quantity of an item is procured under a vague
    project name, suggesting it might be bypassing normal budget controls.
    """
    name = "Unusual Bulk Order"
    weight = 0.3 # 30% chance

    @staticmethod
    def apply(record):
        record['quantity'] *= np.random.randint(20, 35)
        record['project_name'] = 'Special Unbudgeted Project'
        return record

class EndOfYearRush:
    """
    Scenario: A transaction is rushed at the very end of the fiscal year,
    often a red flag for using up leftover budget without proper diligence.
    """
    name = "End of Year Rush"
    weight = 0.3 # 30% chance

    @staticmethod
    def apply(record):
        # Forcing a suspicious date and description.
        record['transaction_date'] = record['transaction_date'].replace(month=12, day=np.random.randint(28, 31))
        record['project_description'] = 'URGENT - Use remaining 2024 budget'
        return record


# --- Master list of all available anomaly blueprints ---
# The generator command will import this list to find available scenarios.
ANOMALY_BLUEPRINTS = [
    SuspiciousOverpricing,
    UnusualBulkOrder,
    EndOfYearRush,
] 