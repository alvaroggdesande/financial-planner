# pages/02_📊_Scenario_Planner.py
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import List, Dict, Optional, Any

# Add project root to Python path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.financial_models import (
    calculate_compound_growth, project_investment_value_over_time,
    calculate_loan_payment, generate_amortization_schedule,
    project_asset_value, project_asset_value_over_time,
    apply_inflation
)

from src.scenario_config import (
    ScenarioConfig,
    CashHoldingParams,
    StockInvestmentParams,
    RealEstateParams,
    IncomeSourceParams,
    MajorExpenseParams
)
from src.scenario_runner import run_scenario
from src.analysis_functions import calculate_historical_average_annual_living_expenses # If using this

st.set_page_config(page_title="Scenario Planner", layout="wide")
st.title("📊 Scenario Planner")

# --- Initialize Session State for Scenario Planner ---
if 'current_scenario_config' not in st.session_state:
    # Initialize with a default scenario config
    st.session_state.current_scenario_config = ScenarioConfig(name="My First Scenario")
if 'scenario_results' not in st.session_state:
    st.session_state.scenario_results = None # Will hold the DataFrame from run_scenario
if 'scenario_summary' not in st.session_state:
    st.session_state.scenario_summary = None # Will hold dict of summary metrics

# --- Helper function to load/save scenarios (basic example) ---
# In a real app, you'd make this more robust
SAVE_DIR = PROJECT_ROOT / "scenario_configs"
SAVE_DIR.mkdir(exist_ok=True)

def save_scenario_config(config: ScenarioConfig, filename: str):
    filepath = SAVE_DIR / f"{filename}.json"
    # Convert dataclass to dict for JSON serialization
    # This needs a more robust way to handle nested dataclasses
    # For now, a simple approach for top-level fields might work,
    # but nested lists of dataclasses need custom handling or a library like Pydantic.
    # Let's simplify for now and assume we'd reconstruct from dict.
    config_dict = config.__dict__.copy() 
    # Remove non-serializable parts if they exist (like results_timeseries)
    config_dict.pop('results_timeseries', None) 
    config_dict.pop('summary_metrics', None)
    
    # Placeholder for serializing lists of dataclasses
    # For actual saving, you'd iterate through lists like stock_investments
    # and convert each dataclass instance to a dict.
    # This is a known challenge with pure dataclasses and json.
    # A library like `dataclasses-json` or Pydantic would handle this better.
    # For this example, we'll focus on the UI and assume a more robust save/load later.
    
    st.warning("Save/Load for nested components is simplified for this example.")
    with open(filepath, 'w') as f:
        json.dump(config_dict, f, indent=4) # This will fail for nested dataclasses
    st.success(f"Scenario '{filename}' (partially) saved.")
    st.info("Full scenario saving with all components needs a more robust serialization method.")


def load_scenario_config(filename: str) -> Optional[ScenarioConfig]:
    filepath = SAVE_DIR / f"{filename}.json"
    if filepath.exists():
        # Needs proper deserialization from dict back to dataclass instances
        st.info("Full scenario loading needs proper deserialization logic.")
        return ScenarioConfig(name=filename) # Placeholder
    return None

# --- Sidebar: Global Scenario Settings & Scenario Management ---
st.sidebar.header("Scenario Setup")
cs = st.session_state.current_scenario_config # Shorthand

cs.name = st.sidebar.text_input("Scenario Name", value=cs.name)
cs.description = st.sidebar.text_area("Scenario Description", value=cs.description, height=100)
cs.horizon_years = st.sidebar.slider("Projection Horizon (Years)", 1, 50, cs.horizon_years)
cs.general_annual_inflation_rate = st.sidebar.slider("Assumed Annual Inflation Rate (%)", 0.0, 10.0, cs.general_annual_inflation_rate * 100, 0.1) / 100

# Basic Save/Load UI (functionality is placeholder for nested data)
# st.sidebar.subheader("Manage Scenarios")
# scenario_filename_to_save = st.sidebar.text_input("Filename to Save As (no .json)", value=cs.name.lower().replace(" ", "_"))
# if st.sidebar.button("Save Current Scenario"):
#     save_scenario_config(cs, scenario_filename_to_save)

# available_configs = [f.stem for f in SAVE_DIR.glob("*.json")]
# if available_configs:
#     selected_config_to_load = st.sidebar.selectbox("Load Scenario", [""] + available_configs)
#     if selected_config_to_load and st.sidebar.button("Load Selected Scenario"):
#         loaded_config = load_scenario_config(selected_config_to_load)
#         if loaded_config:
#             st.session_state.current_scenario_config = loaded_config
#             st.experimental_rerun()
# else:
#     st.sidebar.write("No saved scenarios yet.")

