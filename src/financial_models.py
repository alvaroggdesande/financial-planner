# src/financial_models.py
import pandas as pd
import numpy as np # For numpy financial functions if needed, or general math

# --- Investment Growth ---
def calculate_compound_growth(principal: float, 
                              annual_rate: float, 
                              years: int, 
                              annual_contribution: float = 0, 
                              contribution_timing: str = 'end', # 'end' or 'start' of year
                              compounding_periods_per_year: int = 1) -> float:
    """
    Calculates the future value of an investment with optional annual contributions.
    """
    if compounding_periods_per_year <= 0:
        raise ValueError("Compounding periods per year must be positive.")
    
    rate_per_period = annual_rate / compounding_periods_per_year
    n_periods = years * compounding_periods_per_year
    
    # Future value of initial principal
    fv_principal = principal * (1 + rate_per_period)**n_periods
    
    fv_contributions = 0
    if annual_contribution != 0:
        # For simplicity, treat annual contributions as compounded annually at the end of the period
        # More precise would be to compound them based on compounding_periods_per_year
        # This is a common simplification for annual contributions.
        if contribution_timing == 'end':
            # FV of an ordinary annuity
            if annual_rate == 0: # Avoid division by zero if rate is 0
                fv_contributions = annual_contribution * years
            else:
                fv_contributions = annual_contribution * (((1 + annual_rate)**years - 1) / annual_rate)
        elif contribution_timing == 'start':
            # FV of an annuity due
            if annual_rate == 0:
                fv_contributions = annual_contribution * years
            else:
                fv_contributions = annual_contribution * (((1 + annual_rate)**years - 1) / annual_rate) * (1 + annual_rate)
        else:
            raise ValueError("contribution_timing must be 'start' or 'end'")

    return fv_principal + fv_contributions

def project_investment_value_over_time(principal: float,
                                       annual_rate: float,
                                       years_horizon: int,
                                       annual_contribution: float = 0,
                                       contribution_timing: str = 'end') -> pd.DataFrame:
    """
    Projects investment value year by year.
    Returns a DataFrame with columns ['Year', 'Start_Balance', 'Contribution', 'Growth', 'End_Balance'].
    """
    yearly_data = []
    current_balance = principal

    for year in range(1, years_horizon + 1):
        start_balance_year = current_balance
        contribution_this_year = 0
        
        if contribution_timing == 'start':
            current_balance += annual_contribution
            contribution_this_year = annual_contribution
        
        growth_this_year = current_balance * annual_rate
        current_balance += growth_this_year
        
        if contribution_timing == 'end':
            current_balance += annual_contribution
            contribution_this_year = annual_contribution
            
        yearly_data.append({
            'Year': year,
            'Start_Balance': start_balance_year,
            'Contribution': contribution_this_year,
            'Growth_Amount': growth_this_year,
            'End_Balance': current_balance
        })
        
    return pd.DataFrame(yearly_data)


# --- Loan / Mortgage Calculations ---
def calculate_loan_payment(principal: float, 
                           annual_interest_rate: float, 
                           loan_term_years: int, 
                           payments_per_year: int = 12) -> float:
    """Calculates the fixed periodic payment for a loan (e.g., mortgage)."""
    if annual_interest_rate == 0: # Handle zero interest rate
        return principal / (loan_term_years * payments_per_year)
        
    rate_per_period = annual_interest_rate / payments_per_year
    num_payments = loan_term_years * payments_per_year
    
    if rate_per_period == 0: # Should be caught by annual_interest_rate == 0, but good for safety
         return principal / num_payments

    payment = principal * (rate_per_period * (1 + rate_per_period)**num_payments) / \
              ((1 + rate_per_period)**num_payments - 1)
    return payment

def generate_amortization_schedule(principal: float, 
                                   annual_interest_rate: float, 
                                   loan_term_years: int, 
                                   payments_per_year: int = 12,
                                   start_date: pd.Timestamp = None) -> pd.DataFrame:
    """
    Generates an amortization schedule for a loan.
    Returns a DataFrame with details for each payment period.
    """
    payment = calculate_loan_payment(principal, annual_interest_rate, loan_term_years, payments_per_year)
    rate_per_period = annual_interest_rate / payments_per_year
    num_payments = loan_term_years * payments_per_year
    
    schedule = []
    remaining_balance = principal
    
    if start_date is None:
        start_date = pd.Timestamp.now() # Default to today if no start date

    current_date = start_date

    for i in range(1, int(num_payments) + 1): # Ensure num_payments is int
        interest_paid = remaining_balance * rate_per_period
        principal_paid = payment - interest_paid
        remaining_balance -= principal_paid
        
        # Ensure remaining_balance doesn't go slightly negative due to float precision
        if remaining_balance < 0.01 and remaining_balance > -0.01 : remaining_balance = 0 

        schedule.append({
            'Payment_Period': i,
            'Payment_Date': current_date,
            'Payment': payment,
            'Principal_Paid': principal_paid,
            'Interest_Paid': interest_paid,
            'Remaining_Balance': remaining_balance
        })
        # Increment date by roughly a month (can be improved for exact month ends)
        current_date = current_date + pd.DateOffset(months=1) 
        
    return pd.DataFrame(schedule)


