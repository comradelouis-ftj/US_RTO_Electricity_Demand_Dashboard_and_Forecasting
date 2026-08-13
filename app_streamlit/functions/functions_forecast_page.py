import pandas as pd
import numpy as np

import altair as alt

from pytorch_forecasting import TimeSeriesDataSet

# Function for Creating Known Future Values for Prediction 
def extract_future_vals(rto_data, params):
    # The known future values include: time index, the RTO ID, month, day of week, day of month, and hour

    max_time_idx = rto_data['time_idx'].max() # extracts maximum time index from predictor
    dates_list = pd.date_range(rto_data['time_stamp'].max()+pd.Timedelta(hours=1), periods=24, freq='h') # creates date range for known future values

    future_items = pd.DataFrame({
        'time_idx': [int(max_time_idx+i) for i in range(1, 25)], # stores time index, added chronologically one after the other
        'rto_id': [rto_data['rto_id'].iloc[0]] * 24, # RTO ID
        'time_stamp': dates_list, # raw timestamp
        'month': dates_list.month.astype('str'), # month number, converted to string for model inference
        'day_of_week': dates_list.day_of_week.astype('str'), # day of week number, converted to string for model inference
        'day_of_month': dates_list.day.astype('str'), # day of month number, converted to string for model inference
        'hour': dates_list.hour.astype('str') # hour, converted to string for model inference
    })

    # Since this dataframe would be appended to the predictor dataframe (consisting of historical values of 48 hours back), the unknown numerical
    # values are filled in with zeroes (would not distrub the model, as it only selects the specified known future values)
    unknown_cols = params['time_varying_unknown_reals']
    for col in unknown_cols:
        future_items[col] = 0.0

    return future_items # returns the dataframe

# Function for Preprocessing the Current Dataframe
def preprocess_historical_vals(df_n):
    # This dictionary stores the details of required lag values and rolling average values for preprocessing
    temp = {
        'demand_mwh': { 
            'lag': [1, 2, 24], 'r_avg': []
        },
        'mwh_ng': {
            'lag': [1, 2, 24], 'r_avg': []
        },
        'mwh_nuc': {
            'lag': [1, 2], 'r_avg': [24]
        },
        'mwh_wnd': {
            'lag': [1, 2], 'r_avg': [24]
        },
        'mwh_sun': {
            'lag': [1, 2, 24], 'r_avg': []
        },
        'mwh_col': {
            'lag': [1, 2, 24], 'r_avg': [24]
        },
        'mwh_wat': {
            'lag': [1, 2, 24], 'r_avg': []
        },
        'mwh_oil': {
            'lag': [1, 2], 'r_avg': [24]
        },
        'mwh_oth': {
            'lag': [1, 2, 23], 'r_avg': []
        },
    }

    df_n_lagged = df_n.copy() # copies the original dataframe, so the original dataframe will not be manipulated
    list_data = [] # stores the preprocessed dataframe for each RTO

    # Loops through every RTO and its dataframes, then applies the lag and moving average, as well as creating specific time indexes and
    # removing any null values caused by creating lag and moving average features
    for rto in df_n_lagged['rto_id'].unique():
        current = df_n_lagged[df_n_lagged['rto_id']==rto].copy().sort_values(by='time_stamp', ascending=True).reset_index(drop=True)
        if rto=='ERCO' or rto=='MISO':
            current['mwh_oil'] = current['mwh_oil'].fillna(0)
        current['time_idx'] = np.tile(np.arange(len(current)), 1)
        current = current[['time_idx'] + [col for col in df_n_lagged.columns]]
        for feature, shifts in temp.items():
            lag = shifts['lag']
            rolling_avg = shifts['r_avg']
            for l in lag:
                current[f'{feature}_lag{l}'] = current[feature].shift(l)
            for avg in rolling_avg:
                current[f'{feature}_rolling{avg}'] = current[feature].rolling(window=avg).mean()
        current.dropna(inplace=True)
        list_data.append(current)

    df_n_lagged = pd.concat(list_data, ignore_index=True) # combining all dataframes within the list

    # Creating date features
    df_n_lagged['month'] = df_n_lagged['time_stamp'].dt.month.astype(str)
    df_n_lagged['day_of_week'] = df_n_lagged['time_stamp'].dt.day_of_week.astype(str)
    df_n_lagged['day_of_month'] = df_n_lagged['time_stamp'].dt.day.astype(str)
    df_n_lagged['hour'] = df_n_lagged['time_stamp'].dt.hour.astype(str)

    return df_n_lagged # returns the preprocessed dataframe

