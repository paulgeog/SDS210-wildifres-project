# ----------------------------------------------------------------------------------------------------
# This file stores the country and continent gdfs which are used as lookup tables in several functions
# ----------------------------------------------------------------------------------------------------
import geopandas as gpd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

COUNTRIES_GDF = gpd.read_file(DATA_DIR / "198_countries.gpkg").to_crs(epsg=4326)
CONTINENTS_GDF = gpd.read_file(DATA_DIR / "7_continents.gpkg").to_crs(epsg=4326)