# At the top of pages/02_📊_Scenario_Planner.py
# from src.scenario_config_pydantic import ScenarioConfig # Assuming you made this
# (and your ...Params classes are also Pydantic models within that file)

import streamlit as st
import pandas as pd
from pathlib import Path
import numpy as np # For formatting and potential NaN handling
from typing import Optional # For Pydantic model reference

# Add project root to Python path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Import Pydantic models and runner
from src.scenario_config_pydantic import (
    ScenarioConfig,
    CashHoldingParams,
    StockInvestmentParams,
    RealEstateParams,
    IncomeSourceParams,
    MajorExpenseParams
)
from src.scenario_runner import run_scenario 
from src.analysis_functions import calculate_historical_average_annual_living_expenses
from src.utils import DKK_TO_EUR_RATE#, EUR_TO_DKK_RATE # Make sure these are defined

st.set_page_config(page_title="Scenario Planner", layout="wide")
st.title("📊 Scenario Planner")

# --- Session State Initialization ---
if 'current_scenario_editor' not in st.session_state:
    st.session_state.current_scenario_editor = ScenarioConfig()

if 'scenario_archive' not in st.session_state:
    st.session_state.scenario_archive = {} 

if 'last_run_scenario_name' not in st.session_state:
    st.session_state.last_run_scenario_name = None

if 'scenarios_to_compare' not in st.session_state:
    st.session_state.scenarios_to_compare = []

if 'use_hist_exp_cb_state' not in st.session_state: # For persisting checkbox
    st.session_state.use_hist_exp_cb_state = True


# --- Save/Load Utility Functions (using Pydantic) ---
SAVE_DIR = PROJECT_ROOT / "scenario_json_configs" 
SAVE_DIR.mkdir(exist_ok=True)

def save_scenario_definition_pydantic(config: ScenarioConfig, filename: str):
    filepath = SAVE_DIR / f"{filename.strip()}.json"
    try:
        with open(filepath, 'w') as f:
            # Exclude results when saving the definition
            f.write(config.model_dump_json(indent=4, exclude={'results_timeseries_data', 'summary_metrics'}))
        st.sidebar.success(f"Scenario definition '{filename}' saved.")
    except Exception as e:
        st.sidebar.error(f"Error saving scenario definition: {e}")

def load_scenario_definition_pydantic(filename: str) -> ScenarioConfig | None:
    filepath = SAVE_DIR / f"{filename.strip()}.json"
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                config_obj = ScenarioConfig.model_validate_json(f.read())
            st.sidebar.success(f"Scenario definition '{filename}' loaded.")
            return config_obj
        except Exception as e:
            st.sidebar.error(f"Error loading scenario definition '{filename}': {e}")
            return None
    else:
        st.sidebar.warning(f"Scenario file '{filename}.json' not found.")
        return None

# --- Shorthand for current scenario being edited ---
cs_editor = st.session_state.current_scenario_editor

