# app.py

import streamlit as st
import pandas as pd
import re
import difflib

# ---------------------------
# Load predictions safely
# ---------------------------
@st.cache_data
def load_predictions(path="submission_with_cost.csv"):
    try:
        df = pd.read_csv(path)
        # Ensure numeric types
        for c in ["QtyShipped", "UnitCost", "TotalCost"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception as e:
        st.error(f"⚠️ Could not load predictions file: {e}")
        return pd.DataFrame()

sub = load_predictions()

# ---------------------------
# Streamlit Layout
# ---------------------------
st.set_page_config(page_title="CTD Material Forecasting", layout="wide")
st.title("🏗️ Material Forecasting & Procurement Assistant")

if sub.empty:
    st.warning("No data loaded. Please upload `submission_with_cost.csv` to your repo.")
    st.stop()

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", f"{len(sub):,}")
col2.metric("Unique Items", f"{sub['MasterItemNo'].nunique():,}")
col3.metric("Total Qty", f"{sub['QtyShipped'].sum():,.2f}")
col4.metric("Total Cost (INR)", f"{sub['TotalCost'].sum():,.2f}")

st.divider()

# Filters
with st.sidebar:
    st.header("🔎 Filters")
    mi = st.text_input("MasterItemNo (optional, numeric)")
    id_filter = st.text_input("Prediction ID (optional, numeric)")

df_view = sub.copy()
if mi.isnumeric():
    df_view = df_view[df_view["MasterItemNo"] == int(mi)]
if id_filter.isnumeric():
    df_view = df_view[df_view["id"] == int(id_filter)]

st.subheader("📊 Predictions")
st.dataframe(df_view, use_container_width=True, height=450)

# Download button
st.download_button(
    "⬇️ Download predictions (CSV)",
    data=sub.to_csv(index=False).encode("utf-8"),
    file_name="submission_with_cost.csv",
    mime="text/csv"
)

# ---------------------------
# Chatbot
# ---------------------------
st.divider()
st.subheader("💬 Chatbot Assistant")

def answer(query: str) -> str:
    q = query.lower().strip()
    cols = {"unitcost": "UnitCost", "price": "UnitCost", "price per unit": "UnitCost",
            "qtyshipped": "QtyShipped", "quantity": "QtyShipped", "qty": "QtyShipped",
            "totalcost": "TotalCost", "cost": "TotalCost", "spend": "TotalCost"}
    
    # Explanatory Queries
    if "how" in q and "totalcost" in q:
        return "💡 TotalCost is calculated as: `QtyShipped × UnitCost`."

    # Direct Lookup by ID
    if "id" in q:
        ids = [int(s) for s in re.findall(r"\d+", q)]
        if ids:
            id_val = ids[0]
            row = sub[sub["id"] == id_val]
            if not row.empty:
                return row.to_markdown(index=False)
            return f"No record found for ID {id_val}."

    # Direct Lookup by MasterItemNo
    if "masteritemno" in q or "item" in q:
        ids = [int(s) for s in re.findall(r"\d+", q)]
        if ids:
            mi = ids[0]
            row = sub[sub["MasterItemNo"] == mi]
            if not row.empty:
                if "unitcost" in q or "price" in q:
                    return f"UnitCost for MasterItemNo {mi}: {row['UnitCost'].mean():,.2f}"
                if "qty" in q or "quantity" in q:
                    return f"Total QtyShipped for MasterItemNo {mi}: {row['QtyShipped'].sum():,.2f}"
                if "cost" in q or "totalcost" in q or "spend" in q:
                    return f"TotalCost for MasterItemNo {mi}: {row['TotalCost'].sum():,.2f}"
                return row.to_markdown(index=False)
            return f"No record found for MasterItemNo {mi}."

    # Conditional Queries (> or <)
    if ">" in q or "<" in q:
        for k, v in cols.items():
            if k in q:
                try:
                    threshold = float(re.findall(r"\d+", q)[0])
                    if ">" in q:
                        res = sub[sub[v] > threshold].head(10)
                    else:
                        res = sub[sub[v] < threshold].head(10)
                    if res.empty:
                        return f"No records found with {v} condition."
                    return res.to_markdown(index=False)
                except:
                    pass

    # Aggregations
    if "total" in q and "qty" in q:
        return f"Grand total QtyShipped: {sub['QtyShipped'].sum():,.2f}"
    if "total cost" in q:
        return f"Grand total cost: {sub['TotalCost'].sum():,.2f}"
    if "average" in q and "unitcost" in q:
        avg = sub.groupby("MasterItemNo")["UnitCost"].mean().mean()
        return f"Average UnitCost across items: {avg:,.2f}"

    # Highest / Lowest
    if "highest" in q or "most" in q or "max" in q:
        for k, v in cols.items():
            if k in q:
                row = sub.loc[sub[v].idxmax()]
                return f"Highest {v}: MasterItemNo {int(row['MasterItemNo'])}, {v}={row[v]:,.2f}"
    if "lowest" in q or "min" in q:
        for k, v in cols.items():
            if k in q:
                row = sub.loc[sub[v].idxmin()]
                return f"Lowest {v}: MasterItemNo {int(row['MasterItemNo'])}, {v}={row[v]:,.2f}"

    # Top N items
    if "top" in q:
        k = 5
        nums = [int(s) for s in re.findall(r"\d+", q)]
        if nums:
            k = nums[0]
        for kword in ["cost", "expensive", "totalcost", "spend"]:
            if kword in q:
                res = sub.groupby("MasterItemNo", as_index=False)["TotalCost"].sum().sort_values("TotalCost", ascending=False).head(k)
                return res.to_markdown(index=False)
        for kword in ["qty", "quantity"]:
            if kword in q:
                res = sub.groupby("MasterItemNo", as_index=False)["QtyShipped"].sum().sort_values("QtyShipped", ascending=False).head(k)
                return res.to_markdown(index=False)

    # Comparisons
    if "compare" in q:
        nums = [int(s) for s in re.findall(r"\d+", q)]
        if len(nums) >= 2:
            a, b = nums[:2]
            rows = sub[sub["MasterItemNo"].isin([a, b])].groupby("MasterItemNo")[["QtyShipped", "TotalCost"]].sum().reset_index()
            return rows.to_markdown(index=False)

    return ("I didn’t fully get that 🤔. Try queries like:\n"
            "- 'UnitCost for ID 102'\n"
            "- 'TotalCost of MasterItemNo 555'\n"
            "- 'Show items where QtyShipped > 50'\n"
            "- 'Which MasterItemNo has highest TotalCost?'\n"
            "- 'Top 5 items by cost'\n"
            "- 'Compare item 100 vs 200'\n"
            "- 'How is TotalCost calculated?'")

# Chat UI
if "history" not in st.session_state:
    st.session_state.history = []

user_q = st.chat_input("Ask about costs, quantities, top items...")
if user_q:
    st.session_state.history.append(("user", user_q))
    st.session_state.history.append(("assistant", answer(user_q)))

for role, msg in st.session_state.history:
    st.chat_message(role).write(msg)
