# src/scenario_config_pydantic.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import pandas as pd # For storing/retrieving DataFrame results

# --- Component Parameter Structures (using Pydantic BaseModel) ---
class CashHoldingParams(BaseModel):
    name: str = "Cash Savings"
    initial_amount: float = 0.0
    annual_interest_rate: float = 0.001

class StockInvestmentParams(BaseModel):
    name: str = "Stock Portfolio"
    initial_investment: float = 0.0
    annual_contribution: float = 0.0
    expected_annual_return: float = 0.07
    # For Monte Carlo later (optional fields)
    # volatility_std_dev: Optional[float] = 0.15
    # dividend_yield: Optional[float] = 0.015

class RealEstateParams(BaseModel):
    name: str = "Property Investment"
    is_primary_residence: bool = False
    purchase_price: float = 0.0
    down_payment_pct: float = Field(default=0.20, ge=0.0, le=1.0) # Percentage (0.0 to 1.0)
    
    mortgage_term_years: int = Field(default=20, gt=0)
    mortgage_interest_rate_annual: float = Field(default=0.035, ge=0.0)
    
    property_tax_annual_pct_value: float = Field(default=0.005, ge=0.0)
    insurance_annual_fixed: float = 500.0
    maintenance_annual_pct_value: float = Field(default=0.01, ge=0.0)
    
    expected_annual_appreciation: float = Field(default=0.03, ge=-1.0) # Can depreciate
    
    is_rental: bool = False
    monthly_rent_income: float = 0.0
    vacancy_rate_pct: float = Field(default=0.05, ge=0.0, le=1.0)
    management_fee_pct_rent: float = Field(default=0.08, ge=0.0, le=1.0)
    
    equivalent_monthly_rent_saved: float = 0.0
    selling_costs_pct: float = Field(default=0.06, ge=0.0, le=1.0)

class IncomeSourceParams(BaseModel):
    name: str = "Primary Salary"
    initial_annual_income: float = 60000.0
    expected_annual_growth_rate: float = 0.025

class MajorExpenseParams(BaseModel):
    name: str = "Future Expense"
    year_of_expense: int = Field(default=5, gt=0)
    amount: float = 10000.0 # In today's currency, will be inflated by runner
    # is_recurring: bool = False # Add later if needed
    # recurrence_years: Optional[int] = None

# --- Main Scenario Configuration Structure (using Pydantic BaseModel) ---
class ScenarioConfig(BaseModel):
    name: str = "Default Scenario"
    description: str = "A baseline financial projection."
    horizon_years: int = Field(default=30, gt=0)
    scenario_base_currency: str = "DKK" # Added for currency consistency
    
    general_annual_inflation_rate: float = Field(default=0.02, ge=0.0)
    
    initial_cash_on_hand: float = 50000.0 # Used to initialize a default cash holding
    base_annual_living_expenses: Optional[float] = 30000.0 # Base year expenses
    
    cash_holdings: List[CashHoldingParams] = Field(default_factory=list)
    stock_investments: List[StockInvestmentParams] = Field(default_factory=list)
    real_estate_investments: List[RealEstateParams] = Field(default_factory=list)
    income_sources: List[IncomeSourceParams] = Field(default_factory=list)
    major_expenses: List[MajorExpenseParams] = Field(default_factory=list)
    
    # Results storage (Pydantic can't directly serialize DataFrames to JSON by default)
    # We'll store the DataFrame data as a list of dictionaries
    results_timeseries_data: Optional[List[Dict[str, Any]]] = None 
    summary_metrics: Optional[Dict[str, Any]] = None

    # Custom methods to handle DataFrame results for serialization/deserialization
    def set_results_timeseries(self, df: pd.DataFrame):
        """Converts DataFrame to list of dicts for storage."""
        if df is not None and not df.empty:
            df_copy = df.copy()
            for col in df_copy.select_dtypes(include=['datetime64[ns]', 'datetime64[ns, UTC]']).columns:
                # Ensure Timestamps are converted to ISO strings for JSON
                # Pydantic v2 handles datetime serialization well, but explicit can be safer for generic JSON
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S') # Example ISO format
            self.results_timeseries_data = df_copy.to_dict(orient='records')
        else:
            self.results_timeseries_data = None

    def get_results_timeseries_df(self) -> Optional[pd.DataFrame]:
        """Converts stored list of dicts back to DataFrame."""
        if self.results_timeseries_data:
            df = pd.DataFrame.from_records(self.results_timeseries_data)
            # Attempt to convert known date columns back to datetime
            # Example: if 'Year' column was originally an int, no need to convert.
            # If you stored actual date columns as ISO strings, convert them back:
            # for col in df.columns:
            #     if "date" in col.lower() or "time" in col.lower(): # Heuristic
            #         try:
            #             df[col] = pd.to_datetime(df[col], errors='coerce')
            #         except Exception:
            #             pass # Keep as string if conversion fails
            return df
        return None

    # This is a Pydantic feature: model_config allows global settings for the model
    class Config:
        # arbitrary_types_allowed = True # Use with caution, might be needed if storing complex non-Pydantic types
        validate_assignment = True # Re-validate fields when they are assigned a new value

