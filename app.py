import streamlit as st
import requests
import pandas as pd
from pathlib import Path

# Load external CSS from `style.css` and inject into Streamlit
def load_css():
    css_path = Path(__file__).with_name("style.css")
    try:
        css = css_path.read_text(encoding="utf-8")
    except Exception:
        css = None
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Meghalaya Homestay Dashboard — Government of Meghalaya", page_icon="", layout="wide")

# Theme styles are provided by `style.css` which is loaded above.

st.markdown(
    f""" 
    <div class="meghalaya-header">
      <h1>Meghalaya Homestay Dashboard</h1>
      <p>Government of Meghalaya</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------- API CONFIG ----------------
url = "https://www.cmconnectvdv.meghalaya.gov.in/admin-api/api/v1/hdsbpm/getAllHomeStayData"

payload = {
    "test": "All Data"
}

# ---------------- SECRETS ----------------ntry
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

# ---------------- Helper: render styled table HTML ----------------
def styled_table_html(df: pd.DataFrame) -> str:
    """
    Return HTML of a pandas DataFrame styled with alternating column colours.
    Uses CSS selectors (nth-child) for even/odd column backgrounds.
    """
    # Ensure columns order is preserved and convert to str for safe rendering
    df_copy = df.copy()
    # Use pandas Styler to attach our class and CSS selectors
    styler = df_copy.style.hide_index()
    table_styles = [
        {"selector": "table", "props": [("class", "styled-table")]},
    ]
    # Additional CSS rules are already injected globally above; styler.to_html will produce a table we target.
    # However, to ensure the table tag contains our class, we'll post-process the HTML below.
    html = styler.to_html()
    # Add our class to the table tag (simple replace)
    html = html.replace("<table", '<table class="styled-table"', 1)
    return html

# ---------------- DISPLAY PIVOTS WITH STYLED TABLES ----------------
st.markdown("### New Homestays by District and Block", unsafe_allow_html=True)
st.markdown(styled_table_html(pivot_df_New_homestay), unsafe_allow_html=True)

st.markdown("### Upgradation of Existing Homestays by District and Block", unsafe_allow_html=True)
st.markdown(styled_table_html(pivot_df_Upgradation), unsafe_allow_html=True)

# ---------------- FILTER (UNCHANGED) ----------------
