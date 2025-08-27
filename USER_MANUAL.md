# WatchdogAI User Manual

## Procurement Integrity and Anomaly Detection System

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [System Overview](#system-overview)
3. [Uploading Transactions](#uploading-transactions)
4. [Browsing and Filtering Transactions](#browsing-and-filtering-transactions)
5. [Running Anomaly Analysis](#running-anomaly-analysis)
6. [Viewing Analysis Results](#viewing-analysis-results)
7. [Exporting Results](#exporting-results)
8. [Troubleshooting](#troubleshooting)

---

## 🚀 Getting Started

### First Time Setup

1. **Login**: Visit the system and click "Login" in the top navigation
2. **Credentials**: Use one of the available system accounts (see below)
3. **Dashboard**: After login, you'll see the main dashboard with access to all features

### System Credentials

#### Regular User Accounts

| Username      | Password      |
| ------------- | ------------- |
| `stakeholder` | `demopass123` |
| `officer`     | `demopass123` |

**Access Level**: Standard user access to all procurement analysis features

> 🔒 **Security Note**: These are demo credentials. In production, use strong, unique passwords and change them regularly.

### Navigation Overview

- **Home**: Main dashboard with quick access to key features
- **Upload**: Add new transactions to the system
- **Transactions & Analysis**: Browse and analyze existing transactions
- **Profile**: View your account information and settings

---

## 🎯 System Overview

WatchdogAI is a procurement integrity system that combines:

- **AI-Powered Anomaly Detection**: Identifies suspicious transactions
- **Blockchain Integration**: Ensures data integrity and immutability
- **Comprehensive Analytics**: Provides detailed insights into procurement patterns

### Key Features

- ✅ **Secure Upload**: Add transactions via CSV files or individual entries
- ✅ **Smart Filtering**: Find specific transactions quickly
- ✅ **AI Analysis**: Detect anomalies with configurable sensitivity
- ✅ **Detailed Reports**: View comprehensive analysis results
- ✅ **Export Capabilities**: Download results for further review

---

## 📤 Uploading Transactions

### Method 1: Bulk Upload (Recommended for Multiple Transactions)

1. **Navigate to Upload Page**

   - Click "Upload" in the navigation bar
   - Or click "Upload Transactions" from the home dashboard

2. **Prepare Your CSV File**
   Your CSV must include these **required columns**:

   ```
   item_name, quantity, unit_purchase_price, transaction_date,
   procurement_method_name, supplier, invoice_number, payment_receipt_number
   ```

3. **Upload Process**

   - Click "Choose File" and select your CSV
   - Review the blockchain integration status (if available)
   - Click "Upload File"
   - Wait for processing confirmation

4. **What Happens Next**
   - System validates your data
   - Transactions are saved to the database
   - Data is enriched with additional information
   - Transactions are integrated with the blockchain (if enabled)

### Method 2: Single Transaction Upload

1. **Access Single Upload**

   - Click the "Try the Demo" link on the upload page
   - Or use the "Upload a single transaction" button

2. **Fill in Transaction Details**
   - Complete all required fields
   - Add any optional information
   - Click "Submit Transaction"

### Blockchain Integration Status

The system shows real-time blockchain integration status:

- **Total Transactions**: All transactions in the system
- **Pending Integration**: Transactions waiting to be added to blockchain
- **Successfully Integrated**: Transactions confirmed on blockchain
- **Failed Integration**: Transactions that need retry

> 💡 **Tip**: If you see failed integrations, you can click "Retry Failed Blockchain Integration" to attempt processing again.

---

## 🔍 Browsing and Filtering Transactions

### Accessing the Transaction List

1. **Navigate to Transactions**

   - Click "Transactions & Analysis" in the navigation
   - Or click "View & Analyze" from the home dashboard

2. **Understanding the Interface**
   - **Mission Card**: Provides step-by-step guidance
   - **Filter Section**: Collapsible search and filter options
   - **Transaction Table**: Lists all transactions with key details
   - **Pagination**: Navigate through large datasets

### Using Filters

#### Basic Filters

- **Item Name**: Search for specific items
- **Project Name**: Filter by project
- **Supplier**: Find transactions from specific suppliers
- **Transaction ID**: Search by unique transaction identifier

#### Advanced Filters

Click "Advanced Filters" to access:

- **Financial Filters**: Price ranges, budgets, quantities
- **Date Filters**: Transaction date ranges
- **Procurement Method**: Filter by procurement type
- **Status Filters**: Various transaction statuses

### Selecting Transactions for Analysis

1. **Individual Selection**

   - Check the box next to each transaction you want to analyze
   - Use "Select All" to choose all transactions on the current page

2. **Bulk Selection**

   - Use "Select All" to choose all transactions in the system
   - This works across all pages, not just the current view

3. **Proceed to Analysis**
   - Click the "Analyze" button
   - You'll be taken to the analysis configuration page

> 💡 **Tip**: You can select any number of transactions - from 1 to all transactions in the system.

---

## 🤖 Running Anomaly Analysis

### Analysis Configuration

1. **Access Configuration Page**

   - After selecting transactions, you'll see the analysis configuration page
   - Review the number of selected transactions

2. **Understanding Sensitivity Settings**

   The **sensitivity slider** controls how strict the AI is in detecting anomalies:

   - **Conservative (1-10%)**:

     - More precise, fewer false alarms
     - May miss some actual anomalies
     - Good for clean datasets

   - **Sensitive (20-50%)**:
     - Catches more potential issues
     - May flag some normal transactions
     - Good for high-risk scenarios

3. **Recommended Settings**
   - **Start with 5%** for most analyses
   - **Use 1-3%** for very clean datasets
   - **Use 10-20%** if you suspect many anomalies

### Running the Analysis

1. **Configure Settings**

   - Adjust the sensitivity slider to your desired level
   - Review the description showing how many transactions will be flagged

2. **Start Analysis**

   - Click "Begin Analysis"
   - A progress modal will appear showing the analysis status

3. **Wait for Completion**

   - The system will process your transactions
   - You'll see real-time status updates
   - Analysis typically takes 30 seconds to 2 minutes

4. **Results Ready**
   - When complete, you'll be automatically redirected to the results page
   - If there are any issues, you'll see an error message

> 💡 **Tip**: The sensitivity setting tells the AI what percentage of transactions to flag as potentially anomalous. For example, 5% means the AI will flag the 5 most unusual transactions out of 100.

---

## 📊 Viewing Analysis Results

### Understanding the Results Page

1. **Analysis Summary**

   - **Total Analyzed**: Number of transactions processed
   - **Anomalies Found**: Number of suspicious transactions detected
   - **Sensitivity Setting**: The contamination parameter used

2. **Results Navigation**
   - **Desktop**: Use the left sidebar to navigate between sections
   - **Mobile**: Use the dropdown menu at the top

### Key Result Sections

#### 1. Anomaly Summary

- **Anomaly Score**: How suspicious each transaction is (0-1 scale)
- **Transaction Details**: Key information about flagged transactions
- **Risk Indicators**: What factors contributed to the anomaly detection

#### 2. Detailed Analysis

- **Individual Reports**: Click "View Details" for comprehensive analysis
- **Feature Importance**: See which factors most influenced the detection
- **Comparison Data**: How the transaction compares to normal patterns

#### 3. Statistical Overview

- **Distribution Charts**: Visual representation of anomaly scores
- **Pattern Analysis**: Trends and clusters in the data
- **Risk Assessment**: Overall risk level of the dataset

### Understanding Anomaly Scores

- **0.0-0.3**: Low risk, likely normal transaction
- **0.3-0.7**: Medium risk, worth investigating
- **0.7-1.0**: High risk, strong indication of anomaly

> 💡 **Tip**: Anomaly scores are relative to your dataset. A score of 0.8 in one analysis might be equivalent to 0.6 in another, depending on the overall data characteristics.

---

## 📥 Exporting Results

### Export Options

1. **CSV Export**

   - Click "Export Results" button on the analysis results page
   - Download includes all anomaly details and scores
   - Compatible with Excel, Google Sheets, and other tools

2. **Export Contents**
   - **Transaction Details**: All original transaction information
   - **Anomaly Scores**: Risk assessment for each transaction
   - **Analysis Parameters**: Settings used for the analysis
   - **Metadata**: Timestamp, user, and analysis run information

### Using Exported Data

1. **Further Analysis**

   - Import into Excel for additional filtering
   - Use in reporting tools for presentations
   - Share with stakeholders for review

2. **Documentation**
   - Keep records of all analyses
   - Track patterns over time
   - Maintain audit trails

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Upload Problems

**Issue**: "No file selected" error

- **Solution**: Make sure you've selected a CSV file before clicking upload

**Issue**: "Invalid CSV format" error

- **Solution**: Check that your CSV has all required columns with exact names

**Issue**: "Validation errors" message

- **Solution**: Review the error details and fix data issues in your CSV

#### Analysis Problems

**Issue**: Analysis takes too long

- **Solution**: Try analyzing fewer transactions or use a higher sensitivity setting

**Issue**: No anomalies found

- **Solution**: Try lowering the sensitivity setting or check if your data is very clean

**Issue**: Too many anomalies flagged

- **Solution**: Increase the sensitivity setting to be more conservative

#### System Issues

**Issue**: Can't access certain pages

- **Solution**: Make sure you're logged in and have proper permissions

**Issue**: Blockchain integration failures

- **Solution**: Click "Retry Failed Blockchain Integration" or contact support

### Getting Help

1. **Check the Interface**: Most pages include helpful tips and explanations
2. **Review Error Messages**: They often contain specific guidance
3. **Contact Support**: For persistent issues, contact your system administrator

---

## 📚 Best Practices

### Data Preparation

- ✅ Use consistent formatting in your CSV files
- ✅ Include all required fields
- ✅ Clean your data before uploading
- ✅ Use descriptive project and item names

### Analysis Strategy

- ✅ Start with conservative sensitivity settings
- ✅ Analyze smaller batches for initial testing
- ✅ Document your analysis parameters
- ✅ Review results carefully before taking action

### System Usage

- ✅ Log out when finished
- ✅ Keep your login credentials secure
- ✅ Export important results for backup
- ✅ Regular analysis helps identify patterns

---

## 🎓 Quick Reference

### Keyboard Shortcuts

- **Ctrl+F**: Find in current page
- **Ctrl+S**: Save (when available)
- **Escape**: Close modals and popups

### Important URLs

- **Home**: `/`
- **Upload**: `/transactions/upload/`
- **Transaction List**: `/analytics/transactions/`
- **Login**: `/users/login/`
- **Profile**: `/users/profile/`

### File Requirements

- **Format**: CSV (Comma Separated Values)
- **Encoding**: UTF-8
- **Size**: Up to 10MB per file
- **Required Columns**: 8 specific fields (see Upload section)

---

_This manual covers the core functionality of WatchdogAI. For advanced features or technical support, please contact your system administrator._

**Last Updated**: August 2025
