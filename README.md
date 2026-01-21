# 🌾 FR Agri Excel Formatter & Merger

A Streamlit-based web application to **merge, deduplicate, and enrich farmer records** by combining **Unclaimed (FR)** Excel files with **Rythu Bheema** Excel data.  
The app also maintains a **persistent usage counter** using **TiDB** and provides a downloadable consolidated Excel report.

---

## 🚀 Live Application

👉 **Streamlit App URL**  
(https://fragri.streamlit.app/)

---

## ✨ Features

- Upload **multiple FR (Unclaimed)** Excel files
- Upload **multiple Rythu Bheema** Excel files
- Intelligent merge using:
  - Village Name
  - Farmer Name
  - Identifier / Father Name
- Deduplication using **Bucket ID + Village LGD Code**
- Fetches and attaches:
  - Aadhaar Number
  - Mobile Number
  - PPB Number
- Generates a **single consolidated Excel report**
- **Persistent counter** to track total processing runs
- User-friendly error messages for wrong or invalid files
- Secure database credentials using **Streamlit Secrets**

---

## 🧰 Tech Stack

- **Python**
- **Streamlit**
- **Pandas**
- **TiDB (MySQL-compatible)**
- **xlsxwriter**
- **openpyxl**

---
