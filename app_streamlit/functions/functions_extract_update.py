import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql

from dotenv import load_dotenv
import os
import requests

import datetime
import time

#########################################################################
# EXTRACTING HOURLY ELECTRICITY DEMAND
#########################################################################

# Extracting Specific RTO Demand
def request_region_data(start: str, end: str, api_key: str, institution: str, length: int=5000):
    print(f'Processing {institution}: start - {start}, end - {end}')
    curr_offset = 0 # how much offset would be used per request, done since the API only returns a maximum of 5000 records per request
    total = None # would store total records to be extracted

    # Stores the records returned by the API, consisting of an ID (made using the other items within the returned record), timestamp,
    # the RTO's ID, RTO's full name, and the exact hourly demand in MWh (Megawatt-hours)
    df_rto = {
        'id_demand': [],
        'time_stamp': [],
        'rto_name': [],
        'rto_full_name': [],
        'demand_mwh': []
    }

    while True:
        # This loop will continue, as long as the amount of records processed is not equal to the total number of records returned
        # by a request. The returned records from the API request will return a record, showing the actual amount of data returned
        # by the request which spans from the 'start' to 'end' date as specified by this functions parameter, although the API will
        # only return the first 5000+offset records
        try:
            # Parameters for the API request, specifying the order of records (ascending by period), time span, RTO, the amount of 
            # records returned, and the offset
            params = {
                'api_key': api_key,
                'frequency': 'hourly',
                'data[0]': 'value',
                'facets[respondent][]': institution,
                'facets[type][]': 'D',
                'start': start,
                'end': end,
                'sort[0][column]': 'period', 
                'sort[0][direction]': 'asc',
                'length': length,
                'offset': curr_offset
            }
            res = requests.get('https://api.eia.gov/v2/electricity/rto/region-data/data', params=params, timeout=30)
            res.raise_for_status() # raise error for certain response codes, i.e. 400/500
            if total is None:
                # Updates the total if total is None, by taking the 'total' variable from the API response
                total = int(res.json()['response']['total'])
                print(f'Total lines to process for {institution}: {total}')

            # Looping through all returned records, and appending the speific variables to the data dictionary
            for v in res.json()['response']['data']:
                df_rto['id_demand'].append(f'DER{v['respondent']}{v['period']}AW') # creating unique id for demand using record's RTO ID and timestamp
                df_rto['time_stamp'].append(v['period']) 
                df_rto['rto_name'].append(v['respondent'])
                df_rto['rto_full_name'].append(v['respondent-name'])
                df_rto['demand_mwh'].append(v['value'])

            # Case when the response's last record's timestamp is the same as the end date, or the amount of records processed
            # exceeds/is the same as the total returned records, the loop is stopped
            if res.json()['response']['data'][-1]['period']==end or len(df_rto['time_stamp'])>=total:
                print(f'processed {curr_offset+len(res.json()['response']['data'])} data points - {institution}')
                break

            print(f'processed {curr_offset+len(res.json()['response']['data'])} data points - {institution}')
            curr_offset+=5000 # increases the offset in every iteration
        except Exception as e:
            # If there is an error, i.e. due to a 400/500 code, the loop is delayed for 20 seconds, then continued
            print(f'Error due to {e}, retrying...')
            time.sleep(20)
            continue
            
    return pd.DataFrame(df_rto) # returns a pandas dataframe of the data dictionary

# Function for Extracting and Combining Hourly Demands of All RTOs (Regional Transmission Organizations)
def extract_demands_institutions(start:str, end:str, api_key:str, institutions: list, folder_name: str, max_workers: int=6):
    list_dfs = [] # would store a list of dataframes of hourly electricity demands for every RTO

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # This extracts electricity demands for all RTOs simultaneously (though depends on number of RTOs & allocated workers, set to a 
        # default of 6 for the amount of RTOs in the original project, which is 5 RTOs)
        results = {executor.submit(request_region_data, start, end, api_key, institution): institution for institution in institutions} # executes the extraction function for an RTO

        for res in as_completed(results):
            # When certain RTOs' records have finished being extracted, the resulting dataframe is appended to the list of dataframes
            list_dfs.append(res.result())

    df = pd.concat(list_dfs, axis=0, ignore_index=True) # combines all dataframes (by row) within the dataframes list into one dataframe

    # Storing the raw demands in .csv format
    path_datasets_raw = os.path.abspath(f'../data/{folder_name}')
    if not os.path.exists(path_datasets_raw):
        os.makedirs(path_datasets_raw)

    path_df = os.path.join(path_datasets_raw, f'demand_{folder_name}.csv')
    df.to_csv(path_df, index=False)
    print(f'Saved results to {path_df}')
    return df, path_df # returns the entire dataframe + thepath in which it is saved

