# src/categorizer.py
import pandas as pd
import re # For regular expressions, can be more powerful than simple keyword search

# --- PASTE YOUR CATEGORY_RULES DICTIONARY HERE ---
CATEGORY_RULES = {
    "Groceries": ["coop365", "COOP 365","Coop App","superbrugsen", "netto", "rema1000", "føtex", "meny", "lidl", "irma", "bilka togo",
                  "FAKTA", "FOETEX", "SPAR", "NORMAL", "REMA 1000", "BASALT"
                  ,"MERCADONA", "ALIMENTACION"],
    "Salary": ["løn", "salary", "indkomst", "Lønoverførsel", "Allyy"],
    "Sports": ["fitnessworld", "sats", "gym", "sportmaster", "fitness dk", "FITNESS", "OLYMPIAKOS"
                ,"MobilePay Juan Marti", "MobilePay Jordi", "MobilePay Oscar Goto"
                ,"MobilePay Oscar Meji", "MobilePay Venkatesh"],
    "Education": ["IMF FORMACION", "IMF"],
    "Rent/Mortgage": ["husleje", "rent", "boligudgift", "mortgage payment", "realkredit"],
    "Household": ["ikea", "jysk", "imerco", "silvan", "jem & fix", "bauhaus", "isenkram", "ILVA"
                    ,"MobilePay Niklas Thr", "BOLIGPORTA"],
    "Transport": ["dsb", "rejsekort", "movia", "gomore", "uber", "bolt", "benzin", "esso", "circle k"
                  , "shell", "færge", "brobizz", "parkering", "DOT APP"
                  ,"METRO", "RENFE", "ALSA"],
    "Flights": ["easyjet", "sas", "norwegian", "ryanair", "Iberia", "IBEXPRESS","Air china", "Qatar air"
                ,'ETIHAD AIRW', "INDIGOAIR", "BRUSS AIRLI", "VUELING", "AIRLINES"],
    "Travel": ["LAEGENS VACCINATIONS", "OWNERS CARS", "MONDO", "HEYMONDO", "VND", "INR", "LKR"
                "Vasileios", "MobilePay Francisco" ,"AIRALO", "HOTEL", "NY CARLSBERG", "BOUTIQUE", "GRUPOGALDANA",
                "Berlin", "INDIAN RAILWAY", "RAILWAY", "12GO"],
    "Utilities": ["dong", "hofor", "øresundsenergi", "vand", "varme", "gas", "forsyning", "ANDEL"],
    "Shopping": ["magasin", "zalando", "hm", "elgiganten", "power", "asos", "boozt", "matas", "bog & ide"
                 ,"EL CORTE INGLES", "UNIQLO", "GlobalE Jabra", "Telerepair", "CYKLER", "DECATHLON"
                 ,"ZARA"],
    "Internet/Phone": ["fastnet", "bredbånd", "telia", "tdc", "hiper", "yousee", "YouSee","oister", "cbb mobil", "telefon"],
    "Dining Out": ["restaurant", "cafe", "just eat", "wolt", "mcdonalds", "burger king", "pizzeria"
                    ,"SIDECAR", "PIZZA OTTO", "REFFEN", "JAGGER", "RizRaz", "WOK", "UNION KITCHEN"
                    ,"MobilePay Chantal", "MobilePay Florin", "MobilePay Ana Caroli", "MobilePay Desiree"
                    ,"MobilePay Carlos"
                    ,"MAD OG KAFFE", 'TABERNA', "RTE.", "CASA", "Burgermeister", "RINCON", "CIRKUS APS"
                    ,"FIVE GUYS", "BURGER", "BODEGAS", "SUSHI", "FOOD", "ISMAGERIET", "THAI KACHA"
                    ,"7-ELEVEN", "MAGDALENA", "SHAKE"],
    "Drinks": ["NIGHTPAY", "PROUD MARY CPH", "Sorte Firkant", "IRISH PUB", "ANARKOLI", "BAR", "BLUME"
                ,"LAVAPI", "STELLA POLARIS", "MIKKELLER", "CERVECERIA", "THE LIVING ROOM"
                ,"Dimitrios", "Christos", "MobilePay Ninci"],
    "Subscriptions": ["netflix", "spotify", "hbo", "disney+", "apple music", "storytel", "mofibo"
                    , "tv2 play", "viaplay", "avis", "blad"],
    "Healthcare": ["apotek", "læge", "tandlæge", "sygehus", "optiker", "fysioterapeut"],
    "Transfers": ["overførsel", "transfer", "egen konto", "mobilepay overførsel", "Overført", "Udenl. overf."
                    ,"MobilePay Beatriz"], 
    "Cash Withdrawal": ["hævning", "atm", "kontant", "bankautomat"],
    "Entertainment": ["biograf", "kino", "koncert", "teater", "museum", "tivoli", "zoo", "Instant Gaming"
                        ,"BILLETLUGEN.DK", "BLS*MYHERITAGE", "GOOGLE", "Nintendo"],
    "Gifts/Charity": ["gave", "donation", "indsamling", "røde kors"],
    "Financial/Fees": ["gebyr", "renteudgift", "bank fee", "finance charge", "Nordea-min"],
    "Education": ["kursus", "uddannelse", "skole", "universitet"],
    "Personal Care": ["frisør", "kosmetolog", "barber", "PELUQUEROS", "PELUQUERIA"],
    "Other Income": ["tilbagebetaling", "refund", "renteindtægt"], 
    "Bank Interest": ["Renter"],
    "Rent Flat": ["Danielle Benamour", "Domus Apartments DK"],
    "Deposit Flat": ["Deposit"],
    "Broker investments": ["xtb.com"],
    "Revolut transfers": ["REVOLUT"],
    "Tax payments": ["Skat"],
    # Add "Uncategorized" as a fallback if needed, or handle it in the function
}
# It might be better to load CATEGORY_RULES from a config file (JSON/YAML)
# For example, from config/categories_keywords.json

def categorize_transaction_row(row_description, rules):
    """
    Categorizes a single transaction description based on rules.
    Returns the category name or "Uncategorized" if no match.
    """
    if pd.isna(row_description):
        return "Uncategorized"
    
    description_lower = str(row_description).lower()

    for category, keywords in rules.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            # Option 1: match if description_lower contains 'kw_lower' preceded by a word‐boundary
            pattern = r"\b" + re.escape(kw_lower)
            if re.search(pattern, description_lower):
                return category

    return "Uncategorized"

def categorize_transactions_df(df, rules):
    """
    Adds a 'Category' column to the DataFrame by applying categorization rules.
    df must contain a 'Description' column.
    """
    if 'Description' not in df.columns:
        raise ValueError("DataFrame must contain a 'Description' column for categorization.")
    
    if 'Category' not in df.columns:
        df['Category'] = "Uncategorized"

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