# src/data_loader.py
import pandas as pd
from pathlib import Path
from io import StringIO # To handle uploaded file buffer from Streamlit
import hashlib # For creating a unique ID for transactions to help with deduplication

# --- [Keep the clean_amount_nordea, clean_amount_danske, 
# ---  standardize_nordea_df, standardize_danske_df functions as defined previously] ---

def clean_amount_nordea(amount):
    """
    If `amount` is already a float/int, return it directly.
    Otherwise (a string like "-1.697,00"), strip out thousand-dots,
    replace comma→dot, then float(…).
    """
    if pd.isna(amount):
        return None

    # If Pandas already parsed it as a number, just return it
    if isinstance(amount, (int, float)):
        return float(amount)

    # Otherwise do the “`.`→''” and “`,`→'.'” dance
    s = str(amount).replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

def clean_amount_danske(amount):
    """
    Same idea for Danske files (where Pandas may already parse to float).
    """
    if pd.isna(amount):
        return None
    if isinstance(amount, (int, float)):
        return float(amount)
    try:
        return float(str(amount))
    except ValueError:
        return None


def standardize_nordea_df(df_in):
    df = df_in.copy()
    rename_map = {
        'Booking date': 'Raw_Date',
        'Amount': 'Raw_Amount',
        'Title': 'Description',
        'Balance': 'Raw_Balance',
        'Currency': 'Currency'
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # “Reserved” rows have Raw_Date == "Reserved"
    df['Status'] = df['Raw_Date'].apply(
        lambda x: 'Reserved' if str(x).strip().lower() == 'reserved' else 'Booked'
    )
    # Only parse actual dates for rows where Status=='Booked'
    df['Date'] = pd.to_datetime(
        df.loc[df['Status'] == 'Booked', 'Raw_Date'],
        format='%Y/%m/%d',
        errors='coerce'
    )

    if 'Raw_Amount' in df.columns:
        df['Amount'] = df['Raw_Amount'].apply(clean_amount_nordea)
    if 'Raw_Balance' in df.columns:
        df['Balance'] = df['Raw_Balance'].apply(clean_amount_nordea)

    df['Original_Bank'] = 'Nordea'
    standard_cols = ['Date', 'Description', 'Amount', 'Balance', 'Currency', 'Original_Bank', 'Status']
    for col in standard_cols:
        if col not in df.columns:
            df[col] = None

    return df[standard_cols]

# ─── NEW: “standardize_nordea2_df” for Danish‐headed CSVs ─────────────────────
def standardize_nordea2_df(df_in):
    """
    Handles files whose headers look like:
      Bogføringsdato;Beløb;Afsender;Modtager;Navn;Beskrivelse;Saldo;Valuta;Afstemt;
    """
    df = df_in.copy()
    # Map Danish column names → our Raw_ scheme
    rename_map = {
        'Bogføringsdato': 'Raw_Date',
        'Beløb':          'Raw_Amount',
        'Beskrivelse':    'Description',   # “Beskrivelse” is the same as “Title”
        'Saldo':          'Raw_Balance',
        'Valuta':         'Currency'
        # (We ignore columns like Afsender/Modtager/Navn/Afstemt if present)
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # “Reserved” is now “Reserveret” (Danish). Otherwise treat as “Booked”
    df['Status'] = df['Raw_Date'].apply(
        lambda x: 'Reserved' if str(x).strip().lower() == 'reserveret' else 'Booked'
    )
    # Parse actual dates (Danish format is still YYYY/MM/DD here)
    df['Date'] = pd.to_datetime(
        df.loc[df['Status'] == 'Booked', 'Raw_Date'],
        format='%Y/%m/%d',
        errors='coerce'
    )

    if 'Raw_Amount' in df.columns:
        df['Amount'] = df['Raw_Amount'].apply(clean_amount_nordea)
    if 'Raw_Balance' in df.columns:
        df['Balance'] = df['Raw_Balance'].apply(clean_amount_nordea)

    df['Original_Bank'] = 'Nordea2'
    standard_cols = ['Date', 'Description', 'Amount', 'Balance', 'Currency', 'Original_Bank', 'Status']
    for col in standard_cols:
        if col not in df.columns:
            df[col] = None

    return df[standard_cols]

def standardize_danske_df(df_in):
    df = df_in.copy()
    rename_map = {
        'Booking date': 'Raw_Date',
        'Amount': 'Raw_Amount',
        'Title': 'Description',
        'Balance': 'Raw_Balance',
        'Currency': 'Currency'
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    df['Date'] = pd.to_datetime(
        df['Raw_Date'],
        format='%Y-%m-%d',
        errors='coerce'
    )
    df['Status'] = df['Date'].apply(lambda x: 'Pending/Unknown' if pd.isna(x) else 'Booked')

    if 'Raw_Amount' in df.columns:
        df['Amount'] = df['Raw_Amount'].apply(clean_amount_danske)
    if 'Raw_Balance' in df.columns:
        df['Balance'] = df['Raw_Balance'].apply(clean_amount_danske)

    df['Original_Bank'] = 'Danske Bank'
    standard_cols = ['Date', 'Description', 'Amount', 'Balance', 'Currency', 'Original_Bank', 'Status']
    for col in standard_cols:
        if col not in df.columns:
            df[col] = None

    return df[standard_cols]

# --- [This is the function you were primarily focused on for loading one file] ---
def load_and_standardize_one_transaction_file(file_path_or_buffer, bank_name):
    """
    Loads a single CSV (or buffer), routes to 
    standardize_nordea_df, standardize_nordea2_df, or standardize_danske_df
    depending on bank_name.
    """
    df_raw = None
    try:
        if isinstance(file_path_or_buffer, (str, Path)):
            with open(file_path_or_buffer, 'r', encoding='utf-8-sig') as f:
                raw_text = f.read()
            buf = StringIO(raw_text)
        elif hasattr(file_path_or_buffer, 'getvalue'):
            try:
                buf = StringIO(file_path_or_buffer.getvalue().decode('utf-8-sig'))
            except UnicodeDecodeError:
                file_path_or_buffer.seek(0)
                buf = StringIO(file_path_or_buffer.getvalue().decode('latin1'))
            file_path_or_buffer.seek(0)
        else:
            raise ValueError("Unsupported file input type.")

        lower_name = bank_name.lower()
        if lower_name == 'nordea':
            try:
                df_raw = pd.read_csv(buf, sep=';', decimal=',')
            except ValueError:
                buf.seek(0)
                df_raw = pd.read_csv(buf, sep=';')
            return standardize_nordea_df(df_raw)

        elif lower_name == 'nordea2':
            try:
                df_raw = pd.read_csv(buf, sep=';', decimal=',')
            except ValueError:
                buf.seek(0)
                df_raw = pd.read_csv(buf, sep=';')
            return standardize_nordea2_df(df_raw)

        elif lower_name == 'danske':
            buf.seek(0)
            df_raw = pd.read_csv(buf, sep=',')
            return standardize_danske_df(df_raw)

        else:
            raise ValueError(f"Unsupported bank_name: {bank_name}. "
                             f"Use 'nordea', 'nordea2', or 'danske'.")

    except Exception as e:
        print(f"Error in load_and_standardize_one_transaction_file({bank_name}): {e}")
        return pd.DataFrame()
    
# --- [NEW FUNCTION for processing folders] ---
def process_bank_data_folders(main_bank_data_path: Path):
    """
    Processes all CSV files from Nordea and Danske subfolders within the main_bank_data_path.
    Concatenates them and handles duplicates.
    """
    all_standardized_dfs = []
    
    nordea_path = main_bank_data_path / "nordea"
    danske_path = main_bank_data_path / "danske"

    # Process Nordea files
    if nordea_path.exists() and nordea_path.is_dir():
        print(f"Processing Nordea files from: {nordea_path}")
        for file in sorted(nordea_path.glob("*.csv")):
            print(f"  Loading Nordea file: {file.name}")
            df = load_and_standardize_one_transaction_file(file, bank_name='nordea')
            if not df.empty:
                all_standardized_dfs.append(df)
    else:
        print(f"Nordea path not found or not a directory: {nordea_path}")

    # Process Danske Bank files
    if danske_path.exists() and danske_path.is_dir():
        print(f"Processing Danske Bank files from: {danske_path}")
        for file in sorted(danske_path.glob("*.csv")):
            print(f"  Loading Danske Bank file: {file.name}")
            df = load_and_standardize_one_transaction_file(file, bank_name='danske')
            if not df.empty:
                all_standardized_dfs.append(df)
    else:
        print(f"Danske Bank path not found or not a directory: {danske_path}")

    if not all_standardized_dfs:
        print("No transaction data found or processed.")
        return pd.DataFrame()

    # Concatenate all DataFrames
    combined_df = pd.concat(all_standardized_dfs, ignore_index=True)
    print(f"Total rows before deduplication: {len(combined_df)}")

    # --- Handle Duplicates ---
    # Strategy 1: Simple drop_duplicates based on key columns
    # This requires 'Date' to be parsed correctly and key identifying fields.
    # 'Balance' can change even for duplicate transactions if other transactions happened in between,
    # so it's not always a reliable field for deduplication.
    # 'Description' and 'Amount' along with 'Date' are often good.
    
    # Ensure 'Date' is datetime for proper duplicate checking
    combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')

    # Create a unique ID for more robust deduplication, especially if timestamps are missing
    # We hash key fields to create this ID. Consider nulls carefully.
    # Fill NaNs in key columns for hashing to ensure consistency
    cols_for_id = ['Date', 'Description', 'Amount', 'Original_Bank']
    
    def create_transaction_id(row):
        # Ensure date is string in a consistent format, handle NaT
        date_str = row['Date'].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(row['Date']) else "NoDate"
        # Handle NaN in other fields
        desc_str = str(row['Description']) if pd.notna(row['Description']) else "NoDesc"
        amount_str = f"{row['Amount']:.2f}" if pd.notna(row['Amount']) else "NoAmount"
        bank_str = str(row['Original_Bank']) if pd.notna(row['Original_Bank']) else "NoBank"
        
        # Concatenate and hash
        # Adding a small random element or a sequence number from the original file
        # might be needed if multiple identical transactions on the same day are possible and legitimate.
        # For now, this should catch most statement overlaps.
        id_string = f"{date_str}-{desc_str}-{amount_str}-{bank_str}"
        return hashlib.md5(id_string.encode('utf-8')).hexdigest()

    if not combined_df.empty and all(col in combined_df.columns for col in ['Date', 'Description', 'Amount', 'Original_Bank']):
        combined_df['Transaction_ID'] = combined_df.apply(create_transaction_id, axis=1)
        
        # When dropping duplicates, consider which one to keep ('first' or 'last').
        # 'first' is usually fine if the data is generally chronological within files.
        # We sort by Date (and potentially an original file import order if available) before dropping.
        # Here, we rely on the Transaction_ID which should be stable.
        # 'Status' might also be relevant: a 'Booked' transaction is more definitive than 'Reserved'.
        # If you have both a 'Reserved' and 'Booked' for the same logical transaction, you'd want to keep 'Booked'.
        # This complex logic might require grouping by a more abstract transaction identifier first.
        
        # For now, a simpler deduplication based on Transaction_ID:
        print(f"  Number of unique Transaction_IDs: {combined_df['Transaction_ID'].nunique()}")
        combined_df.drop_duplicates(subset=['Transaction_ID'], keep='first', inplace=True)
        print(f"Total rows after Transaction_ID deduplication: {len(combined_df)}")

    # Alternative/Simpler deduplication if Transaction_ID is too complex or not working as expected:
    # subset_cols = ['Date', 'Description', 'Amount', 'Original_Bank'] # Add more if needed
    # if all(col in combined_df.columns for col in subset_cols):
    #     combined_df.drop_duplicates(subset=subset_cols, keep='first', inplace=True)
    #     print(f"Total rows after subset columns deduplication: {len(combined_df)}")


    # Final cleaning and sorting
    if not combined_df.empty:
        # Drop rows where all key fields are NaN (might have been introduced by concat or original data)
        key_fields_for_empty_check = ['Date', 'Description', 'Amount']
        combined_df.dropna(subset=key_fields_for_empty_check, how='all', inplace=True)

        # Sort by date descending, NaT (e.g. 'Reserved' or 'Pending') at the top or bottom
        combined_df.sort_values(by=['Date', 'Amount'], ascending=[False, True], na_position='first', inplace=True)
        combined_df.reset_index(drop=True, inplace=True)

    return combined_df


# --- Example Usage (for testing this file directly) ---
if __name__ == '__main__':
    # Adjust this path to the PARENT directory containing your 'nordea' and 'danske' subfolders
    # For testing, this should point to your `bank_statements_test` directory if it contains
    # `nordea/nordea_sample.csv` and `danske/danske_sample.csv`
    YOUR_MAIN_BANK_DATA_PATH = Path(r"C:\Users\ag\alvaro\git\financial-planner\bank_statements_test") # ADJUST THIS

    print(f"Main bank data path for testing: {YOUR_MAIN_BANK_DATA_PATH}")

    # Ensure test subdirectories and files exist (create dummy ones if needed for a first run)
    nordea_test_dir = YOUR_MAIN_BANK_DATA_PATH / "nordea"
    danske_test_dir = YOUR_MAIN_BANK_DATA_PATH / "danske"
    nordea_test_file = nordea_test_dir / "nordea_sample.csv"
    danske_test_file = danske_test_dir / "danske_sample.csv"

    for d in [nordea_test_dir, danske_test_dir]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {d}")

    if not nordea_test_file.exists():
        nordea_test_data = """Booking date;Amount;Sender;Recipient;Name;Title;Balance;Currency;Reconciled;Unnamed: 9
Reserved;-1697,00;3.499421e+09;;;IKEA COPENHAGEN DYBBOE;720112,30;DKK;;
2024/01/22;-218,75;3.499421e+09;;;COOP365 SLUSEHOLMEN Den 19.01;721809,30;DKK;;
2024/01/19;-83,87;3.499421e+09;;;COOP365 SLUSEHOLMEN Den 17.01;722028,05;DKK;;
2024/01/19;-18,00;3.499421e+09;;;Nordea pay, . COOP365 METROPOLEN Den 17.01;722111,92;DKK;;
"""
        with open(nordea_test_file, 'w', encoding='utf-8') as f: f.write(nordea_test_data)
        print(f"Created dummy Nordea test file: {nordea_test_file}")

    if not danske_test_file.exists():
        danske_test_data = """Booking date,Amount,Title,Balance,Currency,Positive_negative,TypeExpense
,-1697.00,IKEA COPENHAGEN DYBBOE,720112.30,DKK,Negative,Household
2024-01-22,-218.75,COOP365 SLUSEHOLMEN Den 19.01,721809.30,DKK,Negative,Groceries
2024-01-19,-83.87,COOP365 SLUSEHOLMEN Den 17.01,722028.05,DKK,Negative,Groceries
"""
        with open(danske_test_file, 'w', encoding='utf-8') as f: f.write(danske_test_data)
        print(f"Created dummy Danske test file: {danske_test_file}")
    
    # Test the folder processing function
    combined_df = process_bank_data_folders(YOUR_MAIN_BANK_DATA_PATH)
    if not combined_df.empty:
        print("\n--- Combined and Deduplicated DataFrame ---")
        print(f"Shape: {combined_df.shape}")
        print(combined_df.head(10))
        print("\nInfo:")
        combined_df.info()
    else:
        print("Processing resulted in an empty DataFrame.")