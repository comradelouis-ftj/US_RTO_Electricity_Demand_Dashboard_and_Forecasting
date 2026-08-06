# Electricity Demand Dashboard and Forecasting
---
A web application for showing and forecasting electricity demand of United States RTOs (Regional Transmission Organization) using data from 2023 up to the present date. This is achieved by storing and periodically updating the data within a local database. The data itself is extracted from the EIA API ([found here](https://www.eia.gov/opendata/)). The web dashboard itself could be used to view US RTO demand dynamics from the past three years up to the current date, as well as how said RTOs generate its electricity, utilizing different types of fuels such as coal, oil, and natural gas. Aside from the web dashboard, the other main output of this project is electricity demand forecasting for the specific RTOs (**COMING SOON**).

---

## 📌 Local Set-Up Requirements

1. Create a virtual environment by running: 'python -m venv venv'
2. Install all proper dependencies (use 'pip install -r requirements.txt').
3. Make sure that postgresql is installed in order to store the datasets.
4. Create a .env file which should store your EIA API key ([found here](https://www.eia.gov/opendata/)), postgresql password, and postgresql username
5. Run the .ipynb file which could be found at data_processing/extraction.ipynb.

**Note:**
- It would be even better if you can set up a CRON job using the extract_updated_data.bat file in data_processing folder, which would allow the computer (granted, you need internet) to extract and store updated data automatically for you.
- As with other APIs, the EIA API does have its limitations and require you signing in, so make sure to check out its documentations.

---

## 📖 Project Background

This project's objectives are to implement data engineering concepts on a relatively small scale, as well as to use this in order to feed data into a machine learning model. This would allow automation of data extraction, especially in terms of updating/inserting (upserts) data for the model and the web application. Based on this, the main components of this app are as follows:
1. **Data Processing:** Applies ingestion and transformation of data within the database environment (PostgreSQL), serving said data within a database view to allow better speed and processing efficiency.
2. **Web Application:** Utilizing streamlit to show both electricity demand and electricity generation analytics via a dashboard, as well as showing a forecasting functionality (**COMING SOON**).
3. **Modelling:** (**COMING SOON**)

---

## 📱 Web Application Features and Functionalities
1. **Electricity Demand Dashboard:** Shows electricity demand and generation (aggregated by fuel types such as coal, oil, and natural gas) for several RTOs across the US, showing the contribution of specific fuel types to electricity generation, and how electricity demand changes overtime. The RTO and timestamps are derived from user inputs, and can be manipulated by users.
2. **Electricity Demand Forecasting:** (**COMING SOON**)

---

## 📊 Data Engineering Functions
The data engineering functions could be found within the data_processing folder, within the file 'functions.py'. In this file, there are python functions which could be divided into several categories:
1. **Electricity Demand Extraction:** Utilized in the ingestion process, extracts electricity demand from the EIA API.
2. **Electricity Output Extraction:** Utilized in the ingestion process, extracts electricity output for every fuel type within each RTO from the EIA API.
3. **Storage Into Database:** Utilized to store the extracted data into the database. These functions are also used to automate the creation/update of storage layers, where the raw data itself (converted into tabular format) would be stored within the 'landing' layer. The new data inserted to this layer are extracted, transformed via database queries, then stored into the 'staging' layer. The last layer, 'aggregate' layer, extracts aggregated and joined data from the 'staging' layer via a PostgreSQL materialized view.
