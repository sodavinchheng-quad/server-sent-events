import requests

BASE_URL = ""


def get_stores_from_gcs():
    url = f"{BASE_URL}stores.json"
    response = requests.get(url)
    return response.json()


def get_store_table_data_from_gcs(store_id: int):
    url = f"{BASE_URL}data/{store_id}.json"
    response = requests.get(url)
    return response.json()
