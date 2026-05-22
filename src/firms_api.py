# -------------------------------------------------------------------------
# This file contains all the functions for forwarding api requests to FIRMS
# -------------------------------------------------------------------------

# imports
import requests
import pandas as pd
import geopandas as gpd
import os as os
from dotenv import load_dotenv
import re
import unicodedata
from datetime import datetime, timedelta
import warnings
from .wildfire_class import WildFireQuery
from .country_continent_gdf import COUNTRIES_GDF, CONTINENTS_GDF
from .inputs import get_params


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
    return result

# api query for gettin gthe wildfire data and its helper functions
# -----------------------------------------------
# Helper Functions for checking parameter inputs:
# -----------------------------------------------
def check_sensor(sensor, api_key):
    valid_sensors = set(get_availability_all(api_key)["data_id"]) 
    if sensor not in valid_sensors:
        raise ValueError("Sensor: Invalid sensor name.")

def check_area_list(area):
    west, south, east, north = area
    # check invalid longitude values
    if west < -180 or west > 180: 
        raise ValueError("Area: Invalid coordinate: west")
    if east < -180 or east > 180: 
        raise ValueError("Area: Invalid coordinate: east")
    # check invalid latitude values
    if south < -90 or south > 90:
        raise ValueError("Area: Invalid coordinate: south")
    if north < -90 or north > 90:
        raise ValueError("Area: Invalid coordinate: north")
    # check order of list
    if west > east:
        raise ValueError("Area: Invalid coordinate: west is larger than east")
    if south > north:
        raise ValueError("Area: Invalid coordinate: south is larger than north")
    
def check_date_str(date, sensor, max_date_time, min_date_time):
    is_none = date is None
    is_str = type(date) == str

    # get 
    if not is_none and not is_str:
        raise ValueError("Date: Invalid input type. Either str or None")
    
    if is_str:
        try:
            date_time = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date: Must be in YYYY-MM-DD format and be a valid calendar date")
        if date_time > max_date_time:
            raise ValueError(f"Date: Desired date not available for {sensor}. Latest available data from {max_date_time}")
        if date_time < min_date_time:
            raise ValueError(f"Date: Desired date not available for {sensor}. Earliest available data from {min_date_time}")
        
def check_n_days(n_days):
    if not type(n_days) == int:
        raise ValueError("N_days: Type must be int.")
    if n_days < 1 or n_days > 5:
        raise ValueError("N_days: Minimum 1 day, maximum 5 days.")

# --------------------------------------------------------------------
# Helper Functions for calculating area based on country or continent:
# --------------------------------------------------------------------

# import aliases dictionary from src folder
from src.country_continent_aliases import ALIASES

# function for normalising a country string
def normalise(country: str) -> str:
    country = unicodedata.normalize("NFD", country) # decomposes special characters: ô → o + ^
    country = "".join(c for c in country if unicodedata.category(c) != "Mn") # drop all accents (diacritic characters)
    country = country.lower() # lowercase everything
    country = re.sub(r"[^a-z0-9\s]", "", country) # removes forbidden characters
    country = re.sub(r"\s+", "", country) # removes multi-spaces in middle and all spaces at beginning and end
    country = ALIASES.get(country, country)
    return country

def is_country(area: str) -> bool:
    """
    Checks, whether area input is a continent
    """
    is_country = (area in COUNTRIES_GDF["name"].values
                  or area.upper() in COUNTRIES_GDF["ISO_A3"].values)
    return is_country

def is_continent(area: str) -> bool:
    """
    Checks, whether area input is a continent
    """
    is_continent = area in CONTINENTS_GDF["CONTINENT_NORM"].values
    return is_continent

def is_world(area: str) -> bool:
    """
    Checks, whether area input is equal to 'world'
    """
    return area == "world"
    
# get geometry for either continent or country
def get_geometry(area: str) -> gpd.GeoDataFrame | None:
    """
    Gets a GeoDataFrame with the geometry of the input area. For 'world', no geometry is needed.
    """
    if type(area) == list:
        geom = None
        return geom
    area = normalise(area)
    if is_country(area):
        geom = COUNTRIES_GDF[(COUNTRIES_GDF["name"] == area) |
                             (COUNTRIES_GDF["ISO_A3"] == area.upper())]
    if is_continent(area):
        geom = CONTINENTS_GDF[CONTINENTS_GDF["CONTINENT_NORM"] == area]
    if is_world(area):
        geom = None
    return geom
    

# return list of 4 coordinates for input country
def get_area_coord(area: str) -> list:
    """
    Gets the bounding box coordinates for any valid user input.
    """
    # normalise input using ALIASES dictionary
    area = normalise(area)

    # check validity of area input
    if not is_continent(area) and not is_country(area):
        raise ValueError("Area: Invalid country code, country name or continent.")
    
    # retrieve bbox for continets if input valid
    if is_continent(area):
        continent_gdf = get_geometry(area)
        minx, miny, maxx, maxy = continent_gdf.geometry.total_bounds
        bbox = [minx, miny, maxx, maxy]

    # retrieve bbox for countries if input valid
    else:
        country_gdf = get_geometry(area)
        minx, miny, maxx, maxy = country_gdf.geometry.total_bounds
        bbox = [minx, miny, maxx, maxy]
    print(f"Area name normalised: {area}")
    return [area, ",".join(map(str, bbox))]

