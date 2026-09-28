import streamlit as st
import pandas as pd
import io
import mysql.connector
import tempfile
import hashlib
from datetime import datetime
import streamlit.components.v1 as components


# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="FR DataSync - Merger",
    page_icon="fr_datasync_logo.png",
    layout="centered"
)


# ==================================================
# APP STYLES
# ==================================================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #f1f8f1 0%, #ffffff 40%);
            color: #16351a;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 1.5rem;
        }

        h1, h2, h3, p, label {
            color: #1b5e20;
        }

        /* HERO HEADER */
        .fr-hero {
            background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 55%, #558b2f 100%);
            border-radius: 18px;
            padding: 28px 30px;
            color: #ffffff;
            box-shadow: 0 10px 30px rgba(27, 94, 32, .25);
            margin-bottom: 1.5rem;
        }

        .fr-hero h1 {
            color: #ffffff !important;
            font-size: 2rem;
            margin: 0 0 .4rem 0;
            padding: 0;
        }

        .fr-hero p {
            color: #e8f5e9 !important;
            font-size: .98rem;
            line-height: 1.55;
            margin: 0;
        }

        .fr-hero .badge {
            display: inline-block;
            background: rgba(255, 255, 255, .18);
            color: #ffffff !important;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: .75rem;
            letter-spacing: .5px;
            margin-bottom: .7rem;
        }

        /* FILE UPLOADERS */
        div[data-testid="stFileUploader"] {
            margin-bottom: 1.2rem;
        }

        div[data-testid="stFileUploader"] label p,
        div[data-testid="stFileUploader"] label {
            color: #0d4715 !important;
            font-size: 1.08rem !important;
            font-weight: 800 !important;
            letter-spacing: .15px;
        }

        div[data-testid="stFileUploader"] section {
            border: 3px dashed #2e7d32 !important;
            background: linear-gradient(135deg, #f4fbf4 0%, #eaf7eb 100%) !important;
            border-radius: 16px !important;
            padding: 1rem !important;
            box-shadow: 0 4px 14px rgba(46, 125, 50, .10);
        }

        div[data-testid="stFileUploader"] section:hover {
            border-color: #1b5e20 !important;
            background: #e4f4e5 !important;
            box-shadow: 0 6px 18px rgba(46, 125, 50, .18);
        }

        div[data-testid="stFileUploader"] small,
        div[data-testid="stFileUploader"] span,
        div[data-testid="stFileUploader"] p,
        div[data-testid="stFileUploader"] div {
            color: #234d28 !important;
            font-weight: 600 !important;
        }

        /* Uploaded file name chips */
        div[data-testid="stFileUploaderFile"] {
            background: #ffffff !important;
            border: 1px solid #9ccc9e !important;
            border-radius: 10px !important;
            box-shadow: 0 2px 6px rgba(27, 94, 32, .08) !important;
        }

        div[data-testid="stFileUploaderFile"] * {
            color: #16351a !important;
            font-weight: 700 !important;
        }

        div[data-testid="stFileUploaderFile"] button {
            background: transparent !important;
            border: none !important;
        }

        div[data-testid="stFileUploaderFile"] button:hover {
            background: #ffebee !important;
        }

        div[data-testid="stFileUploaderDropzone"] button {
            background: #2e7d32 !important;
            color: #ffffff !important;
            border-radius: 10px !important;
            border: none !important;
            font-weight: 800 !important;
            padding: .45rem 1rem !important;
        }

        div[data-testid="stFileUploaderDropzone"] button * {
            color: #ffffff !important;
        }

        div[data-testid="stFileUploaderDropzone"] button:hover {
            background: #1b5e20 !important;
        }

        /* BUTTONS */
        div.stButton > button,
        div.stDownloadButton > button {
            background: #2e7d32 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
            padding: .75rem 1rem !important;
            transition: all .2s ease;
        }

        div.stButton > button *,
        div.stDownloadButton > button * {
            color: #ffffff !important;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            background: #1b5e20 !important;
            color: #ffffff !important;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(46, 125, 50, .30);
        }

        div.stButton > button:disabled {
            background: #c8d8c8 !important;
            color: #526452 !important;
        }

        /* CUSTOM METRIC CARDS */
        .custom-metric-card {
            background: linear-gradient(135deg, #ffffff 0%, #edf8ee 100%);
            border: 1px solid #b7ddb9;
            border-left: 6px solid #2e7d32;
            border-radius: 14px;
            padding: 16px 18px;
            min-height: 104px;
            box-shadow: 0 3px 12px rgba(27, 94, 32, .10);
        }

        .custom-metric-card .metric-title {
            color: #1b5e20 !important;
            font-size: .88rem;
            font-weight: 800;
            margin-bottom: 10px;
            line-height: 1.3;
        }

        .custom-metric-card .metric-number {
            color: #103b16 !important;
            font-size: 2rem;
            font-weight: 900;
            line-height: 1;
        }

        /* Native total counter metric */
        div[data-testid="stMetric"] {
            background: linear-gradient(135deg, #ffffff 0%, #edf8ee 100%) !important;
            border: 1px solid #b7ddb9 !important;
            border-left: 6px solid #2e7d32 !important;
            border-radius: 14px !important;
            padding: 14px 18px !important;
            box-shadow: 0 3px 12px rgba(27, 94, 32, .10) !important;
        }

        div[data-testid="stMetric"] * {
            color: #1b5e20 !important;
            font-weight: 800 !important;
        }

        div[data-testid="stMetricValue"] * {
            color: #103b16 !important;
            font-size: 1.8rem !important;
        }

        /* DATAFRAME */
        div[data-testid="stDataFrame"] {
            border: 1px solid #c8e6c9 !important;
            border-radius: 12px !important;
            overflow: hidden !important;
        }

        /* REVIEW CARD */
        .review-card {
            margin-top: 2rem;
            padding: 22px;
            border-radius: 16px;
            background: linear-gradient(135deg, #0f2e13 0%, #1b5e20 100%);
            color: #ffffff;
            box-shadow: 0 8px 22px rgba(15, 46, 19, .20);
            text-align: center;
        }

        .review-card h2 {
            color: #ffffff !important;
            font-size: 1.35rem;
            margin: 0 0 .45rem 0;
        }

        .review-card p {
            color: #d7ead7 !important;
            font-size: .92rem;
            line-height: 1.5;
            margin-bottom: 0;
        }

        .review-note {
            margin-top: .7rem;
            color: #557b58 !important;
            font-size: .78rem;
            text-align: center;
        }
    </style>

    <div class="fr-hero">
        <span class="badge">FARMER RECORDS · EXCEL MERGER</span>
        <h1>FR DataSync - Merger</h1>
        <p>
            Upload multiple agriculture Excel files to bring matching farmer records together,
            remove duplicate information, and create one organised file. FR DataSync makes it
            easier to manage farmer records without manually comparing multiple files.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ==================================================
# SESSION STATE
# ==================================================
if "last_downloaded_fingerprint" not in st.session_state:
    st.session_state.last_downloaded_fingerprint = None

if "latest_metric_value" not in st.session_state:
    st.session_state.latest_metric_value = None

if "process_fingerprint" not in st.session_state:
    st.session_state.process_fingerprint = None

if "show_review_form" not in st.session_state:
    st.session_state.show_review_form = False


# ==================================================
# HELPERS
# ==================================================
def safe_read_excel(file, required_columns=None):
    df = pd.read_excel(file)

    if required_columns:
        missing = [column for column in required_columns if column not in df.columns]
        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(missing)}"
            )

    return df


def get_files_fingerprint(files):
    hasher = hashlib.sha256()

    for file in files:
        hasher.update(file.name.encode())
        hasher.update(str(file.size).encode())
        hasher.update(file.getvalue())

    return hasher.hexdigest()


# ==================================================
# TiDB CONNECTION
# ==================================================
@st.cache_resource
def get_ca_cert_path():
    cert = st.secrets["TIDB_SSL_CA"]
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
    temp.write(cert.encode())
    temp.close()
    return temp.name


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

    try:
        cur.execute(
            """
            UPDATE app_counter
            SET counter_value = counter_value + 1
            WHERE counter_name = %s
            """,
            (counter_name,)
        )
        conn.commit()

        cur.execute(
            """
            SELECT counter_value
            FROM app_counter
            WHERE counter_name = %s
            """,
            (counter_name,)
        )

        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Counter '{counter_name}' was not found.")

        return row[0]
    finally:
        cur.close()


def get_counter_value(counter_name):
    conn = get_tidb_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT counter_value
            FROM app_counter
            WHERE counter_name = %s
            """,
            (counter_name,)
        )

        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Counter '{counter_name}' was not found.")

        return row[0]
    finally:
        cur.close()


# ==================================================
# FILE UPLOADERS
# ==================================================
fr_files = st.file_uploader(
    "📁 Upload Unclaimed Excel Files",
    type="xlsx",
    accept_multiple_files=True,
    key="unclaimed_uploader"
)

bh_files = st.file_uploader(
    "📁 Upload Bheema Excel Files",
    type="xlsx",
    accept_multiple_files=True,
    key="bheema_uploader"
)


# ==================================================
# RESET STATE WHEN FILES ARE CLEARED
# ==================================================
if not fr_files or not bh_files:
    st.session_state.last_downloaded_fingerprint = None
    st.session_state.process_fingerprint = None
    st.session_state.show_review_form = False


# ==================================================
# PROCESS BUTTON
# ==================================================
files_ready = bool(fr_files) and bool(bh_files)
current_fingerprint = (
    get_files_fingerprint(fr_files + bh_files)
    if files_ready
    else None
)

if st.button(
    "🚀 Process Files",
    disabled=not files_ready,
    use_container_width=True
):
    st.session_state.process_fingerprint = current_fingerprint
    st.session_state.show_review_form = False

if not files_ready:
    st.info("👆 Upload both Unclaimed and Bheema Excel files, then click Process Files.")
elif st.session_state.process_fingerprint != current_fingerprint:
    st.info("✅ Files uploaded. Click Process Files to start.")


processed_df = None


# ==================================================
# MAIN EXCEL PROCESSING
# ==================================================
if files_ready and st.session_state.process_fingerprint == current_fingerprint:
    try:
        fr_dfs = [safe_read_excel(file) for file in fr_files]
        df_fr = pd.concat(fr_dfs, ignore_index=True)

        bheema_required_columns = [
            "VillName",
            "PPBNO",
            "FarmerName_Tel",
            "FatherName_Tel",
            "AadharId",
            "MobileNo",
            "EnrollmenStatus"
        ]

        bh_dfs = [
            safe_read_excel(file, required_columns=bheema_required_columns)
            for file in bh_files
        ]
        df_bh = pd.concat(bh_dfs, ignore_index=True)

        unclaimed_required_columns = [
            "Bucket ID",
            "Village LGD Code",
            "Village Name",
            "Farmer Name",
            "Identifier Name",
            "Survey Number",
            "Sub Survey Number"
        ]

        missing_unclaimed = [
            column for column in unclaimed_required_columns
            if column not in df_fr.columns
        ]

        if missing_unclaimed:
            raise ValueError(
                "Missing required columns in Unclaimed file: "
                + ", ".join(missing_unclaimed)
            )

        left_on = ["Village Name", "Farmer Name", "Identifier Name"]
        right_on = ["VillName", "FarmerName_Tel", "FatherName_Tel"]

        df_fr[left_on] = df_fr[left_on].astype(str).apply(
            lambda column: column.str.strip().str.lower()
        )
        df_bh[right_on] = df_bh[right_on].astype(str).apply(
            lambda column: column.str.strip().str.lower()
        )

        merged = df_fr.merge(
            df_bh,
            left_on=left_on,
            right_on=right_on,
            how="left"
        )

        processed_df = merged.groupby(
            ["Bucket ID", "Village LGD Code"],
            dropna=False
        ).agg({
            "Village Name": lambda values: ", ".join(
                str(value) for value in values.dropna().unique()
            ),
            "Farmer Name": "last",
            "Identifier Name": "last",
            "AadharId": "last",
            "MobileNo": "last",
            "PPBNO": "last",
            "Survey Number": lambda values: ", ".join(
                str(value) for value in values.dropna().unique()
            ),
            "Sub Survey Number": lambda values: ", ".join(
                str(value) for value in values.dropna().unique()
            ),
            "EnrollmenStatus": "last"
        }).reset_index()

        processed_df.drop(columns=["Village LGD Code"], inplace=True)

        st.success("✅ File processed successfully.")

        # Custom cards avoid theme-based white-on-white text in st.metric.
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
                <div class="custom-metric-card">
                    <div class="metric-title">📁 Unclaimed records</div>
                    <div class="metric-number">{len(df_fr):,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="custom-metric-card">
                    <div class="metric-title">🛡️ Bheema records</div>
                    <div class="metric-number">{len(df_bh):,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="custom-metric-card">
                    <div class="metric-title">✅ Final merged records</div>
                    <div class="metric-number">{len(processed_df):,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            """
            <h3 style="
                color: #1b5e20 !important;
                background-color: #e8f5e9;
                border-left: 6px solid #2e7d32;
                border-radius: 10px;
                padding: 12px 16px;
                margin-top: 20px;
                margin-bottom: 12px;
                font-weight: 800;
            ">
                📋 Preview of merged farmer records
            </h3>
            """,
            unsafe_allow_html=True
        )

        preview_df = processed_df.head(5).style.set_properties(**{
            "background-color": "#ffffff",
            "color": "#16351a",
            "border-color": "#dcedc8"
        }).set_table_styles([
            {
                "selector": "th",
                "props": [
                    ("background-color", "#2e7d32"),
                    ("color", "#ffffff"),
                    ("font-weight", "800")
                ]
            }
        ])

        st.dataframe(
            preview_df,
            use_container_width=True,
            hide_index=True
        )

    except Exception as error:
        st.error(f"⚠️ There is an issue with the Excel file: {error}")


# ==================================================
# DOWNLOAD + COUNTER
# ==================================================
if processed_df is not None:
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        processed_df.to_excel(
            writer,
            index=False,
            sheet_name="All_Villages"
        )

    fingerprint = get_files_fingerprint(fr_files + bh_files)

    if st.download_button(
        label="⬇️ Download Full Excel Report",
        data=buffer.getvalue(),
        file_name="Full_Farmer_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    ):
        st.session_state.show_review_form = True

        if st.session_state.last_downloaded_fingerprint != fingerprint:
            try:
                new_value = increment_counter("file_process_count")
                st.session_state.last_downloaded_fingerprint = fingerprint
                st.session_state.latest_metric_value = new_value
                st.toast("✅ Download recorded successfully", icon="✅")
            except Exception:
                st.toast(
                    "⚠️ Download completed, but the counter update failed.",
                    icon="⚠️"
                )


# ==================================================
# SHOW PROCESSING COUNTER
# ==================================================
if st.session_state.latest_metric_value is not None:
    st.metric(
        "📊 Total files processed till now",
        st.session_state.latest_metric_value
    )
else:
    try:
        current_value = get_counter_value("file_process_count")
        st.metric("📊 Total files processed till now", current_value)
    except Exception:
        pass


# ==================================================
# REVIEW & FEEDBACK
# ==================================================
if st.session_state.show_review_form:
    st.markdown(
        """
        <div class="review-card">
            <h2>⭐ Thank You for Using FR DataSync</h2>
            <p>
                Your Excel report is ready. Please take one minute to share your experience,
                report an Excel issue, or suggest a useful new feature for agriculture field teams.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    google_form_url = "https://forms.gle/g2EJh29zDgFJPCWi9"
    components.iframe(google_form_url, height=420, scrolling=True)

    st.markdown(
        """
        <p class="review-note">
            Your feedback helps improve FR DataSync for farmer record management.
        </p>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# COMPACT FOOTER
# ==================================================
PORTFOLIO_URL = "https://apkanisandeep01.github.io/my-portfolio/"
GITHUB_URL = "https://github.com/apkanisandeep01"
LINKEDIN_URL = "https://www.linkedin.com/in/sandeep-data-analyst-uk"
CONTACT_EMAIL = "apkansiandeep00@gmail.com"
APP_VERSION = "v1.0"

footer_links = f"""
<a href="{PORTFOLIO_URL}" target="_blank" rel="noopener noreferrer">🌐 Portfolio</a>
"""

if GITHUB_URL:
    footer_links += f"""
    <a href="{GITHUB_URL}" target="_blank" rel="noopener noreferrer">💻 GitHub</a>
    """

if LINKEDIN_URL:
    footer_links += f"""
    <a href="{LINKEDIN_URL}" target="_blank" rel="noopener noreferrer">🔗 LinkedIn</a>
    """

if CONTACT_EMAIL:
    footer_links += f"""
    <a href="mailto:{CONTACT_EMAIL}">✉️ Contact</a>
    """

footer_html = f"""
<style>
    .fr-footer {{
        margin-top: 2rem;
        padding: 16px 18px 12px;
        border-radius: 14px;
        background: linear-gradient(135deg, #0f2e13 0%, #1b5e20 100%);
        color: #d7ead7;
        text-align: center;
        box-shadow: 0 8px 20px rgba(15, 46, 19, .20);
    }}

    .fr-footer .brand {{
        font-size: 1.05rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 2px;
    }}

    .fr-footer .tagline {{
        font-size: .78rem;
        color: #a9d0a9;
        margin-bottom: 8px;
    }}

    .fr-footer .dev {{
        font-size: .8rem;
        color: #e6f2e6;
    }}

    .fr-footer .dev b {{
        color: #ffffff;
    }}

    .fr-footer .links {{
        margin-top: 9px;
    }}

    .fr-footer .links a {{
        display: inline-block;
        margin: 3px 4px;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: .75rem;
        font-weight: 600;
        color: #ffffff !important;
        text-decoration: none;
        background: rgba(255, 255, 255, .10);
        border: 1px solid rgba(255, 255, 255, .20);
    }}

    .fr-footer .links a:hover {{
        background: #43a047;
        border-color: #43a047;
    }}

    .fr-footer .features {{
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 10px;
        font-size: .7rem;
    }}

    .fr-footer .features span {{
        background: rgba(255, 255, 255, .08);
        padding: 3px 8px;
        border-radius: 7px;
        color: #e6f2e6;
    }}

    .fr-footer .bottom {{
        margin-top: 10px;
        padding-top: 8px;
        border-top: 1px solid rgba(255, 255, 255, .12);
        font-size: .68rem;
        color: #92b892;
    }}
</style>

<div class="fr-footer">
    <div class="brand">🌾 FR DataSync</div>
    <div class="tagline">Smart farmer record merging for agriculture field teams</div>
    <div class="dev">Developed by <b>Sandeep Kumar Apkani</b></div>
    <div class="links">{footer_links}</div>
    <div class="features">
        <span>⚡ Fast merging</span>
        <span>🧹 Duplicate removal</span>
        <span>🔒 Files not stored</span>
        <span>📊 Excel ready</span>
    </div>
    <div class="bottom">© {datetime.now().year} FR DataSync · {APP_VERSION} · Made with ❤️ for Users</div>
</div>
"""

try:
    st.html(footer_html)
except AttributeError:
    st.markdown(footer_html, unsafe_allow_html=True)
