import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

@st.cache_resource
def get_client():
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )
    return bigquery.Client(credentials=creds, project=creds.project_id)

@st.cache_data(ttl=3600)
def load_table(table: str):
    return get_client().query(f"select * from `{table}`").to_dataframe()