# clip data points to country/continent extent
def clip(output_gdf: gpd.GeoDataFrame, area: str) -> gpd.GeoDataFrame:
    """
    Clips the gdf output from the API to the user input area geometry
    """
    area = normalise(area)
    if is_country(area):
        clipped_gdf = gpd.clip(output_gdf, COUNTRIES_GDF[COUNTRIES_GDF["name"] == area])
    if is_continent(area):
        clipped_gdf = gpd.clip(output_gdf, CONTINENTS_GDF[CONTINENTS_GDF["CONTINENT_NORM"] == area])
    return clipped_gdf

# ----------------------------------------
# Helper function for converting df to gdf
# ----------------------------------------
def df_to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Converts the pd.DataFrame output from API query to gpd.GeoDataFrame.
    """
    gdf = gpd.GeoDataFrame(
        data=df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )
    return gdf

# ------------
# API Function
# ------------
def area_api_query(api_key: str, sensor: str, area: list|str = 'world', date: str | None = None, n_days: int = 1) -> pd.DataFrame:
    """
    Query the NASA FIRMS API for area data for a given sensor and date. If date is not provided, it will return the most recent data.

    Choose one of these sensors:
        'LANDSAT_NRT',
        'MODIS_NRT',
        'MODIS_SP',
        'VIIRS_NOAA20_NRT',
        'VIIRS_NOAA20_SP',
        'VIIRS_NOAA21_NRT',
        'VIIRS_SNPP_NRT',
        'VIIRS_SNPP_SP'

    Parameters:
    -----------
    api_key: str, your idividual FIRMS API-key

    sensor : str
        Must be from the sensors list.

    area : list or str, optional
        The area for which to query data, 3 options:
        - 'world' for global coverage
        - Country name or ISO 3166-1 alpha-3 country codes (e.g. "Algeria" or "DZA")
        - Continent name (e.g. "North America")
        - Coordinate bounding box with format [west,south,east,north] (e.g. [-180,-90,180,90])

    date : str, optional
        Date in the format 'YYYY-MM-DD'. If not provided, the most recent data will be returned.

    n_days: int, optional
        Number of days that the data should cover. Starting from the stated date
        Max = 5
        Default value = 1

    Returns:
    --------
    pd.DataFrame
        A DataFrame containing the area data for the specified sensor and date.
    """
    # sensor
    # ------
    if check_sensor(sensor, api_key) == False:
        raise ValueError("Sensor: Invalid sensor name, check list of available sensors.")
    print(f"Sensor input: {sensor}")
    
    # area
    # ----
    print(f"Area input: {area}")
    if type(area) == str:
        if is_world(area):
            area_norm = 'world'
            extent= area
        else:
            area_list = get_area_coord(area)
            area_norm = area_list[0]
            extent = area_list[1]
    elif type(area) == list:
        check_area_list(area)
        extent = ",".join(map(str, area)) # converts input list to str for url use
        area_norm = extent
    else:
        raise ValueError("Area: Anvalid input type. Must be either str or list")
    print(f"Area bbox: {extent}")

    # n_days
    # ------
    check_n_days(n_days)
    n_days = str(n_days)
    print(f"N_days input: {n_days}")

    # date
    # ----
    availability_all_df = get_availability_all(api_key)
    max_date = availability_all_df.loc[
            availability_all_df["data_id"] == sensor,
            "max_date"
        ].iloc[0]
    min_date = availability_all_df.loc[
            availability_all_df["data_id"] == sensor,
            "min_date"
        ].iloc[0]
    max_date_time = datetime.strptime(max_date, "%Y-%m-%d")
    min_date_time = datetime.strptime(min_date, "%Y-%m-%d")
    check_date_str(date, sensor, max_date_time, min_date_time)

    if date is None:
        date = max_date_time - timedelta(days=(int(n_days)-1))
        date_str = date.strftime("%Y-%m-%d")
    if type(date) == str:
        date_str = date
    print(f"Date input: {date_str}")
    print("All input correct")

    # API query
    # ---------
    area_url = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv/' + api_key + '/' + sensor + '/' + extent + '/' + n_days + '/' + date_str
    print(f"URL: {area_url}")
    df = pd.read_csv(area_url)

    # Convert to gpd.GeoDataFrame
    unclipped_gdf = df_to_gdf(df)

    # clip to area boundaries
    if is_world(area):
        output_gdf = unclipped_gdf
    elif type(area) == list:
        output_gdf = unclipped_gdf
    else:
        output_gdf = clip(unclipped_gdf, area)
    print(f"Shape (rows, columns): {output_gdf.shape}")

    # instantiate WildFireQuery object
    output = WildFireQuery(
        data = output_gdf,
        sensor = sensor,
        area = area_norm,
        extent = extent,
        date = date_str,
        n_days = n_days,
        geometry= get_geometry(area)
    )
    print (f'Our current transaction count is {get_transaction_count(api_key)}/5000')
    return output

# -------------------
# Fail-Safe functions
# -------------------
# empty dataset
def test_wf_empty(wf: WildFireQuery):
    if len(wf.data) == 0:
      raise ValueError("Empty dataset: nothing to visualise here. Try other parameters.")
    
# max rows
def test_max_rows(wf):
  max_rows = get_params()["max_rows"]
  if len(wf.data) > max_rows:
      wf.sampled = True
      warnings.warn(
          f"Dataset too large for individual point plotting ({len(wf.data)} rows). "
          f"A random subset with n={max_rows} is displayed instead",
          UserWarning
    )