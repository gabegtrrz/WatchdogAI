# watchdog_ai/apps/data_generation/anomaly_definitions.py
import numpy as np
import datetime
import pandas as pd

# ---------------------------------------------------
# Anomaly Blueprint Definitions
# ---------------------------------------------------
# Each class in this file represents a blueprint for an anomaly scenario.
#
#   `name`: The user-facing name, used in the YAML config.
#   `weight`: The probability of this anomaly type being chosen. Weights across all active blueprints will be normalized.
#   `apply(record)`: A static method that takes a single transaction record (a pandas Series) and modifies it in place to be anomalous.
# 
#   !! Items shall be from data/lab_equipment.txt file alone.
# ---------------------------------------------------
# GOAL: To use these to test the effectiveness of the anomaly detection (iforest) model.
# 
# ============================================================================
# TYPE 1: PRICING & BIDDING ANOMALIES
# ============================================================================

class BudgetEfficiencyAnomaly:
    """
    Scenario: The budget efficiency score is manipulated through unusual
    combinations of budget utilization and price deviation, creating
    suspicious patterns that suggest budget manipulation or price collusion.
    """
    name = "Budget Efficiency Anomaly"
    weight = 0.35

    @staticmethod
    def apply(record):
        # Ensure we have valid budget and price data
        if (pd.isna(record.get('approved_budget')) or record.get('approved_budget', 0) <= 0 or
            pd.isna(record.get('total_purchase_price')) or record.get('total_purchase_price', 0) <= 0):
            return record
            
        # Strategy 1: Over-utilization with minimal price deviation
        # This creates a high budget efficiency score that suggests collusion
        if np.random.random() < 0.5:
            # Set total price to 99.5-99.9% of budget (extreme utilization)
            utilization_rate = np.random.uniform(0.97, 0.999)
            record['total_purchase_price'] = record['approved_budget'] * utilization_rate
            
            # Update unit price if quantity is available
            if record.get('quantity', 0) > 0:
                record['unit_purchase_price'] = record['total_purchase_price'] / record['quantity']
            
            record['supplier'] = 'Precision Budget Solutions Inc.'
            record['project_description'] = 'Strategic procurement with optimal budget utilization.'
            
        # Strategy 2: Under-utilization with extreme price deviation
        # This creates a very low budget efficiency score
        else:
            # Set total price to only 5-15% of budget 
            utilization_rate = np.random.uniform(0.05, 0.20)
            record['total_purchase_price'] = record['approved_budget'] * utilization_rate
            
            # Update unit price if quantity is available
            if record.get('quantity', 0) > 0:
                record['unit_purchase_price'] = record['total_purchase_price'] / record['quantity']
            
            record['supplier'] = 'Budget Underutilization Co.'
            record['project_description'] = 'Procurement with significant budget savings and market-based pricing.'
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Direct Contracting'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Direct Contracting'
            
        return record

class SuspiciousOverpricing:
    """
    Scenario: An item is grossly overpriced, and the transaction is pushed
    through a non-competitive procurement method with a favored supplier.
    """
    name = "Suspicious Overpricing"
    weight = 0.4

    @staticmethod
    def apply(record):
        # Ensure we have valid price data
        if pd.isna(record.get('unit_purchase_price')) or record.get('unit_purchase_price', 0) <= 0:
            return record
            
        record['unit_purchase_price'] *= np.random.uniform(7.5, 12.5)
        
        # Recalculate total price to maintain consistency
        if 'quantity' in record and record['quantity'] > 0:
            record['total_purchase_price'] = record['quantity'] * record['unit_purchase_price']
        
        record['supplier'] = 'Premium Imports LLC'
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Direct Contracting'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Direct Contracting'
            
        record['project_description'] = 'URGENT - Item required immediately, no time for competitive process.'
        return record

class BidCeilingCollusion:
    """
    Scenario: The final contract price is suspiciously close to the
    Approved Budget for the Contract (ABC), a strong indicator of bid-rigging
    where bidders have inside knowledge of the budget ceiling.
    """
    name = "Bid Ceiling Collusion"
    weight = 0.35

    @staticmethod
    def apply(record):
        approved_budget = record.get('approved_budget')
        if pd.isna(approved_budget) or approved_budget <= 0:
            return record
            
        # Set total price to 99.5% - 99.95% of the approved budget 
        collusion_factor = np.random.uniform(0.995, 0.9995)
        total_price = approved_budget * collusion_factor
        record['total_purchase_price'] = total_price
        
        # Update unit price based on the manipulated total price
        if record.get('quantity', 0) > 0:
            record['unit_purchase_price'] = total_price / record['quantity']
        return record