st.sidebar.markdown("---")

# choosing currency on the side bar
cs.scenario_base_currency = st.sidebar.selectbox(
    "Scenario Base Currency", 
    ["DKK", "EUR"], 
    index=0, # Default to DKK
    key="scenario_currency"
)
st.session_state.currency_suffix_scenario = cs.scenario_base_currency # For display labels


# --- Main Area: Scenario Component Definitions ---
st.header(f"Define Components for: {cs.name}")

# --- Living Expenses (Integrated from Phase 1 or Manual) ---
with st.expander("Living Expenses & Starting Cash", expanded=True):
    cs.initial_cash_on_hand = st.number_input(
        "Initial Cash on Hand (e.g., current accounts, not for specific investments below)",
        min_value=0.0, value=cs.initial_cash_on_hand, step=1000.0, format="%.2f"
    )
    # This initial cash could be the first item in cs.cash_holdings
    # For simplicity, let's add it as a default cash holding if not already present
    # This logic needs to be more robust if user can add/remove cash holdings.
    if not cs.cash_holdings:
        cs.cash_holdings.append(CashHoldingParams(name="Starting Cash", initial_amount=cs.initial_cash_on_hand, annual_interest_rate=0.001))
    elif cs.cash_holdings[0].name == "Starting Cash": # Update if exists
         cs.cash_holdings[0].initial_amount = cs.initial_cash_on_hand
    
    use_historical_expenses = st.checkbox(
    "Use historical average for baseline living expenses?", 
    value=True, # Default to trying to use it
    key="use_hist_exp"
    )
    calculated_hist_avg_exp = None

    if use_historical_expenses:
        historical_transactions = st.session_state.get('categorized_transactions_df', pd.DataFrame())
        if not historical_transactions.empty:
            all_hist_categories = sorted(historical_transactions['Category'].unique().tolist())
            
            # Add categories to exclude by default
            default_excluded = ["Rent Flat", "Deposit Flat"]
            
            # Filter default_excluded to only include categories actually present in all_hist_categories
            actual_default_excluded = [cat for cat in default_excluded if cat in all_hist_categories]
            
            excluded_categories_for_base = st.multiselect(
                "Exclude these categories from historical average (if handled elsewhere in scenario):",
                options=all_hist_categories, # These are the valid options
                default=actual_default_excluded, # This list MUST only contain items from options
                key="hist_exp_exclude_cats"
            )
            
            calculated_hist_avg_exp = calculate_historical_average_annual_living_expenses(
                historical_transactions,
                exclude_categories=excluded_categories_for_base # Use the user's actual selection
            )

            st.info(f"Est. historical avg. annual living expenses (base year): {calculated_hist_avg_exp:,.2f} {st.session_state.get('currency_suffix_scenario','DKK')}")
            cs.base_annual_living_expenses = calculated_hist_avg_exp # Set it on the config
        else:
            st.warning("No historical data in session from Transaction Tracker. Input expenses manually or load data in Tracker first.")
            # Fallback to manual input if historical not available/chosen
            cs.base_annual_living_expenses = st.number_input(
                "Manually set base annual living expenses (base year value):", 
                min_value=0.0, value=cs.base_annual_living_expenses or 30000.0, step=1000.0, format="%.2f"
            )
    else: # Manual input
        cs.base_annual_living_expenses = st.number_input(
            "Manually set base annual living expenses (base year value):", 
            min_value=0.0, value=cs.base_annual_living_expenses or 30000.0, step=1000.0, format="%.2f"
        )

    # Allow user to adjust the calculated/inputted base for the scenario (e.g., "I plan to save 10% more")
    expense_adjustment_pct = st.slider(
        "Adjust base living expenses for this scenario by (%):",
        min_value=-50.0, max_value=50.0, value=0.0, step=1.0,
        help="E.g., -10% if you plan to be more frugal in this scenario, +5% for lifestyle inflation."
    )
    if cs.base_annual_living_expenses is not None: # Check if it was set
        cs.base_annual_living_expenses *= (1 + expense_adjustment_pct / 100)
        st.write(f"Adjusted base annual living expenses for scenario: {cs.base_annual_living_expenses:,.2f} {st.session_state.get('currency_suffix_scenario','DKK')}")

