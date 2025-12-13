import streamlit as st
import requests
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Homestay Data Analysis",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Homestay Data Analysis Dashboard")
st.markdown("---")

# Base URL + endpoint
url = "https://www.cmconnectvdv.meghalaya.gov.in/admin-api/api/v1/hdsbpm/getAllHomeStayData"

# Get authorization token from secrets
try:
    auth_token = st.secrets["api"]["auth_token"]
except KeyError:
    st.error("⚠️ Authorization token not found in secrets. Please configure .streamlit/secrets.toml")
    st.stop()

# Headers
headers = {
    "Authorization": f"Bearer {auth_token}",
    "Content-Type": "application/json"
}

# Request Body
payload = {
    "test": "All Data"
}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_homestay_data():
    """Fetch data from the API"""
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# Fetch data
with st.spinner("Fetching homestay data..."):
    data_homestay = fetch_homestay_data()

if data_homestay and data_homestay.get("response_code") == "00":
    rows = data_homestay.get("rows", [])
    
    if len(rows) >= 2:
        # Create dataframes
        df1 = pd.DataFrame(rows[0])
        df2 = pd.DataFrame(rows[1])
        
  
        
        # Assuming df1 is New_homestay and df2 is Upgradation_of_Existing_homestay
        # You may need to swap these based on your data structure
        New_homestay = df1
        Upgradation_of_Existing_homestay = df2
        
        # Create pivot tables
        try:
            # Pivot for Upgradation
            pivot_df_Upgradation = Upgradation_of_Existing_homestay.pivot_table(
                index=["district_name", "block_cluster"],
                values="member_id",
                aggfunc="count",
                dropna=False
            ).reset_index()
            
            pivot_df_Upgradation.rename(columns={"member_id": "member_count"}, inplace=True)
            
            # Pivot for New homestay
            pivot_df_New_homestay = New_homestay.pivot_table(
                index=["district_name", "block_cluster"],
                values="member_id",
                aggfunc="count",
                dropna=False
            ).reset_index()
            
            pivot_df_New_homestay.rename(columns={"member_id": "member_count"}, inplace=True)
            
            # Filter New homestay
            pivot_df_New_homestay = pivot_df_New_homestay[
                pivot_df_New_homestay["member_count"].notna() &
                (pivot_df_New_homestay["member_count"].astype(str).str.strip() != "")
            ]
            
            # Rename columns
            pivot_df_New_homestay = pivot_df_New_homestay.rename(
                columns={"member_count": "member_count_New"}
            )
            
            pivot_df_Upgradation = pivot_df_Upgradation.rename(
                columns={"member_count": "member_count_Upgradation"}
            )
            
            # Merge dataframes
            combined_df = pivot_df_New_homestay.merge(
                pivot_df_Upgradation,
                on=["district_name", "block_cluster"],
                how="outer"
            )
            
            # Fill NaN values
            combined_df = combined_df.fillna("")
            
            # Convert columns safely before summing
            new_col = pd.to_numeric(combined_df["member_count_New"], errors="coerce").fillna(0)
            upg_col = pd.to_numeric(combined_df["member_count_Upgradation"], errors="coerce").fillna(0)
            
            # Calculate totals
            total_new = int(new_col.sum())
            total_upg = int(upg_col.sum())
            
            # Create total row
            total_row = pd.DataFrame({
                "district_name": ["TOTAL"],
                "block_cluster": [""],
                "member_count_New": [total_new],
                "member_count_Upgradation": [total_upg]
            })
            
            # Add total row at top
            combined_df = pd.concat([total_row, combined_df], ignore_index=True)
            
            # Filter out rows with both columns empty
            combined_df = combined_df[
                ~(
                    (
                        combined_df["member_count_New"].isna() |
                        (combined_df["member_count_New"].astype(str).str.strip() == "")
                    )
                    &
                    (
                        combined_df["member_count_Upgradation"].isna() |
                        (combined_df["member_count_Upgradation"].astype(str).str.strip() == "")
                    )
                )
            ]
            
            # Rename columns: uppercase and replace _ with space
            combined_df.columns = combined_df.columns.str.upper().str.replace('_', ' ')
            
            # Rename specific columns
            combined_df.rename(columns={
                'MEMBER COUNT NEW': 'NEW HOMESTAY',
                'MEMBER COUNT UPGRADATION': 'UPGRADATION'
            }, inplace=True)
            
            # Reorder columns: DISTRICT NAME, BLOCK CLUSTER, NEW HOMESTAY, UPGRADATION
            column_order = ['DISTRICT NAME', 'BLOCK CLUSTER', 'NEW HOMESTAY', 'UPGRADATION']
            combined_df = combined_df[column_order]
            
            # Convert numeric columns from float to int (handle empty strings)
            combined_df['NEW HOMESTAY'] = pd.to_numeric(combined_df['NEW HOMESTAY'], errors='coerce').fillna(0).astype(int)
            combined_df['UPGRADATION'] = pd.to_numeric(combined_df['UPGRADATION'], errors='coerce').fillna(0).astype(int)
            
            # Reset index to start from 1
            combined_df.index = range(1, len(combined_df) + 1)
            
            # Display summary statistics
            st.markdown("## 📊 Summary")
            summary_col1, summary_col2, summary_col3 = st.columns(3)
            with summary_col1:
                st.metric("Total New Homestays", f"{total_new:,}")
            with summary_col2:
                st.metric("Total Upgradations", f"{total_upg:,}")
            with summary_col3:
                st.metric("Total Combined", f"{total_new + total_upg:,}")
            
            st.markdown("---")
            
            # Display combined dataframe
            st.markdown("## 📋 Combined Data Table")
            
            # Style the dataframe - make TOTAL row bold and bigger, center align numeric columns
            def style_cells(df):
                styles = pd.DataFrame('', index=df.index, columns=df.columns)
                # Center align numeric columns for all rows
                styles['NEW HOMESTAY'] = 'text-align: center;'
                styles['UPGRADATION'] = 'text-align: center;'
                # Bold and bigger for TOTAL row
                total_mask = df['DISTRICT NAME'] == 'TOTAL'
                styles.loc[total_mask, :] = styles.loc[total_mask, :].apply(
                    lambda x: x + 'font-weight: bold; font-size: 1.2em;'
                )
                return styles
            
            styled_df = combined_df.style.apply(style_cells, axis=None)
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=False
            )
            
            # Download button
            csv = combined_df.to_csv(index=True)
            st.download_button(
                label="📥 Download Combined Data as CSV",
                data=csv,
                file_name="homestay_combined_data.csv",
                mime="text/csv"
            )
            
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            st.info("Displaying raw data instead...")
            
            tab1, tab2 = st.tabs(["Dataset 1", "Dataset 2"])
            with tab1:
                st.dataframe(df1, use_container_width=True)
            with tab2:
                st.dataframe(df2, use_container_width=True)
    else:
        st.warning("⚠️ Insufficient data rows received from API")
        st.json(data_homestay)
        
else:
    st.error("❌ Failed to fetch data or invalid response")
    if data_homestay:
        st.json(data_homestay)