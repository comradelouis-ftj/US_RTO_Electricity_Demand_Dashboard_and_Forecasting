from functions_extract_update import update_data_to_newest_datetime, extract_view_to_df
from dotenv import load_dotenv

import os

if __name__=='__main__':
    load_dotenv()
    
    api_key = os.getenv('EIA_API')
    username_postgres = os.getenv('USERNAME_POSTGRES')
    pw_postgres = os.getenv('PW_POSTGRES')
    db_name = 'data_warehouse_electricity'

    res = update_data_to_newest_datetime(api_key=api_key, username_postgres=username_postgres, pw_postgres=pw_postgres, db_name=db_name)
    df_mlready, path_df_mlready = extract_view_to_df(username_postgres=username_postgres, pw_postgres=pw_postgres, db_name=db_name)