# --- Sidebar: Global Scenario Settings & Scenario Management ---
with st.sidebar:
    st.header("Scenario Setup")

    cs_editor.name = st.text_input("Scenario Name", value=cs_editor.name, key="cs_name_sidebar")
    cs_editor.description = st.text_area("Description", value=cs_editor.description, height=75, key="cs_desc_sidebar")
    cs_editor.horizon_years = st.slider("Projection Horizon (Years)", 1, 60, cs_editor.horizon_years, key="cs_horizon_sidebar")
    
    # Determine index for selectbox based on current value
    base_currency_options = ["DKK", "EUR"]
    try:
        current_currency_idx = base_currency_options.index(cs_editor.scenario_base_currency)
    except ValueError: # If current value is not in options, default to DKK (index 0)
        current_currency_idx = 0
        cs_editor.scenario_base_currency = "DKK" # Correct the model if invalid

    cs_editor.scenario_base_currency = st.selectbox(
        "Scenario Base Currency", base_currency_options, 
        index=current_currency_idx,
        key="scenario_currency_sidebar"
    )
    # This session state variable is useful for display labels throughout the app
    st.session_state.currency_suffix_scenario = cs_editor.scenario_base_currency

    cs_editor.general_annual_inflation_rate = st.slider(
        "Assumed Annual Inflation Rate (%)", 0.0, 10.0, 
        float(cs_editor.general_annual_inflation_rate * 100), 0.1, key="cs_inflation_sidebar" # Ensure float for value
    ) / 100

    st.subheader("Manage Scenario Definitions")
    scenario_filename_input = st.text_input(
        "Filename for Save/Load (no .json)", 
        value=cs_editor.name.lower().replace(" ", "_").replace("/", "_").strip(),
        key="filename_editor_sidebar"
    )

    col_save, col_load = st.columns(2)
    if col_save.button("💾 Save Definition", key="save_def_sidebar_btn"):
        if scenario_filename_input:
            save_scenario_definition_pydantic(cs_editor, scenario_filename_input)
        else:
            st.error("Please provide a filename to save.")

    if col_load.button("📥 Load Definition", key="load_def_sidebar_btn"):
        if scenario_filename_input:
            loaded_config = load_scenario_definition_pydantic(scenario_filename_input)
            if loaded_config:
                st.session_state.current_scenario_editor = loaded_config
                st.session_state.last_run_scenario_name = None 
                st.experimental_rerun()
        else:
            st.error("Please provide a filename to load.")
    st.caption(f"Definitions saved in: {SAVE_DIR.resolve()}")
    st.markdown("---")

# --- Main Area: Scenario Component Definitions ---
st.header(f"Define Components for: {cs_editor.name}")

