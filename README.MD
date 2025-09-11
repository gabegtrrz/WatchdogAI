# Watchdog AI: Explainable AI & Blockchain for Transparent Procurement 🕵️‍♂️⛓️

An intelligent system that detects fraud and ensures integrity in procurement using Explainable AI and a tamper-proof ledger. This project was developed as part of a bachelor's thesis to address critical vulnerabilities in public and private sector procurement.

-----

## The Problem

Procurement processes are notoriously vulnerable to financial irregularities and lack transparency. Traditional manual audits are slow and struggle to find a needle in a haystack of vast datasets. Furthermore, while Artificial Intelligence can help, its "black box" nature often creates distrust, making it difficult for organizations to adopt and rely on AI-driven insights for critical oversight.

## The Solution: Watchdog AI

Watchdog AI is an integrated framework that provides a robust, transparent, and user-friendly solution to enhance accountability in procurement. It combines three powerful technologies to create a comprehensive oversight system:

1.  **🤖 AI-Powered Anomaly Detection:** Utilizes an unsupervised **Isolation Forest** machine learning algorithm to intelligently sift through thousands of transactions and flag suspicious activities related to abnormal pricing, quantities, suppliers, and more.
2.  **💡 Explainable AI (XAI):** The system integrates **SHAP** (SHapley Additive exPlanations) to demystify the AI's decisions. Instead of just flagging a transaction, it provides clear, human-interpretable explanations for *why* something was flagged, building trust and enabling auditors to take decisive action.
3.  **⛓️ Blockchain for Integrity:** A **simulated blockchain** provides a tamper-evident, auditable log of all procurement records. This proof-of-concept demonstrates how blockchain principles can be used to guarantee data integrity and create a secure, unalterable audit trail.

-----

## Key Features

  * **Unsupervised Anomaly Detection:** Proactively identifies potential fraud or errors without needing prior examples of "bad" transactions.
  * **Interpretable AI Decisions:** Generates intuitive visualizations and explanations for each anomaly detected.
  * **Tamper-Evident Transaction Ledger:** Ensures that once a record is added, it cannot be altered without detection.
  * **Tunable Synthetic Data Generation:** Includes a data generation framework to create realistic procurement datasets for training and rigorous evaluation.
  * **User-Friendly Web Interface:** A clean and accessible web application designed for non-technical stakeholders to easily upload data, run analyses, and interpret the results.

-----

## Tech Stack

This project was built using a modern, industry-standard stack:

  * **Backend:** Python, Django, Pandas, Scikit-learn
  * **Machine Learning:** Isolation Forest
  * **Explainable AI:** SHAP, Matplotlib
  * **Frontend:** HTML5, CSS3, JavaScript
  * **Database:** PostgreSQL

-----

## Proven Performance & Evaluation

The system underwent a multi-faceted evaluation, demonstrating its efficacy and quality with outstanding results. This isn't just a concept; it's a proven solution.

* ✅ **High-Accuracy AI Model:** Achieved a balanced **F1-Score of 0.72** and an excellent **Area Under the Curve (AUC) of 0.9624** on unseen test data.
* 🔒 **100% Tamper-Detection:** The blockchain component successfully detected **100%** of unauthorized data alteration attempts.
* ⭐ **High User Satisfaction:** Evaluated by 35 stakeholders based on the **ISO/IEC 25010** software quality standard, the system received an overall satisfaction score of **4.38 out of 5**.
      * Performance Efficiency: **4.51 / 5**
      * Reliability: **4.47 / 5**

-----

Of course. Here is a revised "Getting Started" section for your Django project that includes instructions for handling environment variables.

-----

## Getting Started

To get a local copy up and running, follow these simple steps. This guide assumes you have Python, pip, and Git installed on your system.

### Prerequisites

  * **Python 3.9+**
  * **Django**
  * **Git**

### Installation & Setup

1. **Clone the Repository**
    Clone the project to your local machine.

    ```sh
    git clone https://github.com/gabegtrrz/WatchdogAI.git
    cd watchdog-ai
    ```

2. **Install Dependencies**
    Install all the required Python packages using the `requirements.txt` file. It's highly recommended to do this within a virtual environment.

    ```sh
    # Create and activate a virtual environment (optional but recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`

    # Install packages
    pip install -r requirements.txt
    ```

3. **Configure Environment Variables** 🔑
    This project requires several secret keys and configuration variables. Create a `.env` file in the root directory of the project by copying the example file.

    ```sh
    cp .env.example .env
    ```

    Now, open the `.env` file with a text editor and add your specific values for the following variables:

    ```ini
    # .env

    # A strong, unique secret key for Django security.
    SECRET_KEY='your-strong-random-secret-key'

    # The connection URL for your message broker (e.g., RabbitMQ, Redis).
    # Example: amqp://guest:guest@localhost:5672/
    CELERY_BROKER_URL='your-broker-connection-url'

    # Your API key for the web scraping service used for real-time market price data.
    SCRAPEOPS_API_KEY='your-api-key-for-scraping'
    ```

4. **Run Database Migrations**
    Apply the database schema to your local database.

    ```sh
    python manage.py migrate
    ```

5. **Run the Development Server**
    You're all set\! Start the Django development server.

    ```sh
    python manage.py runserver
    ```

    The application will now be running at `http://127.0.0.1:8000/`.

-----

## Usage

1. Navigate to the web interface in your browser.
2. Upload a procurement dataset in `.csv` format.
3. Navigate to Transactions List, and select transactions to analyze.
4. Click the "Analyze" button to initiate the anomaly detection process.
5. Review the dashboard to see flagged transactions, and click on any anomaly to view its detailed SHAP explanation.

-----

## Project Context

This system was developed and validated using a synthetic dataset modeled on the procurement of K-12 Science Laboratory Equipment under Philippine government guidelines. While the model is tuned for this specific scenario, the underlying framework is highly adaptable to other procurement contexts.

-----

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).  
See the [LICENSE](./LICENSE) file for details.  

If you use this software, please provide attribution:  
**Developed by Gabriel Louis Gutierrez (2025).**

-----

## Contact

Gabriel Louis Gutierrez - linkedin.com/in/gabegtrrz
