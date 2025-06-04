# src/categorizer.py
import pandas as pd
import re # For regular expressions, can be more powerful than simple keyword search

# --- PASTE YOUR CATEGORY_RULES DICTIONARY HERE ---
# Example:
CATEGORY_RULES = {
    "Groceries": ["coop365", "superbrugsen", "netto", "rema1000", "føtex", "meny", "lidl", "irma", "bilka togo"],
    "Salary": ["løn", "salary", "indkomst", "[YOUR COMPANY NAME HERE]"], # Replace with actual company name
    "Sports": ["fitnessworld", "sats", "gym", "sportmaster", "fitness dk"],
    "Rent/Mortgage": ["husleje", "rent", "boligudgift", "mortgage payment", "realkredit"],
    "Household": ["ikea", "jysk", "imerco", "silvan", "jem & fix", "bauhaus", "isenkram"],
    "Transport": ["dsb", "rejsekort", "movia", "gomore", "uber", "bolt", "benzin", "esso", "circle k", "shell", "færge", "easyjet", "sas", "norwegian", "ryanair", "brobizz", "parkering"],
    "Utilities": ["dong", "hofor", "øresundsenergi", "vand", "varme", "el", "gas", "forsyning"],
    "Shopping": ["magasin", "zalando", "hm", "elgiganten", "power", "asos", "boozt", "matas", "bog & ide"],
    "Internet/Phone": ["fastnet", "bredbånd", "telia", "tdc", "hiper", "yousee", "oister", "cbb mobil", "telefon"],
    "Dining Out": ["restaurant", "cafe", "just eat", "wolt", "mcdonalds", "burger king", "pizzeria"],
    "Subscriptions": ["netflix", "spotify", "hbo", "disney+", "apple music", "storytel", "mofibo", "tv2 play", "viaplay", "avis", "blad"],
    "Healthcare": ["apotek", "læge", "tandlæge", "sygehus", "optiker", "fysioterapeut"],
    "Transfers": ["overførsel", "transfer", "egen konto", "mobilepay overførsel"], # To filter out internal movements
    "Cash Withdrawal": ["hævning", "atm", "kontant", "bankautomat"],
    "Entertainment": ["biograf", "kino", "koncert", "teater", "museum", "tivoli", "zoo"],
    "Gifts/Charity": ["gave", "donation", "indsamling", "røde kors"],
    "Financial/Fees": ["gebyr", "renteudgift", "bank fee", "finance charge"],
    "Education": ["kursus", "uddannelse", "skole", "universitet"],
    "Personal Care": ["frisør", "kosmetolog", "barber"],
    "Other Income": ["tilbagebetaling", "refund", "renteindtægt"], # Income not from salary
    # Add "Uncategorized" as a fallback if needed, or handle it in the function
}
# It might be better to load CATEGORY_RULES from a config file (JSON/YAML)
# For example, from config/categories_keywords.json

def categorize_transaction_row(row_description, rules):
    """
    Categorizes a single transaction description based on rules.
    Returns the category name or a default if no match.
    """
    if pd.isna(row_description):
        return "Uncategorized"

    description_lower = str(row_description).lower()

    for category, keywords in rules.items():
        for keyword in keywords:
            # Using \b for word boundaries to avoid partial matches (e.g., "car" in "card")
            # Make keyword lowercase as well for consistent matching
            pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
            if re.search(pattern, description_lower):
                return category
    
    return "Uncategorized" # Default category if no rule matches

def categorize_transactions_df(df, rules):
    """
    Adds a 'Category' column to the DataFrame by applying categorization rules.
    df: Standardized DataFrame with a 'Description' column.
    rules: Dictionary of category rules (like CATEGORY_RULES).
    """
    if 'Description' not in df.columns:
        raise ValueError("DataFrame must contain a 'Description' column for categorization.")
    
    # Ensure the 'Category' column exists, initialize if not
    if 'Category' not in df.columns:
        df['Category'] = "Uncategorized" # Default for all initially

    # Apply categorization
    # For potentially large DFs, df.apply can be slow.
    # A more optimized way might involve creating boolean masks for each keyword list
    # or using str.contains with a regex joining all keywords for a category.
    # However, for moderate datasets, .apply() is fine and readable.
    
    # Example: Prioritize existing 'TypeExpense' from Danske if it's already there and valid
    # This logic depends on how you want to integrate your pre-categorized Danske data.
    # For now, let's assume we always re-categorize based on rules for consistency.
    
    df['Category'] = df['Description'].apply(lambda desc: categorize_transaction_row(desc, rules))
    
    return df

# --- Example Usage (for testing this file directly) ---
if __name__ == '__main__':
    # Create a sample DataFrame similar to your standardized one
    sample_data = {
        'Date': pd.to_datetime(['2024-01-22', '2024-01-19', '2024-01-20', '2024-01-21', '2024-01-23']),
        'Description': [
            'COOP365 SLUSEHOLMEN Den 19.01',
            'IKEA COPENHAGEN DYBBOE',
            'Netflix Subscription',
            'Lønoverførsel My Cool Company Aps', # Salary transfer
            'Payment for something unknown'
        ],
        'Amount': [-218.75, -1697.00, -89.00, 50000.00, -50.00],
        'Original_Bank': ['Nordea', 'Danske Bank', 'Nordea', 'Danske Bank', 'Nordea']
    }
    test_df = pd.DataFrame(sample_data)

    print("--- DataFrame Before Categorization ---")
    print(test_df)

    # Make sure CATEGORY_RULES is defined above or loaded from a config
    # For testing, ensure some keywords match your sample_data
    if 'My Cool Company Aps'.lower() not in CATEGORY_RULES.get("Salary", []): # Ensure company name in rules
        if "Salary" in CATEGORY_RULES:
            CATEGORY_RULES["Salary"].append('My Cool Company Aps'.lower())
        else:
            CATEGORY_RULES["Salary"] = ['My Cool Company Aps'.lower()]


    categorized_df = categorize_transactions_df(test_df.copy(), CATEGORY_RULES) # Use .copy() to avoid modifying original

    print("\n--- DataFrame After Categorization ---")
    print(categorized_df)
    print("\nCategory Counts:")
    print(categorized_df['Category'].value_counts())