with st.form(key="scenario_input_form"):
    # --- Living Expenses & Starting Cash ---
    with st.expander("💰 Living Expenses & Starting Cash", expanded=True):
        cs_editor.initial_cash_on_hand = st.number_input(
            f"Initial Liquid Cash (in {cs_editor.scenario_base_currency})",
            min_value=0.0, value=float(cs_editor.initial_cash_on_hand), step=1000.0, format="%.2f", 
            key="form_init_cash"
        )
        
        # --- Historical Expenses Integration ---
        st.session_state.use_hist_exp_cb_state = st.checkbox(
            "Use historical average for baseline living expenses?", 
            value=st.session_state.use_hist_exp_cb_state, # Persist checkbox state
            key="form_use_hist_exp_cb"
        )
        
        _base_expense_for_input_field = cs_editor.base_annual_living_expenses or 30000.0

        if st.session_state.use_hist_exp_cb_state:
            # Use raw_transactions_df (assumed DKK) for calculation, then convert
            historical_transactions_dkk = st.session_state.get('raw_transactions_df', pd.DataFrame())
            if not historical_transactions_dkk.empty and 'Category' in historical_transactions_dkk.columns: # Ensure 'Category' exists
                all_hist_categories = sorted(historical_transactions_dkk['Category'].unique().tolist())
                default_excluded_cats = ["Rent/Mortgage", "Investments", "Savings Transfer", "Major Debt Payment", "Uncategorized", "Salary"]
                # Filter defaults to only those present in actual categories
                actual_default_excluded = [cat for cat in default_excluded_cats if cat in all_hist_categories]
                
                excluded_cats_input = st.multiselect(
                    "Exclude these categories from historical average:",
                    options=all_hist_categories, default=actual_default_excluded, key="form_hist_exp_exclude"
                )
                
                _calculated_hist_avg_dkk = calculate_historical_average_annual_living_expenses(
                    historical_transactions_dkk, 
                    exclude_categories=excluded_cats_input
                )

                if cs_editor.scenario_base_currency == "EUR":
                    _base_expense_for_input_field = _calculated_hist_avg_dkk * DKK_TO_EUR_RATE
                else: # DKK
                    _base_expense_for_input_field = _calculated_hist_avg_dkk
                
                st.info(f"Est. hist. avg. annual living expenses: {_base_expense_for_input_field:,.2f} {cs_editor.scenario_base_currency}")
            elif not historical_transactions_dkk.empty and 'Category' not in historical_transactions_dkk.columns:
                st.warning("Historical transactions loaded but not categorized. Run Transaction Tracker first or input manually.")
            else: # No historical data
                st.warning("No historical data in session. Input expenses manually or run Transaction Tracker first.")
        
        # This number_input holds the base expense value (either from historical or manual override)
        base_annual_living_expenses_form_val = st.number_input(
            "Base annual living expenses (today's value):", 
            min_value=0.0, 
            value=float(_base_expense_for_input_field), 
            step=1000.0, format="%.2f",
            key="form_base_exp_input"
        )

        expense_adjustment_pct_form_val = st.slider(
            "Adjust base living expenses for this scenario by (%):", -50.0, 50.0, 0.0, 1.0,
            help="E.g., -10% for frugality. Applied to the value above.", key="form_exp_adj_slider"
        )

    # --- Initialize Component Lists in Pydantic Model if Empty ---
    if not cs_editor.cash_holdings: 
        cs_editor.cash_holdings.append(CashHoldingParams(name="Primary Liquid Cash", initial_amount=cs_editor.initial_cash_on_hand))
    else: # Update first cash holding to match initial_cash_on_hand
        cs_editor.cash_holdings[0].initial_amount = cs_editor.initial_cash_on_hand
        cs_editor.cash_holdings[0].name="Primary Liquid Cash"

    if not cs_editor.income_sources: cs_editor.income_sources.append(IncomeSourceParams())
    if not cs_editor.stock_investments: cs_editor.stock_investments.append(StockInvestmentParams())
    if not cs_editor.real_estate_investments: cs_editor.real_estate_investments.append(RealEstateParams())
    if not cs_editor.major_expenses: cs_editor.major_expenses.append(MajorExpenseParams())
    
    # --- Component Inputs (Simplified to one of each for now) ---
    with st.expander("📈 Income Source 1", expanded=True):
        inc = cs_editor.income_sources[0]
        inc.name = st.text_input("Name##inc1", value=inc.name, key="form_inc1_name")
        inc.initial_annual_income = st.number_input("Initial Annual Income##inc1", value=float(inc.initial_annual_income), min_value=0.0, format="%.2f", key="form_inc1_amt")
        inc.expected_annual_growth_rate = st.slider("Annual Growth (%)##inc1", 0.0, 10.0, float(inc.expected_annual_growth_rate*100), 0.1, key="form_inc1_growth") / 100

    with st.expander("💹 Stock Portfolio 1", expanded=True):
        stock = cs_editor.stock_investments[0]
        stock.name = st.text_input("Name##stock1", value=stock.name, key="form_stock1_name")
        stock.initial_investment = st.number_input("Initial##stock1", value=float(stock.initial_investment), min_value=0.0, format="%.2f", key="form_stock1_init")
        stock.annual_contribution = st.number_input("Annual Contribution##stock1", value=float(stock.annual_contribution), min_value=0.0, format="%.2f", key="form_stock1_contrib")
        stock.expected_annual_return = st.slider("Expected Return (%)##stock1", 0.0, 20.0, float(stock.expected_annual_return*100), 0.1, key="form_stock1_ret") / 100

    with st.expander("🏡 Real Estate Property 1", expanded=False):
        prop = cs_editor.real_estate_investments[0]
        prop.name = st.text_input("Property Nickname##prop1", value=prop.name, key="form_prop1_name")
        prop.purchase_price = st.number_input("Purchase Price##prop1", value=float(prop.purchase_price), format="%.2f", key="form_prop1_price")
        prop.down_payment_pct = st.slider("Down Payment (%)##prop1", 0.0, 100.0, float(prop.down_payment_pct * 100), 1.0, key="form_prop1_dppct") / 100
        prop.mortgage_term_years = st.number_input("Mortgage Term (Years)##prop1", min_value=1, max_value=50, value=int(prop.mortgage_term_years), step=1, key="form_prop1_term")
        prop.mortgage_interest_rate_annual = st.slider("Mortgage Rate (%)##prop1", 0.0, 15.0, float(prop.mortgage_interest_rate_annual * 100), 0.05, key="form_prop1_rate") / 100
        prop.expected_annual_appreciation = st.slider("Property Appreciation (%)##prop1", -5.0, 15.0, float(prop.expected_annual_appreciation * 100), 0.1, key="form_prop1_apprec") / 100
        prop.property_tax_annual_pct_value = st.slider("Property Tax (% of Value)##prop1", 0.0, 5.0, float(prop.property_tax_annual_pct_value * 100), 0.01, key="form_prop1_tax") / 100
        prop.insurance_annual_fixed = st.number_input("Annual Insurance##prop1", value=float(prop.insurance_annual_fixed), format="%.2f", key="form_prop1_ins")
        prop.maintenance_annual_pct_value = st.slider("Maintenance (% of Value)##prop1", 0.0, 5.0, float(prop.maintenance_annual_pct_value * 100), 0.1, key="form_prop1_maint") / 100
        prop.selling_costs_pct = st.slider("Selling Costs (% of Value)##prop1", 0.0, 10.0, float(prop.selling_costs_pct * 100), 0.5, key="form_prop1_sellcost") / 100
        
        prop_type_options = ["Not Used / Investment Only", "Primary Residence", "Rental Property"]
        current_prop_type_index = 0
        if prop.is_primary_residence: current_prop_type_index = 1
        elif prop.is_rental: current_prop_type_index = 2
        prop_type_selection = st.radio("Property Type:##prop1", prop_type_options, index=current_prop_type_index, key="form_prop1_type")
        prop.is_primary_residence = (prop_type_selection == "Primary Residence")
        prop.is_rental = (prop_type_selection == "Rental Property")

        if prop.is_primary_residence:
            prop.equivalent_monthly_rent_saved = st.number_input("Equivalent Monthly Rent Saved##prop1", value=float(prop.equivalent_monthly_rent_saved), format="%.2f", key="form_prop1_rentsaved")
        if prop.is_rental:
            prop.monthly_rent_income = st.number_input("Gross Monthly Rent##prop1", value=float(prop.monthly_rent_income), format="%.2f", key="form_prop1_rentincome")
            prop.vacancy_rate_pct = st.slider("Vacancy Rate (%)##prop1", 0.0, 50.0, float(prop.vacancy_rate_pct * 100), 1.0, key="form_prop1_vacancy") / 100
            prop.management_fee_pct_rent = st.slider("Management Fee (% Rent)##prop1", 0.0, 20.0, float(prop.management_fee_pct_rent * 100), 0.5, key="form_prop1_mgmtfee") / 100

    with st.expander("💸 Major Expense 1", expanded=False):
        maj_exp = cs_editor.major_expenses[0]
        maj_exp.name = st.text_input("Description##maj_exp1", value=maj_exp.name, key="form_majexp1_name")
        maj_exp.amount = st.number_input("Amount (today's value)##maj_exp1", value=float(maj_exp.amount), format="%.2f", key="form_majexp1_amt")
        maj_exp.year_of_expense = st.number_input("Year of Expense##maj_exp1", value=maj_exp.year_of_expense, min_value=1, step=1, key="form_majexp1_year")

    # Form submit button
    submitted_form = st.form_submit_button("🚀 Run Scenario Projection", type="primary")

