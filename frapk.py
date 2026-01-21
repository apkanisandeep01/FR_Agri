import streamlit as st
import pandas as pd
import io
import mysql.connector
import tempfile
import hashlib

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="FR Agri Excel Merger",
    page_icon="❤️",
    layout="wide"
)

st.title("🌾 FR Excel formatter - Merger")
st.markdown("Upload multiple Excel files to deduplicate and merge to fetch Aadhar Card.")

# ==================================================
# SESSION STATE FLAGS
# ==================================================
if "processing_warning" not in st.session_state:
    st.session_state.processing_warning = False

if "metric_warning" not in st.session_state:
    st.session_state.metric_warning = False

if "last_fingerprint" not in st.session_state:
    st.session_state.last_fingerprint = None

# ==================================================
# SAFE EXCEL READER (SOFT FAILURE)
# ==================================================
def safe_read_excel(file, required_columns=None):
    try:
        df = pd.read_excel(file)

        if required_columns:
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns: {missing}")

        return df

    except Exception:
        raise RuntimeError("Invalid Excel")

# ==================================================
# FILE FINGERPRINT
# ==================================================
def get_files_fingerprint(files):
    hasher = hashlib.sha256()
    for f in files:
        hasher.update(f.name.encode())
        hasher.update(str(f.size).encode())
    return hasher.hexdigest()

# ==================================================
# TiDB SSL CA
# ==================================================
@st.cache_resource
def get_ca_cert_path():
    cert = st.secrets["TIDB_SSL_CA"]
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(cert.encode())
    temp.close()
    return temp.name

# ==================================================
# TiDB CONNECTION
# ==================================================
@st.cache_resource
def get_tidb_connection():
    return mysql.connector.connect(
        host=st.secrets["TIDB_HOST"],
        port=st.secrets["TIDB_PORT"],
        user=st.secrets["TIDB_USER"],
        password=st.secrets["TIDB_PASSWORD"],
        database=st.secrets["TIDB_DATABASE"],
        ssl_ca=get_ca_cert_path(),
        ssl_verify_cert=True
    )

# ==================================================
# COUNTER FUNCTIONS
# ==================================================
def increment_counter(counter_name):
    conn = get_tidb_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE app_counter SET counter_value = counter_value + 1 WHERE counter_name = %s",
        (counter_name,)
    )
    conn.commit()
    cur.execute(
        "SELECT counter_value FROM app_counter WHERE counter_name = %s",
        (counter_name,)
    )
    value = cur.fetchone()[0]
    cur.close()
    return value

def get_counter_value(counter_name):
    conn = get_tidb_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT counter_value FROM app_counter WHERE counter_name = %s",
        (counter_name,)
    )
    value = cur.fetchone()[0]
    cur.close()
    return value

# ==================================================
# FILE UPLOADERS
# ==================================================
fr_files = st.file_uploader(
    "Upload Unclaimed files",
    type="xlsx",
    accept_multiple_files=True
)

bh_files = st.file_uploader(
    "Upload Bheema files",
    type="xlsx",
    accept_multiple_files=True
)

processed_df = None

# ==================================================
# MAIN PROCESSING (FULLY GUARDED)
# ==================================================
if fr_files and bh_files:
    try:
        # ---------- FR FILES ----------
        dfs = [safe_read_excel(f) for f in fr_files]
        df_fr = pd.concat(dfs, ignore_index=True)

        # ---------- BHEEMA FILES ----------
        b_dfs = [
            safe_read_excel(
                f,
                required_columns=[
                    "VillName",
                    "PPBNO",
                    "FarmerName_Tel",
                    "FatherName_Tel",
                    "AadharId",
                    "MobileNo"
                ]
            )
            for f in bh_files
        ]
        df_bh = pd.concat(b_dfs, ignore_index=True)

        # ---------- MERGE ----------
        left_on = ["Village Name", "Farmer Name", "Identifier Name"]
        right_on = ["VillName", "FarmerName_Tel", "FatherName_Tel"]

        df_fr[left_on] = df_fr[left_on].astype(str).apply(
            lambda c: c.str.strip().str.lower()
        )
        df_bh[right_on] = df_bh[right_on].astype(str).apply(
            lambda c: c.str.strip().str.lower()
        )

        merged = df_fr.merge(
            df_bh,
            left_on=left_on,
            right_on=right_on,
            how="left"
        )

        # ---------- GROUP BY ----------
        processed_df = merged.groupby(
            ["Bucket ID", "Village LGD Code"]
        ).agg({
            "Village Name": lambda x: ", ".join(pd.unique(x.astype(str))),
            "Farmer Name": "last",
            "Identifier Name": "last",
            "Farmer Mobile Number": "last",
            "AadharId": "last",
            "MobileNo": "last",
            "PPBNO": "last",
            "Survey Number": lambda x: ", ".join(pd.unique(x.astype(str))),
            "Sub Survey Number": lambda x: ", ".join(pd.unique(x.astype(str)))
        }).reset_index()

        processed_df.drop(columns=["Village LGD Code"], inplace=True)

        st.session_state.processing_warning = False

    except Exception:
        st.session_state.processing_warning = True
        st.toast(
            "⚠️ There is an issue with the Excel file. Please reupload.",
            icon="⚠️"
        )

# ==================================================
# METRIC (NON-BLOCKING)
# ==================================================
if processed_df is not None:
    try:
        fingerprint = get_files_fingerprint(fr_files + bh_files)

        if st.session_state.last_fingerprint != fingerprint:
            count = increment_counter("file_process_count")
            st.session_state.last_fingerprint = fingerprint
        else:
            count = get_counter_value("file_process_count")

        st.metric("📊 Total files processed till now", count)
        st.session_state.metric_warning = False

    except Exception:
        st.session_state.metric_warning = True
        st.toast(
            "⚠️ Unable to update usage metric. Download is still available.",
            icon="⚠️"
        )

# ==================================================
# DOWNLOAD (ALWAYS AVAILABLE IF DATA EXISTS)
# ==================================================
if processed_df is not None:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        processed_df.to_excel(writer, index=False, sheet_name="All_Villages")

    st.download_button(
        label="Download Full Excel",
        data=buffer.getvalue(),
        file_name="Full_Farmer_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("Waiting for files to be uploaded...")

# ==================================================
# FOOTER
# ==================================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; color:gray; font-size:14px;">
        Developed and maintained by <b>Sandeep Kumar</b><br>
        <a href="https://apkanisandeep01.github.io/my-portfolio/"
           target="_blank"
           style="color:#4a90e2; text-decoration:none;">
            Visit my portfolio
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
