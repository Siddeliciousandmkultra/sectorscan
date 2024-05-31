import streamlit as st
import pandas as pd
import requests
import altair as alt

# Title
st.title("SectorScan")

@st.cache_data
def fetch_data(url):
  api_key = st.secrets["SECTORS_KEY"]

  headers = {
      "Authorization": api_key
  }

  response = requests.get(url, headers = headers)

  if response.status_code == 200:
      return response.json()
  else:
      # Handle error
      st.error("Error: Something went wrong. Please reload the app.")

# Get sectors data
url = "https://api.sectors.app/api/data/subsectors/"
sectors = fetch_data(url)
sectors.sort()

def format_option(option):
    return option.replace("-", " ").title() # change - to space and use title case

# Sectors filter component
options = st.multiselect(
    label="Filter Sectors",
    options=sectors,
    default=sectors[0:3], 
    format_func=format_option,
    max_selections=5
)

if len(options) == 0:
    st.warning("Please select at least one sector!")
else:
    # Market cap section
    df_mc_curr = pd.DataFrame()
    df_mc_hist = pd.DataFrame()
    df_mc_change = pd.DataFrame()

    for i in options:
        url = f"https://api.sectors.app/api/data/sector/report/{i}/?sections=market_cap"
        market_cap = fetch_data(url)

        mc_curr = pd.DataFrame({
            "Sector": market_cap["sub_sector"],
            "Total Market Cap": market_cap["market_cap"]["total_market_cap"]
        }, index=[0])
        df_mc_curr = pd.concat([df_mc_curr, mc_curr], ignore_index=True)

        mc_hist = pd.DataFrame()
        for i in ["prev_ttm_mcap", "current_ttm_mcap"]:
            df = pd.melt(pd.DataFrame(market_cap["market_cap"]["quarterly_market_cap"][i], index=["quarter"]), var_name="Quarter", value_name="Market Cap")
            df["Sector"] = market_cap["sub_sector"]
            df = df[["Sector", "Quarter", "Market Cap"]]
            mc_hist = pd.concat([mc_hist, df], ignore_index=True)
        df_mc_hist = pd.concat([df_mc_hist, mc_hist], ignore_index=True)

        mc_change = pd.melt(pd.DataFrame(market_cap["market_cap"]["mcap_summary"]["monthly_performance"], index=["date"]), var_name="Date", value_name="Market Cap Change")
        mc_change["Sector"] = market_cap["sub_sector"]
        mc_change = mc_change[["Sector", "Date", "Market Cap Change"]]
        df_mc_change = pd.concat([df_mc_change, mc_change], ignore_index=True)

    # Finalize df_mc_curr
    url = f"https://api.sectors.app/api/data/sector/report/{sectors[0]}/?sections=idx"
    idx = fetch_data(url)

    idx_mc = idx["idx"]["idx_cap"]

    df_idx_mc = pd.DataFrame({
            "Sector": "Others",
            "Total Market Cap": idx_mc - df_mc_curr["Total Market Cap"].sum()
    }, index=[0])
    df_mc_curr = pd.concat([df_mc_curr, df_idx_mc], ignore_index=True)
    df_mc_curr["% Market Cap"] = (df_mc_curr["Total Market Cap"] / df_mc_curr["Total Market Cap"].sum()) * 100
    df_mc_curr["Market Cap (Trillion IDR)"] = df_mc_curr["Total Market Cap"]/10**12

    # mc_curr_chart
    mc_curr_chart = alt.Chart(df_mc_curr).mark_arc().encode(
        theta=alt.Theta("% Market Cap:Q"),
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="reds"),
            sort=alt.EncodingSortField(field="% Market Cap", order="ascending") # sort color based on % Market Cap value
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("% Market Cap:Q", format=".2f"),
            alt.Tooltip("Market Cap (Trillion IDR):Q", format=",.2f"),
        ]
    ).properties(
        title="% Market Cap of Each Sector of the Total IDX Market Cap",
        width=400
    )

    # Finalize df_mc_hist
    df_mc_hist["Market Cap (Trillion IDR)"] = df_mc_hist["Market Cap"]/10**12

    # mc_hist_chart
    mc_hist_chart = alt.Chart(df_mc_hist).mark_line(
        point=True # add individual data points to the line chart
    ).encode(
        x=alt.X("Quarter:N", axis=alt.Axis(labelAngle=0)), # 0 degree of x-axis label angle
        y=alt.Y("Market Cap (Trillion IDR):Q"),
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Quarter:N"),
            alt.Tooltip("Market Cap (Trillion IDR):Q", format=".2f")
        ]
    ).properties(
        title="Historical Market Cap Across Sectors",
        width=500
    )

    # Market cap section title
    st.subheader("Market Cap")

    # First row visualization
    col1, col2 = st.columns(
        spec=[0.6, 0.4], # relative width of each column
        gap="large" # size of gap between column
    )

    # First column
    with col1:
        st.altair_chart(mc_curr_chart)

    # Second column
    with col2:
        st.altair_chart(mc_hist_chart)

    # Finalize df_mc_change
    df_mc_change["Market Cap Change (%)"] = df_mc_change["Market Cap Change"] * 100

    # mc_change_chart
    mc_change_chart = alt.Chart(df_mc_change).mark_line(
        point=True # add individual data points to the line chart
    ).encode(
        x=alt.X("Date:T"),
        y=alt.Y("Market Cap Change (%):Q"),
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Date:T"),
            alt.Tooltip("Market Cap Change (%):Q", format=".2f")
        ]
    ).properties(
        title="Historical Market Cap Change Across Sectors",
        width=900
    )

    # Second row visualization
    st.altair_chart(mc_change_chart)

    # Valuation section
    df_valuation = pd.DataFrame()

    for i in options:
        url = f"https://api.sectors.app/api/data/sector/report/{i}/?sections=valuation"
        valuation = fetch_data(url)
        df = pd.DataFrame(valuation["valuation"]["historical_valuation"])
        df["Sector"] = valuation["sub_sector"]
        df_valuation = pd.concat([df_valuation, df], ignore_index=True)

    try: 
        df_valuation = df_valuation.drop(["pb_rank", "pe_rank", "ps_rank", "pcf_rank"], axis=1)
    except:
        pass
    df_valuation.columns = ["Price/Book Ratio", "Price/Earning Ratio", "Price/Sales Ratio", "Price/Cash Flow Ratio", "Year", "Sector"]

    # Valuation section title
    st.subheader("Valuation")

    # Valuation metric filter
    option = st.selectbox(
        label="Select Valuation Metric",
        options=("Price/Book Ratio", "Price/Earning Ratio", "Price/Sales Ratio", "Price/Cash Flow Ratio")
    )

    # valuation_chart
    valuation_chart = alt.Chart(df_valuation).mark_line(
        point=True # add individual data points to the line chart
    ).encode(
        x=alt.X("Year:N", axis=alt.Axis(labelAngle=0)), # 0 degree of x-axis label angle
        y=alt.Y(f"{option}:Q"),
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Year:N"),
            alt.Tooltip(f"{option}:Q", format=".2f")
        ]
    ).properties(
        title=f"{option} Across Sectors",
        width=900
    )

    st.altair_chart(valuation_chart)

    # Top companies section
    df_top_mc = pd.DataFrame()
    df_top_growth = pd.DataFrame()
    df_top_profit = pd.DataFrame()
    df_top_revenue = pd.DataFrame()

    for i in options:
        url = f"https://api.sectors.app/api/data/sector/report/{i}/?sections=companies"
        company = fetch_data(url)

        keys = ["top_mcap", "top_growth", "top_profit", "top_revenue"]
        dfs = {}

        for key in keys:
            df = pd.DataFrame(company["companies"]["top_companies"][key])
            df["Sector"] = company["sub_sector"]
            dfs[key] = df

        df_top_mc = pd.concat([df_top_mc, dfs["top_mcap"]], ignore_index=True)
        df_top_growth = pd.concat([df_top_growth, dfs["top_growth"]], ignore_index=True)
        df_top_profit = pd.concat([df_top_profit, dfs["top_profit"]], ignore_index=True)
        df_top_revenue = pd.concat([df_top_revenue, dfs["top_revenue"]], ignore_index=True)

    df_top_mc.columns = ["Symbol", "Market Cap", "Sector"]
    df_top_growth.columns = ["Symbol", "Revenue Growth", "Sector"]
    df_top_profit.columns = ["Symbol", "Profit", "Sector"]
    df_top_revenue.columns = ["Symbol", "Revenue", "Sector"]

    # Finalize df_top_mc
    df_top_mc["Market Cap (Trillion IDR)"] = df_top_mc["Market Cap"]/10**12

    # mc_chart
    mc_chart = alt.Chart(df_top_mc).mark_bar().encode(
        x=alt.X("Market Cap (Trillion IDR):Q"),
        y=alt.Y("Symbol:N", sort="-x"), # sort y-axis based on the value of the x-axis in descending order
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Symbol:N"),
            alt.Tooltip("Market Cap (Trillion IDR):Q", format=".2f")
        ]
    ).properties(
        title="Top Companies based on Market Cap Across Sectors",
        width=900,
        height=500,
    )

    # Finalize df_top_growth
    df_top_growth["Revenue Growth (%)"] = df_top_growth["Revenue Growth"] * 100

    # growth_chart
    growth_chart = alt.Chart(df_top_growth).mark_bar().encode(
        x=alt.X("Revenue Growth (%):Q"),
        y=alt.Y("Symbol:N", sort="-x"), # sort y-axis based on the value of the x-axis in descending order
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Symbol:N"),
            alt.Tooltip("Revenue Growth (%):Q", format=",.2f")
        ]
    ).properties(
        title="Top Companies based on Revenue Growth Across Sectors",
        width=900,
        height=500,
    )

    # Finalize df_top_profit
    df_top_profit["Profit (Billion IDR)"] = df_top_profit["Profit"]/10**9

    # profit_chart
    profit_chart = alt.Chart(df_top_profit).mark_bar().encode(
        x=alt.X("Profit (Billion IDR):Q"),
        y=alt.Y("Symbol:N", sort="-x"), # sort y-axis based on the value of the x-axis in descending order
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Symbol:N"),
            alt.Tooltip("Profit (Billion IDR):Q", format=",.2f")
        ]
    ).properties(
        title="Top Companies based on Profit Across Sectors",
        width=900,
        height=500,
    )

    # Finalize df_top_revenue
    df_top_revenue["Revenue (Trillion IDR)"] = df_top_revenue["Revenue"]/10**12

    # revenue_chart
    revenue_chart = alt.Chart(df_top_revenue).mark_bar().encode(
        x=alt.X("Revenue (Trillion IDR):Q"),
        y=alt.Y("Symbol:N", sort="-x"), # sort y-axis based on the value of the x-axis in descending order
        color=alt.Color(
            "Sector:N",
            scale=alt.Scale(scheme="lightgreyred"),
            sort=alt.SortField(field="Sector", order="ascending") # sort color based on the sector's name
        ),
        tooltip=[
            alt.Tooltip("Sector:N"),
            alt.Tooltip("Symbol:N"),
            alt.Tooltip("Revenue (Trillion IDR):Q", format=",.2f")
        ]
    ).properties(
        title="Top Companies based on Revenue Across Sectors",
        width=900,
        height=500,
    )

    # Top companies section title
    st.subheader("Top Companies")

    # Top companies visualization
    tab1, tab2, tab3, tab4 = st.tabs(
        tabs=["Market Cap", "Growth", "Profit", "Revenue"]
    )

    # First tab
    with tab1:
        st.altair_chart(mc_chart)
    
    # Second tab
    with tab2:
        st.altair_chart(growth_chart)

    # Third tab
    with tab3:
        st.altair_chart(profit_chart)
    
    # Fourth tab
    with tab4:
        st.altair_chart(revenue_chart)