#########################################################################
# EXTRACTING HOURLY ELECTRICITY OUTPUT
#########################################################################

# Function for Extracting Electricity Output for an RTO's Fuel Types
def request_fuel_type_data(start: str, end: str, api_key: str, institution: str, length: int=5000):
    print(f'Processing {institution}: start - {start}, end - {end}')
    curr_offset = 0 # how much offset would be used per request, done since the API only returns a maximum of 5000 records per request
    total = None # would store total records to be extracted

    # Stores the records returned by the API, consisting of an ID (made using the other items within the returned record), timestamp,
    # the RTO's ID, RTO's full name, fuel type id, fuel type name, and the exact hourly output in MWh (Megawatt-hours)
    df_rto = {
        'id_elec_generated': [],
        'time_stamp': [],
        'rto_name': [],
        'rto_full_name': [],
        'fuel_name': [],
        'fuel_full_name': [],
        'mwh_generated': []
    }

    while True:
        # This loop will continue, as long as the amount of records processed is not equal to the total number of records returned
        # by a request. The returned records from the API request will return a record, showing the actual amount of data returned
        # by the request which spans from the 'start' to 'end' date as specified by this functions parameter, although the API will
        # only return the first 5000+offset records
        try:
            # Parameters for the API request, specifying the order of records (ascending by period), time span, RTO, the amount of 
            # records returned, and the offset
            params = {
                'api_key': api_key,
                'frequency': 'hourly',
                'data[0]': 'value',
                'facets[respondent][]': institution,
                'start': start,
                'end': end,
                'sort[0][column]': 'period', 
                'sort[0][direction]': 'asc',
                'length': length,
                'offset': curr_offset
            }
            res = requests.get('https://api.eia.gov/v2/electricity/rto/fuel-type-data/data', params=params, timeout=30)
            res.raise_for_status() # raise error for certain response codes, i.e. 400/500
            if total is None:
                # Updates the total if total is None, by taking the 'total' variable from the API response
                total = int(res.json()['response']['total'])
                print(f'Total lines to process for {institution}: {total}')

            for v in res.json()['response']['data']:
                df_rto['id_elec_generated'].append(f'FER{v['respondent']}{v['fueltype']}{v['period']}AW') # the record's id, created using record RTO ID, fuel type ID, and timestamp
                df_rto['time_stamp'].append(v['period'])
                df_rto['rto_name'].append(v['respondent'])
                df_rto['rto_full_name'].append(v['respondent-name'])
                df_rto['fuel_name'].append(v['fueltype'])
                df_rto['fuel_full_name'].append(v['type-name'])
                df_rto['mwh_generated'].append(v['value'])

            # Case when the response's last record's timestamp is the same as the end date, or the amount of records processed
            # exceeds/is the same as the total returned records, the loop is stopped
            if res.json()['response']['data'][-1]['period']==end or len(df_rto['time_stamp'])>=total:
                print(f'processed {curr_offset+len(res.json()['response']['data'])} data points - {institution}')
                break

            print(f'processed {curr_offset+len(res.json()['response']['data'])} data points - {institution}')
            curr_offset+=5000 # increases offset for each iteration
        except Exception as e:
            # If there is an error, i.e. due to a 400/500 code, the loop is delayed for 20 seconds, then continued
            print(f'Error due to {e}, retrying...')
            #print(len(res.json()['response']['data']))
            time.sleep(20)
            continue
            
    return pd.DataFrame(df_rto) # returns a pandas dataframe containing the data dictionary in pandas dataframe format