class PriceExceedsBudget:
    """
    Scenario: The final contract price is significantly higher than the
    Approved Budget for the Contract (ABC), indicating a possible lack of
    controls, unauthorized contract variations, or severe miscalculation.
    """
    name = "Price Exceeds Budget"
    weight = 0.2

    @staticmethod
    def apply(record):
        approved_budget = record.get('approved_budget')
        if pd.isna(approved_budget) or approved_budget <= 0:
            return record
            
        # Set total price to be 120% - 180% of the approved budget
        escalation_factor = np.random.uniform(1.2, 1.8)
        total_price = approved_budget * escalation_factor
        record['total_purchase_price'] = total_price
        
        # Update unit price accordingly
        if record.get('quantity', 0) > 0:
            record['unit_purchase_price'] = total_price / record['quantity']
        return record

class ExtremePriceAnomaly:
    """
    Scenario: Prices are so extreme they defy market reality - either
    massively overpriced or suspiciously underpriced, suggesting
    price manipulation or kickback schemes.
    """
    name = "Extreme Price Anomaly"
    weight = 0.3

    @staticmethod
    def apply(record):
        # Ensure we have valid price data
        if pd.isna(record.get('unit_purchase_price')) or record.get('unit_purchase_price', 0) <= 0:
            return record
            
        # 50% chance of extreme overpricing, 50% chance of suspicious underpricing
        if np.random.random() < 0.5:
            # Extreme overpricing: 100-500x multiplier
            record['unit_purchase_price'] *= np.random.uniform(100.0, 500.0)
            record['supplier'] = 'Luxury Premium Suppliers Ltd.'
            record['project_description'] = 'Premium quality items with exceptional specifications.'
        else:
            # Suspicious underpricing: 0.01-0.1x multiplier (suggesting kickbacks)
            record['unit_purchase_price'] *= np.random.uniform(0.01, 0.1)
            record['supplier'] = 'Discount Wholesale Co.'
            record['project_description'] = 'Bulk purchase with significant volume discounts.'
        
        # # Recalculate total price
        # if 'quantity' in record and record['quantity'] > 0:
        #     record['total_purchase_price'] = record['quantity'] * record['unit_purchase_price']
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Direct Contracting'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Direct Contracting'
            
        return record

# ============================================================================
# TYPE 2: QUANTITY & SCOPE ANOMALIES
# ============================================================================

class UnusualBulkOrder:
    """
    Scenario: A very large quantity of an item is procured under a vague
    project name, suggesting it might be bypassing normal budget controls.
    """
    name = "Unusual Bulk Order"
    weight = 0.3

    @staticmethod
    def apply(record):
        # Ensure we have valid quantity
        if pd.isna(record.get('quantity')) or record.get('quantity', 0) <= 0:
            return record
            
        # Much more extreme quantity increase: 50-200x multiplier
        record['quantity'] *= np.random.randint(50, 200)
        
        # Recalculate total price to maintain consistency
        if 'unit_purchase_price' in record and record['unit_purchase_price'] > 0:
            record['total_purchase_price'] = record['quantity'] * record['unit_purchase_price']
        
        record['project_name'] = 'Special Unbudgeted Project'
        record['project_description'] = 'Procurement for unlisted special activities and contingencies.'
        return record

class ContractSplitting:
    """
    Scenario: A project is intentionally broken down into smaller contracts
    to bypass the stricter requirements of public bidding, allowing the use
    of less scrutinized procurement methods like Small Value Procurement.
    """
    name = "Contract Splitting"
    weight = 0.3

    @staticmethod
    def apply(record):
        # Much wider range around the Small Value Procurement threshold
        # The total price is set just below this threshold with more variation
        total_price = np.random.uniform(800000, 999999)
        record['total_purchase_price'] = total_price
        
        if record.get('quantity', 0) > 0:
            record['unit_purchase_price'] = total_price / record['quantity']
        
        record['approved_budget'] = total_price * np.random.uniform(1.0, 1.05)
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Negotiated Procurement (Small Value Procurement)'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Negotiated Procurement (Small Value Procurement)'
            
        record['project_name'] = f"{record.get('project_name', 'Project')} (Phase {np.random.randint(1, 5)})"
        record['project_description'] = "Component of a larger project, procured separately to expedite."
        return record

