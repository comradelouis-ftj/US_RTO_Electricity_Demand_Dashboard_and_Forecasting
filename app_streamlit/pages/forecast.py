import streamlit as st
import pandas as pd

import os

from functions.functions_forecast_page import preprocess_historical_vals, forecast_24_h, visualize_forecast

import torch
from pytorch_forecasting import TemporalFusionTransformer

# -----------------------------------------------------------------------------
# 1. Page Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title='Electricity Demand Analytics & Forecasting',
    layout='wide',
    initial_sidebar_state='collapsed'
)

st.title('US RTO Electricity Demand Forecast')
st.divider()

# -----------------------------------------------------------------------------
# 2. Data Extraction & Preprocessing
# -----------------------------------------------------------------------------

# Data extraction - tells streamlit to re-fetch latest data every one hour
@st.cache_data(ttl=3600)
def load_data(path):
    df = pd.read_csv(path)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    df_n_lagged = preprocess_historical_vals(df)
    return df, df_n_lagged

@st.cache_data
def load_model_and_params():
    path_modelling = os.path.abspath('modelling')
    path_model = os.path.join(os.path.join(path_modelling, 'models'), 'tft_best.ckpt')
    path_dataset_params = os.path.join(path_modelling, 'dataset_params.pt')

    params = torch.load(path_dataset_params, weights_only=False)
    model = TemporalFusionTransformer.load_from_checkpoint(path_model)
    return params, model

try:
    df, df_n_lagged = load_data('https://raw.githubusercontent.com/comradelouis-ftj/US_RTO_Electricity_Demand_Dashboard_and_Forecasting/refs/heads/master/app_streamlit/data/demand_electricty_generation_mlready.csv')
    params, model = load_model_and_params()
except:
    st.error('Data/model not found, try again later')
    st.stop()

# -----------------------------------------------------------------------------
# 3. RTO Selection
# -----------------------------------------------------------------------------
dict_rtos = {}
for rto_name in df['rto_full_name'].unique():
    dict_rtos[rto_name] = df[df['rto_full_name']==rto_name]['rto_id'].unique()[0]

col1, col2 = st.columns([1, 1,], vertical_alignment='center')
with st.container():
    with st.form('RTO Selection'):
        rto = st.selectbox(
            'Select RTO', 
            options=df['rto_full_name'].unique(),
            index=0
        )
        show = st.form_submit_button('Show Forecast', use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 4. Showing Forecast Result
# -----------------------------------------------------------------------------
if not show:
    st.info('💡 Select RTO, then click show to show 24-hour forecast from the most recent timestamp')
else:
    rto_id = dict_rtos[rto]
    out_raw, x, _, forecast = forecast_24_h(df_n_lagged, rto_id=rto_id, params=params, model=model)
    st.subheader(f'**24-Hour Forecast - {forecast['time_stamp'].min()} to {forecast['time_stamp'].max()}**', text_alignment='center')
    st.divider()

    with st.container(width='stretch'):
        st.markdown(f'**Forecast Details**', text_alignment='center')
        forecast_cp = forecast[forecast['label']=='forecast'].copy().reset_index(drop=True)
        forecast_cp['hours'] = [f'hour {i+1}' for i in forecast_cp.index]
        forecast_cp['time_stamp'] = forecast_cp['time_stamp'].astype('str')
        forecast_cp['demand_mwh'] = forecast_cp['demand_mwh'].round(2).astype('str')

        st.dataframe(forecast_cp[['hours', 'time_stamp', 'demand_mwh']].set_index('hours').T, width='stretch')

    with st.container(border=1):
        st.markdown(f'**Demand Forecast Line Chart**', text_alignment='center')
        chart = visualize_forecast(forecast)
        st.altair_chart(chart, width='stretch')