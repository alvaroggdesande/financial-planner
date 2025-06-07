# src/scenario_runner.py
"""import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))"""

import pandas as pd
from src.financial_models import (
    calculate_compound_growth, project_investment_value_over_time,
    calculate_loan_payment, generate_amortization_schedule,
    project_asset_value, project_asset_value_over_time,
    apply_inflation, adjust_for_inflation_to_present_value
    # Import others as needed
)
from src.scenario_config import (ScenarioConfig
                                 ,CashHoldingParams
                                 ,StockInvestmentParams
                                 ,RealEstateParams
                                 ,IncomeSourceParams
                                 ,MajorExpenseParams) # Import the dataclass structure

def run_scenario(config: ScenarioConfig) -> ScenarioConfig:
    """
    Runs the financial projection for a given scenario configuration.
    Populates config.results_timeseries and config.summary_metrics.
    """
    horizon = config.horizon_years
    inflation_rate = config.general_annual_inflation_rate
    
    # Initialize yearly data storage
    yearly_results = []
    
    # --- Initialize Starting State for Assets and Liabilities ---
    # This needs careful thought: how do initial components contribute to starting net worth?
    # For simplicity, let's assume we track component values separately and sum them up.
    
    # Create detailed projections for each component over the horizon
    # These will be DataFrames showing year-by-year values for each asset/liability
    
    # Cash Projections
    all_cash_projections = {} # Dict to store df for each cash holding
    for cash_item in config.cash_holdings:
        # Simple model: cash grows by its own interest, or is just a static pool
        # For dynamic cash flow, this needs to be integrated into the main loop
        # For now, let's assume it's an account that just sits there or has its own growth
        cash_df = project_investment_value_over_time(
            principal=cash_item.initial_amount,
            annual_rate=cash_item.annual_interest_rate,
            years_horizon=horizon
        )
        all_cash_projections[cash_item.name] = cash_df.set_index('Year')['End_Balance']

    # Stock Investment Projections
    all_stock_projections = {}
    for stock_item in config.stock_investments:
        stock_df = project_investment_value_over_time(
            principal=stock_item.initial_investment,
            annual_rate=stock_item.expected_annual_return,
            years_horizon=horizon,
            annual_contribution=stock_item.annual_contribution # Assuming contributions from other sources
        )
        all_stock_projections[stock_item.name] = stock_df.set_index('Year')['End_Balance']

    # Real Estate Projections (more complex)
    all_real_estate_equity = {}
    all_real_estate_debt = {}
    all_real_estate_cashflow_annual = {} # From rentals or saved rent
    all_real_estate_value = {}

    for prop_item in config.real_estate_investments:
        loan_amount = prop_item.purchase_price * (1 - prop_item.down_payment_pct)
        
        # Property Value Appreciation
        prop_value_df = project_asset_value_over_time(
            initial_value=prop_item.purchase_price,
            annual_growth_rate=prop_item.expected_annual_appreciation,
            years_horizon=horizon
        )
        all_real_estate_value[prop_item.name] = prop_value_df.set_index('Year')['Value']

        # Mortgage Debt
        if loan_amount > 0:
            amort_schedule = generate_amortization_schedule(
                principal=loan_amount,
                annual_interest_rate=prop_item.mortgage_interest_rate_annual,
                loan_term_years=prop_item.mortgage_term_years
            )
            # Get end-of-year remaining balance
            # Need to map payment periods to years
            # For simplicity, let's take remaining balance at year end.
            # This requires a more detailed merge or lookup.
            # Quick approx: assume constant principal reduction over mortgage term for simplicity here,
            # OR use the amort_schedule to find year-end balances
            
            # Correctly get year-end balances from amortization schedule
            debt_series_list = []
            for year_idx in range(1, horizon + 1):
                payments_this_year = min(year_idx * 12, len(amort_schedule)) # Cap at total payments
                if payments_this_year > 0:
                    debt_series_list.append(amort_schedule.loc[payments_this_year - 1, 'Remaining_Balance'])
                else: # Before any payments
                    debt_series_list.append(loan_amount)
            
            # Handle cases where loan is paid off before horizon
            while len(debt_series_list) < horizon:
                debt_series_list.append(0) # Paid off

            all_real_estate_debt[prop_item.name] = pd.Series(debt_series_list, index=range(1, horizon + 1))
        else:
            all_real_estate_debt[prop_item.name] = pd.Series([0]*horizon, index=range(1, horizon + 1))

        # Equity = Value - Debt
        all_real_estate_equity[prop_item.name] = all_real_estate_value[prop_item.name] - all_real_estate_debt[prop_item.name]

        # Cashflow (Simplified)
        annual_cashflow = 0
        if prop_item.is_rental:
            gross_rent_annual = prop_item.monthly_rent_income * 12 * (1 - prop_item.vacancy_rate_pct)
            management_annual = gross_rent_annual * prop_item.management_fee_pct_rent
            taxes_annual = prop_item.purchase_price * prop_item.property_tax_annual_pct_value # Simplified, should use current value
            maintenance_annual = prop_item.purchase_price * prop_item.maintenance_annual_pct_value # Simplified
            
            # Mortgage payment (annualized)
            # Only consider first year's mortgage payment for simplicity here
            # A more accurate model would take the annual mortgage payment from the amortization schedule
            mortgage_payment_annual = 0
            if loan_amount > 0 and not amort_schedule.empty:
                 # Sum of first 12 payments or fewer if loan term is < 1 year
                mortgage_payment_annual = amort_schedule.head(12)['Payment'].sum()


            op_expenses_annual = management_annual + taxes_annual + prop_item.insurance_annual_fixed + maintenance_annual
            annual_cashflow = gross_rent_annual - op_expenses_annual - mortgage_payment_annual
            all_real_estate_cashflow_annual[prop_item.name] = pd.Series([annual_cashflow]*horizon, index=range(1, horizon + 1))

        elif prop_item.is_primary_residence:
            # "Saved" rent could be considered positive cash flow or reduced expenses elsewhere
            annual_cashflow = prop_item.equivalent_monthly_rent_saved * 12
            all_real_estate_cashflow_annual[prop_item.name] = pd.Series([annual_cashflow]*horizon, index=range(1, horizon + 1))
        else:
            all_real_estate_cashflow_annual[prop_item.name] = pd.Series([0]*horizon, index=range(1, horizon + 1))


    # Income Projections
    all_income_projections = {}
    for income_item in config.income_sources:
        income_df = project_asset_value_over_time( # Using this for simplicity to project growth
            initial_value=income_item.initial_annual_income,
            annual_growth_rate=income_item.expected_annual_growth_rate,
            years_horizon=horizon
        )
        all_income_projections[income_item.name] = income_df.set_index('Year')['Value']

    # --- Main Simulation Loop (Year by Year) ---
    # This loop will aggregate values from the pre-calculated component projections.
    # A more sophisticated model would have dynamic cash flow affecting contributions to investments etc.
    # This version is simpler: components evolve somewhat independently, then we sum up.
    
    for year in range(1, horizon + 1):
        # --- Assets ---
        total_cash_year = sum(proj.get(year, 0) for proj_name, proj in all_cash_projections.items())
        total_stocks_year = sum(proj.get(year, 0) for proj_name, proj in all_stock_projections.items())
        total_real_estate_equity_year = sum(proj.get(year, 0) for proj_name, proj in all_real_estate_equity.items())
        
        total_assets_year = total_cash_year + total_stocks_year + total_real_estate_equity_year

        # --- Liabilities ---
        total_real_estate_debt_year = sum(proj.get(year, 0) for proj_name, proj in all_real_estate_debt.items())
        # Add other debts if modeled (e.g., student loans, car loans)
        total_liabilities_year = total_real_estate_debt_year
        
        net_worth_year = total_assets_year - total_liabilities_year
        
        # --- Cash Flow Elements for this year (Simplified) ---
        total_income_from_sources_year = sum(proj.get(year, 0) for proj_name, proj in all_income_projections.items())
        total_real_estate_cf_year = sum(proj.get(year, 0) for proj_name, proj in all_real_estate_cashflow_annual.items())
        
        # Major Expenses for this year
        current_year_major_expenses = 0
        for expense_item in config.major_expenses:
            if expense_item.year_of_expense == year:
                current_year_major_expenses += apply_inflation(expense_item.amount, inflation_rate, year) # Inflate future expense
            # Add logic for recurring major expenses if needed

        # Living expenses (This is a big assumption or needs detailed input)
        # For now, let's assume a fixed (inflated) living expense not covered by specific models
        # This should ideally come from Phase 1 analysis or be an input.
        """annual_living_expenses_base = config.base_annual_living_expenses # Example base
        annual_living_expenses_inflated = apply_inflation(annual_living_expenses_base, inflation_rate, year)"""

        annual_living_expenses_base = config.base_annual_living_expenses if config.base_annual_living_expenses is not None else 30000.0 # Fallback
        annual_living_expenses_inflated = apply_inflation(annual_living_expenses_base, inflation_rate, year)
        
        # Net Cash Flow for the year (approximation)
        # Income + RE_Cashflow - LivingExpenses - MajorExpenses_this_year
        # Note: Investment contributions are handled within their projections.
        # Mortgage payments are implicitly handled in RE_Cashflow or RE_Debt reduction.
        net_cash_flow_year = total_income_from_sources_year + total_real_estate_cf_year \
                             - annual_living_expenses_inflated - current_year_major_expenses
        

        # Calculate real values by discounting nominal values back to present day (Year 0)
        real_net_worth_year = adjust_for_inflation_to_present_value(
            net_worth_year, # This is the nominal net worth for the current 'year'
            config.general_annual_inflation_rate,
            year # Number of years from the start of the scenario
        )
        real_total_assets_year = adjust_for_inflation_to_present_value(
            total_assets_year, config.general_annual_inflation_rate, year
        )
        # ... (similarly for other key financial figures you want in real terms)
        real_income_year = adjust_for_inflation_to_present_value(
            total_income_from_sources_year, config.general_annual_inflation_rate, year
        )
        real_living_expenses_year = adjust_for_inflation_to_present_value(
            annual_living_expenses_inflated, config.general_annual_inflation_rate, year
        )

        yearly_results.append({
            'Year': year,
            'Net_Worth_Nominal': net_worth_year,
            'Net_Worth_Real': real_net_worth_year,
            'Total_Assets_Nominal': total_assets_year,
            'Total_Assets_Real': real_total_assets_year,
            'Assets_Cash_Nominal': total_cash_year, # Assuming this is already nominal for the year
            'Assets_Stocks_Nominal': total_stocks_year,
            'Assets_RealEstate_Equity_Nominal': total_real_estate_equity_year,
            'Total_Liabilities_Nominal': total_liabilities_year, # Liabilities are usually nominal
            'Income_Sources_Total_Nominal': total_income_from_sources_year,
            'Income_Sources_Total_Real': real_income_year,
            'RealEstate_Net_Cashflow_Nominal': total_real_estate_cf_year,
            'Annual_Living_Expenses_Nominal': annual_living_expenses_inflated,
            'Annual_Living_Expenses_Real': real_living_expenses_year,
            'Major_Expenses_Scheduled_Nominal': current_year_major_expenses, # This was already inflated
            'Net_Annual_Cash_Flow_Est_Nominal': net_cash_flow_year
            # Add real cash flow if needed
        })
        
    #config.results_timeseries = pd.DataFrame(yearly_results)

    # Use your setter method:
    results_df = pd.DataFrame(yearly_results)
    config.set_results_timeseries(results_df) # This will store it correctly as results_timeseries_data
    
    # --- Summary Metrics ---
    if not results_df.empty: # Check the DataFrame before accessing .iloc
        final_net_worth_nominal = results_df['Net_Worth_Nominal'].iloc[-1]
        final_net_worth_real = results_df['Net_Worth_Real'].iloc[-1]
        config.summary_metrics = {
            'Scenario_Name': config.name,
            'Ending_Net_Worth_Nominal': final_net_worth_nominal,
            'Ending_Net_Worth_Real': final_net_worth_real,
            'Horizon_Years': config.horizon_years
            # Add more...
        }
    else:
        config.summary_metrics = { # Default summary if no results
            'Scenario_Name': config.name,
            'Ending_Net_Worth_Nominal': 0,
            'Ending_Net_Worth_Real': 0,
            'Horizon_Years': config.horizon_years
        }
        
    return config
    
    """# --- Summary Metrics ---
    # Example summary metrics
    if not config.results_timeseries.empty:
        final_net_worth_nominal = config.results_timeseries['Net_Worth_Nominal'].iloc[-1]
        final_net_worth_real = config.results_timeseries['Net_Worth_Real'].iloc[-1]
        config.summary_metrics = {
            'Scenario_Name': config.name,
            'Ending_Net_Worth_Nominal': final_net_worth_nominal,
            'Ending_Net_Worth_Real': final_net_worth_real,
            'Horizon_Years': config.horizon_years
            # Add more...
        }
        
    return config # Return the config object now populated with results"""


