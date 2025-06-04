# Personal Financial Planner

## Overview

This project is a personal financial planning and visualization application built with Python, Pandas, and Streamlit. The goal is to provide tools for:
1.  Tracking income and expenses from bank statements.
2.  Categorizing transactions to understand spending habits.
3.  Simulating various financial scenarios (investments, property purchases, debt management).
4.  Visualizing financial health and projections to aid in decision-making.

## Features (Planned)

*   **Transaction Tracking:**
    *   Upload bank statements (CSV format).
    *   Automatic and manual transaction categorization.
    *   Monthly/Annual spending summaries and visualizations.
*   **Scenario Planning:**
    *   Investment growth projections (stocks, ETFs, etc.).
    *   Real estate purchase and rental analysis.
    *   Debt management strategies.
    *   Comparison of multiple financial scenarios.
*   **Data Fetching (Future):**
    *   Integration with APIs for stock market data, real estate trends, inflation rates, etc.
*   **Multi-Page Streamlit Interface.**

## Project Structure

financial-planner/
├── Home.py # Main landing page
├── pages/ # Streamlit pages
│ ├── 01_💰_Transaction_Tracker.py
│ └── ... # Other pages as they are developed
├── core_logic/ # Backend Python modules
│ ├── init.py
│ ├── data_loader.py
│ ├── categorizer.py
│ ├── financial_models.py
│ ├── scenario_manager.py
│ └── config_loader.py
├── data_fetchers/ # Modules for fetching external data
│ ├── init.py
│ └── ...
├── utils/ # Utility functions
│ ├── init.py
│ └── ...
├── config/ # Configuration files (e.g., YAML)
├── saved_scenarios/ # User-defined scenarios
├── assets/ # Static assets like images/CSS
├── .gitignore
├── requirements.txt
└── README.md

## Setup

1.  **Prerequisites:**
    *   Python 3.9+
    *   Git
2.  **Clone the Repository (if applicable):**
    ```bash
    git clone https://github.com/YOUR_USERNAME/financial-planner.git
    cd financial-planner
    ```
3.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # Windows:
    .\venv\Scripts\Activate.ps1
    # macOS/Linux:
    source venv/bin/activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Environment Variables (API Keys - Future):**
    *   Create a `.env` file in the project root (ensure it's in `.gitignore`!).
    *   Add any necessary API keys, e.g.:
        ```
        IDEALISTA_API_KEY="your_key"
        ```

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Navigate to the project root directory.
3.  Run the Streamlit app:
    ```bash
    streamlit run home.py
    ```
4.  Open your web browser and go to the local URL provided by Streamlit (usually `http://localhost:8501`).

## Contributing (Personal Project Notes)

*   Commit frequently with clear messages.
*   Use branches for new features or significant changes.
*   Keep sensitive data (bank statements, API keys in `.env`) out of version control using `.gitignore`.