# Function for Extracting and Combining Hourly Electricity Outputs of All RTOs (Regional Transmission Organizations)
def extract_values_fuel_type(start: str, end: str, api_key: str, institutions: list, folder_name: str, max_workers: int=6):
    df_list = [] # stores a list of dataframes from every RTOs, containing the hourly electricity output for every fuel type

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # This extracts electricity outputs for all RTOs simultaneously (though depends on number of RTOs & allocated workers, set to a 
        # default of 6 for the amount of RTOs in the original project, which is 5 RTOs)
        results = {executor.submit(request_fuel_type_data, start, end, api_key, institution): institution for institution in institutions}

        for res in as_completed(results):
            # When certain RTOs' records have finished being extracted, the resulting dataframe is appended to the list of dataframes
            df_list.append(res.result())

    df_n = pd.concat(df_list, axis=0, ignore_index=True) # combining all dataframes in the list of dataframes by row

    # Storing the dataframe in .csv format
    path_datasets_raw = os.path.abspath(f'../data/{folder_name}')
    if not os.path.exists(path_datasets_raw):
        os.makedirs(path_datasets_raw)

    path_df_n = os.path.join(path_datasets_raw, f'fueltype_{folder_name}.csv')
    df_n.to_csv(path_df_n, index=False)
    print(f'Saved results to {path_df_n}')
    return df_n, path_df_n # returns the pandas dataframe and its storage directory

#########################################################################
# STORING DATAFRAMES INTO POSTGRESQL DATABASE
#########################################################################

# Function for Initializing Database
def initialize_database(user: str, pw: str, db_name: str, host: str='localhost'):
    connection = psycopg2.connect(f'host={host} dbname=postgres user={user} password={pw}') # connecting to default database
    connection.autocommit=True # setting autocommit to true, so if the required database does not exists, it could be created & then commited quickly

    with connection.cursor() as cursor:
        cursor.execute( # checking if the required database 'db_name' exists
            "SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_database WHERE datname=%s);", 
            (db_name, )
        )
        result = cursor.fetchone()[0]
        print(f'DB {db_name} exists? {result}')

        if result:
            # If the database is found, a new connection is made, connecting to said database, and the function
            # returns the connection and cursor
            connection.close()
            new_connection = psycopg2.connect(f'host={host} dbname={db_name} user={user} password={pw}')
            new_cursor = new_connection.cursor()
            return new_connection, new_cursor # returns connection & cursor for the new database
        else:
            # If the database is not found, it is created and the fynction would then call itself, so the new connection & cursor for the database is returned
            print(f'Creating {db_name}')
            cursor.execute(sql.SQL('CREATE DATABASE {db};').format(db=sql.Identifier(db_name)))
            connection.close()
            return initialize_database(user=user, pw=pw, db_name=db_name, host=host)

