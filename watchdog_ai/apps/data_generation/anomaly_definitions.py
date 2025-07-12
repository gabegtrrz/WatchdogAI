# watchdog_ai/apps/data_generation/anomaly_definitions.py
import numpy as np
import datetime

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

class CompressedTimeline:
    """
    Scenario: The entire procurement timeline is unnaturally short,
    suggesting the winning bidder was pre-selected.
    """
    name = "Compressed Timeline"
    weight = 0.35 # High chance, as this is a common anomaly pattern

    @staticmethod
    def apply(record):
        # All key events happen within a single week
        record['contract_signing_date'] = record['transaction_date'] - datetime.timedelta(days=1)
        record['notice_of_award_date'] = record['contract_signing_date'] - datetime.timedelta(days=1)
        record['bid_opening_date'] = record['notice_of_award_date'] - datetime.timedelta(days=1)
        record['bid_submission_deadline'] = record['bid_opening_date']
        record['invitation_to_bid_posting_date'] = record['bid_submission_deadline'] - datetime.timedelta(days=2) # Violates 7-day rule
        return record

class WeekendActivity:
    """
    Scenario: Key procurement events occur on a weekend, which is highly
    irregular for official government/business processes.
    """
    name = "Weekend Activity"
    weight = 0.25 # A more specific, but important, anomaly

    @staticmethod
    def apply(record):
        # Find the most recent Saturday from the transaction date
        transaction_date = record['transaction_date']
        weekend_date = transaction_date - datetime.timedelta(days=(transaction_date.weekday() + 2) % 7)
        
        # Set key dates to this weekend
        record['contract_signing_date'] = weekend_date
        record['notice_of_award_date'] = weekend_date - datetime.timedelta(days=1) # A Friday or Saturday
        return record

class InsufficientBiddingPeriod:
    """
    Scenario: The period between the bid invitation and the submission deadline
    is less than the legally required minimum (e.g., 7 days), discouraging
    fair competition.
    """
    name = "Insufficient Bidding Period"
    weight = 0.4 # A very common and important anomaly to detect

    @staticmethod
    def apply(record):
        # This modification directly violates the 7-day rule.
        short_period = np.random.randint(1, 6) # 1 to 6 days
        record['bid_submission_deadline'] = record['bid_opening_date']
        record['invitation_to_bid_posting_date'] = record['bid_submission_deadline'] - datetime.timedelta(days=short_period)
        return record

class DelayedAwardNotice:
    """
    Scenario: The Notice of Award is issued much later than the legal
    timeframe after bid opening, suggesting possible irregularities or delays.
    """
    name = "Delayed Award Notice"
    weight = 0.2

    @staticmethod
    def apply(record):
        # This violates the typical 7-day period for issuing an award.
        long_delay = np.random.randint(15, 45) # 15 to 45 days late
        record['notice_of_award_date'] = record['bid_opening_date'] + datetime.timedelta(days=long_delay)
        # All subsequent dates must be pushed forward to maintain logical sequence.
        record['contract_signing_date'] = record['notice_of_award_date'] + datetime.timedelta(days=np.random.randint(1, 10))
        record['transaction_date'] = record['contract_signing_date'] + datetime.timedelta(days=np.random.randint(1, 15))
        return record

class PrematureContractSigning:
    """
    Scenario: The contract is signed before the Notice of Award is even issued,
    a clear sign of a pre-arranged or rigged deal.
    """
    name = "Premature Contract Signing"
    weight = 0.2

    @staticmethod
    def apply(record):
        # This makes the timeline logically impossible.
        record['contract_signing_date'] = record['notice_of_award_date'] - datetime.timedelta(days=np.random.randint(1, 5))
        return record


# --- Master list of all available anomaly blueprints ---
# The generator command will import this list to find available scenarios.
ANOMALY_BLUEPRINTS = [
    SuspiciousOverpricing,
    UnusualBulkOrder,
    EndOfYearRush,
    CompressedTimeline,
    WeekendActivity,
    InsufficientBiddingPeriod,
    DelayedAwardNotice,
    PrematureContractSigning,
] 