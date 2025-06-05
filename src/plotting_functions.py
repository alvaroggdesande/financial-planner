import streamlit as st
import pandas as pd
import numpy as np
# Import plotly.express as px if you decide to use it later

def plot_spending_by_category(df_expenses, currency_suffix):
    """Plots spending by category using st.bar_chart."""
    if df_expenses.empty:
        st.write("No expense data for category plot.")
        return

    # Ensure 'Absolute_Amount' is numeric and NaNs are handled
    df_expenses['Absolute_Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').abs().fillna(0)
    
    cat_spend = (
        df_expenses.groupby('Category')['Absolute_Amount']
        .sum()
        .sort_values(ascending=False)
        .fillna(0)
    )

    if not cat_spend.empty:
        st.subheader(f"Spending by Category ({currency_suffix})")
        cat_spend.index.name = 'Category' # Important for st.bar_chart if using Series index
        st.bar_chart(cat_spend)
    else:
        st.write("No expense data after grouping by category.")


def plot_income_expense_trend(df_for_trend, currency_suffix):
    """Plots monthly income vs. expense trend using st.bar_chart."""
    if df_for_trend.empty:
        st.write("No data for income/expense trend.")
        return

    df_month = df_for_trend.copy()
    df_month['Date'] = pd.to_datetime(df_month['Date'], errors='coerce') # Ensure datetime
    df_month = df_month.dropna(subset=['Date']) # Drop rows if Date became NaT
    if df_month.empty:
        st.write("No valid date data for income/expense trend.")
        return
        
    df_month.set_index('Date', inplace=True)
    df_month['Amount'] = pd.to_numeric(df_month['Amount'], errors='coerce').fillna(0)

    monthly_summary = (
        df_month.resample('ME')['Amount'] # Use ME for Month End
        .agg(
            Income=lambda x: x[x > 0].sum(),
            Expenses=lambda x: x[x < 0].sum()
        )
        .reset_index()
    )
    monthly_summary['Income'] = monthly_summary['Income'].fillna(0)
    monthly_summary['Expenses'] = monthly_summary['Expenses'].fillna(0).abs()

    if not monthly_summary.empty:
        st.subheader(f"Income vs. Expenses Over Time (Monthly, {currency_suffix})")
        monthly_idx = monthly_summary.set_index('Date')[['Income', 'Expenses']]
        st.bar_chart(monthly_idx)
    else:
        st.write("Not enough data to form a monthly income/expense trend.")

def plot_net_savings_trend(df_for_trend, currency_suffix):
    """Plots monthly net savings trend using st.bar_chart."""
    if df_for_trend.empty:
        st.write("No data for net savings trend.")
        return

    df_month = df_for_trend.copy()
    df_month['Date'] = pd.to_datetime(df_month['Date'], errors='coerce')
    df_month = df_month.dropna(subset=['Date'])
    if df_month.empty:
        st.write("No valid date data for net savings trend.")
        return

    df_month.set_index('Date', inplace=True)
    df_month['Amount'] = pd.to_numeric(df_month['Amount'], errors='coerce').fillna(0)
    
    net_month = df_month.resample('ME')['Amount'].sum().reset_index()
    net_month.rename(columns={'Amount': 'Net Savings'}, inplace=True)
    net_month['Net Savings'] = net_month['Net Savings'].fillna(0)

    if not net_month.empty:
        st.subheader(f"Net Savings Over Time (Monthly, {currency_suffix})")
        net_idx = net_month.set_index('Date')['Net Savings']
        st.bar_chart(net_idx)
    else:
        st.write("Not enough data for net savings trend.")