# Function for Extracting Predictor Dataframe
def extract_predictors(df_n_lagged, rto_id, params):
    rto_data = df_n_lagged[df_n_lagged['rto_id']==rto_id].iloc[-48:] # takes the last 48 hours of observations from the preprocessed dataframe
    data = pd.concat([rto_data,extract_future_vals(rto_data, params)], ignore_index=True) # combines the preprocessed dataframe with known future values
    return data # returns combined dataframe

# Function for Executing Forecast
def forecast_24_h(df_n_lagged, rto_id, params, model):
    rto_data_cut = extract_predictors(df_n_lagged, rto_id=rto_id, params=params) # creating dataframe for model input

    # Conversion of the input dataframe to suitable format for the inference process
    new_set = TimeSeriesDataSet.from_parameters(params, rto_data_cut, predict=True, allow_missing_timesteps=True)

    # Model inference
    res = model.predict(new_set, return_x=True, return_y=True, trainer_kwargs={'logger': False, 'enable_progress_bar': False, 'enable_model_summary': False})

    # Creating dataframe, consisting of the historical demand value (past 48 hours, labeled 'historical value') and the forecasted values (labeled 'forecast')
    result_df = rto_data_cut[['time_stamp', 'demand_mwh']]
    result_df['label'] = 'historical value'
    result_df.loc[48:, 'demand_mwh'] = [float(v) for v in res.output[0]]
    result_df.loc[48:, 'label'] = 'forecast'

    return res.output[0], res.x, res.y, result_df # returns the raw inference output, predictors, known future values, and the clean dataframe of inputs + forecast

def visualize_forecast(forecast_data):
    # Converts the last 'historical value'-labeled data point to 'forecast'
    last_hist_row = forecast_data[forecast_data['label'] == 'historical value'].iloc[[-1]].copy()
    last_hist_row['label'] = 'forecast'

    # Concats the newly converted row into the dataframe, then orders it by timestamp so said row is now placed
    # before any of the 'forecast' rows, forcing altair (later) to make it so the plot between historical values and
    # forecast data points to connect
    forecast_data_n = pd.concat([forecast_data, last_hist_row], ignore_index=True).sort_values('time_stamp')

    # Building streamlit-compatible altair chart
    chart = alt.Chart(forecast_data_n).mark_line(
        point={'size': 150, 'filled': True}
    ).encode(
        x=alt.X('time_stamp:T', title='Time'),
        y=alt.Y('demand_mwh:Q', title='Demand (MWh)'),
        color=alt.Color(
            'label:N', 
            scale=alt.Scale(
                domain=['historical value', 'forecast'],
                range=['blue', 'green']
            ),
            legend=alt.Legend(title="Label")
        ),
        detail='block_id:N', # prevents the lines from overlapping with each other
        tooltip=[
            alt.Tooltip('time_stamp:T', title='Timestamp', format='%Y-%m-%d %H:%M:%S'),
            alt.Tooltip('demand_mwh:Q', title='Demand (MWh)', format='.2f'),
            alt.Tooltip('Label:N')
        ]
    ).properties(
        height=450, width=800
    ).interactive() # allow interactiveness

    return chart # returns ready-to-use chart