# --- End of st.form ---

if submitted_form:
    # At this point, cs_editor (st.session_state.current_scenario_editor)
    # has been updated by all the widgets inside the form.
    
    # Create a final config object for the run, applying the expense adjustment
    config_to_run_dict = cs_editor.model_dump() # Get a dict from the editor's state
    
    # Apply the expense adjustment from the form's slider value
    # base_annual_living_expenses_form_val was the value in the number_input at submission
    # expense_adjustment_pct_form_val was the value in the slider at submission
    adjusted_base_living_expenses = base_annual_living_expenses_form_val * (1 + expense_adjustment_pct_form_val / 100)
    config_to_run_dict['base_annual_living_expenses'] = adjusted_base_living_expenses
    
    try:
        config_to_run = ScenarioConfig.model_validate(config_to_run_dict) # Create validated Pydantic model
    except Exception as e_val:
        st.error(f"Input Validation Error when preparing scenario for run: {e_val}")
        st.stop()

    with st.spinner("Calculating..."):
        run_config_with_results = run_scenario(config_to_run)
        st.session_state.last_run_scenario_name = run_config_with_results.name
        st.session_state.scenario_archive[run_config_with_results.name] = run_config_with_results
    st.success("Scenario projection complete!")

# --- Display Results (for the last run scenario) ---
if st.session_state.last_run_scenario_name and \
   st.session_state.last_run_scenario_name in st.session_state.scenario_archive:
    
    st.header(f"Results for: {st.session_state.last_run_scenario_name}")
    
    results_config = st.session_state.scenario_archive[st.session_state.last_run_scenario_name]
    results_df = results_config.get_results_timeseries_df() 
    current_display_currency = results_config.scenario_base_currency

    if results_config.summary_metrics:
        st.subheader("Summary")
        summary = results_config.summary_metrics
        cols_summary = st.columns(3)
        cols_summary[0].metric("Horizon (Years)", f"{summary.get('Horizon_Years', 'N/A')}")
        cols_summary[1].metric(f"Ending Net Worth (Nominal {current_display_currency})", 
                               f"{summary.get('Ending_Net_Worth_Nominal', 0):,.0f}")
        cols_summary[2].metric(f"Ending Net Worth (Real {current_display_currency})", 
                               f"{summary.get('Ending_Net_Worth_Real', 0):,.0f}")

    if results_df is not None and not results_df.empty:
        st.subheader("Projected Net Worth Over Time")
        # Radio button for Nominal vs Real
        nw_display_options = ("Nominal Value", f"Real Value (Today's {current_display_currency})")
        # Ensure index is valid for radio button based on a persistent state or default
        if 'nw_display_type_index' not in st.session_state: st.session_state.nw_display_type_index = 0
        
        selected_nw_display = st.radio(
            "Display Net Worth As:", nw_display_options, 
            index=st.session_state.nw_display_type_index, 
            key="nw_radio_select"
        )
        st.session_state.nw_display_type_index = nw_display_options.index(selected_nw_display)


        if selected_nw_display == nw_display_options[0]: # Nominal
            if 'Net_Worth_Nominal' in results_df.columns:
                st.line_chart(results_df.set_index('Year')['Net_Worth_Nominal'])
            else: st.warning("Nominal Net Worth data missing.")
        else: # Real
            if 'Net_Worth_Real' in results_df.columns:
                st.line_chart(results_df.set_index('Year')['Net_Worth_Real'])
            else: st.warning("Real Net Worth data missing.")

        if st.checkbox("Show Nominal & Real Net Worth Together?", value=False, key="nw_both_cb_results"):
            if 'Net_Worth_Nominal' in results_df.columns and 'Net_Worth_Real' in results_df.columns:
                st.line_chart(results_df.set_index('Year')[['Net_Worth_Nominal', 'Net_Worth_Real']])

        st.subheader("Projected Asset Breakdown (Nominal)")
        asset_cols_nominal = ['Assets_Cash_Nominal', 'Assets_Stocks_Nominal', 'Assets_RealEstate_Equity_Nominal']
        
        if all(col in results_df.columns for col in asset_cols_nominal) and 'Year' in results_df.columns:
            df_for_area_chart = results_df.set_index('Year')[asset_cols_nominal].copy()
            for col in asset_cols_nominal: 
                df_for_area_chart[col] = pd.to_numeric(df_for_area_chart[col], errors='coerce').fillna(0)
            st.area_chart(df_for_area_chart)
        else:
            missing_asset_cols = [col for col in asset_cols_nominal if col not in results_df.columns]
            st.warning(f"Asset breakdown columns missing for plotting: {missing_asset_cols}")
        
        with st.expander("View Detailed Results Table for Last Run"):
            # Select numeric columns for formatting, excluding 'Year' if it's float/int by mistake
            numeric_cols_to_format = [
                col for col in results_df.select_dtypes(include=np.number).columns 
                if col.lower() != 'year' # Exclude 'Year' from general numeric formatting if it's just an int
            ]
            format_dict = {col: "{:,.0f}" for col in numeric_cols_to_format}
            if 'Year' in results_df.columns and pd.api.types.is_numeric_dtype(results_df['Year']):
                 format_dict['Year'] = "{:.0f}" # Format Year if it's numeric (e.g. int)

            st.dataframe(results_df.style.format(format_dict, na_rep="-"))
    else:
        st.info(f"No detailed results to display. Run the scenario.")
