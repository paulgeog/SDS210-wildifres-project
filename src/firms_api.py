# -------------------------------------------------------------------------
# This file contains all the functions for forwarding api requests to FIRMS
# -------------------------------------------------------------------------

# imports
import requests
import pandas as pd
import os as os
from dotenv import load_dotenv


def get_api_key():
  load_dotenv()
  api_key = os.getenv("MY_API_KEY")
  print(f"API-Key: {api_key}")
  return api_key


# this function is taken directly from the FIRMS documentation
def api_key_status(api_key):
  url = 'https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=' + api_key
  try:
    df = pd.Series(requests.get(url).json()) # gets a table of information about your api key usage
    display(df)
  except:
    print ("There is an issue with your API key. Please check the value of MY_API_KEY in your .env file and your internet connection and try again.")


# this function is taken directly from the FIRMS documentation
def get_transaction_count(api_key):
  count = 0
  url = 'https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=' + api_key
  try:
    response = requests.get(url)
    data = response.json()
    df = pd.Series(data)
    count = df['current_transactions']
  except:
    print ("Error in our call.")
  return count

def get_availability_all(api_key):
    url = 'https://firms.modaps.eosdis.nasa.gov/api/data_availability/csv/' + api_key + '/ALL'
    result = pd.read_csv(url) 
    display(result.head(8))
    return result

# api query for gettin gthe wildfire data and its helper functions