class MassiveQuantityAnomaly:
    """
    Scenario: Quantities so large they defy practical use, suggesting
    either fraud, resale schemes, or budget padding.
    """
    name = "Massive Quantity Anomaly"
    weight = 0.25

    @staticmethod
    def apply(record):
        # Ensure we have valid quantity
        if pd.isna(record.get('quantity')) or record.get('quantity', 0) <= 0:
            return record
            
        # Extremely large quantities: 500-2000x multiplier
        record['quantity'] *= np.random.randint(500, 2000)
        
        # Recalculate total price
        if 'unit_purchase_price' in record and record['unit_purchase_price'] > 0:
            record['total_purchase_price'] = record['quantity'] * record['unit_purchase_price']
        
        record['project_name'] = 'Emergency Stockpile Project'
        record['project_description'] = 'Critical supplies for extended emergency operations and contingencies.'
        record['supplier'] = 'Bulk Supply Solutions Inc.'
        return record

# ============================================================================
# TYPE 3: TIMELINE & DATE ANOMALIES
# ============================================================================

class EndOfYearRush:
    """
    Scenario: A transaction is rushed at the very end of the fiscal year,
    often a red flag for using up leftover budget without proper diligence.
    """
    name = "End of Year Rush"
    weight = 0.3

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        # Force a suspicious date at the very end of the fiscal year
        end_of_year = record['transaction_date'].replace(month=12, day=np.random.randint(28, 31))
        record['transaction_date'] = end_of_year
        
        # Make other dates suspiciously close
        record['contract_signing_date'] = end_of_year - datetime.timedelta(days=1)
        record['notice_of_award_date'] = end_of_year - datetime.timedelta(days=2)
        record['project_description'] = 'URGENT - Use remaining fiscal year budget before expiration.'
        return record

class CompressedTimeline:
    """
    Scenario: The entire procurement timeline is unnaturally short,
    suggesting the winning bidder was pre-selected.
    """
    name = "Compressed Timeline"
    weight = 0.35

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        # All key events happen within an extremely short period (1-3 days)
        start_date = record['transaction_date'] - datetime.timedelta(days=np.random.randint(1, 3))
        record['contract_signing_date'] = start_date + datetime.timedelta(days=1)
        record['notice_of_award_date'] = start_date
        record['bid_opening_date'] = start_date
        record['bid_submission_deadline'] = start_date
        
        # Invitation posted only 1-2 days before deadline, violating 7-day rule
        record['invitation_to_bid_posting_date'] = start_date - datetime.timedelta(days=np.random.randint(1, 2))
        return record

class BackdatedDocuments:
    """
    Scenario: Key procurement dates are logically inconsistent, suggesting
    document falsification or backdating. For example, bids are opened
    before an invitation to bid is even published.
    """
    name = "Backdated Documents"
    weight = 0.2

    @staticmethod
    def apply(record):
        # Swap dates to create a logical impossibility.
        # This makes it appear that the bid opening happened before the invitation was posted.
        if ('bid_opening_date' in record and 'invitation_to_bid_posting_date' in record and
            not pd.isna(record['bid_opening_date']) and not pd.isna(record['invitation_to_bid_posting_date'])):
            record['bid_opening_date'], record['invitation_to_bid_posting_date'] = \
                record['invitation_to_bid_posting_date'], record['bid_opening_date']
        return record

class WeekendActivity:
    """
    Scenario: Key procurement events occur on a weekend, which is highly
    irregular for official government/business processes.
    """
    name = "Weekend Activity"
    weight = 0.25

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        # Find the most recent Saturday from the transaction date
        transaction_date = record['transaction_date']
        days_since_saturday = (transaction_date.weekday() - 5) % 7
        weekend_date = transaction_date - datetime.timedelta(days=days_since_saturday)
        
        # Set key dates to this weekend (Saturday or Sunday)
        record['contract_signing_date'] = weekend_date
        record['notice_of_award_date'] = weekend_date
        record['bid_opening_date'] = weekend_date - datetime.timedelta(days=1) # Friday evening or Saturday
        return record

