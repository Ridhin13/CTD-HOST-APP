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
    st.warning("No data loaded. Please upload submission_with_cost.csv to your repo.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", f"{len(sub):,}")
col2.metric("Unique Items", f"{sub['MasterItemNo'].nunique():,}")
col3.metric("Total Qty", f"{sub['QtyShipped'].sum():,.2f}")
col4.metric("Total Cost (INR)", f"Rs. {sub['TotalCost'].sum():,.2f}")

st.divider()

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

try:
    from tabulate import tabulate
    TABULATE_AVAILABLE = True
except ImportError:
    TABULATE_AVAILABLE = False

def df_to_string(df):
    if TABULATE_AVAILABLE:
        return tabulate(df, headers='keys', tablefmt='pipe', showindex=False)
    else:
        return df.to_string(index=False)

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

    # 1. Handle conditional queries first
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
                return "⚠️ Invalid operator."
            if res.empty:
                return f"No records found where {column} {operator} {threshold}."
            return df_to_string(res.head(10))

    # 2. Handle direct lookup by ID
    if "id" in q and "where" not in q:
        ids = [int(s) for s in re.findall(r"\d+", q)]
        if ids:
            id_val = ids[0]
            row = sub[sub["id"] == id_val]
            if not row.empty:
                return df_to_string(row)
            return f"No record found for ID {id_val}."

    # 3. Handle lookup by MasterItemNo
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
        else:
            return "⚠️ Please specify a valid MasterItemNo."

    # 4. Aggregations
    if "total" in q and ("qty" in q or "quantity" in q):
        total_qty = sub["QtyShipped"].sum()
        uom = sub["UOM"].mode().values[0] if not sub["UOM"].mode().empty else ""
        return f"Grand total QtyShipped: {total_qty:,.2f} {uom}"
    if "total cost" in q or "totalcost" in q or "spend" in q:
        return f"Grand total cost: Rs. {sub['TotalCost'].sum():,.2f}"
    if "average" in q and ("unitcost" in q or "price" in q):
        avg = sub["UnitCost"].mean()
        return f"Average UnitCost: Rs. {avg:,.2f}"

    # 5. Highest / Lowest
    if "highest" in q or "max" in q or "most" in q:
        for word in cols.keys():
            if word in q:
                column = cols[word]
                row = sub.loc[sub[column].idxmax()]
                return f"Highest {column}: MasterItemNo {int(row['MasterItemNo'])}, {column}=Rs. {row[column]:,.2f}"
    if "lowest" in q or "min" in q:
        for word in cols.keys():
            if word in q:
                column = cols[word]
                row = sub.loc[sub[column].idxmin()]
                return f"Lowest {column}: MasterItemNo {int(row['MasterItemNo'])}, {column}=Rs. {row[column]:,.2f}"

    # 6. Top N items
    if "top" in q:
        nums = [int(s) for s in re.findall(r"\d+", q)]
        k = nums[0] if nums else 5
        if any(w in q for w in ["cost", "spend", "totalcost", "expensive"]):
            res = sub.groupby("MasterItemNo", as_index=False)["TotalCost"].sum().sort_values("TotalCost", ascending=False).head(k)
            return df_to_string(res)
        if any(w in q for w in ["qty", "quantity"]):
            res = sub.groupby("MasterItemNo", as_index=False)["QtyShipped"].sum().sort_values("QtyShipped", ascending=False).head(k)
            return df_to_string(res)

    # 7. Compare
    if "compare" in q:
        nums = [int(s) for s in re.findall(r"\d+", q)]
        if len(nums) >= 2:
            a, b = nums[:2]
            rows = sub[sub["MasterItemNo"].isin([a, b])]
            if rows.empty:
                return "No matching records found to compare."
            result = rows.groupby("MasterItemNo")[["QtyShipped", "TotalCost"]].sum().reset_index()
            result["TotalCost"] = result["TotalCost"].apply(lambda x: f"Rs. {x:,.2f}")
            return df_to_string(result)
        return "Please specify two MasterItemNo values to compare."

    # 8. Explanations
    if "how" in q and ("totalcost" in q or "total cost" in q):
        return "💡 TotalCost is calculated as: QtyShipped × UnitCost."

    # Fallback
    return (
        "🤖 I didn’t fully understand that. Here are example queries you can try:\n"
        "- 'UnitCost for ID 102'\n"
        "- 'TotalCost of MasterItemNo 555'\n"
        "- 'Total Qty shipped'\n"
        "- 'Top 5 items by cost'\n"
        "- 'Compare items 123 and 456'\n"
        "- 'TotalCost > 10000'\n"
        "- 'Explain how total cost is calculated'"
    )

# ---------------------------
# Chatbox Interface
# ---------------------------
if "history" not in st.session_state:
    st.session_state.history = []

user_q = st.chat_input("Ask about costs, quantities, top items...")

if user_q:
    st.session_state.history.append(("user", user_q))
    try:
        ans = answer(user_q)
    except Exception as e:
        ans = f"⚠️ An error occurred: {e}"
    st.session_state.history.append(("assistant", ans))

for role, msg in st.session_state.history:
    st.chat_message(role).write(msg)