# --- Income Sources ---
# For now, assume one primary income source. Expand later for multiple.
with st.expander("Income Sources", expanded=True):
    st.markdown("Define your primary income source.")
    if not cs.income_sources: # Initialize if empty
        cs.income_sources.append(IncomeSourceParams())
    
    inc_params = cs.income_sources[0] # Get the first (and currently only) income source
    inc_params.name = st.text_input("Income Source Name", value=inc_params.name, key="inc_name")
    inc_params.initial_annual_income = st.number_input("Initial Annual Income (Gross)", min_value=0.0, value=inc_params.initial_annual_income, step=1000.0, format="%.2f", key="inc_initial")
    inc_params.expected_annual_growth_rate = st.slider("Expected Annual Growth Rate (%)", 0.0, 15.0, inc_params.expected_annual_growth_rate * 100, 0.1, key="inc_growth") / 100
    # TODO: Add button "Add another income source"

# --- Stock Investments ---
# For now, assume one primary stock portfolio. Expand later for multiple.
with st.expander("Stock Market Investments", expanded=True):
    st.markdown("Define your main stock/ETF investment portfolio.")
    if not cs.stock_investments: # Initialize if empty
        cs.stock_investments.append(StockInvestmentParams())

    stock_params = cs.stock_investments[0]
    stock_params.name = st.text_input("Portfolio Name", value=stock_params.name, key="stock_name")
    stock_params.initial_investment = st.number_input("Initial Investment Amount", min_value=0.0, value=stock_params.initial_investment, step=1000.0, format="%.2f", key="stock_initial")
    stock_params.annual_contribution = st.number_input("Planned Annual Contribution (from savings/income)", min_value=0.0, value=stock_params.annual_contribution, step=500.0, format="%.2f", key="stock_contrib")
    stock_params.expected_annual_return = st.slider("Expected Avg. Annual Return (%)", 0.0, 20.0, stock_params.expected_annual_return * 100, 0.5, key="stock_return") / 100
    # TODO: Add button "Add another stock portfolio"

# --- Real Estate Investments ---
# For now, assume one property. Expand later for multiple.
with st.expander("Real Estate", expanded=False): # Start collapsed as it has many fields
    st.markdown("Define a real estate property (primary residence or rental).")
    if not cs.real_estate_investments: # Initialize if empty
        cs.real_estate_investments.append(RealEstateParams())

    prop_params = cs.real_estate_investments[0]
    prop_params.name = st.text_input("Property Nickname/Address", value=prop_params.name, key="prop_name")
    
    col1, col2 = st.columns(2)
    with col1:
        prop_params.purchase_price = st.number_input("Purchase Price", min_value=0.0, value=prop_params.purchase_price, step=10000.0, format="%.2f", key="prop_price")
        prop_params.down_payment_pct = st.slider("Down Payment (%)", 0.0, 100.0, prop_params.down_payment_pct * 100, 1.0, key="prop_dp_pct") / 100
        prop_params.mortgage_term_years = st.number_input("Mortgage Term (Years)", min_value=1, max_value=50, value=prop_params.mortgage_term_years, step=1, key="prop_mort_term")
        prop_params.mortgage_interest_rate_annual = st.slider("Mortgage Annual Interest Rate (%)", 0.0, 15.0, prop_params.mortgage_interest_rate_annual * 100, 0.05, key="prop_mort_rate") / 100
        prop_params.expected_annual_appreciation = st.slider("Expected Annual Property Appreciation (%)", -5.0, 15.0, prop_params.expected_annual_appreciation * 100, 0.1, key="prop_apprec") / 100
    
    with col2:
        prop_params.property_tax_annual_pct_value = st.slider("Property Tax (Annual % of Value)", 0.0, 5.0, prop_params.property_tax_annual_pct_value * 100, 0.01, key="prop_tax") / 100
        prop_params.insurance_annual_fixed = st.number_input("Annual Insurance (Fixed Amount)", min_value=0.0, value=prop_params.insurance_annual_fixed, step=50.0, format="%.2f", key="prop_ins")
        prop_params.maintenance_annual_pct_value = st.slider("Maintenance (Annual % of Value)", 0.0, 5.0, prop_params.maintenance_annual_pct_value * 100, 0.1, key="prop_maint") / 100
        prop_params.selling_costs_pct = st.slider("Selling Costs (Agent, Fees % of Value)", 0.0, 10.0, prop_params.selling_costs_pct * 100, 0.5, key="prop_sell_cost") / 100

    prop_type = st.radio("Property Type:", ["Not Used / Investment Only", "Primary Residence", "Rental Property"], 
                         index=1 if prop_params.is_primary_residence else (2 if prop_params.is_rental else 0) ,key="prop_type_radio")
    
    prop_params.is_primary_residence = (prop_type == "Primary Residence")
    prop_params.is_rental = (prop_type == "Rental Property")

    if prop_params.is_primary_residence:
        prop_params.equivalent_monthly_rent_saved = st.number_input("Equivalent Monthly Rent Saved (if primary)", min_value=0.0, value=prop_params.equivalent_monthly_rent_saved, step=50.0, format="%.2f", key="prop_rent_saved")
    
    if prop_params.is_rental:
        prop_params.monthly_rent_income = st.number_input("Gross Monthly Rent Income (if rental)", min_value=0.0, value=prop_params.monthly_rent_income, step=50.0, format="%.2f", key="prop_rent_income")
        prop_params.vacancy_rate_pct = st.slider("Vacancy Rate (% of Year)", 0.0, 50.0, prop_params.vacancy_rate_pct * 100, 1.0, key="prop_vacancy") / 100
        prop_params.management_fee_pct_rent = st.slider("Management Fee (% of Gross Rent)", 0.0, 20.0, prop_params.management_fee_pct_rent * 100, 0.5, key="prop_mgmt_fee") / 100
    # TODO: Add button "Add another property"


