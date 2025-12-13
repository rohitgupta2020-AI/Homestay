import streamlit as st
import requests
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config( page_title="Homestay Data Analysis — Government of Meghalaya", page_icon="", layout="wide" )

st.markdown( """ <div style="text-align:center;"> <h1 style="color:#b4a7d6; font-weight:700; margin:0;">Homestay Data Analysis</h1> <p style="color:blue; font-weight:700; margin:0;">Government of Meghalaya</p> </div> """, unsafe_allow_html=True, )

# ---------------- API CONFIG ----------------
url = "https://www.cmconnectvdv.meghalaya.gov.in/admin-api/api/v1/hdsbpm/getAllHomeStayData"

payload = {
    "test": "All Data"
}

# ---------------- SECRETS ----------------
try:
    auth_token = st.secrets["api"]["auth_token"]
except KeyError:
    st.error(" Authorization token not found in Streamlit Secrets")
    st.stop()


# ---------------- FETCH FUNCTION ----------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_homestay_data(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=15
    )
    response.raise_for_status()
    return response.json()


# ---------------- API CALL ----------------
with st.spinner("Fetching homestay data..."):
    try:
        data_homestay = fetch_homestay_data(auth_token)
    except Exception as e:
        st.error(f"API Error: {e}")
        st.stop()


# ---------------- VALIDATION ----------------
if not data_homestay or data_homestay.get("response_code") != "00":
    st.error(" Failed to fetch valid data")
    st.json(data_homestay)
    st.stop()

rows = data_homestay.get("rows", [])

if len(rows) < 2:
    st.warning("⚠️ Insufficient data rows received from API")
    st.json(data_homestay)
    st.stop()


# ---------------- DATAFRAMES ----------------
df1 = pd.DataFrame(rows[0])
df2 = pd.DataFrame(rows[1])

New_homestay = df1
Upgradation_of_Existing_homestay = df2


# ---------------- PIVOTS (LOGIC UNCHANGED) ----------------
pivot_df_Upgradation = Upgradation_of_Existing_homestay.pivot_table(
    index=["district_name", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index()

pivot_df_Upgradation.rename(
    columns={"member_id": "member_count"},
    inplace=True
)

pivot_df_New_homestay = New_homestay.pivot_table(
    index=["district_name", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index()

pivot_df_New_homestay.rename(
    columns={"member_id": "member_count"},
    inplace=True
)

# ---------------- FILTER (UNCHANGED) ----------------
pivot_df_New_homestay = pivot_df_New_homestay[
    pivot_df_New_homestay["member_count"].notna() &
    (pivot_df_New_homestay["member_count"].astype(str).str.strip() != "")
]

pivot_df_New_homestay.rename(
    columns={"member_count": "member_count_New"},
    inplace=True
)

pivot_df_Upgradation.rename(
    columns={"member_count": "member_count_Upgradation"},
    inplace=True
)

# ---------------- MERGE ----------------
combined_df = pivot_df_New_homestay.merge(
    pivot_df_Upgradation,
    on=["district_name", "block_cluster"],
    how="outer"
)

combined_df = combined_df.fillna("")

# ---------------- TOTALS (UNCHANGED) ----------------
new_col = pd.to_numeric(
    combined_df["member_count_New"], errors="coerce"
).fillna(0)

upg_col = pd.to_numeric(
    combined_df["member_count_Upgradation"], errors="coerce"
).fillna(0)

total_new = int(new_col.sum())
total_upg = int(upg_col.sum())

total_row = pd.DataFrame({
    "district_name": ["TOTAL"],
    "block_cluster": [""],
    "member_count_New": [total_new],
    "member_count_Upgradation": [total_upg]
})

combined_df = pd.concat([total_row, combined_df], ignore_index=True)

# ---------------- FINAL CLEANUP ----------------
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

combined_df.columns = combined_df.columns.str.upper().str.replace("_", " ")

combined_df.rename(columns={
    "MEMBER COUNT NEW": "NEW HOMESTAY",
    "MEMBER COUNT UPGRADATION": "UPGRADATION"
}, inplace=True)

combined_df = combined_df[
    ["DISTRICT NAME", "BLOCK CLUSTER", "NEW HOMESTAY", "UPGRADATION"]
]

combined_df["NEW HOMESTAY"] = pd.to_numeric(
    combined_df["NEW HOMESTAY"], errors="coerce"
).fillna(0).astype(int)

combined_df["UPGRADATION"] = pd.to_numeric(
    combined_df["UPGRADATION"], errors="coerce"
).fillna(0).astype(int)

combined_df.index = range(1, len(combined_df) + 1)


# ---------------- UI ----------------
st.markdown("##  Summary")

c1, c2, c3 = st.columns(3)
c1.metric("Total New Homestays", f"{total_new:,}")
c2.metric("Total Upgradations", f"{total_upg:,}")
c3.metric("Total Combined", f"{total_new + total_upg:,}")

st.markdown("---")
st.markdown("##  Combined Data Table")

st.dataframe(
    combined_df,
    use_container_width=True
)

st.download_button(
    label="📥 Download Combined Data as CSV",
    data=combined_df.to_csv(index=True),
    file_name="homestay_combined_data.csv",
    mime="text/csv"
)