else:
    st.info("Define and run a scenario using the form. Previously run scenarios can be compared below.")

# --- Scenario Comparison Section (at the bottom of the main page or new page) ---
st.markdown("---")
st.header("⚖️ Compare Scenarios")


if st.session_state.scenario_archive:
    scenario_names_in_archive = list(st.session_state.scenario_archive.keys())
    
    selected_for_comparison = st.multiselect( 
        "Select scenarios to compare (from run/archived):",
        options=scenario_names_in_archive,
        default=st.session_state.scenarios_to_compare, 
        key="compare_multi_select"
    )
    if selected_for_comparison != st.session_state.scenarios_to_compare:
        st.session_state.scenarios_to_compare = selected_for_comparison
        st.experimental_rerun()


    if len(st.session_state.scenarios_to_compare) >= 1:
        comparison_data_nominal = []
        comparison_data_real = []
        summary_comparison_list = []

        for scenario_name in st.session_state.scenarios_to_compare:
            archived_sc_config = st.session_state.scenario_archive.get(scenario_name) # Get the Pydantic object
            
            if archived_sc_config: # Make sure we found the scenario config
                results_df_compare = archived_sc_config.get_results_timeseries_df() # Use the correct method
                
                if results_df_compare is not None and not results_df_compare.empty:
                    # For Net Worth line chart (Nominal)
                    if 'Year' in results_df_compare.columns and 'Net_Worth_Nominal' in results_df_compare.columns:
                        df_nom = results_df_compare[['Year', 'Net_Worth_Nominal']].copy()
                        df_nom.rename(columns={'Net_Worth_Nominal': scenario_name}, inplace=True)
                        comparison_data_nominal.append(df_nom.set_index('Year'))
                    
                    # For Net Worth line chart (Real)
                    if 'Year' in results_df_compare.columns and 'Net_Worth_Real' in results_df_compare.columns:
                        df_real = results_df_compare[['Year', 'Net_Worth_Real']].copy()
                        df_real.rename(columns={'Net_Worth_Real': scenario_name}, inplace=True)
                        comparison_data_real.append(df_real.set_index('Year'))
                    
                    # For summary table
                    if archived_sc_config.summary_metrics:
                        # Add scenario name to summary metrics if it's not already a key (like 'Scenario_Name')
                        # This is good practice if summary_metrics dict itself doesn't contain the name
                        metrics_to_add = archived_sc_config.summary_metrics.copy()
                        if 'Scenario_Name' not in metrics_to_add : # Ensure Scenario_Name is present for DataFrame index
                            metrics_to_add['Scenario_Name'] = scenario_name
                        summary_comparison_list.append(metrics_to_add)
                else:
                    st.warning(f"No results data found within the archived scenario: '{scenario_name}'")
            else:
                st.warning(f"Could not find archived scenario: '{scenario_name}'")


        if comparison_data_nominal:
            st.subheader("Comparison: Net Worth Over Time (Nominal)")
            # Concatenate DataFrames: ensure they have the same index ('Year')
            # If a scenario is shorter than others, concat will fill with NaN, which is fine for plotting
            final_nominal_df = pd.concat(comparison_data_nominal, axis=1) 
            st.line_chart(final_nominal_df)
        
        if comparison_data_real:
            st.subheader("Comparison: Net Worth Over Time (Real - Today's Value)")
            final_real_df = pd.concat(comparison_data_real, axis=1)
            st.line_chart(final_real_df)

        if summary_comparison_list:
            st.subheader("Comparison: Summary Metrics")
            # Check if 'Scenario_Name' exists before setting as index
            if all('Scenario_Name' in item for item in summary_comparison_list):
                summary_df_compare = pd.DataFrame(summary_comparison_list).set_index('Scenario_Name')
                # Select only numeric columns for formatting, or format specific ones
                numeric_cols_summary = summary_df_compare.select_dtypes(include=np.number).columns
                st.dataframe(summary_df_compare.style.format("{:,.0f}", subset=numeric_cols_summary))
            else:
                st.dataframe(pd.DataFrame(summary_comparison_list)) # Display without index if name missing
            
    else:
        st.info("Select at least one scenario from the archive to compare.")
else:
    st.info("No scenarios have been run and archived in this session yet. Run a scenario to enable comparison.")