def plot_balance_trend(df_with_balance, currency_suffix):
    """Plots EOM and EOY balance trends using st.line_chart."""
    if 'Balance' not in df_with_balance.columns:
        st.write("No 'Balance' column available to show balance trend.")
        return

    df_bal_trend = df_with_balance.copy()
    df_bal_trend['Date'] = pd.to_datetime(df_bal_trend['Date'], errors='coerce')
    df_bal_trend['Balance'] = pd.to_numeric(df_bal_trend['Balance'], errors='coerce')
    df_bal_trend = df_bal_trend.dropna(subset=['Date', 'Balance'])

    if df_bal_trend.empty:
        st.write("No valid 'Balance' data (after dropping NaNs) to plot trend.")
        return

    st.subheader(f"Account Balance Trend ({currency_suffix})")
    df_bal_trend.set_index('Date', inplace=True)

    # Monthly
    st.markdown("##### End-of-Month Balance")
    monthly_balance_eom = df_bal_trend.resample('ME')['Balance'].last().reset_index()
    if not monthly_balance_eom.empty:
        st.line_chart(monthly_balance_eom.set_index('Date')['Balance'])
    else:
        st.write("No data for end-of-month balance.")

    # Yearly
    st.markdown("##### End-of-Year Balance")
    yearly_balance_eoy = df_bal_trend.resample('YE')['Balance'].last().reset_index()
    if not yearly_balance_eoy.empty:
        st.line_chart(yearly_balance_eoy.set_index('Date')['Balance'])
    else:
        st.write("No data for end-of-year balance.")

# --- Add more plotting functions here as needed ---
def plot_monthly_spending_by_category(df_expenses, currency_suffix):
    """Shows spending for each category, month by month."""
    if df_expenses.empty:
        st.write("No expense data for monthly category plot.")
        return

    st.subheader(f"Monthly Spending by Category ({currency_suffix})")
    
    df_exp_monthly_cat = df_expenses.copy()
    df_exp_monthly_cat['Date'] = pd.to_datetime(df_exp_monthly_cat['Date'], errors='coerce')
    df_exp_monthly_cat = df_exp_monthly_cat.dropna(subset=['Date'])
    if df_exp_monthly_cat.empty:
        st.write("No valid date data for monthly category plot.")
        return

    df_exp_monthly_cat['Month'] = df_exp_monthly_cat['Date'].dt.to_period('M')
    df_exp_monthly_cat['Absolute_Amount'] = pd.to_numeric(df_exp_monthly_cat['Amount'], errors='coerce').abs().fillna(0)

    monthly_category_spend = df_exp_monthly_cat.groupby(['Month', 'Category'])['Absolute_Amount'].sum().unstack(fill_value=0)
    
    if not monthly_category_spend.empty:
        st.dataframe(monthly_category_spend.style.format("{:.2f}")) # Display as a table first
        
        # For plotting, st.bar_chart might get too crowded if many categories.
        # Consider allowing user to select a few categories to compare over time.
        selected_cats_for_trend = st.multiselect(
            "Select categories to see monthly trend:",
            options=monthly_category_spend.columns.tolist(),
            default=monthly_category_spend.columns.tolist()[:3] if len(monthly_category_spend.columns) >=3 else monthly_category_spend.columns.tolist(), # Default to first 3 or all if less
            key="monthly_cat_trend_select"
        )
        if selected_cats_for_trend:
            # Convert PeriodIndex to DatetimeIndex for st.line_chart if needed, or plot directly
            data_to_plot = monthly_category_spend[selected_cats_for_trend].copy()
            # st.line_chart might need datetime index
            if isinstance(data_to_plot.index, pd.PeriodIndex):
                 data_to_plot.index = data_to_plot.index.to_timestamp()
            st.line_chart(data_to_plot)
    else:
        st.write("No data for monthly spending by category.")

