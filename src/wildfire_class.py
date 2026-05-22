# --------------------------------------------------------------------------------------------------------
# This file defines the WildFireQuery class which stores all necessary variables and GDFs of one API query
# --------------------------------------------------------------------------------------------------------

import sys
from pathlib import Path
sys.path.append(str(Path().resolve().parent))

from dataclasses import dataclass
import geopandas as gpd


from .country_continent_gdf import COUNTRIES_GDF, CONTINENTS_GDF

@dataclass
class WildFireQuery:
    data: gpd.GeoDataFrame
    sensor: str
    area: str
    extent: str
    date: str
    n_days: int
    sampled: bool = False
    cleaned: gpd.GeoDataFrame = None
    clustered: gpd.GeoDataFrame = None
    geometry: gpd.GeoDataFrame = None

    def __post_init__(self):
        # deduces instrument from sensor
        sensor_list = self.sensor.split("_")
        self.instrument = sensor_list[0]
        
        # calculates pixel area$
        if self.instrument in ["VIIRS", "MODIS"]:
            self.pixel_area = self.data["track"].mean() * self.data["scan"].mean()
        if self.instrument == 'LANDSAT':
            self.pixel_area = 0.03 ** 2

        # handles the special case of 'world'
        if self.area == "world":
            self.extent = "-180,-90,180,90"
        self.bbox = [float(n) for n in self.extent.split(",")]

        # display name, because it is lost during the api query
        if self.area == "world":
            self.area_display = "World"

        # we can use the gdf for continents and countries to look up the names again
        elif self.area in CONTINENTS_GDF["CONTINENT_NORM"].values:
            match = CONTINENTS_GDF[
                CONTINENTS_GDF["CONTINENT_NORM"] == self.area
            ]

            self.area_display = (
                match["CONTINENT"].values[0]
                if not match.empty
                else self.area
            )

        else:
            match = COUNTRIES_GDF[
                COUNTRIES_GDF["name"] == self.area
            ]

            self.area_display = (
                match["ADMIN"].values[0]
                if not match.empty
                else self.area
            )
        # epsilon for dbscan depending on instrument
        if self.instrument == "MODIS":
            self.dbscan_epsilon = 2
        elif self.instrument == "VIIRS":
            self.dbscan_epsilon = 1.3
        elif self.instrument == "LANDSAT":
            self.dbscan_epsilon = 0.1

    # calculate coordinates of polygon center for centering the final folium map
    def get_center(self) -> tuple:
        if self.area == "world":
            return (20, 0)
        bbox = self.bbox
        return ((bbox[1] + bbox[3]) / 2,
                (bbox[0] + bbox[2]) / 2)
    
    # calculate fitting start zoom based on area extent for final folium map
    def get_zoom_level(self) -> int:
        bbox = self.bbox
        max_extent = max(bbox[2] - bbox[0],
                         bbox[3] - bbox[1])

        # thresholds were picked manually 
        if max_extent >= 180: return 2
        elif max_extent > 60: return 3
        elif max_extent > 30: return 4
        elif max_extent > 18: return 5
        elif max_extent > 10: return 6
        elif max_extent > 5:  return 7
        else:                 return 8