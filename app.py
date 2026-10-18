from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "superstore_sales.csv"

REGION_CN = {
    "Central": "中部",
    "East": "东部",
    "South": "南部",
    "West": "西部",
}
CATEGORY_CN = {
    "Furniture": "家具",
    "Office Supplies": "办公用品",
    "Technology": "科技产品",
}
SUBCATEGORY_CN = {
    "Accessories": "配件",
    "Appliances": "电器",
    "Art": "美术用品",
    "Binders": "活页夹",
    "Bookcases": "书柜",
    "Chairs": "椅子",
    "Copiers": "复印机",
    "Envelopes": "信封",
    "Fasteners": "紧固件",
    "Furnishings": "家居用品",
    "Labels": "标签",
    "Machines": "机器设备",
    "Paper": "纸张",
    "Phones": "电话设备",
    "Storage": "收纳用品",
    "Supplies": "日常用品",
    "Tables": "桌子",
}

st.set_page_config(
    page_title="北辰分析｜销售脉搏",
    page_icon="📈",
    layout="wide",
)


@st.cache_data
def load_data() -> pd.DataFrame:
    data = pd.read_csv(DATA_PATH)
    data["Order Date"] = pd.to_datetime(data["Order Date"], dayfirst=True)
    data["Ship Date"] = pd.to_datetime(data["Ship Date"], dayfirst=True)
    data["Delivery Days"] = (data["Ship Date"] - data["Order Date"]).dt.days
    data["Month"] = data["Order Date"].dt.to_period("M").dt.to_timestamp()
    data["Region"] = data["Region"].replace(REGION_CN)
    data["Category"] = data["Category"].replace(CATEGORY_CN)
    data["Sub-Category"] = data["Sub-Category"].replace(SUBCATEGORY_CN)
    return data


df = load_data()

st.title("北辰分析｜销售脉搏")
st.caption(
    "帮助区域销售经理判断下周销售复盘应重点关注哪里。"
)

with st.sidebar:
    st.header("筛选条件")
    region_options = sorted(df["Region"].dropna().unique())
    selected_regions = st.multiselect(
        "区域", region_options, default=region_options
    )
    category_options = sorted(df["Category"].dropna().unique())
    selected_categories = st.multiselect(
        "产品类别", category_options, default=category_options
    )
    year_options = sorted(df["Order Date"].dt.year.unique())
    selected_years = st.multiselect("订单年份", year_options, default=year_options)

filtered = df[
    df["Region"].isin(selected_regions)
    & df["Category"].isin(selected_categories)
    & df["Order Date"].dt.year.isin(selected_years)
].copy()

if filtered.empty:
    st.warning("没有符合当前筛选条件的订单。")
    st.stop()

total_sales = filtered["Sales"].sum()
order_count = filtered["Order ID"].nunique()
median_delivery = filtered["Delivery Days"].median()

metric_cols = st.columns(3)
metric_cols[0].metric("销售额", f"${total_sales:,.0f}")
metric_cols[1].metric("订单数", f"{order_count:,}")
metric_cols[2].metric("配送时间中位数", f"{median_delivery:.0f} 天")

monthly = (
    filtered.groupby("Month", as_index=False)
    .agg(Sales=("Sales", "sum"), Orders=("Order ID", "nunique"))
    .sort_values("Month")
)
monthly["月份"] = monthly["Month"].dt.strftime("%Y-%m")
trend = px.line(
    monthly,
    x="月份",
    y="Sales",
    markers=True,
    title="月度销售额趋势",
    labels={"Sales": "销售额（美元）", "月份": "订单月份"},
    color_discrete_sequence=["#28527A"],
)
trend.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(trend, width="stretch")

breakdown = (
    filtered.groupby(["Region", "Category"], as_index=False)["Sales"]
    .sum()
    .sort_values("Sales", ascending=False)
)
bars = px.bar(
    breakdown,
    x="Region",
    y="Sales",
    color="Category",
    barmode="group",
    title="各区域与产品类别的销售额",
    labels={"Sales": "销售额（美元）", "Region": "区域", "Category": "产品类别"},
    color_discrete_sequence=["#28527A", "#E07A5F", "#81B29A"],
)
bars.update_layout(margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(bars, width="stretch")

detail = (
    filtered.groupby("Sub-Category", as_index=False)
    .agg(Sales=("Sales", "sum"), Orders=("Order ID", "nunique"))
    .sort_values("Sales", ascending=False)
    .head(10)
)
detail["Sales"] = detail["Sales"].map(lambda value: f"${value:,.0f}")
detail = detail.rename(columns={"Sub-Category": "产品子类别", "Sales": "销售额", "Orders": "订单数"})
st.subheader("销售额最高的产品子类别")
st.dataframe(detail, width="stretch", hide_index=True)

period_start = df["Order Date"].min().strftime("%Y 年 %m 月")
period_end = df["Order Date"].max().strftime("%Y 年 %m 月")
st.caption(
    f"数据范围：{period_start}–{period_end}，来源为 Kaggle 固定快照。"
    "实际生产环境建议每晚更新数据，区域销售经理每周一进行复盘。"
)
st.caption(
    "说明：销售额仅表示收入，不包含产品成本、退货或利润，不能直接解释为盈利能力。"
)