# --- Major Future Expenses ---
# For now, assume one major expense. Expand later for multiple.
with st.expander("Major Future Expenses", expanded=False):
    st.markdown("Define significant one-off or recurring future expenses.")
    if not cs.major_expenses: # Initialize if empty
        cs.major_expenses.append(MajorExpenseParams())

    exp_params = cs.major_expenses[0]
    exp_params.name = st.text_input("Expense Name (e.g., New Car, Dream Vacation)", value=exp_params.name, key="maj_exp_name")
    exp_params.amount = st.number_input("Expense Amount (in today's money)", min_value=0.0, value=exp_params.amount, step=500.0, format="%.2f", key="maj_exp_amount")
    exp_params.year_of_expense = st.number_input("Year of Expense (from scenario start, e.g., 5 for 5 years from now)", min_value=1, max_value=cs.horizon_years, value=exp_params.year_of_expense, step=1, key="maj_exp_year")
    # exp_params.is_recurring = st.checkbox("Is this a recurring expense?", value=exp_params.is_recurring, key="maj_exp_recur")
    # if exp_params.is_recurring:
    #     exp_params.recurrence_years = st.number_input("Recurs every X years", min_value=1, value=exp_params.recurrence_years or 4, step=1, key="maj_exp_recur_years")
    # TODO: Add button "Add another major expense"


# --- Run Scenario Button ---
st.markdown("---")
if st.button("🚀 Run Scenario Projection", type="primary"):
    # Here, you would ensure that cs.base_annual_living_expenses is correctly set
    # in the cs object if it was derived from historical data.
    # The current structure of the ScenarioConfig dataclass might need an explicit field for this.
    # For now, assuming scenario_runner.py handles a default or you pass it.
    # Modify ScenarioConfig in scenario_config.py to include:
    # base_annual_living_expenses: float = 30000.0 (or some default)
    # Then cs.base_annual_living_expenses is set above.

    with st.spinner("Calculating scenario... This may take a moment for complex scenarios."):
        # Ensure all components are correctly assigned to the current_scenario_config instance
        # The direct modification `cs.income_sources[0].name = ...` updates the object in session_state
        
        # Update the default cash holding with the initial cash on hand if it was changed
        if cs.cash_holdings and cs.cash_holdings[0].name == "Starting Cash":
            cs.cash_holdings[0].initial_amount = cs.initial_cash_on_hand
        elif not cs.cash_holdings and cs.initial_cash_on_hand > 0 : # if list was empty but cash > 0
             cs.cash_holdings.append(CashHoldingParams(name="Starting Cash", initial_amount=cs.initial_cash_on_hand, annual_interest_rate=0.001))


        # Make sure scenario_runner.py uses cs.base_annual_living_expenses
        # (Update scenario_runner.py to accept this or read from config object)
        # Example modification in scenario_runner.py's run_scenario:
        # annual_living_expenses_base = config.base_annual_living_expenses 
        
        st.session_state.current_scenario_config = run_scenario(st.session_state.current_scenario_config)
        st.session_state.scenario_results = st.session_state.current_scenario_config.results_timeseries
        st.session_state.scenario_summary = st.session_state.current_scenario_config.summary_metrics
    st.success("Scenario projection complete!")