class InsufficientBiddingPeriod:
    """
    Scenario: The period between the bid invitation and the submission deadline
    is less than the legally required minimum (7 days), discouraging
    fair competition.
    """
    name = "Insufficient Bidding Period"
    weight = 0.4

    @staticmethod
    def apply(record):
        # Ensure we have valid dates
        if pd.isna(record.get('bid_opening_date')):
            return record
            
        # Explicitly violate the standard 7-day minimum bidding period
        short_period = np.random.randint(1, 6) # 1 to 5 days
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
        # Ensure we have a valid bid opening date
        if pd.isna(record.get('bid_opening_date')):
            return record
            
        # Violates the typical timeframe for issuing an award (7-15 days)
        long_delay = np.random.randint(30, 90) # 1 to 3 months late
        award_date = record['bid_opening_date'] + datetime.timedelta(days=long_delay)
        record['notice_of_award_date'] = award_date
        
        # All subsequent dates must be pushed forward
        record['contract_signing_date'] = award_date + datetime.timedelta(days=np.random.randint(5, 15))
        record['transaction_date'] = record['contract_signing_date'] + datetime.timedelta(days=np.random.randint(5, 20))
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
        # Ensure we have a valid notice of award date
        if pd.isna(record.get('notice_of_award_date')):
            return record
            
        # This makes the timeline logically impossible and suggests a rigged deal
        record['contract_signing_date'] = record['notice_of_award_date'] - datetime.timedelta(days=np.random.randint(1, 10))
        return record

class ImpossibleTimeline:
    """
    Scenario: Timeline events occur in a completely impossible sequence,
    such as contract signing before bid invitation posting.
    """
    name = "Impossible Timeline"
    weight = 0.15

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        base_date = record['transaction_date']
        
        # Create completely impossible timeline sequence
        record['contract_signing_date'] = base_date - datetime.timedelta(days=30)
        record['notice_of_award_date'] = base_date - datetime.timedelta(days=35)
        record['bid_opening_date'] = base_date - datetime.timedelta(days=40)
        record['bid_submission_deadline'] = base_date - datetime.timedelta(days=45)
        record['invitation_to_bid_posting_date'] = base_date - datetime.timedelta(days=50)
        
        record['project_description'] = 'Special procurement arrangement with modified timeline.'
        return record

# ============================================================================
# TYPE 4: SUPPLIER & METHOD ANOMALIES
# ============================================================================

class UnjustifiedDirectContracting:
    """
    Scenario: Direct Contracting, a method for proprietary items, is used
    for common, off-the-shelf goods, suggesting an attempt to avoid
    competition without justification.
    """
    name = "Unjustified Direct Contracting"
    weight = 0.25

    @staticmethod
    def apply(record):
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Direct Contracting'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Direct Contracting'
            
        record['item_name'] = np.random.choice([
            'Beaker – Low Form Griffin, 250 mL, Borosilicate Glass 3.3, with spout and printed graduations',
            'Graduated Cylinder – 100 mL capacity, Class B, Polypropylene, with hexagonal base and molded graduations',
            'Test Tube – 16 × 150 mm, Borosilicate Glass 3.3, rimmed, reusable',
            'Erlenmeyer Flask – 250 mL, Borosilicate Glass 3.3, narrow mouth, with printed graduations',
            'Funnel – Utility type, Polypropylene plastic, 100 mm top diameter',
            'Watch Glass – 100 mm diameter, Soda-Lime glass, fire-polished with beveled edges',
            'Stirring Rod – 200 mm × 7 mm, Borosilicate glass, rounded ends',
            'Test Tube Brush – For 16–20 mm tubes, nylon bristles, galvanized steel wire handle with looped end',
            'Dry Cell Battery – Size D, Carbon-Zinc (Heavy Duty), 1.5 Volts, shrink-wrapped pack of 2',
            'pH Indicator Paper – Universal range (pH 1–14), plastic dispenser roll, 5 meters length',
            'Wire Gauze – 125 × 125 mm (5" × 5"), woven steel mesh with ceramic fiber center',
            'Bond Paper, A4 size, 70 gsm, 500 sheets/ream',
            'Ballpoint Pen, Black Ink, 1.0mm medium point, box of 12',
            'Stapler, Standard size, includes 1000 staples',
            'Whiteboard Marker, Black, chisel tip, non-toxic',
        ])
        record['supplier'] = 'Sole Provider Solutions Inc.'
        return record

