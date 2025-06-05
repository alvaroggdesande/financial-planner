# pages/01_💰_Transaction_Tracker.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date
import plotly.express as px

# Add project root to Python path so we can import from src/
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.data_loader import process_bank_data_folders, load_and_standardize_one_transaction_file
from src.categorizer import categorize_transactions_df, CATEGORY_RULES
from src.utils import convert_currency_in_df, DKK_TO_EUR_RATE

from src.plotting_functions import (
    plot_spending_by_category, 
    plot_income_expense_trend, 
    plot_net_savings_trend,
    plot_balance_trend,
    plot_monthly_spending_by_category,
    plot_percentage_change_expenses,
    plot_savings_rate_trend
)

from src.analysis_functions import display_big_ticket_expenses, category_deep_dive_section, display_net_worth_snapshot

st.set_page_config(page_title="Transaction Tracker", layout="wide")
st.title("💰 Transaction Tracker")

# --- Session State Initialization ---
if 'raw_transactions_df' not in st.session_state:
    st.session_state.raw_transactions_df = pd.DataFrame()
if 'categorized_transactions_df' not in st.session_state:
    st.session_state.categorized_transactions_df = pd.DataFrame()
if 'rules_for_categorization' not in st.session_state:
    st.session_state.rules_for_categorization = CATEGORY_RULES
if 'data_loaded_successfully' not in st.session_state:
    st.session_state.data_loaded_successfully = False

# --- Helper to dedupe + categorize ---
def process_and_categorize_data(df_in):
    """ Deduplicate on (Date, Description, Amount, Original_Bank) and then categorize. """
    if df_in.empty:
        return pd.DataFrame()

    # Make sure Date is datetime
    df = df_in.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Create a simple ID for deduplication
    if all(col in df.columns for col in ['Date', 'Description', 'Amount', 'Original_Bank']):
        def make_temp_id(r):
            ds = r['Date'].strftime('%Y-%m-%d') if pd.notna(r['Date']) else 'NoDate'
            desc = str(r['Description'])[:50] if pd.notna(r['Description']) else 'NoDesc'
            amt = f"{r['Amount']:.2f}" if pd.notna(r['Amount']) else 'NoAmt'
            bank = str(r['Original_Bank']) if pd.notna(r['Original_Bank']) else 'NoBank'
            return f"{ds}-{desc}-{amt}-{bank}"

        df['Temp_ID'] = df.apply(make_temp_id, axis=1)
        df = df.drop_duplicates(subset=['Temp_ID'], keep='first').drop(columns=['Temp_ID'])

    # Now categorize using your rules
    df_cat = categorize_transactions_df(
        df.copy(),
        st.session_state.rules_for_categorization
    )
    return df_cat

# --- Sidebar: Data Source Selection ---
st.sidebar.header("Load Data")
data_source_option = st.sidebar.radio(
    "Select Data Source:",
    ("Upload Files", "Process Local Folders"),
    key="data_source_select"
)

# Button to trigger the actual load + categorize
if st.sidebar.button("Load and Categorize Data", key="load_data_btn"):
    # Clear previous state
    st.session_state.data_loaded_successfully = False
    st.session_state.raw_transactions_df = pd.DataFrame()
    st.session_state.categorized_transactions_df = pd.DataFrame()

    if data_source_option == "Upload Files":
        cached = st.session_state.get('uploaded_files_cache', None)
        if not cached:
            st.sidebar.warning("Please upload files first, then click ‘Load and Categorize Data’.")
        else:
            frames = []
            for entry in cached:
                file_obj = entry['file']
                bank_type = entry['bank_type']
                file_obj.seek(0)
                df_one = load_and_standardize_one_transaction_file(file_obj, bank_name=bank_type)
                if not df_one.empty:
                    frames.append(df_one)

            if frames:
                combined = pd.concat(frames, ignore_index=True)
                st.session_state.raw_transactions_df = combined
                st.session_state.categorized_transactions_df = process_and_categorize_data(combined)
                st.session_state.data_loaded_successfully = True
                st.sidebar.success(
                    f"Uploaded files processed. "
                    f"Total categorized transactions: {len(st.session_state.categorized_transactions_df)}"
                )
            else:
                st.sidebar.warning("No data processed from those upload(s).")

    else:  # Process Local Folders
        default_path = PROJECT_ROOT / "bank_statements_test"
        folder_path = Path(st.session_state.get('local_folder_path_cache', str(default_path)))
        if folder_path.exists() and folder_path.is_dir():
            loaded = process_bank_data_folders(folder_path)
            st.session_state.raw_transactions_df = loaded
            st.session_state.categorized_transactions_df = process_and_categorize_data(loaded)
            st.session_state.data_loaded_successfully = True
            st.sidebar.success(
                f"Data from folders loaded successfully. "
                f"Total categorized transactions: {len(st.session_state.categorized_transactions_df)}"
            )
        else:
            st.sidebar.error("Invalid folder path for local processing.")

# --- File Uploader (separate from the load button) ---
if data_source_option == "Upload Files":
    uploaded_list = st.sidebar.file_uploader(
        "Upload Bank CSVs",
        type="csv",
        accept_multiple_files=True,
        key="file_uploader_main"
    )
    if uploaded_list:
        st.session_state.uploaded_files_cache = []
        for idx, upload in enumerate(uploaded_list):
            # 1) Add "Nordea 2 (DK)" → "nordea2"
            bank_map = {
                "Nordea (DK)":  "nordea",
                "Nordea 2 (DK)": "nordea2",
                "Danske Bank (DK)": "danske"
            }
            choice = st.sidebar.selectbox(
                f"Select bank for {upload.name}:",
                list(bank_map.keys()),
                key=f"bank_select_{idx}_{upload.name}"
            )
            st.session_state.uploaded_files_cache.append({
                'file': upload,
                'bank_type': bank_map[choice]
            })

