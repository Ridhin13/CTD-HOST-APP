import streamlit as st
import pandas as pd
import numpy as np
import re

# Load data from CSV
@st.cache_data
def load_data():
    return pd.read_csv("submission_with_cost.csv")

df = load_data()

st.title("📦 CTD Material Forecasting & Procurement Assistant")

# Function to format currency
def format_money(val):
    return f"Rs. {val:,.2f}"

# Chatbot logic
def answer(query: str) -> str:
    query = query.lower()
    
    # Search for MasterItemNo in the query
    ids = [int(s) for s in re.findall(r"\d+", query)]
    
    if "qty" in query or "quantity" in query:
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                qty = row['QtyShipped'].sum()
                uoms = row['UOM'].unique()
                uom_text = ", ".join(uoms)
                return f"📦 **Quantity Details**\nMasterItemNo **{mi}** has shipped a total of **{qty:,.2f} {uom_text}**."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        return "❌ Please specify a valid MasterItemNo."

    if "unitcost" in query or "price per unit" in query or "price" in query:
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                cost = row['UnitCost'].mean()
                return f"💰 **Pricing Info**\nThe unit cost for MasterItemNo **{mi}** is **{format_money(cost)}** per item."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        return "❌ Please specify a valid MasterItemNo."

    if "totalcost" in query or "cost" in query or "spend" in query:
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                total = row['TotalCost'].sum()
                return f"💰 **Total Cost Summary**\nFor MasterItemNo **{mi}**, the total cost amounts to **{format_money(total)}**."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        elif "greater than" in query or "more than" in query:
            nums = [float(s.replace(",", "")) for s in re.findall(r"\d+\.?\d*", query)]
            if nums:
                threshold = nums[0]
                count = df[df["TotalCost"] > threshold].shape[0]
                return f"📊 **Filtered Results**\n✅ There are **{count} items** where the total cost exceeds **{format_money(threshold)}**."
            else:
                return "❌ Please specify a valid cost threshold."
        else:
            return "❌ Please specify a valid MasterItemNo or condition."

    if "how is totalcost calculated" in query or "formula" in query:
        return "🔍 **Calculation Guide**\nTotalCost is calculated as:\n`TotalCost = QtyShipped × UnitCost`"

    return "❌ Sorry, I didn't understand your query. Please try again with more details."

# User input
user_input = st.text_input("Ask me about your materials:")

if user_input:
    response = answer(user_input)
    st.markdown(response)
