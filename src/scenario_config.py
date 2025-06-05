# src/scenario_config.py
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# --- Component Parameter Structures ---
@dataclass
class CashHoldingParams:
    name: str = "Cash Savings"
    initial_amount: float = 0.0
    annual_interest_rate: float = 0.001 # Default low interest

@dataclass
class StockInvestmentParams:
    name: str = "Stock Portfolio"
    initial_investment: float = 0.0
    annual_contribution: float = 0.0
    expected_annual_return: float = 0.07 # e.g., 7%
    # For Monte Carlo later:
    # volatility_std_dev: float = 0.15
    # dividend_yield: float = 0.015

@dataclass
class RealEstateParams:
    name: str = "Property Investment"
    is_primary_residence: bool = False # If true, "saves" rent
    purchase_price: float = 0.0
    down_payment_pct: float = 0.20
    
    mortgage_term_years: int = 20
    mortgage_interest_rate_annual: float = 0.035
    
    property_tax_annual_pct_value: float = 0.005 # 0.5% of property value
    insurance_annual_fixed: float = 500.0
    maintenance_annual_pct_value: float = 0.01 # 1% of property value
    
    expected_annual_appreciation: float = 0.03 # 3% property value growth
    
    # For Rentals
    is_rental: bool = False
    monthly_rent_income: float = 0.0
    vacancy_rate_pct: float = 0.05 # 5%
    management_fee_pct_rent: float = 0.08 # 8%
    
    # For Primary (if is_primary_residence is True)
    equivalent_monthly_rent_saved: float = 0.0

    # Selling params (for calculating net proceeds at end of horizon if sold)
    selling_costs_pct: float = 0.06 # e.g., 6% agent, taxes, etc.

@dataclass
class IncomeSourceParams:
    name: str = "Primary Salary"
    initial_annual_income: float = 60000.0
    expected_annual_growth_rate: float = 0.025 # 2.5%

@dataclass
class MajorExpenseParams:
    name: str = "Future Expense"
    year_of_expense: int = 5 # In how many years from start
    amount: float = 10000.0
    is_recurring: bool = False
    recurrence_years: Optional[int] = None # if recurring, e.g., every 4 years for a car

# --- Scenario Configuration Structure ---
@dataclass
class ScenarioConfig:
    name: str = "Default Scenario"
    description: str = "A baseline financial projection."
    horizon_years: int = 30
    
    # Global assumptions for this scenario
    general_annual_inflation_rate: float = 0.02
    
    # Starting financial position (can be pre-filled)
    initial_cash_on_hand: float = 50000.0 # This might be part of a CashHoldingComponent
    # initial_net_worth: float = 100000.0 # Or calculate from initial components

    # Components of the scenario
    cash_holdings: List[CashHoldingParams] = field(default_factory=list)
    stock_investments: List[StockInvestmentParams] = field(default_factory=list)
    real_estate_investments: List[RealEstateParams] = field(default_factory=list)
    income_sources: List[IncomeSourceParams] = field(default_factory=list)
    major_expenses: List[MajorExpenseParams] = field(default_factory=list)
    
    # Other scenario-specific flags or settings
    # e.g., tax_strategy: str = "simplified_flat_rate"

    # To store results from the runner
    results_timeseries: Optional[pd.DataFrame] = None # Will hold year-by-year data
    summary_metrics: Optional[Dict[str, Any]] = None # Key outcome numbers