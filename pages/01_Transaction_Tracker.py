# pages/01_💰_Transaction_Tracker.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Transaction Tracker", layout="wide")

st.title("💰 Transaction Tracker")
st.write("Upload your bank statements and categorize transactions here.")

# Placeholder for file uploader
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.write("### Uploaded Data Preview:")
        st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error reading CSV: {e}")