# Function for Inserting Data to Staging Schema
def insert_to_staging(connection, cursor, interval_h: int=2, insert_raw_data: bool=False):
    # When insert_raw_data is True, it means that the function would be used for inserting all raw data from the 'landing' schema into an empty 
    # 'staging' schema. When this is the case, the condition is simply set to an empty string. When it is set to False, it means this function
    # is being used for upserting records from 'landing' to 'staging' schema, and as such, requires a specific interval of time which is recent 
    # enough
    if insert_raw_data:
        condition=sql.SQL('')
    else:
        # This sets the interval of time in hours, so that the data that is being upserted to 'staging' is only data from the previous x hours
        condition=sql.SQL("WHERE to_timestamp(REPLACE(SUBSTRING(TRIM(time_stamp), 1), 'T', ' '), 'YYYY-MM-DD HH24') >= (NOW() - INTERVAL '{i} Hours')").format(i=sql.Identifier(str(interval_h)))

    # SQL query, using MERGE in order to merge changes into the 'staging' schema
    query = sql.SQL('''
        MERGE INTO staging.rto_details AS t
        USING (
            SELECT DISTINCT(rto_name) AS rto_code, rto_full_name FROM landing.raw_rto_demand
            {condition}
            GROUP BY rto_code, rto_full_name
        ) AS s
        ON t.rto_id = s.rto_code
        WHEN MATCHED THEN
            UPDATE SET rto_full_name = s.rto_full_name
        WHEN NOT MATCHED THEN
            INSERT (rto_id, rto_full_name) VALUES (rto_code, rto_full_name);

        MERGE INTO staging.fuel_type_generation AS t
        USING (
            SELECT
                CONCAT('FU', UPPER(rto_name), time_stamp) AS fuel_generation_id,
                to_timestamp(REPLACE(SUBSTRING(TRIM(time_stamp), 1), 'T', ' '), 'YYYY-MM-DD HH24') AS time_stamp, 
                TRIM(rto_name) AS rto_id, 
                SUM(CASE WHEN fuel_name = 'NG'  THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_ng,
                SUM(CASE WHEN fuel_name = 'NUC' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_nuc,
                SUM(CASE WHEN fuel_name = 'WND' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_wnd,
                SUM(CASE WHEN fuel_name = 'SUN' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_sun,
                SUM(CASE WHEN fuel_name = 'COL' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_col,
                SUM(CASE WHEN fuel_name = 'WAT' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_wat,
                SUM(CASE WHEN fuel_name = 'OIL' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_oil,
                SUM(CASE WHEN fuel_name = 'OTH' THEN CAST(mwh_generated AS NUMERIC) ELSE NULL END) AS mwh_oth
            FROM
                landing.raw_fuel_electricity_generation
            {condition}
            GROUP BY time_stamp, rto_name
            ORDER BY rto_name ASC, time_stamp ASC
        ) AS s
        ON t.fuel_generation_id = s.fuel_generation_id
        WHEN MATCHED THEN
            UPDATE SET
                mwh_ng  = s.mwh_ng,
                mwh_nuc = s.mwh_nuc,
                mwh_wnd = s.mwh_wnd,
                mwh_sun = s.mwh_sun,
                mwh_col = s.mwh_col,
                mwh_wat = s.mwh_wat,
                mwh_oil = s.mwh_oil,
                mwh_oth = s.mwh_oth
        WHEN NOT MATCHED THEN
            INSERT (
                fuel_generation_id, time_stamp, rto_id, 
                mwh_ng, mwh_nuc, mwh_wnd, mwh_sun, mwh_col, mwh_wat, mwh_oil, mwh_oth
            )
            VALUES (
                s.fuel_generation_id, s.time_stamp, s.rto_id, 
                s.mwh_ng, s.mwh_nuc, s.mwh_wnd, s.mwh_sun, s.mwh_col, s.mwh_wat, s.mwh_oil, s.mwh_oth
            )
        ;

        MERGE INTO staging.electricity_demands AS t
        USING (
            SELECT
                CONCAT('DE', UPPER(rto_name), time_stamp) AS demand_id,
                to_timestamp(REPLACE(SUBSTRING(TRIM(time_stamp), 1), 'T', ' '), 'YYYY-MM-DD HH24') AS time_stamp,
                TRIM(rto_name) AS rto_id,
                SUM(CAST(demand_mwh AS NUMERIC)) AS demand_mwh
            FROM 
                landing.raw_rto_demand
            {condition}
            GROUP BY time_stamp, rto_name, rto_full_name
            ORDER BY rto_name ASC, time_stamp ASC
        ) AS s
        ON t.demand_id = s.demand_id
        WHEN MATCHED THEN
            UPDATE SET 
                time_stamp=s.time_stamp,
                rto_id=s.rto_id,
                demand_mwh=s.demand_mwh
        WHEN NOT MATCHED THEN
            INSERT (demand_id, time_stamp, rto_id, demand_mwh)
            VALUES (s.demand_id, s.time_stamp, s.rto_id, s.demand_mwh)
        ;
    ''').format(condition=condition)

    cursor.execute(query) # executes the query
    connection.commit() # commits the changes to the database

