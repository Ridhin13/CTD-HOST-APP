import streamlit as st
import pandas as pd
import re

# Load your data
@st.cache_data
def load_data():
    return pd.read_csv("your_file.csv")  # Replace with your actual CSV file path

df = load_data()

# Format money
def format_money(val):
    return f"Rs. {val:,.2f}"

# Main chatbot logic
def answer(query):
    q = query.lower().strip()
    
    # IDs or MasterItemNo mentioned in query
    ids = [int(s) for s in re.findall(r"\d+", query)]
    
    # Quantity question
    if "qty" in q or "quantity" in q or "shipped" in q:
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                total_qty = row['QtyShipped'].sum()
                uoms = row['UOM'].unique()
                uom_text = ", ".join(uoms)
                return f"📦 **Quantity Details**\nMasterItemNo **{mi}** has shipped a total of **{total_qty:,.2f} {uom_text}**."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        else:
            return f"📦 Please specify the MasterItemNo for which you want the quantity shipped."

    # Unit cost question
    if "unitcost" in q or "price" in q or "rate" in q:
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                cost = row['UnitCost'].mean()
                return f"💰 **Pricing Info**\nThe unit cost for MasterItemNo **{mi}** is **{format_money(cost)}** per item."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        else:
            return f"💰 Please specify the MasterItemNo for which you want the unit cost."

    # Total cost question
    if "totalcost" in q or "cost" in q or "spend" in q:
        if "greater than" in q or "above" in q:
            # e.g., total cost greater than 100000
            amounts = [float(s.replace(',', '')) for s in re.findall(r"\d[\d,]*\.?\d*", q)]
            if amounts:
                threshold = amounts[0]
                filtered = df[df["TotalCost"] > threshold]
                count = len(filtered)
                return f"📊 **Filtered Results**\n✅ There are **{count} items** where the total cost exceeds **{format_money(threshold)}**."
            else:
                return "❌ Please mention the amount for filtering total cost."
        
        if ids:
            mi = ids[0]
            row = df[df["MasterItemNo"] == mi]
            if not row.empty:
                total = row['TotalCost'].sum()
                return f"💰 **Total Cost Summary**\nFor MasterItemNo **{mi}**, the total cost amounts to **{format_money(total)}**."
            else:
                return f"❌ No record found for MasterItemNo **{mi}**."
        else:
            return "💰 Please specify the MasterItemNo for which you want the total cost."

    # Highest cost query
    if "highest" in q or "most expensive" in q or "top" in q:
        top = df.sort_values(by="TotalCost", ascending=False).head(5)
        table = "| MasterItemNo | TotalCost |\n|--------------|------------|\n"
        for _, row in top.iterrows():
            table += f"| {row['MasterItemNo']} | {format_money(row['TotalCost'])} |\n"
        return f"📊 **Top 5 Most Expensive Items**\n{table}"

    # Calculation explanation
    if "how is totalcost" in q or "formula" in q or "calculate" in q:
        return "🔍 **Calculation Guide**\nTotalCost is calculated as:\n\n`TotalCost = QtyShipped × UnitCost`"

    # Comparison query example
    if "compare" in q and len(ids) >= 2:
        mi1, mi2 = ids[0], ids[1]
        row1 = df[df["MasterItemNo"] == mi1]
        row2 = df[df["MasterItemNo"] == mi2]
        if row1.empty or row2.empty:
            return "❌ One or both MasterItemNos not found."
        
        cost1 = row1['TotalCost'].sum()
        cost2 = row2['TotalCost'].sum()
        higher = mi1 if cost1 > cost2 else mi2
        return f"📊 **Comparison**\nMasterItemNo **{mi1}** has total cost {format_money(cost1)}.\nMasterItemNo **{mi2}** has total cost {format_money(cost2)}.\n✅ MasterItemNo **{higher}** has the higher total cost."

    # Default fallback
    return "❌ Sorry, I couldn't understand your query. Please ask with specific MasterItemNo or mention quantity/cost."

# Streamlit UI
st.set_page_config(page_title="Material Forecasting Chatbot", layout="wide")
st.title("📦 CTD Material Forecasting & Procurement Assistant")

query = st.text_input("Ask me about items, quantities, and costs...")

if query:
    result = answer(query)
    st.markdown(result, unsafe_allow_html=True)

st.markdown("---")
st.caption("You can ask questions like:\n• 'QtyShipped for MasterItemNo 60830'\n• 'Total cost greater than 100000'\n• 'Compare item 123 and 456'\n• 'How is total cost calculated?'")