else:  # Process Local Folders
    default_folder = str(PROJECT_ROOT / "bank_statements_test")
    folder_input = st.sidebar.text_input(
        "Enter Path to Bank Data Parent Folder:",
        value=default_folder,
        key="local_folder_path_input"
    )
    st.session_state.local_folder_path_cache = folder_input

# --- Main Display: only when data is loaded & categorized ---
if st.session_state.data_loaded_successfully and not st.session_state.categorized_transactions_df.empty:
    df_display_base = st.session_state.categorized_transactions_df.copy()

    # --- Currency Conversion (unchanged) ---
    st.sidebar.markdown("---")
    st.sidebar.header("Display Options")
    display_currency = st.sidebar.selectbox(
        "Display Currency:",
        ["DKK", "EUR"],
        key="display_currency_select"
    )

    currency_suffix = "DKK"
    if display_currency == "EUR":
        df_display_base = convert_currency_in_df(
            df_display_base.copy(),
            target_currency="EUR",
            rate_dkk_eur=DKK_TO_EUR_RATE
        )
        currency_suffix = "EUR"

    # --- Filtering Section (unchanged) ---
    st.header("Filters & Transactions")

    df_display_base['Date'] = pd.to_datetime(df_display_base['Date'], errors='coerce')
    df_display_base = df_display_base.dropna(subset=['Date'])
    if df_display_base.empty:
        st.warning("No valid date data remains after parsing.")
    else:
        min_d = df_display_base['Date'].min().date()
        max_d = df_display_base['Date'].max().date()
        if min_d > max_d:
            min_d, max_d = max_d, min_d

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input(
                "Start date",
                min_value=min_d,
                max_value=max_d,
                value=min_d,
                key="min_date_filter"
            )
        with c2:
            end_date = st.date_input(
                "End date",
                min_value=min_d,
                max_value=max_d,
                value=max_d,
                key="max_date_filter"
            )

        all_cats = sorted(df_display_base['Category'].unique().tolist())
        select_all = st.checkbox("Select/Deselect All Categories", value=True, key="select_all_cat_cb")
        default_cats = all_cats if select_all else []

        chosen_cats = st.multiselect(
            "Filter by Category:",
            all_cats,
            default=default_cats,
            key="category_filter"
        )

        mask = (
            (df_display_base['Date'].dt.date >= start_date) &
            (df_display_base['Date'].dt.date <= end_date) &
            (df_display_base['Category'].isin(chosen_cats))
        )
        df_filtered = df_display_base.loc[mask].copy()

        if df_filtered.empty:
            st.warning("No transactions match the current filters.")
        else:
            st.subheader("Filtered Transactions")
            st.dataframe(
                df_filtered[['Date', 'Description', 'Amount', 'Category', 'Original_Bank', 'Status']]
            )
            st.metric("Total Transactions Displayed", len(df_filtered))

            # --- Financial Summary ---
            st.header("Financial Summary")

            # Call your modular plotting functions
            # 1. Spending by Category
            plot_spending_by_category(
                df_filtered[df_filtered['Amount'] < 0].copy(), # Pass only expenses
                currency_suffix
            )
            
            # 2. Income vs. Expense Trend
            plot_income_expense_trend(df_filtered.copy(), currency_suffix)

            # 3. Net Savings Trend
            plot_net_savings_trend(df_filtered.copy(), currency_suffix)

            # 4. Balance Trend
            plot_balance_trend(df_filtered.copy(), currency_suffix)
            
            # 5. Monthly Spending by Category (NEW)
            plot_monthly_spending_by_category(
                df_filtered[df_filtered['Amount'] < 0].copy(), # Pass only expenses
                currency_suffix
            )

            # 6. Percentage Change in Expenses (NEW)
            plot_percentage_change_expenses(
                df_filtered[df_filtered['Amount'] < 0].copy(), # Pass only expenses
                currency_suffix
            )

            # 7. Savings Rate Trend (NEW)
            plot_savings_rate_trend(df_filtered.copy(), currency_suffix)

            # -------- From analysis_functions --------
            # 8. Big Ticket Expense Tracker (NEW)
            display_big_ticket_expenses(
                df_filtered[df_filtered['Amount'] < 0].copy(), # Pass only expenses
                currency_suffix
            )
            # 9. Category Deep Dive Section (NEW)
            st.markdown("---") # Add a separator
            category_deep_dive_section(
                df_filtered[df_filtered['Amount'] < 0].copy(), # Pass only expenses
                currency_suffix
            )

            # 10. Net Worth Snapshot (NEW - Manual)
            st.markdown("---")
            display_net_worth_snapshot(currency_suffix)

else:
    st.info("Please load and categorize transaction data using the sidebar.")

# Footer: clear button
st.sidebar.markdown("---")
if st.sidebar.button("Clear All Loaded Data", key="clear_data_btn"):
    st.session_state.raw_transactions_df = pd.DataFrame()
    st.session_state.categorized_transactions_df = pd.DataFrame()
    st.session_state.data_loaded_successfully = False
    st.experimental_rerun()
