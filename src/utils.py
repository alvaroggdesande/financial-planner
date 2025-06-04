# src/utils.py (or a new src/currency_converter.py)
import pandas as pd

# Placeholder: In a real app, fetch this dynamically or use a library
# For simplicity, using a fixed rate. Update this or fetch from an API.
DKK_TO_EUR_RATE = 1 / 7.46 # Example: 1 EUR = 7.46 DKK

def convert_currency_in_df(df, amount_col='Amount', balance_col='Balance', target_currency='EUR', rate_dkk_eur=DKK_TO_EUR_RATE):
    """
    Converts 'Amount' and 'Balance' columns from DKK to target_currency (EUR by default).
    Assumes original currency is DKK if not specified otherwise.
    """
    df_converted = df.copy()
    if amount_col in df_converted.columns:
        # Ensure amount_col is numeric
        df_converted[amount_col] = pd.to_numeric(df_converted[amount_col], errors='coerce')
        df_converted[amount_col] = df_converted[amount_col] * rate_dkk_eur
    if balance_col in df_converted.columns and balance_col != amount_col: # Avoid double conversion if same col
        df_converted[balance_col] = pd.to_numeric(df_converted[balance_col], errors='coerce')
        df_converted[balance_col] = df_converted[balance_col] * rate_dkk_eur
    
    # Update currency column if it exists
    if 'Currency' in df_converted.columns:
        df_converted['Currency'] = target_currency
        
    return df_converted