import streamlit as st
import pandas as pd

st.set_page_config(page_title="CTD Material Forecasting", layout="wide")

@st.cache_data
def load_predictions(path="submission_with_cost.csv"):
    df = pd.read_csv(path)
    for c in ["QtyShipped", "UnitCost", "TotalCost"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

sub = load_predictions()

st.title("🏗️ Material Forecasting & Procurement Assistant")

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
    id_filter = st.text_input("Prediction id (optional, numeric)")

df_view = sub.copy()
if mi.isnumeric():
    df_view = df_view[df_view["MasterItemNo"] == int(mi)]
if id_filter.isnumeric():
    df_view = df_view[df_view["id"] == int(id_filter)]

st.subheader("📊 Predictions")
st.dataframe(df_view, use_container_width=True, height=450)

# Download
st.download_button(
    "⬇️ Download predictions (CSV)",
    data=sub.to_csv(index=False).encode("utf-8"),
    file_name="submission_with_cost.csv",
    mime="text/csv"
)

st.divider()
st.subheader("💬 Chatbot")

def answer(query: str) -> str:
    q = query.lower()

    # totals
    if "total cost" in q:
        return f"Total cost for all predicted materials is {sub['TotalCost'].sum():,.2f} INR."
    if "total quantity" in q or "total qty" in q:
        return f"Total predicted quantity across all items is {sub['QtyShipped'].sum():,.2f}."

    # per item
    nums = [int(tok) for tok in q.replace(",", " ").split() if tok.isnumeric()]
    if nums:
        item = nums[0]
        by_item = sub[sub["MasterItemNo"] == item]
        if "cost" in q and not by_item.empty:
            return f"Estimated cost for MasterItemNo {item}: {by_item['TotalCost'].sum():,.2f} INR."
        if ("quantity" in q or "qty" in q) and not by_item.empty:
            return f"Predicted quantity for MasterItemNo {item}: {by_item['QtyShipped'].sum():,.2f}."
        if not by_item.empty:
            return (f"MasterItemNo {item}: Qty={by_item['QtyShipped'].sum():,.2f}, "
                    f"UnitCost≈{by_item['UnitCost'].median():,.2f}, "
                    f"TotalCost={by_item['TotalCost'].sum():,.2f} INR.")
        return f"I couldn't find MasterItemNo {item} in predictions."

    if "top" in q and ("expensive" in q or "cost" in q):
        k = 5
        for tok in q.split():
            if tok.isnumeric():
                k = int(tok); break
        topk = (sub.groupby("MasterItemNo", as_index=False)["TotalCost"]
                  .sum().sort_values("TotalCost", ascending=False).head(k))
        lines = [f"Top {len(topk)} by total cost:"]
        for _, r in topk.iterrows():
            lines.append(f"- {int(r['MasterItemNo'])}: {r['TotalCost']:,.2f} INR")
        return "\n".join(lines)

    return ("Try:\n"
            "- 'What is the total cost?'\n"
            "- 'Total quantity'\n"
            "- 'Cost for MasterItemNo 361'\n"
            "- 'Quantity for MasterItemNo 361'\n"
            "- 'Top 5 expensive items'")

if "history" not in st.session_state:
    st.session_state.history = []

user_q = st.chat_input("Ask about costs, quantities, top items...")
if user_q:
    st.session_state.history.append(("user", user_q))
    st.session_state.history.append(("assistant", answer(user_q)))

for role, msg in st.session_state.history:
    st.chat_message(role).write(msg)
