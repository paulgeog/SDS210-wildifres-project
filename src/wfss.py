# ------------------------------------------------------------------------------------------
# This file contains all functions related to calculating the wildfire severity score (WFSS)
# ------------------------------------------------------------------------------------------
import geopandas as gpd
import numpy as np
from .wildfire_class import WildFireQuery

def severity_score(wf: WildFireQuery, weights: list) -> gpd.GeoDataFrame:
    """ 
    Calculates a severity score and class for fire pixel clusters and adds it to gdf.  
    It uses:
    - FRP sum
    - FRP mean
    - cluster size  
    with user specified weights

    Parameters:
    -----------
    wf : WildFireQuery, entire class object containing the clustered gdf as attribute
    weights: list, List with 3 integer values which specify the weights in the order [frp sum, frp mean, cluster size]

    Returns:
    --------
    gpd.GeoDataFrame: The severity score/class is added as a column.
    """
    # raise error if weights do not sum to 1
    if round(sum(weights), 4) != 1.0:
        raise ValueError(f"Weights must sum to 1, got {sum(weights)}")
    
    severity_gdf = wf.clustered.copy()
    FRP_SUM_VIIRS = 119387   # MW
    FRP_MEAN_VIIRS = 277    # MW
    CLUSTER_SIZE = 893      # km2
    
    # calculate fire cluster duration for normalisation later (rounds to higher integer, at least 1)
    severity_gdf["time_span_days"] = np.ceil(severity_gdf["time_span"].dt.total_seconds() / 86400).clip(1, 5).round(1)

    if wf.instrument == 'LANDSAT':
        severity_gdf["cluster_size_approx"] = ((severity_gdf["pixel_count"] * wf.pixel_area)).round(3)
        severity_gdf["severity_class"] = 'unknown'
        severity_gdf["frp_mean"] = 'unknown'
        severity_gdf["frp_sum"] = 'unknown'
        
    elif wf.instrument == 'VIIRS':
        # frp sum
        severity_gdf["frp_sum_day"] = (severity_gdf["frp_sum"] / severity_gdf["time_span_days"]).round(1)
        severity_gdf["frp_sum_day_norm"] = (severity_gdf["frp_sum_day"] / FRP_SUM_VIIRS).clip(0, 1)
        # frp mean
        severity_gdf["frp_mean_norm"] = (severity_gdf["frp_mean"] / FRP_MEAN_VIIRS).clip(0, 1)
        # cluster size in km2
        severity_gdf["cluster_size_approx"] = ((severity_gdf["pixel_count"] * wf.pixel_area) / 3.5).round(3)

        # normalise
        severity_gdf["cluster_size_approx_norm"] = (severity_gdf["cluster_size_approx"] / CLUSTER_SIZE).clip(0, 1)

        severity_gdf["severity_score"] = (severity_gdf["frp_sum_day_norm"] * weights[0] +
                                severity_gdf["frp_mean_norm"] * weights[1] +
                                severity_gdf["cluster_size_approx_norm"] * weights[2])
        
        # creates log scale between 0 and 1 and then multiplies by 9 -> range 0 to 10,
        # and adds 1 to get to scale between 1 and 10
        severity_gdf["severity_class"] = (
            np.log1p(severity_gdf["severity_score"] * 9 + 1) / np.log1p(10) * 9 + 1
        ).round(1)

        # since 3.5 seems to be the lowest possible value, we stretch it to 1,
        # 6.7 becomes 10 and it now is an almost open ended scale (technically
        # max is 20, which was 10 before stretching)
        severity_gdf["severity_class"] = (
            (severity_gdf["severity_class"] - 3.5) / (6.7 - 3.6) * 9 + 1
        ).clip(lower=1).round(1)

    elif wf.instrument == 'MODIS':
        # cluster size in km2 (Factor 3.5: )
        severity_gdf["cluster_size_approx"] = ((severity_gdf["pixel_count"] * wf.pixel_area) / 1.5).round(3)
        severity_gdf["severity_class"] = 'unknown'

    return severity_gdf