import streamlit as st
import pandas as pd

import os

# -----------------------------------------------------------------------------
# 1. Page Setup & Data Extraction
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Electricity Demand Analytics & Forecasting',
    layout='wide',
    initial_sidebar_state='collapsed'
)

st.title('COMING SOON', text_alignment='center')
st.divider()

# Data extraction
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    return df

try:
    df = load_data(os.path.abspath('data_processing/data/demand_electricty_generation_mlready.csv'))
except:
    st.error('Data not found, try again later')
    st.stop()