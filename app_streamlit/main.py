import streamlit as st

st.set_page_config(
    page_title='Electricity Demand Analytics & Forecasting',
    layout='wide',
    initial_sidebar_state='collapsed'
)

dashboard = st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True)
prediction = st.Page("pages/forecast.py", title="Prediction", icon="🔮")

pages = st.navigation({
    'dashboard': [dashboard],
    'forecast': [prediction]
})
pages.run()