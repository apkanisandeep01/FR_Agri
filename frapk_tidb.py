import streamlit as st
import pandas as pd
import io
import mysql.connector
import tempfile

# --------------------------------------------------
# Page config (same as your working app)
# --------------------------------------------------
st.set_page_config(
    page_title="FR Agri Excel Merger",
    page_icon="❤️",
    layout="wide"
)

st.title("🌾 FR Excel formatter - Merger (TiDB Test)")
st.markdown("Upload multiple Excel files to deduplicate and merge to fetch Aadhar Card.")

# --------------------------------------------------
# SAFE EXCEL READER (prevents redacted errors)
# --------------------------------------------------
def safe_read_excel(file, required_columns=None):
    try:
        df = pd.read_excel(file)

        if required_columns:
            missing = [c for c in required_columns if c not in df.columns]
            if missing:
                st.error(
                    "❌ Please check the Rythu Bheema file once again.\n\n"
                    f"Missing columns: {', '.join(missing)}"
                )
                st.stop()

        return df

    except Exception:
        st.error(
            "❌ Please check the files once again.\n\n"
            "• Ensure correct Excel file is uploaded\n"
            "• Ensure files are uploaded in the correct place"
        )
        st.stop()

# --------------------------------------------------
# TiDB SSL CA handling
# --------------------------------------------------
@st.cache_resource
def get_ca_cert_path():
    cert = st.secrets["TIDB_SSL_CA"]
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(cert.encode())
    temp.close()
    return temp.name

# --------------------------------------------------
# TiDB connection
# --------------------------------------------------
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

# --------------------------------------------------
# Counter function
# --------------------------------------------------
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

# --------------------------------------------------
# File upload (same UI as your app)
# --------------------------------------------------
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

# --------------------------------------------------
# Main processing logic (UNCHANGED logic)
# --------------------------------------------------
if fr_files and bh_files:

    # --- FR files ---
    dfs = [safe_read_excel(file) for file in fr_files]
    df_fr = pd.concat(dfs, ignore_index=True)
    st.divider()

    # --- Bheema files ---
    b_dfs = [
        safe_read_excel(
            file,
            required_columns=[
                'VillName',
                'PPBNO',
                'FarmerName_Tel',
                'FatherName_Tel',
                'AadharId',
                'MobileNo'
            ]
        )
        for file in bh_files
    ]
    df_bh = pd.concat(b_dfs, ignore_index=True)

    # --- Join columns ---
    left_on = ['Village Name', 'Farmer Name', 'Identifier Name']
    right_on = ['VillName', 'FarmerName_Tel', 'FatherName_Tel']

    df_fr[left_on] = df_fr[left_on].astype(str).apply(
        lambda col: col.str.strip().str.lower()
    )
    df_bh[right_on] = df_bh[right_on].astype(str).apply(
        lambda col: col.str.strip().str.lower()
    )

    merged = df_fr.merge(
        df_bh,
        left_on=left_on,
        right_on=right_on,
        how='left'
    )

    st.header('Processed file')
    st.divider()

    processed_df = merged.groupby(
        ['Bucket ID', 'Village LGD Code']
    ).agg({
        "Village Name": lambda x: ", ".join(map(str, pd.unique(x))),
        "Farmer Name": "last",
        "Identifier Name": "last",
        "Farmer Mobile Number": "last",
        "AadharId": "last",
        "MobileNo": "last",
        "PPBNO": "last",
        "Survey Number": lambda x: ", ".join(map(str, pd.unique(x))),
        "Sub Survey Number": lambda x: ", ".join(map(str, pd.unique(x)))
    }).reset_index()

    processed_df['Farmer Mobile Number'] = processed_df['Farmer Mobile Number'].astype(str)
    processed_df['AadharId'] = processed_df['AadharId'].astype('Int64').astype(str)
    processed_df['MobileNo'] = processed_df['MobileNo'].astype('Int64').astype(str)

    processed_df.drop(columns=['Village LGD Code'], inplace=True)
    processed_df = processed_df.rename(
        {
            'Farmer Mobile Number': 'FR Mobile No',
            'MobileNo': 'Bheema Mobile No'
        },
        axis=1
    )

    st.write(processed_df.head())

    # --------------------------------------------------
    # Increment counter ONLY on success
    # --------------------------------------------------
    run_count = increment_counter("file_process_count")
    st.metric("📊 Total Processing Runs", run_count)

    st.info("📦 Combined File Ready")

    # --- Download ---
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        processed_df.to_excel(writer, index=False, sheet_name='All_Villages')

    st.download_button(
        label="Download Full Excel",
        data=excel_buffer.getvalue(),
        file_name="Full_Farmer_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

else:
    st.info("Waiting for files to be uploaded...")
