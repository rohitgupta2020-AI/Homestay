import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import numpy as np

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
    page_title="Chief Minister's Homestay Mission — Government of Meghalaya",
    page_icon="🏠",
    layout="wide"
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


# ---------------- PIVOTS (ORIGINAL LOGIC) ----------------
pivot_df_Upgradation = Upgradation_of_Existing_homestay.pivot_table(
    index=["district_cluster", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index()

pivot_df_Upgradation.rename(
    columns={"member_id": "member_count"},
    inplace=True
)

pivot_df_New_homestay = New_homestay.pivot_table(
    index=["district_cluster", "block_cluster"],
    values="member_id",
    aggfunc="count",
    dropna=False
).reset_index()

pivot_df_New_homestay.rename(
    columns={"member_id": "member_count"},
    inplace=True
)


# ---------------- FILTER ----------------
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
    on=["district_cluster", "block_cluster"],
    how="outer"
).fillna("No Cluster Mapping")


# ---------------- TOTALS ----------------
new_col = pd.to_numeric(combined_df["member_count_New"], errors="coerce").fillna(0)
upg_col = pd.to_numeric(combined_df["member_count_Upgradation"], errors="coerce").fillna(0)

total_new = int(new_col.sum())
total_upg = int(upg_col.sum())

total_row = pd.DataFrame({
    "district_cluster": ["TOTAL"],
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

combined_df.columns = combined_df.columns.str.upper().str.replace("_", " ", regex=False)

combined_df.rename(columns={
    "DISTRICT CLUSTER": "DISTRICT NAME",
    "MEMBER COUNT NEW": "DEVELOPMENT OF NEW HOMESTAY",
    "MEMBER COUNT UPGRADATION": "UPGRADATION OF EXISTING HOMESTAY",
    "BLOCK CLUSTER" : "CLUSTER NAME"
}, inplace=True)

display_columns = [
    "DISTRICT NAME",
    "CLUSTER NAME",
    "DEVELOPMENT OF NEW HOMESTAY",
    "UPGRADATION OF EXISTING HOMESTAY"
]
missing_display_columns = [col for col in display_columns if col not in combined_df.columns]

if missing_display_columns:
    st.error(f"Final table is missing columns: {', '.join(missing_display_columns)}")
    st.write("Available columns:", list(combined_df.columns))
    st.stop()

combined_df = combined_df[display_columns]

combined_df["DEVELOPMENT OF NEW HOMESTAY"] = pd.to_numeric(combined_df["DEVELOPMENT OF NEW HOMESTAY"], errors="coerce").fillna(0).astype(int)
combined_df["UPGRADATION OF EXISTING HOMESTAY"] = pd.to_numeric(combined_df["UPGRADATION OF EXISTING HOMESTAY"], errors="coerce").fillna(0).astype(int)

# ---------------- REMOVE ZERO-ZERO ROWS ----------------
combined_df = combined_df[
    ~(
        (combined_df["DEVELOPMENT OF NEW HOMESTAY"] == 0) &
        (combined_df["UPGRADATION OF EXISTING HOMESTAY"] == 0)
    )
]

total_df = combined_df[combined_df["DISTRICT NAME"] == "TOTAL"]
data_df = combined_df[combined_df["DISTRICT NAME"] != "TOTAL"].sort_values(
    by="DEVELOPMENT OF NEW HOMESTAY",
    ascending=False
)
combined_df = pd.concat([total_df, data_df], ignore_index=True)




# ---------------- FIX SERIAL NUMBER ----------------

display_df = combined_df.copy()

display_df.insert(0, "S. NO", np.nan)

mask = display_df["DISTRICT NAME"] != "TOTAL"

display_df.loc[mask, "S. NO"] = np.arange(1, mask.sum() + 1)
   
# ---------------- UI ----------------
total_combined = total_new + total_upg
district_count = display_df.loc[mask, "DISTRICT NAME"].replace("", pd.NA).dropna().nunique()
cluster_count = display_df.loc[mask, "CLUSTER NAME"].replace("", pd.NA).dropna().nunique()

st.markdown(
    f"""
    <section class="dashboard-hero">
        <div>
            <p class="eyebrow">Government of Meghalaya</p>
            <h1>Chief Minister's Homestay Mission</h1>
            <p class="hero-copy">
                District and cluster summary for new homestay development
                and upgradation of existing homestays.
            </p>
        </div>
        <div class="hero-stat">
            <span>Total Applications</span>
            <strong>{total_combined:,}</strong>
        </div>
    </section>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <section class="metric-grid">
        <div class="metric-card accent-green">
            <span>Development of New Homestay</span>
            <strong>{total_new:,}</strong>
        </div>
        <div class="metric-card accent-blue">
            <span>Upgradation of Existing Homestay</span>
            <strong>{total_upg:,}</strong>
        </div>
        <div class="metric-card accent-amber">
            <span>Districts Covered</span>
            <strong>{district_count:,}</strong>
        </div>
        <div class="metric-card accent-slate">
            <span>Clusters Covered</span>
            <strong>{cluster_count:,}</strong>
        </div>
    </section>
    """,
    unsafe_allow_html=True
)


# ---------------- TABLE (HTML – GOOD UI) ----------------
st.markdown(
    """
    <div class="section-heading">
        <div>
            <p class="eyebrow">Summary</p>
            <h2>District and Cluster Report</h2>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="table-shell">
        {display_df.to_html(
        index=False,
        classes="custom-table",
        border=0
    )}
    </div>
    """,
    unsafe_allow_html=True
)


# ---------------- DOWNLOAD ----------------
download_col, _ = st.columns([1, 3])
with download_col:
    st.download_button(
        label="Download CSV",
        data=display_df.to_csv(index=False),
        file_name="homestay_combined_data.csv",
        mime="text/csv",
        use_container_width=True
    )






