import streamlit as st
import pandas as pd
import difflib
import re

# Load data
sub = pd.read_excel("data.xlsx")

# Title
st.title("Chatbot Assistant")

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []

# Helper function to convert DataFrame to string with formatting
def df_to_string(df):
    if df.empty:
        return "No records found."
    else:
        df_display = df.copy()
        # Format currency columns
        if 'UnitCost' in df_display.columns:
            df_display['UnitCost'] = df_display['UnitCost'].apply(lambda x: f"Rs. {x:,.2f}")
        if 'TotalCost' in df_display.columns:
            df_display['TotalCost'] = df_display['TotalCost'].apply(lambda x: f"Rs. {x:,.2f}")
        # Format Qty with UOM if available
        if 'QtyShipped' in df_display.columns and 'UOM' in df_display.columns:
            df_display['QtyShipped'] = df_display.apply(lambda row: f"{row['QtyShipped']:.2f} {row['UOM']}", axis=1)
        return df_display.to_markdown(index=False)

# Main answer function
def answer(query: str) -> str:
    q = query.lower().strip()
    cols = {
        "unitcost": "UnitCost",
        "price": "UnitCost",
        "price per unit": "UnitCost",
        "qtyshipped": "QtyShipped",
        "quantity": "QtyShipped",
        "qty": "QtyShipped",
        "totalcost": "TotalCost",
        "total cost": "TotalCost",
        "cost": "TotalCost",
        "spend": "TotalCost"
    }

    def find_column(word):
        matches = difflib.get_close_matches(word, cols.keys(), n=1, cutoff=0.6)
        if matches:
            return cols[matches[0]]
        return None

    # ---------------------------
    # 1. CONDITIONAL FILTERS FIRST
    # ---------------------------
    condition_match = re.search(r"(totalcost|total cost|qtyshipped|quantity|qty|unitcost|price)[^\d<>]*([<>]=?)\s*(\d+\.?\d*)", q)
    if condition_match:
        col_word, operator, num_str = condition_match.groups()
        column = find_column(col_word)
        if column:
            threshold = float(num_str)
            if operator in [">", ">="]:
                res = sub[sub[column] >= threshold] if operator == ">=" else sub[sub[column] > threshold]
            elif operator in ["<", "<="]:
                res = sub[sub[column] <= threshold] if operator == "<=" else sub[sub[column] < threshold]
            else:
                return "Invalid operator in query."
            if res.empty:
                return f"No records found where {column} {operator} {threshold}."
            return df_to_string(res.head(10))

    # ---------------------------
    # 2. EXPLANATORY QUERIES
    # ---------------------------
    if "how" in q and ("totalcost" in q or "total cost" in q):
        return "💡 TotalCost is calculated as: QtyShipped × UnitCost."

    # ---------------------------
    # 3. DIRECT LOOKUP BY ID OR MasterItemNo
    # ---------------------------
    if "id" in q and "where" not in q:
        ids = [int(s) for s in re.findall(r"\d+", q)]
        if ids:
            id_val = ids[0]
            row = sub[sub["id"] == id_val]
            if not row.empty:
                return df_to_string(row)
            return f"No record found for ID {id_val}."

    if ("masteritemno" in q or "item" in q) and "where" not in q:
        ids = [int(s) for s in re.findall(r"\d+", q)]
        if ids:
            mi_val = ids[0]
            row = sub[sub["MasterItemNo"] == mi_val]
            if not row.empty:
                if "unitcost" in q or "price" in q:
                    return f"UnitCost for MasterItemNo {mi_val}: Rs. {row['UnitCost'].mean():,.2f}"
                if "qty" in q or "quantity" in q:
                    total_qty = row['QtyShipped'].sum()
                    uom = row['UOM'].mode().values[0] if not row['UOM'].mode().empty else ""
                    return f"Total QtyShipped for MasterItemNo {mi_val}: {total_qty:,.2f} {uom}"
                if "totalcost" in q or "cost" in q or "spend" in q:
                    return f"TotalCost for MasterItemNo {mi_val}: Rs. {row['TotalCost'].sum():,.2f}"
                return df_to_string(row)
            return f"No record found for MasterItemNo {mi_val}."

    # ---------------------------
    # 4. AGGREGATION QUERIES
    # ---------------------------
    if "number of items" in q and "totalcost" in q:
        match = re.search(r"totalcost[^\d]*([<>]=?)\s*(\d+\.?\d*)", q)
        if match:
            operator, value = match.groups()
            threshold = float(value)
            if operator in [">", ">="]:
                res = sub[sub["TotalCost"] >= threshold] if operator == ">=" else sub[sub["TotalCost"] > threshold]
            elif operator in ["<", "<="]:
                res = sub[sub["TotalCost"] <= threshold] if operator == "<=" else sub[sub["TotalCost"] < threshold]
            else:
                return "Invalid operator."
            count = len(res)
            return f"Number of items where TotalCost {operator} {threshold}: {count}"

    # ---------------------------
    # 5. SHOW ALL OR DEFAULT
    # ---------------------------
    if "show all" in q or "list all" in q:
        return df_to_string(sub.head(10))

    return "Sorry, I didn't understand your question."

# Streamlit interface
user_q = st.text_input("Enter your question here:")
if user_q:
    ans = answer(user_q)
    st.session_state.history.append(("user", user_q))
    st.session_state.history.append(("assistant", ans))

# Show history
for role, message in st.session_state.history:
    if role == "user":
        st.markdown(f"**You:** {message}")
    else:
        st.markdown(f"**Bot:** {message}")
