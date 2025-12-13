import streamlit as st
import requests
import pandas as pd
from pathlib import Path


# ---------------- LOAD CSS ----------------
def load_css():
    css_path = Path(__file__).with_name("style.css")
    try:
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        pass

load_css()


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Meghalaya Homestay Dashboard — Government of Meghalaya",
    page_icon="🏠",
    layout="wide"
)

# ---------------- HEADER ----------------
st.markdown(
    """
    <div style="text-align:center; margin-bottom:10px;">
        <h1 style="color:#2F539B; font-weight:700; margin:0;">
            Meghalaya Homestay Dashboard
        </h1>
        <p style="color:#36454F; font-weight:600; margin:0;">
            Government of Meghalaya
        </p>
    </div>
    <hr style="margin-top:15px; margin-bottom:15px;">
    """,
    unsafe_allow_html=True
)


# ---------------- API CONFIG ----------------
url = "https://www.cmconnectvdv.meghalaya.gov.in/admin-api/api/v1/hdsbpm/getAllHomeStayData"
payload = {"test": "All Data"}


# ---------------- SECRETS ----------------
try:
    auth_token = st.secrets["api"]["auth_token"]
except KeyError:
    st.error("Authorization token not found in Streamlit Secrets")
    st.stop()


# ---------------- FETCH FUNCTION ----------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_homestay_data(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers, timeout=15)
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
    st.error("Failed to fetch valid data")
    st.json(data_homestay)
    st.stop()

rows = data_homestay.get("rows", [])
if len(rows) < 2:
    st.warning("Insufficient data rows received from API")
    st.stop()


# ---------------- DATAFRAMES ----------------
New_homestay = pd.DataFrame(rows[0])
Upgradation_of_Existing_homestay = pd.DataFrame(rows[1])


# ---------------- PIVOTS ----------------
pivot_df_Upgradation = Upgradation_of_Existing_homestay.pivot_table(
    index=["district_name", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index().rename(columns={"member_id": "member_count_Upgradation"})

pivot_df_New_homestay = New_homestay.pivot_table(
    index=["district_name", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index().rename(columns={"member_id": "member_count_New"})

pivot_df_New_homestay = pivot_df_New_homestay[
    pivot_df_New_homestay["member_count_New"].notna() &
    (pivot_df_New_homestay["member_count_New"].astype(str).str.strip() != "")
]


# ---------------- MERGE ----------------
combined_df = pivot_df_New_homestay.merge(
    pivot_df_Upgradation,
    on=["district_name", "block_cluster"],
    how="outer"
).fillna("")


# ---------------- TOTALS ----------------
total_new = int(pd.to_numeric(combined_df["member_count_New"], errors="coerce").fillna(0).sum())
total_upg = int(pd.to_numeric(combined_df["member_count_Upgradation"], errors="coerce").fillna(0).sum())

total_row = pd.DataFrame({
    "district_name": ["TOTAL"],
    "block_cluster": [""],
    "member_count_New": [total_new],
    "member_count_Upgradation": [total_upg]
})

combined_df = pd.concat([total_row, combined_df], ignore_index=True)


# ---------------- FINAL CLEANUP ----------------
combined_df.columns = combined_df.columns.str.upper().str.replace("_", " ")

combined_df.rename(columns={
    "MEMBER COUNT NEW": "NEW HOMESTAY",
    "MEMBER COUNT UPGRADATION": "UPGRADATION"
}, inplace=True)

combined_df = combined_df[
    ["DISTRICT NAME", "BLOCK CLUSTER", "NEW HOMESTAY", "UPGRADATION"]
]

combined_df["NEW HOMESTAY"] = pd.to_numeric(combined_df["NEW HOMESTAY"], errors="coerce").fillna(0).astype(int)
combined_df["UPGRADATION"] = pd.to_numeric(combined_df["UPGRADATION"], errors="coerce").fillna(0).astype(int)


# ---------------- FILTERS ----------------
st.markdown("## 🔎 Filters")

f1, f2 = st.columns(2)

district_filter = f1.multiselect(
    "District",
    options=sorted(combined_df["DISTRICT NAME"].unique()),
    default=sorted(combined_df["DISTRICT NAME"].unique())
)

block_filter = f2.multiselect(
    "Block Cluster",
    options=sorted(combined_df["BLOCK CLUSTER"].unique()),
    default=sorted(combined_df["BLOCK CLUSTER"].unique())
)

filtered_df = combined_df[
    (combined_df["DISTRICT NAME"].isin(district_filter)) &
    (combined_df["BLOCK CLUSTER"].isin(block_filter))
]


# ---------------- SERIAL NUMBER (DATA ROWS ONLY) ----------------
display_df = filtered_df.copy()
display_df.insert(0, "S. NO", "")

mask = display_df["DISTRICT NAME"] != "TOTAL"
display_df.loc[mask, "S. NO"] = range(1, mask.sum() + 1)


# ---------------- SUMMARY ----------------
st.markdown("## Summary")

c1, c2, c3 = st.columns([1, 1, 1])
c1.metric("Total New Homestays", f"{total_new:,}")
c2.metric("Total Upgradations", f"{total_upg:,}")
c3.metric("Total Combined", f"{total_new + total_upg:,}")


# ---------------- TABLE ----------------
st.markdown(
    display_df.to_html(
        index=False,
        classes="custom-table",
        border=0
    ),
    unsafe_allow_html=True
)


# ---------------- DOWNLOAD ----------------
st.download_button(
    label="📥 Download Filtered Data as CSV",
    data=display_df.to_csv(index=False),
    file_name="homestay_combined_data_filtered.csv",
    mime="text/csv"
)