# --- Display Results ---
if st.session_state.scenario_results is not None and not st.session_state.scenario_results.empty:
    st.header("Scenario Results")
    
    results_df = st.session_state.scenario_results
    
    # Key Summary Metrics
    if st.session_state.scenario_summary:
        st.subheader("Summary")
        summary = st.session_state.scenario_summary
        col_sm1, col_sm2, col_sm3 = st.columns(3)
        col_sm1.metric("Scenario Name", summary.get('Scenario_Name', 'N/A'))
        col_sm2.metric("Horizon (Years)", f"{summary.get('Horizon_Years', 'N/A')}")
        col_sm3.metric(f"Ending Net Worth ({st.session_state.get('currency_suffix','DKK')})", 
                       f"{summary.get('Ending_Net_Worth', 0):,.0f}") # Assuming DKK for now
        # Add more summary metrics as calculated by scenario_runner

    # Net Worth Over Time Chart
    st.subheader("Projected Net Worth Over Time")
    if 'Net_Worth_Nominal' in results_df.columns and \
       'Net_Worth_Real' in results_df.columns and \
       'Year' in results_df.columns:
        
        # Let user choose which value to see, or plot both
        display_value_type = st.radio(
            "Display Net Worth As:", 
            ("Nominal Value (Future Money)", f"Real Value (Today's {cs.scenario_base_currency} Purchasing Power)"),
            key="nw_display_type"
        )

        if display_value_type.startswith("Nominal"):
            chart_data_nw = results_df.set_index('Year')[['Net_Worth_Nominal']]
            st.line_chart(chart_data_nw)
            st.caption(f"Nominal value in future {cs.scenario_base_currency}, not adjusted for inflation.")
        else:
            chart_data_nw_real = results_df.set_index('Year')[['Net_Worth_Real']]
            st.line_chart(chart_data_nw_real)
            st.caption(f"Real value in today's {cs.scenario_base_currency} purchasing power (inflation adjusted).")

        # Option to plot both for comparison
        if st.checkbox("Show Nominal and Real Net Worth on same chart?"):
            chart_data_nw_both = results_df.set_index('Year')[['Net_Worth_Nominal', 'Net_Worth_Real']]
            st.line_chart(chart_data_nw_both)
    else:
        st.warning("Net Worth (Nominal/Real) or Year column missing in results.")

    # Update Summary Metrics display
    if st.session_state.scenario_summary:
        st.subheader("Summary")
        summary = st.session_state.scenario_summary
        # ... other metrics ...
        col_sm3.metric(f"Ending Net Worth (Nominal {cs.scenario_base_currency})", 
                       f"{summary.get('Ending_Net_Worth_Nominal', 0):,.0f}")
        # Add another column or row for Real Net Worth
        st.metric(f"Ending Net Worth (Real {cs.scenario_base_currency} - Today's Value)", 
                  f"{summary.get('Ending_Net_Worth_Real', 0):,.0f}")
    

    with st.expander("View Detailed Results Table"):
        st.dataframe(results_df.style.format("{:,.0f}", subset=pd.IndexSlice[:, results_df.select_dtypes(include=np.number).columns]))


    #Projects assets break down graph
    st.subheader("Projected Asset Breakdown Over Time")
    asset_cols = ['Assets_Cash_Nominal', 'Assets_Stocks_Nominal', 'Assets_RealEstate_Equity_Nominal']

    # --- Start Debug ---
    #st.write("DEBUG: Checking columns for Asset Breakdown:")
    #st.write(f"results_df columns: {results_df.columns.tolist()}")
    #st.write(f"Expected asset_cols: {asset_cols}")

    year_present = 'Year' in results_df.columns
    #st.write(f"'Year' column present: {year_present}")

    all_asset_cols_present = all(col in results_df.columns for col in asset_cols)
    #st.write(f"All expected asset_cols present: {all_asset_cols_present}")

    if not all_asset_cols_present:
        missing_cols = [col for col in asset_cols if col not in results_df.columns]
        st.warning(f"Missing asset breakdown columns: {missing_cols}")
    # --- End Debug ---

    if all_asset_cols_present and year_present:
        chart_data_assets = results_df.set_index('Year')[asset_cols]
        st.area_chart(chart_data_assets) # Stacked area chart
    else:
        st.write("Asset breakdown columns missing or 'Year' column missing, cannot plot.")

    # TODO: Add more charts (Asset breakdown, Debt breakdown, Cash Flow)

else:
    st.info("Define a scenario and click 'Run Scenario Projection' to see results.")