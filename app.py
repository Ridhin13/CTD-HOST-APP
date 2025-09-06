def format_money(val):
    return f"Rs. {val:,.2f}"

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
                    return f"UnitCost for MasterItemNo {mi}: {format_money(row['UnitCost'].mean())}"
                if "qty" in q or "quantity" in q:
                    total_qty = row['QtyShipped'].sum()
                    uoms = row['UOM'].unique()
                    uom_text = ", ".join(uoms)
                    return f"Total QtyShipped for MasterItemNo {mi}: {total_qty:,.2f} {uom_text}"
                if "cost" in q or "totalcost" in q or "spend" in q:
                    return f"TotalCost for MasterItemNo {mi}: {format_money(row['TotalCost'].sum())}"
                return row.to_markdown(index=False)
            return f"No record found for MasterItemNo {mi}."

    # Conditional Queries (> or <)
    if ">" in q or "<" in q or "greater" in q or "less" in q:
        for k, v in cols.items():
            if k in q:
                nums = [float(s) for s in re.findall(r"\d+\.?\d*", q)]
                if nums:
                    threshold = nums[0]
                    if ">" in q or "greater" in q or "more" in q:
                        res = sub[sub[v] > threshold].head(10)
                    elif "<" in q or "less" in q or "below" in q:
                        res = sub[sub[v] < threshold].head(10)
                    else:
                        res = sub[sub[v] == threshold].head(10)
                    if res.empty:
                        return f"No records found with {v} condition."
                    return res.to_markdown(index=False)

    # Count Queries
    if "number" in q and ("total cost" in q or "cost" in q or "qty" in q or "quantity" in q):
        for k, v in cols.items():
            if k in q:
                nums = [float(s) for s in re.findall(r"\d+\.?\d*", q)]
                if nums:
                    threshold = nums[0]
                    if "greater" in q or "more" in q or ">" in q:
                        count = sub[sub[v] > threshold].shape[0]
                    elif "less" in q or "<" in q:
                        count = sub[sub[v] < threshold].shape[0]
                    else:
                        count = sub[sub[v] == threshold].shape[0]
                    return f"Number of items with {v} condition: {count}"

    # Aggregations
    if "total" in q and "qty" in q:
        return f"Grand total QtyShipped: {sub['QtyShipped'].sum():,.2f}"
    if "total cost" in q or "spend" in q:
        return f"Grand total cost: {format_money(sub['TotalCost'].sum())}"
    if "average" in q and "unitcost" in q:
        avg = sub.groupby("MasterItemNo")["UnitCost"].mean().mean()
        return f"Average UnitCost across items: {format_money(avg)}"

    # Highest / Lowest
    if "highest" in q or "most" in q or "max" in q:
        for k, v in cols.items():
            if k in q:
                row = sub.loc[sub[v].idxmax()]
                return f"Highest {v}: MasterItemNo {int(row['MasterItemNo'])}, {v}={format_money(row[v])}"
    if "lowest" in q or "min" in q:
        for k, v in cols.items():
            if k in q:
                row = sub.loc[sub[v].idxmin()]
                return f"Lowest {v}: MasterItemNo {int(row['MasterItemNo'])}, {v}={format_money(row[v])}"

    # Top N items
    if "top" in q:
        k = 5
        nums = [int(s) for s in re.findall(r"\d+", q)]
        if nums:
            k = nums[0]
        for kword in ["cost", "expensive", "totalcost", "spend"]:
            if kword in q:
                res = sub.groupby("MasterItemNo", as_index=False)["TotalCost"].sum().sort_values("TotalCost", ascending=False).head(k)
                res["TotalCost"] = res["TotalCost"].apply(format_money)
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
            rows["TotalCost"] = rows["TotalCost"].apply(format_money)
            return rows.to_markdown(index=False)

    return ("I didn’t fully get that 🤔. Try queries like:\n"
            "- 'UnitCost for ID 102'\n"
            "- 'TotalCost of MasterItemNo 555'\n"
            "- 'Show items where QtyShipped > 50'\n"
            "- 'Which MasterItemNo has highest TotalCost?'\n"
            "- 'Top 5 items by cost'\n"
            "- 'Compare item 100 vs 200'\n"
            "- 'How is TotalCost calculated?'")
