import streamlit as st
import pandas as pd
import io
import zipfile

st.set_page_config(page_title="FR Agri Excel Merger", page_icon="❤️", layout="wide")

st.title("🌾 FR Excel formatter - Meger")
st.markdown("Upload multiple Excel files to deduplicate and merge to fetch Aadhar Card.")

fr_files = st.file_uploader("Upload Unclaimed files", type="xlsx", accept_multiple_files=True)
bh_files = st.file_uploader("Upload Bheema files", type="xlsx", accept_multiple_files=True)

if len(fr_files) > 0 and len(bh_files):
    dfs = [pd.read_excel(file) for file in fr_files]
    df_fr = pd.concat(dfs,ignore_index=True)
    # st.write(df_fr.head())
    st.divider()
    
    #bheema Files
    b_dfs = [pd.read_excel(file, usecols=['VillName','PPBNO','FarmerName_Tel','FatherName_Tel', 'AadharId', 'MobileNo']) for file in bh_files]
    df_bh = pd.concat(b_dfs,ignore_index=True)  
    # st.write(df_bh.head())

    # columns to clean
    left_on = ['Village Name', 'Farmer Name', 'Identifier Name']
    right_on = ['VillName', 'FarmerName_Tel', 'FatherName_Tel']
    
    # normalize join columns in df (left)
    df_fr[left_on] = df_fr[left_on].astype(str).apply(lambda col: col.str.strip().str.lower())
    
    # normalize join columns in bh (right)
    df_bh[right_on] = df_bh[right_on].astype(str).apply(lambda col: col.str.strip().str.lower())
    merged = df_fr.merge(df_bh, left_on=left_on, right_on=right_on, how='left')
    
    st.header('Processed file')
    # st.write(merged.head())

    st.divider()
    processed_df = merged.groupby(['Bucket ID', 'Village LGD Code']).agg({
        "Village Name": lambda x: ", ".join(map(str, pd.unique(x))),
        "Farmer Name": "last",
        "Identifier Name": "last",
        "Farmer Mobile Number": "last",
        "AadharId": 'last',
        "MobileNo": 'last',
        "PPBNO": 'last',
        "Survey Number": lambda x: ", ".join(map(str, pd.unique(x))),
        "Sub Survey Number": lambda x: ", ".join(map(str, pd.unique(x)))
    }).reset_index()
    processed_df['Farmer Mobile Number'] = processed_df['Farmer Mobile Number'].astype(str)
    processed_df['AadharId'] = processed_df['AadharId'].astype('Int64').astype(str)
    processed_df['MobileNo'] = processed_df['MobileNo'].astype('Int64').astype(str)

    processed_df.drop(columns=['Village LGD Code'], inplace=True)
    processed_df =processed_df.rename({'Farmer Mobile Number':'FR Mobile No', 'MobileNo':'Bheema Mobile No'}, axis=1)
    
    st.write(processed_df.head())

    st.info("📦 **Combined File Ready**")
    
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
