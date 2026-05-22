# ---------------------------------------------------------------------------------------------
# This file contains all functions related to clustering wf.cleaned. The result is wf.clustered
# ---------------------------------------------------------------------------------------------

import geopandas as gpd
import pandas as pd
import numpy as np
from .wildfire_class import WildFireQuery
from sklearn.cluster import DBSCAN


# Helper functions
# ----------------
def cluster_feature_engineering(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Generates a 'stats' DF which contains all the necessary attributes of the fire clusters.
    """
    # fixed feature engineering
    agg_kwargs = {'pixel_count': ('geometry', 'count'),
                'first_pixel': ('datetime', 'min'),
                'last_pixel': ('datetime', 'max'),
                'time_mean': ('datetime', 'mean')}
    
    # preserve 'type' column if available
    if 'type' in gdf.columns:
        agg_kwargs['type'] = ('type', 'first')
    
    # engineer frp density if available
    if 'frp_density' in gdf.columns:
        agg_kwargs['frp_sum'] = ('frp', 'sum')
        agg_kwargs['frp_mean'] = ('frp', 'mean')

    # uses the specific agg_kwargs create stats DataFrame for clusters (groupy)
    stats = gdf.groupby('cluster').agg(**agg_kwargs)

    # and rounds the values for readability
    round_cols = []
    if 'frp_density' in gdf.columns:
        round_cols.append('frp_mean')
        round_cols.append('frp_sum')
    if round_cols:
        stats[round_cols] = stats[round_cols].round(1)
    
    return stats

def convert_type(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # convert type from ordinal numbers to readable names
    types_dict = {
        0: 'vegetation fire',
        1: 'active volcano',
        2: 'other (land)',
        3: 'offshore'
    }
    if 'type' in gdf.columns:
        gdf['type_str'] = gdf['type'].apply(lambda x: types_dict[x])

    return gdf

# clustering function
# -------------------
def cluster_wf(wf: WildFireQuery, min_samples=2) -> gpd.GeoDataFrame:
    """
    Clusters the fire pixels into groups representing individual fires using DBSCAN

    Parameters:
    -----------
    wf: WildFireQuery, Cleaned GDF from FIRMS API query
    min_samples: int, min points within eps to be considered core point

    Returns:
    --------
    clustered_gdf: gpd.GeoDataFrame, Clustered GDF GeoDataFrame
    """
    # Setting Parameters
    # ------------------
    # volumetric mean readius of earth
    # used, because Haversine uses radians instead of degrees
    KM_PER_RADIAN = 6371.0088 
    epsilon_km = wf.dbscan_epsilon

    # 2 different approaches, dependon on whether 'type' column is present
    # --------------------------------------------------------------------
    db_params = DBSCAN(
        # min distance to nearest neighbor to be included in the cluster
        eps=epsilon_km / KM_PER_RADIAN,
        # min points within eps to be considered core point (essentially sets min cluster size)
        min_samples=min_samples,
        # required when using haversine
        algorithm='ball_tree',
        # handles lat, lon coordinates, as compared to using metric and having to reproject twice
        metric='haversine'
        )
    
    # cluster by 'type'
    if 'type' in wf.cleaned.columns and wf.cleaned['type'].notna().any(): 
        all_clusters = []
        offset = 0
        
        # splits the dataset into subsets by fire type and iterates over each type
        for fire_type, group in wf.cleaned.groupby('type'): 
            # extract lon/lat for each fire pixel and convert to radians
            coords_rad = np.radians(
                np.column_stack([group.geometry.y, group.geometry.x])
            )

            # assuming spherical earth
            db = db_params.fit(coords_rad)
            
            labels = db.labels_.copy()
            # add offset to IDs to avoid ID collisions
            labels[labels >= 0] += offset  
            offset = labels.max() + 1 if labels.max() >= 0 else offset
            
            all_clusters.append(pd.Series(labels, index=group.index))
        
        wf.cleaned['cluster'] = pd.concat(all_clusters)

        clustered = wf.cleaned[wf.cleaned['cluster'] >= 0].copy()

    # disregard 'type'
    else: # same procedure
        coords_rad = np.radians(
            np.column_stack([wf.cleaned.geometry.y, wf.cleaned.geometry.x])
        )
        db = db_params.fit(coords_rad)
        wf.cleaned['cluster'] = db.labels_

        clustered = wf.cleaned[wf.cleaned['cluster'] >= 0].copy()

    # feature preservation and engineering for dissolve
    # -------------------------------------------------
    stats = cluster_feature_engineering(clustered)

    # dissolve (going from points to clusters)
    # ----------------------------------------
    # one centroid point per cluster
    centroids = clustered.dissolve(by='cluster').centroid.rename('geometry')

    # feature engineering in clustered GDF
    # ------------------------------------
    # add stats DF to centroids GDF
    cluster_gdf = gpd.GeoDataFrame(stats, geometry=centroids, crs=wf.cleaned.crs)
    # calculate timespan of fire
    cluster_gdf["time_span"] = cluster_gdf["last_pixel"] - cluster_gdf["first_pixel"]
    # convert type to readable fire types
    cluster_gdf = convert_type(cluster_gdf)
    # sort by size
    cluster_gdf = cluster_gdf.sort_values("pixel_count", ascending=False)

    return cluster_gdf