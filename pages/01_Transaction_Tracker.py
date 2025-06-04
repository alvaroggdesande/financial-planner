# pages/01_💰_Transaction_Tracker.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date
import plotly.express as px

# Assuming your custom modules are in a 'src' directory at the project root
# You might need to adjust sys.path if running Streamlit from a different CWD or if src isn't in PYTHONPATH
import sys
# Determine project root dynamically (assuming this file is in financial-planner/pages/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT)) # Add project root to path
# Now you can import from src
from src.data_loader import process_bank_data_folders, load_and_standardize_one_transaction_file
from src.categorizer import categorize_transactions_df, CATEGORY_RULES # Import your rules too
from src.utils import convert_currency_in_df


st.set_page_config(page_title="Transaction Tracker", layout="wide")
st.title("💰 Transaction Tracker")

# --- Session State Initialization ---
if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = pd.DataFrame()
if 'rules_for_categorization' not in st.session_state: # Load rules once
    # In a real app, you'd load this from config/categories_keywords.json or similar
    st.session_state.rules_for_categorization = CATEGORY_RULES

# --- Data Loading Section ---
st.sidebar.header("Load Data")
data_source_option = st.sidebar.radio("Select Data Source:", ("Upload Files", "Process Local Folders"))

if data_source_option == "Upload Files":
    uploaded_files = st.sidebar.file_uploader("Upload Bank CSVs", type="csv", accept_multiple_files=True)
    if uploaded_files:
        all_dfs_list = []
        for uploaded_file in uploaded_files:
            # Simple way to ask for bank type - can be improved
            bank_type_map = {"Nordea (DK)": "nordea", "Danske Bank (DK)": "danske"}
            bank_display_name = st.sidebar.selectbox(
                f"Select bank for {uploaded_file.name}:",
                list(bank_type_map.keys()),
                key=f"bank_select_{uploaded_file.name}" # Unique key for each selectbox
            )
            bank_internal_name = bank_type_map.get(bank_display_name)

            if bank_internal_name:
                df_single = load_and_standardize_one_transaction_file(uploaded_file, bank_name=bank_internal_name)
                if not df_single.empty:
                    all_dfs_list.append(df_single)
        
        if all_dfs_list:
            combined_df = pd.concat(all_dfs_list, ignore_index=True)
            # Simplified deduplication for uploaded files (can be enhanced like in process_bank_data_folders)
            if not combined_df.empty:
                cols_for_id = ['Date', 'Description', 'Amount', 'Original_Bank']
                if all(col in combined_df.columns for col in cols_for_id):
                    # Ensure Date is datetime before formatting
                    combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')
                    def create_transaction_id_simple(row):
                        date_str = row['Date'].strftime('%Y-%m-%d') if pd.notna(row['Date']) else "NoDate"
                        desc_str = str(row['Description'])[:50] if pd.notna(row['Description']) else "NoDesc" # Truncate
                        amount_str = f"{row['Amount']:.2f}" if pd.notna(row['Amount']) else "NoAmount"
                        bank_str = str(row['Original_Bank']) if pd.notna(row['Original_Bank']) else "NoBank"
                        return f"{date_str}-{desc_str}-{amount_str}-{bank_str}" # Simpler ID for this context
                    combined_df['Temp_ID'] = combined_df.apply(create_transaction_id_simple, axis=1)
                    combined_df.drop_duplicates(subset=['Temp_ID'], keep='first', inplace=True)
                    combined_df.drop(columns=['Temp_ID'], inplace=True, errors='ignore')

            st.session_state.transactions_df = combined_df
            st.sidebar.success(f"{len(uploaded_files)} file(s) processed. Total transactions: {len(st.session_state.transactions_df)}")
        else:
            st.sidebar.warning("No data processed from uploaded files.")


elif data_source_option == "Process Local Folders":
    # IMPORTANT: For security, this path should NOT be hardcoded if deploying publicly.
    # For local use, it's fine. Consider using an environment variable or config.
    default_path_str = str(PROJECT_ROOT / "bank_statements_test") # Default to test data path
    bank_data_main_path_str = st.sidebar.text_input("Enter Path to Bank Data Parent Folder:", value=default_path_str)
    if st.sidebar.button("Load from Local Folders"):
        bank_data_main_path = Path(bank_data_main_path_str)
        if bank_data_main_path.exists() and bank_data_main_path.is_dir():
            st.session_state.transactions_df = process_bank_data_folders(bank_data_main_path)
            st.sidebar.success(f"Data loaded from folders. Total transactions: {len(st.session_state.transactions_df)}")
        else:
            st.sidebar.error("Invalid path or folder does not exist.")

