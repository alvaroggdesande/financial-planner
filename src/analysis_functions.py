import streamlit as st
import pandas as pd
import numpy as np

def display_big_ticket_expenses(df_expenses, currency_suffix):
    """Allows user to define a threshold and lists expenses exceeding it."""
    if df_expenses.empty:
        st.write("No expense data to analyze for big tickets.")
        return
        
    st.subheader(f"Big Ticket Expense Tracker ({currency_suffix})")
    
    # User defines threshold - ensure it's positive for expense comparison
    # Default to a reasonable value, e.g., 500
    # Max value can be dynamic based on max expense if desired
    default_threshold = 500.0
    max_abs_expense = df_expenses['Amount'].abs().max() if not df_expenses.empty else default_threshold * 2
    
    threshold = st.number_input(
        f"Show expenses greater than ({currency_suffix}):", 
        min_value=0.0, 
        value=default_threshold, 
        step=50.0,
        max_value=max_abs_expense, # Optional: set a dynamic max
        key="big_ticket_threshold"
    )

    df_exp_copy = df_expenses.copy()
    # Ensure Amount is numeric
    df_exp_copy['Amount'] = pd.to_numeric(df_exp_copy['Amount'], errors='coerce')
    
    big_expenses = df_exp_copy[df_exp_copy['Amount'].abs() > threshold]
    
    if not big_expenses.empty:
        st.write(f"Found {len(big_expenses)} expenses exceeding {threshold:.2f} {currency_suffix}:")
        st.dataframe(
            big_expenses[['Date', 'Description', 'Amount', 'Category']].sort_values(by='Amount') # Sort by smallest (most negative)
            .style.format({'Amount': "{:.2f}"})
        )
    else:
        st.write(f"No expenses found exceeding {threshold:.2f} {currency_suffix} in the selected period.")

def category_deep_dive_section(df_expenses, currency_suffix):
    """Provides a detailed analysis for a user-selected expense category."""
    if df_expenses.empty:
        st.write("No expense data for category deep dive.")
        return

    st.header(f"Category Deep Dive ({currency_suffix})")
    
    all_expense_categories = sorted(df_expenses['Category'].unique().tolist())
    if not all_expense_categories:
        st.write("No categories found in expense data.")
        return

    selected_category = st.selectbox(
        "Select a category for detailed analysis:",
        options=all_expense_categories,
        key="deep_dive_category_select"
    )

    if selected_category:
        st.subheader(f"Analysis for: {selected_category}")
        
        cat_df = df_expenses[df_expenses['Category'] == selected_category].copy()
        if cat_df.empty:
            st.write(f"No transactions found for '{selected_category}' in the selected period.")
            return

        cat_df['Date'] = pd.to_datetime(cat_df['Date'], errors='coerce')
        cat_df = cat_df.dropna(subset=['Date'])
        if cat_df.empty:
            st.write(f"No valid date data for '{selected_category}'.")
            return
            
        cat_df['Absolute_Amount'] = pd.to_numeric(cat_df['Amount'], errors='coerce').abs().fillna(0)
        cat_df.set_index('Date', inplace=True) # For resampling

        # a. Trend of spending in that category over time (line chart)
        st.markdown("##### Monthly Spending Trend")
        monthly_spend_cat = cat_df.resample('ME')['Absolute_Amount'].sum().reset_index()
        if not monthly_spend_cat.empty:
            st.line_chart(monthly_spend_cat.set_index('Date')['Absolute_Amount'])
        else:
            st.write("No monthly spending data for this category.")

        # b. List of all transactions in that category for the selected period
        with st.expander("View All Transactions for this Category"):
            st.dataframe(
                cat_df.reset_index()[['Date', 'Description', 'Amount']] # Reset index to show Date as column
                .sort_values(by='Date', ascending=False)
                .style.format({'Amount': "{:.2f}"})
            )

        # c. Average monthly spend in that category
        if not monthly_spend_cat.empty:
            avg_monthly_spend = monthly_spend_cat['Absolute_Amount'].mean()
            st.metric(f"Average Monthly Spend in {selected_category}", f"{avg_monthly_spend:.2f} {currency_suffix}")
        
        # d. Comparison to the previous period (e.g., current month vs. last month)
        #    This requires at least two months of data for the category.
        if len(monthly_spend_cat) >= 2:
            latest_month_spend = monthly_spend_cat['Absolute_Amount'].iloc[-1]
            previous_month_spend = monthly_spend_cat['Absolute_Amount'].iloc[-2]
            
            if previous_month_spend > 0: # Avoid division by zero
                pct_change = ((latest_month_spend - previous_month_spend) / previous_month_spend) * 100
                change_text = f"{pct_change:+.1f}%" # Format with sign
                delta_color = "inverse" if pct_change < 0 else "normal" # Green for decrease in expense
                st.metric(
                    f"Spend in {monthly_spend_cat['Date'].iloc[-1]:%B %Y} vs. {monthly_spend_cat['Date'].iloc[-2]:%B %Y}",
                    f"{latest_month_spend:.2f} {currency_suffix}",
                    delta=change_text,
                    delta_color=delta_color
                )
            elif latest_month_spend > 0 and previous_month_spend == 0:
                 st.metric(
                    f"Spend in {monthly_spend_cat['Date'].iloc[-1]:%B %Y} vs. {monthly_spend_cat['Date'].iloc[-2]:%B %Y}",
                    f"{latest_month_spend:.2f} {currency_suffix}",
                    delta="New spending (was 0)"
                )
            # Add more conditions as needed (e.g. what if latest is 0 and prev was > 0)
        elif len(monthly_spend_cat) == 1:
            st.write("Only one month of data available for this category; cannot compare to previous month.")


        # e. Rolling Averages (for this specific category)
        st.markdown("##### Rolling Average Spending (3-Month)")
        if len(monthly_spend_cat) >= 3:
            monthly_spend_cat_indexed = monthly_spend_cat.set_index('Date')
            monthly_spend_cat_indexed['Rolling_Avg_3M'] = monthly_spend_cat_indexed['Absolute_Amount'].rolling(window=3, min_periods=1).mean()
            st.line_chart(monthly_spend_cat_indexed[['Absolute_Amount', 'Rolling_Avg_3M']])
        else:
            st.write("Not enough data (at least 3 months) for a 3-month rolling average.")