class FavoredSupplier:
    """
    Scenario: A specific supplier consistently wins contracts using a
    non-competitive procurement method, regardless of the item being procured.
    This points to potential favoritism.
    """
    name = "Favored Supplier"
    weight = 0.3

    @staticmethod
    def apply(record):
        record['supplier'] = 'VIP General Merchandise'
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = np.random.choice(
                ['Direct Contracting', 'Negotiated Procurement (Small Value Procurement)'],
                p=[0.5, 0.5]
            )
        elif 'procurement_method' in record:
            record['procurement_method'] = np.random.choice(
                ['Direct Contracting', 'Negotiated Procurement (Small Value Procurement)'],
                p=[0.5, 0.5]
            )
            
        record['procurement_officer'] = 'John Lloyd Cruz Miranda' # A specific officer for correlation
        return record

class FictitiousWinner:
    """
    Scenario: The winning supplier appears to be a shell or non-existent
    company, often with a generic-sounding name. This is a common tactic
    to channel funds illicitly.
    """
    name = "Fictitious Winner"
    weight = 0.15

    @staticmethod
    def apply(record):
        first_part = np.random.choice(['Global', 'Nationwide', 'Universal', 'Apex', 'Prime', 'Dynamic'])
        second_part = np.random.choice(['Solutions', 'Enterprises', 'Trading', 'Ventures', 'Group', 'Logistics'])
        suffix = np.random.choice(['Inc.', 'LLC', 'Corp.'])
        record['supplier'] = f'{first_part} {second_part} {suffix}'
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Negotiated Procurement (Small Value Procurement)'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Negotiated Procurement (Small Value Procurement)'
            
        record['project_description'] = 'Services rendered for confidential internal project.'
        return record

class SupplierMonopoly(BidCeilingCollusion):
    """
    Scenario: A single supplier consistently wins bids for specific items,
    even under 'Competitive Bidding', by bidding just under the approved
    budget. This suggests they have inside knowledge of the budget ceiling.
    Inherits logic from BidCeilingCollusion.
    """
    name = "Supplier Monopoly"
    weight = 0.2

    @staticmethod
    def apply(record):
        # Inherit the price manipulation from BidCeilingCollusion
        record = BidCeilingCollusion.apply(record)
        
        # Set a specific supplier and ensure the method appears legitimate
        record['supplier'] = 'Dominant Office Supplies Co.'
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = 'Competitive Bidding'
        elif 'procurement_method' in record:
            record['procurement_method'] = 'Competitive Bidding'
            
        return record


class BudgetManipulation:
    """
    Scenario: The approved budget is artificially inflated to justify
    higher contract prices, creating a false sense of value.
    """
    name = "Budget Manipulation"
    weight = 0.25

    @staticmethod
    def apply(record):
        # Ensure we have valid price data
        if pd.isna(record.get('unit_purchase_price')) or record.get('unit_purchase_price', 0) <= 0:
            return record
            
        # Inflate the approved budget significantly
        inflation_factor = np.random.uniform(3.0, 8.0)  # 3-8x inflation instead of 1.5-2.5x
        record['approved_budget'] = record['unit_purchase_price'] * record.get('quantity', 1) * inflation_factor
        
        # Update total purchase price to be close to the inflated budget
        budget_utilization = np.random.uniform(0.85, 0.95)
        record['total_purchase_price'] = record['approved_budget'] * budget_utilization
        
        record['project_description'] = 'Budget allocation based on comprehensive market analysis and future requirements.'
        return record

class ExpeditedProcurement:
    """
    Scenario: The entire procurement process is unnaturally rushed,
    with all key events happening within an extremely short timeframe.
    This suggests pre-selection of the winning bidder.
    """
    name = "Expedited Procurement"
    weight = 0.25

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        # Create an extremely compressed timeline
        base_date = record['transaction_date']
        
        # All events happen within 1-2 days
        compressed_period = np.random.randint(1, 3)
        record['invitation_to_bid_posting_date'] = base_date - datetime.timedelta(days=compressed_period)
        record['bid_submission_deadline'] = base_date - datetime.timedelta(days=2)
        record['bid_opening_date'] = base_date - datetime.timedelta(days=1)
        record['notice_of_award_date'] = base_date
        record['contract_signing_date'] = base_date + datetime.timedelta(days=1)
        
        record['project_description'] = 'URGENT - Expedited procurement due to critical operational requirements.'
        return record

