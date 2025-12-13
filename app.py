import streamlit as st
import requests
import pandas as pd

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Homestay Data Analysis",
    page_icon="🏠",
    layout="wide"
)

st.title("🏠 Homestay Data Analysis Dashboard")
st.divider()

# ---------------- API CONFIG ----------------
URL = "https://www.cmconnectvdv.meghalaya.gov.in/admin-api/api/v1/hdsbpm/getAllHomeStayData"
PAYLOAD = {"test": "All Data"}

# ---------------- SECRETS ----------------
try:
    AUTH_TOKEN = st.secrets["api"]["auth_token"]
except KeyError:
    st.error("⚠️ Authorization token missing in Streamlit Secrets")
    st.stop()


# ---------------- DATA FETCH ----------------
@st.cache_data(ttl=300, show_spinner=False)
def fetch_homestay_data(token: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            URL,
            json=PAYLOAD,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return {"error": f"HTTP {response.status_code}", "text": response.text}

        return response.json()

    except requests.exceptions.Timeout:
        return {"error": "API timeout"}
    except Exception as e:
        return {"error": str(e)}


# ---------------- FETCH WITH SPINNER ----------------
with st.spinner("Fetching homestay data…"):
    data_homestay = fetch_homestay_data(AUTH_TOKEN)

# ---------------- VALIDATION ----------------
if not data_homestay:
    st.error("❌ Empty response from API")
    st.stop()

if "error" in data_homestay:
    st.error("❌ API Error")
    st.json(data_homestay)
    st.stop()

if data_homestay.get("response_code") != "00":
    st.error("❌ Invalid API response")
    st.json(data_homestay)
    st.stop()

rows = data_homestay.get("rows", [])
if len(rows) < 2:
    st.warning("⚠️ Insufficient data returned from API")
    st.json(data_homestay)
    st.stop()


# ---------------- DATA PROCESSING ----------------
df_new = pd.DataFrame(rows[0])
df_upg = pd.DataFrame(rows[1])

def make_pivot(df):
    return (
        df.pivot_table(
            index=["district_name", "block_cluster"],
            values="member_id",
            aggfunc="count"
        )
        .reset_index()
        .rename(columns={"member_id": "count"})
    )

pivot_new = make_pivot(df_new).rename(columns={"count": "NEW HOMESTAY"})
pivot_upg = make_pivot(df_upg).rename(columns={"count": "UPGRADATION"})

combined_df = pivot_new.merge(
    pivot_upg,
    on=["district_name", "block_cluster"],
    how="outer"
).fillna(0)

# totals
total_new = int(combined_df["NEW HOMESTAY"].sum())
total_upg = int(combined_df["UPGRADATION"].sum())

total_row = pd.DataFrame({
    "district_name": ["TOTAL"],
    "block_cluster": [""],
    "NEW HOMESTAY": [total_new],
    "UPGRADATION": [total_upg]
})

combined_df = pd.concat([total_row, combined_df], ignore_index=True)

combined_df.columns = combined_df.columns.str.upper().str.replace("_", " ")
combined_df.index = range(1, len(combined_df) + 1)


# ---------------- UI ----------------
st.markdown("## 📊 Summary")
c1, c2, c3 = st.columns(3)
c1.metric("New Homestays", f"{total_new:,}")
c2.metric("Upgradations", f"{total_upg:,}")
c3.metric("Total", f"{total_new + total_upg:,}")

st.divider()
st.markdown("## 📋 Combined Table")

st.dataframe(combined_df, use_container_width=True)

st.download_button(
    "📥 Download CSV",
    combined_df.to_csv(index=True),
    "homestay_summary.csv",
    "text/csv"
)