def display_net_worth_snapshot(currency_suffix):
    """Simple manual input for net worth calculation."""
    st.header("Net Worth Snapshot (Manual Input)")
    
    st.markdown(
        "Enter your current assets and liabilities. "
        "The 'Account Balance Trend' already shows your tracked bank balances."
    )
    
    cols_nw = st.columns(2)
    with cols_nw[0]:
        st.subheader("Assets")
        cash_savings = st.number_input(f"Cash & Savings Accounts ({currency_suffix})", min_value=0.0, value=0.0, step=1000.0, key="nw_cash")
        investments = st.number_input(f"Investments (Stocks, ETFs, etc.) ({currency_suffix})", min_value=0.0, value=0.0, step=1000.0, key="nw_invest")
        property_value = st.number_input(f"Real Estate Value ({currency_suffix})", min_value=0.0, value=0.0, step=10000.0, key="nw_property")
        other_assets = st.number_input(f"Other Assets ({currency_suffix})", min_value=0.0, value=0.0, step=100.0, key="nw_other_assets")
        total_assets = cash_savings + investments + property_value + other_assets
        st.metric("Total Assets", f"{total_assets:.2f} {currency_suffix}")

    with cols_nw[1]:
        st.subheader("Liabilities")
        mortgage_debt = st.number_input(f"Mortgage Debt ({currency_suffix})", min_value=0.0, value=0.0, step=1000.0, key="nw_mortgage")
        other_loans = st.number_input(f"Other Loans (Car, Student, etc.) ({currency_suffix})", min_value=0.0, value=0.0, step=100.0, key="nw_other_loans")
        credit_card_debt = st.number_input(f"Credit Card Debt ({currency_suffix})", min_value=0.0, value=0.0, step=10.0, key="nw_cc_debt")
        total_liabilities = mortgage_debt + other_loans + credit_card_debt
        st.metric("Total Liabilities", f"{total_liabilities:.2f} {currency_suffix}")
        
    st.markdown("---")
    net_worth = total_assets - total_liabilities
    st.metric("Estimated Net Worth", f"{net_worth:.2f} {currency_suffix}", delta_color="off")


def calculate_historical_average_annual_living_expenses(
    categorized_df: pd.DataFrame, 
    exclude_categories: list = None
) -> float:
    """
    Calculates average annual living expenses from historical categorized transactions.
    Excludes specified categories (e.g., mortgage, large investments).
    """
    if categorized_df.empty:
        return 0.0
    if exclude_categories is None:
        exclude_categories = []

    expenses_df = categorized_df[categorized_df['Amount'] < 0].copy()
    
    # Filter out explicitly excluded categories
    expenses_df = expenses_df[~expenses_df['Category'].isin(exclude_categories)]
    
    expenses_df['Date'] = pd.to_datetime(expenses_df['Date'])
    expenses_df['YearMonth'] = expenses_df['Date'].dt.to_period('M')
    
    monthly_total_expenses = expenses_df.groupby('YearMonth')['Amount'].sum().abs()
    
    if monthly_total_expenses.empty:
        return 0.0
        
    average_monthly_expense = monthly_total_expenses.mean()
    return average_monthly_expense * 12