class IrregularTimelineSequence:
    """
    Scenario: Procurement timeline events occur in a logically impossible
    sequence, such as contract signing before bid opening or award notice
    before bid submission deadline.
    """
    name = "Irregular Timeline Sequence"
    weight = 0.10

    @staticmethod
    def apply(record):
        # Ensure we have valid dates
        if pd.isna(record.get('transaction_date')):
            return record
            
        base_date = record['transaction_date']
        
        # Create impossible timeline sequence
        record['contract_signing_date'] = base_date - datetime.timedelta(days=10)
        record['notice_of_award_date'] = base_date - datetime.timedelta(days=15)
        record['bid_opening_date'] = base_date - datetime.timedelta(days=20)
        record['bid_submission_deadline'] = base_date - datetime.timedelta(days=25)
        record['invitation_to_bid_posting_date'] = base_date - datetime.timedelta(days=30)
        
        record['project_description'] = 'Special procurement arrangement with modified timeline.'
        return record

class MultipleTimelineViolations:
    """
    Scenario: Multiple timeline violations occur simultaneously, indicating
    a systematic disregard for procurement regulations.
    """
    name = "Multiple Timeline Violations"
    weight = 0.2

    @staticmethod
    def apply(record):
        # Ensure we have a valid transaction date
        if pd.isna(record.get('transaction_date')):
            return record
            
        # Create multiple timeline violations
        base_date = record['transaction_date']
        
        # 1. Insufficient bidding period (less than 7 days)
        short_period = np.random.randint(1, 3)  # 1-2 days instead of 2-5
        record['invitation_to_bid_posting_date'] = base_date - datetime.timedelta(days=short_period)
        record['bid_submission_deadline'] = base_date - datetime.timedelta(days=1)
        record['bid_opening_date'] = base_date - datetime.timedelta(days=1)
        
        # 2. Delayed award notice (beyond 7-15 days)
        long_delay = np.random.randint(45, 120)  # 1.5-4 months late instead of 20-45 days
        record['notice_of_award_date'] = record['bid_opening_date'] + datetime.timedelta(days=long_delay)
        
        # 3. Contract signing before award notice
        record['contract_signing_date'] = record['notice_of_award_date'] - datetime.timedelta(days=np.random.randint(1, 5))
        
        record['project_description'] = 'Expedited procurement due to urgent operational requirements.'
        return record

class MethodMisuse:
    """
    Scenario: Procurement methods are used inappropriately, such as using
    Small Value Procurement for high-value items or Direct Contracting for
    common goods.
    """
    name = "Method Misuse"
    weight = 0.2

    @staticmethod
    def apply(record):
        # Randomly choose an inappropriate method for the context
        inappropriate_methods = [
            'Direct Contracting',  # For common goods
            'Negotiated Procurement (Small Value Procurement)',  # For high-value items
            'Repeat Order'  # For new items
        ]
        
        # Handle both field name variations
        if 'procurement_method_name' in record:
            record['procurement_method_name'] = np.random.choice(inappropriate_methods)
        elif 'procurement_method' in record:
            record['procurement_method'] = np.random.choice(inappropriate_methods)
            
        # Inflate quantity or price to make the method choice suspicious
        if record.get('quantity', 0) > 0:
            record['quantity'] *= np.random.randint(5, 15)
            if 'unit_purchase_price' in record and record['unit_purchase_price'] > 0:
                record['total_purchase_price'] = record['quantity'] * record['unit_purchase_price']
        
        record['project_description'] = 'Special procurement arrangement due to unique requirements.'
        return record

# --- Master list of all available anomaly blueprints ---
# The generator command will import this list to find available scenarios.
ANOMALY_BLUEPRINTS = [
    # Pricing & Bidding
    SuspiciousOverpricing,
    BidCeilingCollusion,
    PriceExceedsBudget,
    BudgetManipulation,
    BudgetEfficiencyAnomaly,
    ExtremePriceAnomaly,
    # Quantity & Scope
    UnusualBulkOrder,
    ContractSplitting,
    MassiveQuantityAnomaly,
    # Timeline & Dates
    EndOfYearRush,
    CompressedTimeline,
    WeekendActivity,
    InsufficientBiddingPeriod,
    DelayedAwardNotice,
    PrematureContractSigning,
    BackdatedDocuments,
    ExpeditedProcurement,
    IrregularTimelineSequence,
    MultipleTimelineViolations,
    ImpossibleTimeline,
    # Supplier & Method
    UnjustifiedDirectContracting,
    FavoredSupplier,
    FictitiousWinner,
    SupplierMonopoly,
    MethodMisuse,
] 