# Currency. Runs if transactions_df is updated
if not st.session_state.transactions_df.empty:
    # Option for currency conversion
    st.sidebar.markdown("---")
    st.sidebar.header("Display Options")
    display_currency = st.sidebar.selectbox("Display Currency:", ["DKK", "EUR"], key="display_currency_select")

    # Get the base DKK dataframe
    base_transactions_df = st.session_state.transactions_df.copy() # Work with a copy for display

    if display_currency == "EUR":
        # Fetch current DKK_TO_EUR_RATE from an API or config here if dynamic
        # For now, using the one defined in utils
        transactions_to_display = convert_currency_in_df(base_transactions_df, target_currency="EUR")
        currency_suffix = "EUR"
    else:
        transactions_to_display = base_transactions_df
        currency_suffix = "DKK"
    
    # --- NOW USE 'transactions_to_display' FOR ALL FILTERING AND PLOTTING ---
    # And update y-axis labels for charts to include currency_suffix
    # e.g., fig_line_ie.update_layout(yaxis_title=f"Amount ({currency_suffix})")

# --- Categorization (runs if transactions_df is updated) ---
if not st.session_state.transactions_df.empty:
    if 'Category' not in st.session_state.transactions_df.columns or st.session_state.transactions_df['Category'].isnull().all():
        with st.spinner("Categorizing transactions..."):
            st.session_state.transactions_df = categorize_transactions_df(
                st.session_state.transactions_df.copy(), # Work on a copy
                st.session_state.rules_for_categorization
            )
    
    st.subheader("Filtered Transactions")
    
    # --- Filters ---
    # Date Range Slider/Input
    min_date = st.session_state.transactions_df['Date'].min()
    max_date = st.session_state.transactions_df['Date'].max()

    if pd.isna(min_date) or pd.isna(max_date):
        st.warning("Date range cannot be determined. Please check your data.")
        # Set default dates if min/max are NaT
        min_date = date.today().replace(day=1, month=1) if pd.isna(min_date) else min_date.date()
        max_date = date.today() if pd.isna(max_date) else max_date.date()
    else:
        # Convert to datetime.date objects for st.slider compatibility if they are Timestamps
        min_date = min_date.date() if isinstance(min_date, pd.Timestamp) else min_date
        max_date = max_date.date() if isinstance(max_date, pd.Timestamp) else max_date

    # Ensure min_date is not after max_date
    if min_date > max_date:
        min_date, max_date = max_date, min_date # Swap if order is wrong

    # Date filter
    # Using two st.date_input for better control if slider range is too large
    col1_filter, col2_filter = st.columns(2)
    with col1_filter:
        selected_min_date = st.date_input("Start date", min_date, min_value=min_date, max_value=max_date, key="min_date_filter")
    with col2_filter:
        selected_max_date = st.date_input("End date", max_date, min_value=min_date, max_value=max_date, key="max_date_filter")

    all_categories = sorted(st.session_state.transactions_df['Category'].unique().tolist())

    # Add a "Select All" checkbox
    select_all_categories = st.checkbox("Select/Deselect All Categories", value=True, key="select_all_cat_cb")

    if select_all_categories:
        default_selected_categories = all_categories
    else:
        # If you want it to deselect all when unchecked, otherwise you might want it to remember previous selection
        default_selected_categories = [] 

    # The multiselect will now be controlled by the checkbox for its default state
    selected_categories = st.multiselect(
        "Filter by Category:", 
        all_categories, 
        default=default_selected_categories, 
        key="category_filter"
    )

    # If the user manually changes multiselect, you might want to uncheck "Select All"
    # This makes the interaction a bit more complex. A simpler way is that the checkbox
    # just SETS the state of multiselect, and then multiselect can be changed independently.
    # For a true toggle, you'd need more session_state logic to see if multiselect was changed.
    # Apply filters
    filtered_df = st.session_state.transactions_df[
        (st.session_state.transactions_df['Date'].dt.date >= selected_min_date) &
        (st.session_state.transactions_df['Date'].dt.date <= selected_max_date) &
        (st.session_state.transactions_df['Category'].isin(selected_categories))
    ]
    
    if filtered_df.empty:
        st.warning("No transactions match the current filter criteria.")
    else:
        st.dataframe(filtered_df)
        st.metric("Total Transactions Displayed", len(filtered_df))

        # --- Aggregations and Graphs ---
        st.header("Financial Summary")

        # Prepare data for monthly aggregation
        # Ensure 'Date' is datetime and set as index for resampling
        monthly_df = filtered_df.copy()
        monthly_df['Date'] = pd.to_datetime(monthly_df['Date'])
        monthly_df.set_index('Date', inplace=True)

        # 1. Spending by Category
        st.subheader("Spending by Category")
        expenses_df = filtered_df[filtered_df['Amount'] < 0].copy()
        expenses_df['Absolute_Amount'] = expenses_df['Amount'].abs()
        category_spending = expenses_df.groupby('Category')['Absolute_Amount'].sum().sort_values(ascending=False)
        
        if not category_spending.empty:
            fig_bar_horizontal = px.bar(
                category_spending.reset_index(), # reset_index to get 'Category' as a column
                y='Category', 
                x='Absolute_Amount', 
                orientation='h',
                title="Expense by Category",
                labels={'Absolute_Amount': 'Amount (DKK)', 'Category': 'Category'}
            )
            fig_bar_horizontal.update_layout(yaxis={'categoryorder':'total ascending'}) # Sort by value
            st.plotly_chart(fig_bar_horizontal, use_container_width=True)
            
            st.bar_chart(category_spending)

            fig_treemap = px.treemap(
                category_spending.reset_index(), 
                path=[px.Constant("All Expenses"), 'Category'], # Defines hierarchy
                values='Absolute_Amount',
                title="Expense Distribution Treemap"
            )
            st.plotly_chart(fig_treemap, use_container_width=True)    
        else:
            st.write("No expense data to display for category spending.")

        # 2. Income vs. Expense Trend (Monthly)
        st.subheader("Income vs. Expenses Over Time (Monthly)")
        # Resample to get monthly sums
        # Income: positive amounts, Expenses: negative amounts (sum directly)
        monthly_summary = monthly_df.resample('M')['Amount'].agg(
            Income=lambda x: x[x > 0].sum(),
            Expenses=lambda x: x[x < 0].sum() # Expenses are negative, sum will be negative
        ).reset_index()
        monthly_summary['Expenses'] = monthly_summary['Expenses'].abs() # Make expenses positive for plotting alongside income

        if not monthly_summary.empty:
            # Melt for st.line_chart or st.bar_chart with grouped bars
            plot_data_income_expense = monthly_summary.melt(id_vars='Date', value_vars=['Income', 'Expenses'], var_name='Type', value_name='Value')
            
            fig_line_ie = px.line(plot_data_income_expense, x='Date', y='Value', color='Type', title="Monthly Income vs. Expenses")
            fig_line_ie.update_layout(yaxis_title="Amount (DKK)")
            st.plotly_chart(fig_line_ie, use_container_width=True)

            # Using st.bar_chart for grouped bars
            # For st.bar_chart, index needs to be the x-axis
            st.bar_chart(monthly_summary.set_index('Date')[['Income', 'Expenses']])
        else:
            st.write("No data for monthly income/expense trend.")

        # 3. Net Savings Trend (Monthly)
        st.subheader("Net Savings Over Time (Monthly)")
        # Ensure monthly_df has 'Date' as index for resampling
        # and 'Amount' is numeric
        if not monthly_df.empty and 'Amount' in monthly_df.columns and pd.api.types.is_numeric_dtype(monthly_df['Amount']):
            monthly_net_savings = monthly_df.resample('M')['Amount'].sum().reset_index() # Ensure 'Date' becomes a column
            monthly_net_savings.rename(columns={'Amount': 'Net Savings'}, inplace=True) # Rename summed column

            if not monthly_net_savings.empty:
                fig_net_savings = px.bar(
                    monthly_net_savings, 
                    x='Date',  # Make sure 'Date' is the x-axis
                    y='Net Savings', # Make sure 'Net Savings' is the y-axis
                    title="Monthly Net Savings"
                )
                fig_net_savings.update_layout(yaxis_title=f"Net Savings ({currency_suffix})")
                fig_net_savings.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_net_savings, use_container_width=True)
            else:
                st.write("Not enough data for net savings trend after resampling.")
        else:
            st.write("No valid data for net savings trend.")
else:
    st.info("Please load transaction data using the sidebar options.")

st.sidebar.markdown("---")
