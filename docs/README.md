# Electricity Demand Dashboard and Forecasting
---
A web application for showing and forecasting electricity demand of United States RTOs (Regional Transmission Organization) using data from 2023 up to the present date. This is achieved by storing and periodically updating the data within a local database. The data itself is extracted from the EIA API ([found here](https://www.eia.gov/opendata/)). The web dashboard itself could be used to view US RTO demand dynamics from the past three years up to the current date, as well as how said RTOs generate its electricity, utilizing different types of fuels such as coal, oil, and natural gas. Aside from the web dashboard, the other main output of this project is electricity demand forecasting for the specific RTOs for the next 24 hours from the most recent and valid observation.

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

This project's objectives are to implement data engineering concepts on a relatively small scale, as well as to use this in order to feed data into a machine learning model. This would allow automation of data extraction, especially in terms of updating/inserting (upserts) data for the model and the web application. Based on this, the main components of this project are as follows:
1. **Data Processing:** Applies ingestion and transformation of data within the database environment (PostgreSQL), serving said data within a database view to allow better speed and processing efficiency.
2. **Web Application:** Utilizing streamlit to show both electricity demand and electricity generation analytics via a dashboard, as well as showing a forecasting functionality.
3. **Modelling:** Utilizing ARIMAX as a baseline and TFT (Temporal Fusion Transformer) as the main forecasting model, deployed into the streamlit web application.

---

## 📱 Web Application Features and Functionalities
1. **Electricity Demand Dashboard:** Shows electricity demand and generation (aggregated by fuel types such as coal, oil, and natural gas) for several RTOs across the US, showing the contribution of specific fuel types to electricity generation, and how electricity demand changes overtime. The RTO and timestamps are derived from user inputs, and can be manipulated by users.
2. **Electricity Demand Forecasting:** Allows users to select the specific RTOs' demand which is to be forecasted for the next 24 hours. The forecast itself is based on the previous 48 observations (48 hours) that are considered valid (not missing much of its features).

---

## 📊 Data Engineering Functions
The data engineering functions could be found within the data_processing folder, within the file 'functions.py'. In this file, there are python functions which could be divided into several categories:
1. **Electricity Demand Extraction:** Utilized in the ingestion process, extracts electricity demand from the EIA API.
2. **Electricity Output Extraction:** Utilized in the ingestion process, extracts electricity output for every fuel type within each RTO from the EIA API.
3. **Storage Into Database:** Utilized to store the extracted data into the database. These functions are also used to automate the creation/update of storage layers, where the raw data itself (converted into tabular format) would be stored within the 'landing' layer. The new data inserted to this layer are extracted, transformed via database queries, then stored into the 'staging' layer. The last layer, 'aggregate' layer, extracts aggregated and joined data from the 'staging' layer via a PostgreSQL materialized view.


---

## 🧠 Model Details
1. **ARIMAX Model -->** Utilized as the baseline to compare against the TFT model. The ARIMAX model was able to achieve an average sMAPE of 6-18% across all RTOs, an MAE score of ~2000 to ~16000 for every RTOs, and an RMSE of ~2500 up to ~ 18400 for each RTOs. This model utilized all of the same features and preprocessing methods, except for the lookback window, which in the case of ARIMAX utilizes a 24-hour lookback window.
2. **TFT (Temporal Fusion Transformer) Model -->** Compared to ARIMAX was able to achieve a much more uniform result across all RTOs, with a sMAPE ranging from ~3% up to ~4.6%, RMSE of ~2000 to ~4900, and MAE of ~1200 to ~3600. This model utilized a lookback window of 48 hours, and is trained over 20 epochs using the sMAPE function as its loss function (details of loss curve shown within modelling.ipynb). Unlike the ARIMAX model, this model is trained across all the dataset, utilizing the RTO IDs as a static feature.

In general, TFT handily outperformed the ARIMAX model. Evaluation of these two models are done per RTO, as the data distribution between US RTOs differ. As mentioned earlier, the key metrics utilized in evaluationg the two models are as follows:
- sMAPE (Symmetric Mean Absolute Percentage Error) - used as the loss function for the TFT model, chosen since it is easy to interpret (outputs are in the form of percentages, the lower the better)
- MAE (Mean Absolute Error) - chosen because it shows the absolute average of errors (prediction overshoots/undershoots) in the original format & scale of the data.
- RMSE (Root Mean Squared Error) - also returns outputs in the original format & scale of the data, but is chosen since it gives higher penalties for larger errors, thus showing how the model is able to deal with outliers.

Note: both models utilized features lagged between 1 to 24 hours, as well as moving averages of 24 hours on certain features. The pre-processing steps taken to do this are shown in detail within modelling.ipynb. In total there are almost 40 features used in training both the baseline ARIMAX model and TFT model, its details can be viewed in the modelling.ipynb notebook

---

## Directory Summary

```
.
├── app_streamlit/
|   ├── data/
|   │   └── demand_electricty_generation_mlready.csv
|   ├── functions/
|   │   ├── extract_updated_data.bat
|   │   ├── extract_updated_data.py
|   │   ├── functions_extract_update.py
|   │   └── functions_forecast_page.py
|   ├── pages/
|   │   ├── dashboard.py
|   │   └── forecast.py
|   └── main.py
├── data_processing/
│   ├── data/
|   │   └── demand_electricty_generation_mlready.csv
|   ├── extraction.ipynb
|   └── functions.py
├── modelling/
|   ├── data/
|   │   └── demand_electricty_generation_mlready.csv
|   ├── models/
|   │   ├── log_tft/
|   │   │   └── version_0/
|   │   │       ├── hparams.yaml
|   │   │       └── metrics.csv
|   │   ├── last.ckpt
|   │   ├── tft_best.ckpt
|   │   └── tft_per_epoch.ckpt
|   ├── dataset_params.pt
|   └── modelling.ipynb
├── requirements.txt
└── .gitignore
```