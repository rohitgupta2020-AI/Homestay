import streamlit as st
import requests
import pandas as pd

# ---------------- HIDE STREAMLIT TOOLBAR (GITHUB / FORK) ----------------
st.markdown(
    """
    <style>
    [data-testid="stToolbar"] {
        visibility: hidden;
        height: 0px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Meghalaya Homestay Dashboard — Government of Meghalaya", page_icon="", layout="wide")

# ---------------- THEME / STYLES (pleasant palette + even column colouring) ----------------
# Primary / heading: teal/sea-green palette
PRIMARY_HEX = "#0B5E6F"   # heading
SUBTITLE_HEX = "#455A64"  # subtitle / muted text
HEADER_BG = "#E6F7F5"     # header background
TABLE_HEADER_BG = "#CFECE9"
TABLE_ODD_BG = "#FFFFFF"
TABLE_EVEN_BG = "#F2F8F7"
TABLE_BORDER = "#E6EDEE"
TEXT_COLOR = "#0A3C3A"

st.markdown(
    f"""
    <style>
    /* Page header style */
    .meghalaya-header {{
        background-color: {HEADER_BG};
        padding: 6px 12px;
        border-radius: 6px;
    }}
    .meghalaya-header h1 {{
        color: {PRIMARY_HEX};
        margin: 0;
        font-weight: 700;
    }}
    .meghalaya-header p {{
        color: {SUBTITLE_HEX};
        margin: 0;
        font-weight: 600;
    }}

    /* Styled pandas table produced as HTML (used by styled_table_html) */
    .styled-table {{
        border-collapse: collapse;
        width: 100%;
        font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: {TEXT_COLOR};
    }}
    .styled-table thead th {{
        background-color: {TABLE_HEADER_BG};
        color: {TEXT_COLOR};
        font-weight: 700;
        padding: 10px;
        text-align: left;
        border-bottom: 2px solid {TABLE_BORDER};
    }}
    .styled-table tbody td {{
        padding: 10px;
        border-top: 1px solid {TABLE_BORDER};
    }}
    .styled-table tbody td:nth-child(odd) {{
        background-color: {TABLE_ODD_BG};
    }}
    .styled-table tbody td:nth-child(even) {{
        background-color: {TABLE_EVEN_BG};
    }}

    /* Make Streamlit's container match a bit (optional) */
    .stMarkdown {{ margin-bottom: 8px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

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