if __name__ == '__main__':
    # --- Test Scenario ---
    test_config = ScenarioConfig(
        name="Test Investment Scenario",
        horizon_years=10,
        general_annual_inflation_rate=0.02,
        initial_cash_on_hand=20000 # Part of a cash holding
    )
    
    test_config.cash_holdings.append(
        CashHoldingParams(initial_amount=20000, annual_interest_rate=0.005)
    )
    test_config.stock_investments.append(
        StockInvestmentParams(
            initial_investment=50000, 
            annual_contribution=5000, 
            expected_annual_return=0.06
        )
    )
    test_config.income_sources.append(
        IncomeSourceParams(initial_annual_income=70000, expected_annual_growth_rate=0.03)
    )
    # test_config.major_expenses.append(
    #     MajorExpenseParams(name="Car Purchase", year_of_expense=5, amount=25000)
    # )

    # Real Estate Example (Optional for initial test)
    # test_config.real_estate_investments.append(
    #     RealEstateParams(
    #         name="Rental Property A",
    #         purchase_price=300000,
    #         down_payment_pct=0.25,
    #         mortgage_term_years=25,
    #         mortgage_interest_rate_annual=0.04,
    #         expected_annual_appreciation=0.025,
    #         is_rental=True,
    #         monthly_rent_income=1500,
    #         vacancy_rate_pct=0.05,
    #         management_fee_pct_rent=0.08,
    #         property_tax_annual_pct_value=0.006,
    #         insurance_annual_fixed=600,
    #         maintenance_annual_pct_value=0.01
    #     )
    # )

    
    result_config = run_scenario(test_config)
    
    if result_config.results_timeseries is not None:
        print(f"\n--- Results for Scenario: {result_config.name} ---")
        print(result_config.results_timeseries)
    if result_config.summary_metrics is not None:
        print("\n--- Summary Metrics ---")
        for k, v in result_config.summary_metrics.items():
            print(f"{k}: {v}")