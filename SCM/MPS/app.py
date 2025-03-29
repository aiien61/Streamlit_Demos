import streamlit as st
import urllib.request
import polars as pl
import numpy as np
import os
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from typing import List

# Define font path
font_path: str = "/tmp/NotoSansCJK-Regular.otf"

# Download font if it doesn't exist
if not os.path.exists(font_path):
    font_url:str = "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/NotoSansCJK-Regular.otf"
    try:
        urllib.request.urlretrieve(font_url, font_path)
    except Exception as e:
        print("Font download failed, using default font.", e)
        font_path = None  # Mark font as unavailable

# Try loading the font
if font_path and os.path.exists(font_path):
    font_prop = fm.FontProperties(fname=font_path, size=12)  # Define font properties
    plt.rcParams["font.family"] = font_prop.get_name()  # Apply globally
else:
    font_prop = None  # Avoid using an undefined variable

st.title('主生產排程 (MPS) 系統')
st.markdown("#### 平準化生產 (Leveling Production Strategy) ")

# How many periods
PERIOD_INPUT: str = "請輸入計劃週期數（例如：4 週）"
num_periods: int = st.number_input(PERIOD_INPUT, min_value=1, value=12)

DEMAND_INPUT: str = "請輸入總需求數量"
total_demand: int = st.number_input(DEMAND_INPUT, min_value=1, value=120)

# Stocktaking
st.subheader("請輸入期初存貨量")
STOCK_INPUT: str = "請輸入期初存貨量"
init_stock: int = st.number_input(STOCK_INPUT, min_value=0, value=20)
scheduled_stocks: List[int] = []

# Initial demand
initial_demand: List[int] = [int(total_demand / num_periods)] * num_periods

# Set max number of columns (each row has only 8 periods at most in the table)
MAX_COLUMNS: int = 8

# How many tables to record demand stats
num_tables: int = (num_periods + MAX_COLUMNS - 1) // MAX_COLUMNS

# Divide a series of stats into separate tables
st.subheader("請輸入每週需求量")
sub_tables = []
for i in range(num_tables):
    start_index: int = i * MAX_COLUMNS
    end_index: int = min(start_index + MAX_COLUMNS, num_periods)

    # Fetch corresponding demand stats
    row_data = initial_demand[start_index: end_index]

    # The number of columns equals to periods when only 1 table
    # The number of columns will be fixed to be fixed number when two or more table
    if num_tables == 1:
        column_names: List[str] = [f"第{j+1}週" for j in range(start_index, end_index)]
    else:
        column_names = [f"第{j+1}週" for j in range(start_index, end_index)]
        empty_columns: int = MAX_COLUMNS - (end_index - start_index)
        column_names += [f"N{j+1}" for j in range(empty_columns)]
        row_data += [None] * empty_columns

    # Create Polars DataFrame
    df = pl.DataFrame([row_data], schema=column_names, orient="row")

    # st.data_editor allows displayed table to be editable
    # convert to pandas to make it handy
    edited_df = st.data_editor(df.to_pandas(), num_rows="fixed", hide_index=True)

    # Save it to aggregate table
    sub_tables.append(pl.from_pandas(edited_df))

# Combine all teh sub tables
full_table = pl.concat(sub_tables, how="horizontal")

# Use edited demand stats
demand_values: List[int] = []
for row in full_table.to_pandas().values.tolist():
    for value in row:
        if value is not None and not np.isnan(value):
            demand_values.append(value)

# Calculate leveling production planning
avg_production: int = int(np.ceil(sum(demand_values) / num_periods)) if len(demand_values) > 0 else 0
production_plan: int = [avg_production] * num_periods

pre_stock: int = init_stock
for i in range(num_periods):
    stock = production_plan[i] + pre_stock - demand_values[i]
    scheduled_stocks.append(stock)
    pre_stock = stock

# Convert to vertical dataframe
df = pl.DataFrame({
    "週期": list(range(1, num_periods + 1)),
    "需求量": demand_values,
    "庫存量": scheduled_stocks,
    "生產量": production_plan
})

# Display the table
st.subheader("生產排程結果")
st.dataframe(df)

# Plotting
st.subheader("需求與生產計劃圖表")

fig, ax = plt.subplots()
ax.plot(df['週期'], df['需求量'], 'ro-', label='Demands')
ax.plot(df['週期'], df['生產量'], 'bs--', label='MPS')
ax.plot(df['週期'], df['庫存量'], 'g^-', label='Stocks')

ax.set_xlabel('Weeks', fontproperties=font_prop)
ax.set_ylabel('Qty', fontproperties=font_prop, rotation=0, labelpad=20)
ax.set_title("Demands / Stocks / MPS", fontproperties=font_prop)
legend = ax.legend(prop=font_prop)
st.pyplot(fig)