# Function for Updating Data to the Most Recent Timestamp
def update_data_to_newest_datetime(api_key:str, username_postgres: str, pw_postgres: str, db_name: str='data_warehouse_electricity'):
    connection, cursor = initialize_database(user=username_postgres, pw=pw_postgres, db_name=db_name) # initializing database connection

    # Checking the most recent timestamp for each RTOs in the demand and electricity output tables, then extracting the oldest timestamp from this list of timestamps
    cursor.execute('SELECT rto_id, MAX(time_stamp) FROM staging.fuel_type_generation GROUP BY rto_id;')
    max_time_fuel = min([i[1] for i in cursor.fetchall()])
    cursor.execute('SELECT rto_id, MAX(time_stamp) FROM staging.electricity_demands GROUP BY rto_id;')
    max_time_demand = min([i[1] for i in cursor.fetchall()])

    # Extracting a list of RTOs
    cursor.execute('SELECT DISTINCT rto_id FROM staging.rto_details;')
    institutions = [c[0] for c in cursor.fetchall()]

    end_n = datetime.datetime.now() # setting end date for API call parameter
    start_n = min([max_time_fuel, max_time_demand]) # setting start date for API call parameter, which is the older timestamp between the oldest timestamp on electricity & demand tables
    if start_n.strftime('%Y-%m-%dT%H')==end_n.strftime('%Y-%m-%dT%H'):
        # If the end date is the same as the start date, the function returns nothing
        print('Timestamp too new, try again later!')
        return

    # This dictionary stores the raw dataframes for electricity demands as well as RTO electricity outputs by fuel types. Each keys for this dictionary is named after the
    # specific dataframe's designation within the database, thus allowing easy integration in the SQL queries
    dict_data = {
        'raw_rto_demand': extract_demands_institutions(start=start_n.strftime('%Y-%m-%dT%H'), end=end_n.strftime('%Y-%m-%dT%H'), api_key=api_key, institutions=institutions, folder_name='temp', max_workers=6),
        'raw_fuel_electricity_generation': extract_values_fuel_type(start=start_n.strftime('%Y-%m-%dT%H'), end=end_n.strftime('%Y-%m-%dT%H'), api_key=api_key, institutions=institutions, folder_name='temp', max_workers=6)
    }

    # This loops through the data dictionary, allowing the data from both demand and fuel electricity generation dataframes to be inserted in bulk into the database
    for tbl, (data, _) in dict_data.items():
        print(f'Upserting to landing.{tbl}')
        cols = sql.SQL(', ').join(map(sql.Identifier, data.columns.to_list())) # creates columns list suitable for SQL query
        update = ', '.join([f'{col}=EXCLUDED.{col}' for col in data.columns[1:]]) # creates the EXCLUDED clause for SQL's ON UPDATE SET

        # SQL query for upserting into the landing schema's tables
        query = sql.SQL('''
            INSERT INTO landing.{tbl} ({cols})
            VALUES %s
            ON CONFLICT ({pk})
            DO UPDATE SET {update};
        ''').format(
            tbl=sql.Identifier(tbl),
            cols=cols,
            pk=sql.Identifier(data.columns[0]),
            update=sql.SQL(update)
        )
        execute_values(cursor, query.as_string(cursor), data.where(pd.notnull(data), None).to_numpy().tolist()) # query execution
        connection.commit() # committing changes
        print(f'Finished upserting to landing - {tbl}')

    hours = int((end_n - start_n).total_seconds()/3600)+4
    insert_to_staging(connection=connection, cursor=cursor, interval_h=hours, insert_raw_data=False) # upserting data to staging schema
    print('Finished upserting data to staging')

    cursor.execute('REFRESH MATERIALIZED VIEW aggregate.view_demand_electricty_generation_mlready;') # Updating materialized view in the 'aggregate' schema
    connection.commit()
    print('Finished updating materialized view')

    connection.close()
    return dict_data # returns the dictionary of data

# Function for Extracting View to Pandas Dataframe
def extract_view_to_df(username_postgres: str, pw_postgres: str, db_name: str='data_warehouse_electricity'):
    connection, cursor = initialize_database(user=username_postgres, pw=pw_postgres, db_name=db_name) # initializing database connection

    cursor.execute('REFRESH MATERIALIZED VIEW aggregate.view_demand_electricty_generation_mlready;') # Updating materialized view in the 'aggregate' schema
    connection.commit()
    cursor.execute('SELECT * FROM aggregate.view_demand_electricty_generation_mlready') # queries the view
    features = [col[0] for col in cursor.description] # extracts feature
    df_mlready = pd.DataFrame(data=cursor.fetchall(), columns=features) # creates the pandas dataframe

    # Storing dataframe in csv format
    path_datasets = os.path.abspath(f'../data')
    if not os.path.exists(path_datasets):
        os.makedirs(path_datasets)
    path_df_mlready = os.path.join(path_datasets, 'demand_electricty_generation_mlready.csv')
    df_mlready.to_csv(path_df_mlready, index=False)

    connection.close()
    return df_mlready, path_df_mlready # returns dataframe and its csv path