def plot_percentage_change_expenses(df_expenses, currency_suffix):
    """Shows MoM % change for top N expense categories."""
    if df_expenses.empty:
        st.write("No expense data for % change plot.")
        return

    st.subheader(f"Month-over-Month % Change in Top Expense Categories ({currency_suffix})")

    df_exp_pct = df_expenses.copy()
    df_exp_pct['Date'] = pd.to_datetime(df_exp_pct['Date'], errors='coerce')
    df_exp_pct = df_exp_pct.dropna(subset=['Date'])
    if df_exp_pct.empty:
        st.write("No valid date data for % change plot.")
        return
        
    df_exp_pct['Month'] = df_exp_pct['Date'].dt.to_period('M')
    df_exp_pct['Absolute_Amount'] = pd.to_numeric(df_exp_pct['Amount'], errors='coerce').abs().fillna(0)

    monthly_category_spend = df_exp_pct.groupby(['Month', 'Category'])['Absolute_Amount'].sum().unstack(fill_value=0)

    if monthly_category_spend.empty or len(monthly_category_spend) < 2:
        st.write("Not enough monthly data (at least 2 months) to calculate percentage change.")
        return

    # Calculate % change
    # fill_value=None ensures that if a category disappears, pct_change doesn't show 0 for it
    # but rather NaN, which we can then handle.
    pct_change_df = monthly_category_spend.pct_change().fillna(0) * 100 
    
    # Select top N categories by total spending to display % change for, to avoid clutter
    top_n = st.slider("Number of top expense categories to show % change for:", 1, 10, 5, key="top_n_pct_change")
    total_spend_per_category = monthly_category_spend.sum().sort_values(ascending=False)
    top_categories = total_spend_per_category.head(top_n).index.tolist()

    if top_categories:
        st.write(f"Displaying MoM % change for: {', '.join(top_categories)}")
        data_to_plot_pct = pct_change_df[top_categories].copy()
        if isinstance(data_to_plot_pct.index, pd.PeriodIndex):
            data_to_plot_pct.index = data_to_plot_pct.index.to_timestamp()
        st.line_chart(data_to_plot_pct)
        
        # Display the table as well
        st.dataframe(pct_change_df[top_categories].style.format("{:.2f}%"))
    else:
        st.write("No categories found to display percentage change.")

def plot_savings_rate_trend(df_for_trend, currency_suffix):
    """Calculates and plots the monthly savings rate."""
    if df_for_trend.empty:
        st.write("No data for savings rate trend.")
        return

    st.subheader(f"Monthly Savings Rate Trend ({currency_suffix})")

    df_month = df_for_trend.copy()
    df_month['Date'] = pd.to_datetime(df_month['Date'], errors='coerce')
    df_month = df_month.dropna(subset=['Date'])
    if df_month.empty:
        st.write("No valid date data for savings rate trend.")
        return
        
    df_month.set_index('Date', inplace=True)
    df_month['Amount'] = pd.to_numeric(df_month['Amount'], errors='coerce').fillna(0)

    monthly_summary = (
        df_month.resample('ME')['Amount']
        .agg(
            Income=lambda x: x[x > 0].sum(),
            Expenses=lambda x: x[x < 0].sum() # Expenses are negative
        )
        .reset_index()
    )
    monthly_summary['Income'] = monthly_summary['Income'].fillna(0)
    monthly_summary['Expenses_Abs'] = monthly_summary['Expenses'].fillna(0).abs() # Absolute expenses
    
    # Calculate Net Savings
    monthly_summary['Net_Savings'] = monthly_summary['Income'] - monthly_summary['Expenses_Abs']
    
    # Calculate Savings Rate: (Net Savings / Income) * 100
    # Handle cases where income is 0 to avoid division by zero
    monthly_summary['Savings_Rate'] = np.where(
        monthly_summary['Income'] > 0, # Condition: Income must be positive
        (monthly_summary['Net_Savings'] / monthly_summary['Income']) * 100,
        0 # Value if income is 0 or negative (or np.nan if you prefer)
    )
    # Fill any resulting NaNs in Savings_Rate (e.g., if Income was NaN initially)
    monthly_summary['Savings_Rate'] = monthly_summary['Savings_Rate'].fillna(0)


    if not monthly_summary.empty:
        # For st.line_chart, index should be Date
        savings_rate_to_plot = monthly_summary.set_index('Date')['Savings_Rate']
        st.line_chart(savings_rate_to_plot)
        st.caption("Savings Rate = (Monthly Income - Monthly Absolute Expenses) / Monthly Income")
        
        # Optional: Display the table
        with st.expander("View Savings Rate Data Table"):
            st.dataframe(monthly_summary[['Date', 'Income', 'Expenses_Abs', 'Net_Savings', 'Savings_Rate']].style.format({
                'Income': "{:.2f}", 'Expenses_Abs': "{:.2f}", 'Net_Savings': "{:.2f}", 'Savings_Rate': "{:.1f}%"
            }))
    else:
        st.write("Not enough data to calculate savings rate trend.")