# --- Asset & Value Projections ---
def project_asset_value(initial_value: float, annual_growth_rate: float, years: int) -> float:
    """Calculates the future value of an asset based on an annual growth rate."""
    return initial_value * (1 + annual_growth_rate)**years

def project_asset_value_over_time(initial_value: float, 
                                  annual_growth_rate: float, 
                                  years_horizon: int) -> pd.DataFrame:
    """Projects asset value year by year."""
    yearly_data = []
    current_value = initial_value
    for year in range(1, years_horizon + 1):
        current_value = current_value * (1 + annual_growth_rate)
        yearly_data.append({'Year': year, 'Value': current_value})
    return pd.DataFrame(yearly_data)


# --- Inflation ---
def apply_inflation(value: float, annual_inflation_rate: float, years: int) -> float:
    """Calculates the future cost of a current value due to inflation."""
    return value * (1 + annual_inflation_rate)**years

def adjust_for_inflation_to_present_value(future_value: float, annual_inflation_rate: float, years: int) -> float:
    """Calculates the present value of a future amount, adjusted for inflation."""
    return future_value / (1 + annual_inflation_rate)**years


# --- Taxes (Very Simplified Examples - EXPAND AS NEEDED) ---
def calculate_simple_capital_gains_tax(gains: float, tax_rate: float) -> float:
    """Calculates tax on capital gains at a flat rate."""
    return gains * tax_rate if gains > 0 else 0

# --- Rental Property Model (Placeholder - This will be complex) ---
# This would likely call many of the above functions.
# For now, just a conceptual placeholder.
def project_simple_rental_cashflow_annually(
    property_value: float, 
    # ... many more parameters ...
    years_horizon: int
) -> pd.DataFrame:
    """
    Placeholder for a simplified annual rental cashflow projection.
    Output: DataFrame with ['Year', 'Gross_Rent', 'Operating_Expenses', 'Mortgage_Payment_Annual', 'Net_Cashflow']
    """
    # This would involve:
    # 1. Calculating mortgage payments (annualized).
    # 2. Projecting rental income (with vacancy and growth).
    # 3. Projecting operating expenses (with inflation).
    # 4. Calculating net cash flow.
    # 5. Projecting property value appreciation.
    # 6. Calculating loan paydown and equity buildup.
    print("Rental cashflow model placeholder - to be implemented.")
    # Dummy DataFrame for structure
    return pd.DataFrame({'Year': range(1, years_horizon + 1), 'Net_Cashflow_Annual': [1000*i for i in range(1, years_horizon + 1)]})


if __name__ == '__main__':
    # Test functions
    print("--- Compound Growth ---")
    fv = calculate_compound_growth(principal=10000, annual_rate=0.05, years=10, annual_contribution=1200)
    print(f"Future Value (with contributions): {fv:.2f}")
    
    fv_series = project_investment_value_over_time(principal=10000, annual_rate=0.05, years_horizon=5, annual_contribution=1200)
    print("Investment Growth Over Time:\n", fv_series)

    print("\n--- Loan Payment ---")
    mp = calculate_loan_payment(principal=200000, annual_interest_rate=0.035, loan_term_years=20)
    print(f"Monthly Mortgage Payment: {mp:.2f}")

    print("\n--- Amortization Schedule ---")
    amort_schedule = generate_amortization_schedule(principal=50000, annual_interest_rate=0.04, loan_term_years=5, start_date=pd.Timestamp('2024-01-01'))
    print(amort_schedule.head())
    print("Total Interest Paid:", amort_schedule['Interest_Paid'].sum())

    print("\n--- Asset Value Projection ---")
    future_asset_val = project_asset_value(initial_value=300000, annual_growth_rate=0.03, years=10)
    print(f"Future Asset Value: {future_asset_val:.2f}")
    
    print("\n--- Inflation ---")
    future_cost = apply_inflation(value=100, annual_inflation_rate=0.02, years=10)
    print(f"100 today will cost {future_cost:.2f} in 10 years at 2% inflation.")