# Watchdog AI - Procurement Anomaly Detection & Blockchain Ledger

This Django application analyzes procurement transactions for anomalies and records them onto a simulated blockchain ledger for data integrity.

### 30% Includes:

* **Data Generation:** generating simulated data for training the Isolation Forest Model
* **Web Scraping Module:** scraping item prices from external sources (Amazon), retrieving average price for each item, mechanism for checking if it's up-to-date; and running the scraper if not up-to-date, storing this in JSON format
* **Initial Simulated Blockchain Module:** an initial implementation of the simulated blockchain, along with its data_structure, its integration as a Django Model for ORM, and its internal services.
* **Initial Implementation of Transaction Verification and Blockchain Integration Services** 
* **Inital User Interface:** Providing a view of the Blockchain Ledger, Generated Transactions, and an interface for uploading transactions into the program. (with proper user message capabilities).

## Prerequisites

* **Python:** Version 3.10 or higher recommended (based on project documentation).
* **pip:** Python package installer.
* **virtualenv** (Recommended): To create isolated Python environments.
* **Git**
  
## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/gabegtrrz/WatchdogAI.git
    cd watchdog_ai 
    ```
    
    *(If you already have the `watchdog_ai` folder, just navigate into it)*
    ```bash
    cd path/to/watchdog_ai
    ```

2.  **Create and Activate Virtual Environment (Recommended):**

    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate 
    ```

4.  **Install Dependencies:**
  make sure currently in directory containing requirements.txt
   
    ```bash
    pip install -r requirements.txt 
    ```
    

5.  **Apply Database Migrations:**
   
    This sets up the database tables defined in `viewer/models.py` including `BlockchainTransactionData`.

     Change directory to `watchdog_ai`
    
    ```bash
    python manage.py migrate
    ```

## Running the Application

1.  **Start the Development Server:**
    ```bash
    python manage.py runserver
    ```

2.  **Access the Application:**
    Open your web browser and go to: `http://127.0.0.1:8000/`

## How to Interact

1.  **Upload Transaction Data:**
    * Navigate to the upload page.
    * Click the "Choose File" button and select your procurement transaction CSV file.
      
    * **Required CSV Columns:** The file must contain the columns: `transaction_id`, `item_name`, `quantity`, `procurement_method`, `unit_price`, `average_price`, `supplier`, `procurement_officer`, `transaction_date`.
    * (A sample file is provided. It's located in `transaction_sample/` folder.
    * Click the "Upload" button.
    * Upon successful upload, the transactions will be processed and added to the blockchain ledger. You should see a success message.

2.  **View Blockchain Ledger:**
    * Navigate to the blockchain view page.
    * This page displays the immutable records stored in the `BlockchainTransactionData` table, ordered by block number.

3.  **Generate Simulated Data (via Terminal):**
    * The project includes a utility for generating sample data.
    * Open your terminal/command prompt.
    * Make sure your virtual environment is activated.
    * Navigate to the `data_utils` directory:
        ```bash
        cd watchdog_ai/data_utils 
        ```
    * Run the generation script:
        ```bash
        python generate_data.py
        ```
    * **Output:** Check the script's output messages. Generated CSV files are likely saved within the `watchdog_ai/data_utils/transactions_folder/` directory. You can then upload these generated files via the web interface.

## Output Locations

* **Blockchain Data:** Viewed directly in the web application at `/blockchain/`.
* **Generated Sample Data:** Saved as CSV files in the `watchdog_ai/data_utils/transactions_folder/` directory.
