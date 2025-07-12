#!/usr/bin/env python3
"""
Test script to verify the three average_price modes work correctly.

This script tests the generate_data command with different average_price configurations
to ensure all three modes work as expected.
"""

import os
import sys
import subprocess
import pandas as pd
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ SUCCESS")
            if result.stdout:
                print("Output:", result.stdout)
            return True
        else:
            print("✗ FAILED")
            print("Error:", result.stderr)
            return False
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
        return False

def check_csv_columns(csv_path, expected_columns, description):
    """Check if a CSV file has the expected columns."""
    print(f"\nChecking CSV: {csv_path}")
    print(f"Expected columns: {expected_columns}")
    
    try:
        df = pd.read_csv(csv_path)
        actual_columns = list(df.columns)
        print(f"Actual columns: {actual_columns}")
        
        # Check if average_price is present/absent as expected
        has_avg_price = 'average_price' in actual_columns
        expected_has_avg_price = 'average_price' in expected_columns
        
        if has_avg_price == expected_has_avg_price:
            print("✓ Column check PASSED")
            return True
        else:
            print("✗ Column check FAILED")
            return False
    except Exception as e:
        print(f"✗ Error reading CSV: {e}")
        return False

def main():
    """Main test function."""
    print("Testing Average Price Modes")
    print("="*60)
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Test configurations
    configs = [
        {
            'file': 'data/no_average_price_config.yml',
            'description': 'No Average Price Mode',
            'expected_columns': ['transaction_id', 'transaction_date', 'invoice_number', 'payment_receipt_number', 'project_name', 'end_user_unit', 'project_description', 'item_name', 'quantity', 'unit_purchase_price', 'approved_budget', 'procurement_method_name', 'supplier', 'procurement_officer', 'invitation_to_bid_posting_date', 'bid_opening_date', 'bid_submission_deadline', 'notice_of_award_date', 'contract_signing_date', 'created_at', 'blockchain_status', 'blockchain_error', 'blockchain_retry_count', 'last_blockchain_attempt', 'is_anomaly']
        },
        {
            'file': 'data/yaml_average_price_config.yml',
            'description': 'YAML Average Price Mode',
            'expected_columns': ['transaction_id', 'transaction_date', 'invoice_number', 'payment_receipt_number', 'project_name', 'end_user_unit', 'project_description', 'item_name', 'quantity', 'unit_purchase_price', 'average_price', 'approved_budget', 'procurement_method_name', 'supplier', 'procurement_officer', 'invitation_to_bid_posting_date', 'bid_opening_date', 'bid_submission_deadline', 'notice_of_award_date', 'contract_signing_date', 'created_at', 'blockchain_status', 'blockchain_error', 'blockchain_retry_count', 'last_blockchain_attempt', 'is_anomaly']
        },
        {
            'file': 'data/scrape_average_price_config.yml',
            'description': 'Scrape Average Price Mode',
            'expected_columns': ['transaction_id', 'transaction_date', 'invoice_number', 'payment_receipt_number', 'project_name', 'end_user_unit', 'project_description', 'item_name', 'quantity', 'unit_purchase_price', 'average_price', 'approved_budget', 'procurement_method_name', 'supplier', 'procurement_officer', 'invitation_to_bid_posting_date', 'bid_opening_date', 'bid_submission_deadline', 'notice_of_award_date', 'contract_signing_date', 'created_at', 'blockchain_status', 'blockchain_error', 'blockchain_retry_count', 'last_blockchain_attempt', 'is_anomaly']
        }
    ]
    
    results = []
    
    for config in configs:
        config_file = config['file']
        description = config['description']
        expected_columns = config['expected_columns']
        
        # Test the generate_data command
        command = f"python manage.py generate_data {config_file}"
        success = run_command(command, description)
        
        if success:
            # Find the generated CSV file
            output_dir = None
            for root, dirs, files in os.walk('data'):
                for dir_name in dirs:
                    if 'generated_data' in dir_name:
                        output_dir = os.path.join(root, dir_name)
                        break
                if output_dir:
                    break
            
            if output_dir:
                csv_file = os.path.join(output_dir, 'transactions_with_labels.csv')
                if os.path.exists(csv_file):
                    csv_success = check_csv_columns(csv_file, expected_columns, description)
                    results.append((description, success and csv_success))
                else:
                    print(f"✗ CSV file not found: {csv_file}")
                    results.append((description, False))
            else:
                print("✗ Output directory not found")
                results.append((description, False))
        else:
            results.append((description, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for description, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{description}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\nOverall Result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 All average_price modes are working correctly!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 