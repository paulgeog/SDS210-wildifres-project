# --------------------------------------------------------------------------------------
# This file contains all functions related to cleaning wf.data. The result is wf.cleaned
# --------------------------------------------------------------------------------------
import geopandas as gpd
import pandas as pd

def clean(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Cleans a raw wildfire GeoDataFrame by removing invalid rows.
    Drops rows silently and prints a summary of what was removed.
    - Converts acq_time and acq_date to datetime
    - Checks coordinate plausibility
    - Drops rows with frp < 0
    - Normalises frp to MW per km^2
    - Removes all brightness columns
    - Checks confidence plausibility
    - Removes low confidence entries
    - Checks Day/Night
    - Drops duplicate rows

    Parameters:
    -----------
    gdf : gpd.GeoDataFrame
        Raw GeoDataFrame from FIRMS API query

    Returns:
    --------
    gpd.GeoDataFrame
        Cleaned GeoDataFrame
    """
    original_len = len(gdf)
    dropped = {}

    # dropping rows with NaN for required columns
    # -------------------------------------------
    required_cols = ['latitude', 'longitude', 'scan', 'track', 'confidence', 'acq_time', 'acq_date']
    mask = gdf[required_cols].notna().all(axis=1)
    dropped["missing_required"] = (~mask).sum()
    gdf = gdf[mask]

    # Datetime
    # --------
    if "acq_time" in gdf.columns:
        gdf["datetime"] = pd.to_datetime(
            gdf["acq_date"] + " " + gdf["acq_time"].astype(str).str.zfill(4),
            format="%Y-%m-%d %H%M",
            utc=True
        )
        gdf = gdf.drop(columns=["acq_time", "acq_date"])

    # Coordinates
    # -----------
    mask = (
        gdf["latitude"].between(-90, 90) &
        gdf["longitude"].between(-180, 180)
    )
    dropped["invalid_coordinates"] = (~mask).sum()
    gdf = gdf[mask]

    # FRP cleaning
    # ------------
    if "frp" in gdf.columns:
        mask = gdf["frp"] > 0
        dropped["invalid_frp"] = (~mask).sum()
        gdf = gdf[mask]
    else:
        dropped["invalid_frp"] = 0
        gdf["frp"] = 0

    # FRP normalisation
    # -----------------
    if "frp" in gdf.columns:
        gdf["frp_density"] = (gdf["frp"] / (gdf["scan"] * gdf["track"])).round(1) # MW per km^2

    # Brightness temperatures
    # -----------------------
    bt_checks = ["brightness", "bright_t31", "bright_ti4", "bright_ti5"]

    for col in bt_checks:
        if col in gdf.columns:
            gdf = gdf.drop(columns=[col])

    # Confidence
    # ----------
    # MODIS
    if pd.api.types.is_numeric_dtype(gdf["confidence"]):
        # remove invalid confidence
        mask_valid = gdf["confidence"].between(0, 100)
        dropped["invalid_confidence"] = (~mask_valid).sum()
        gdf = gdf[mask_valid]
        # remove unconfident entries: > 30%
        mask_likely = gdf["confidence"] > 30
        dropped["low_confidence"] = (~mask_likely).sum()
        gdf = gdf[mask_likely]
    # VIIRS
    else:
        # convert Landsat confidence to lowercase
        gdf["confidence"] = gdf["confidence"].str.lower()
        # remove unconfident entries: "l" (= low)
        dropped["invalid_confidence"] = 0
        mask_likely = gdf["confidence"].isin(["n", "h"])
        dropped["low_confidence"] = (~mask_likely).sum()
        gdf = gdf[mask_likely]

    # Day/Night flag
    # --------------
    mask = gdf["daynight"].isin(["D", "N"])
    dropped["invalid_daynight"] = (~mask).sum()
    gdf = gdf[mask]

    # Type
    # ----
    if 'type' in gdf.columns:
        mask = gdf['type'].isin([0,1,2,3])
        dropped['invalid_type'] = (~mask).sum()
        gdf = gdf[mask]

    # Duplicates
    # ----------
    # also removes duplicates accross different satellites
    duplicate_mask = gdf.duplicated(subset=["latitude", "longitude", "datetime"])
    dropped["duplicates"] = duplicate_mask.sum()
    gdf = gdf[~duplicate_mask]

    # Summary
    # -------
    total_dropped = original_len - len(gdf)
    print(f"=== Cleaning Summary ===")
    print(f"Missing required fields : {dropped['missing_required']}")
    print(f"Invalid coordinates     : {dropped['invalid_coordinates']}")
    if 'frp' in gdf.columns:
        print(f"Invalid FRP             : {dropped['invalid_frp']}")
    print(f"Invalid confidence      : {dropped['invalid_confidence']}")
    print(f"Low confidence          : {dropped['low_confidence']}")
    print(f"Invalid daynight        : {dropped['invalid_daynight']}")
    if 'type' in gdf.columns:
        print(f"Invalid type            : {dropped['invalid_type']}")
    print(f"Duplicates              : {dropped['duplicates']}")
    print(f"-------------------------")
    print(f"Rows removed: {total_dropped} of {original_len}")
    print(f"Rows remaining: {len(gdf)}")

    return gdf.reset_index(drop=True)