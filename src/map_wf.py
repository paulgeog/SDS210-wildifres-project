# ------------------------------------------------------------------------------------------
# This file contains the mapping function
# ------------------------------------------------------------------------------------------
import folium as fm
from folium import plugins
from .wildfire_class import WildFireQuery
import branca.colormap as cm
import webbrowser
import os

def map_wf(wf: WildFireQuery, MAX_ROWS: int, save: bool = True, browser: bool = False) -> fm.Map:
    """
    map_wf creates a folium map with wildfire data from FIRMS API

    Map layers:
    - Area outline
    - heatmap
    - Fires (clustered pixels)
    - Severity Score (Only VIIRS_xxx_SP sensors)
    - Fire pixels by Fire Radiative Power (VIIRS and MODIS)
    - Fire pixels by detection time (VIIRS and MODIS)
    - Volcanoes (Only xxx_xxx_SP sensors)
    - Offshore fires (Only xxx_xxx_SP sensors)
    - Other landbased fire sources (Only xxx_xxx_SP sensors)

    Parameters:
    -----------
    wf : WildFireQuery, entire class object which has the cleaned and clustered gdf stored as attributes.
    save: bool, toggle saving map as html
    browser: bool, opens the notebook in the browser (requires saving)

    Returns:
    --------
    m : fm.Map, a folium map with all the layers above for interactively exploring the wild fire data.
    file : if save == True, saves file to current working directory
    """
    # ---------------------------------
    # prepare clusters gdf for mapping in folium
    # ---------------------------------
    # convert datetime to strings for JSON handling
    cluster_gdf_plot = wf.clustered.copy()
    severity_gdf_plot = wf.clustered.copy()
    if len(cluster_gdf_plot) > MAX_ROWS:
        cluster_gdf_plot = cluster_gdf_plot.sort_values("pixel_count", ascending = False)
        cluster_gdf_plot = cluster_gdf_plot.head(MAX_ROWS)
        wf.sampled = True
        severity_gdf_plot = severity_gdf_plot.sort_values("severity_class", ascending = False)
        severity_gdf_plot = severity_gdf_plot.head(MAX_ROWS)
        wf.sampled = True
    # datetimes
    cluster_gdf_plot["first_pixel"] = cluster_gdf_plot["first_pixel"].dt.strftime("%Y-%m-%d %H:%M UTC")
    cluster_gdf_plot["last_pixel"] = cluster_gdf_plot["last_pixel"].dt.strftime("%Y-%m-%d %H:%M UTC")
    cluster_gdf_plot["time_mean"] = cluster_gdf_plot["time_mean"].dt.strftime("%Y-%m-%d %H:%M UTC")
    cluster_gdf_plot["time_span"] = cluster_gdf_plot["time_span"].apply(
        lambda x: f"{int(x.total_seconds() // 3600)}h {int((x.total_seconds() % 3600) // 60)}m" # lambda just used to construct the string and pass x
    )

    # add column to use later for tooltip: what kind of object am I looking at?
    cluster_gdf_plot["display_type"] = "Fire Cluster"
    severity_gdf_plot["display_type"] = "Fire Cluster"

    # ---------------------------------
    # prepare point gdf for mapping in folium
    # ---------------------------------
    gdf_plot = wf.cleaned.copy()
    if len(gdf_plot) > MAX_ROWS:
        gdf_plot = gdf_plot.sample(MAX_ROWS)
        wf.sampled = True
    gdf_plot['display_type'] = 'Fire Pixel' # add column to use later for tooltip: what kind of object am I looking at?
    gdf_plot["datetime_num"] = gdf_plot["datetime"].astype("int64") // 1e9 # convert nanoseconds to seconds
    gdf_plot["datetime"] = gdf_plot["datetime"].dt.strftime("%Y-%m-%d %H:%M UTC")

    # ---------------------------------
    # initiate the folium map canvas
    # ---------------------------------
    center = wf.get_center()
    zoom_start = wf.get_zoom_level()
    m = fm.Map(
        location=center,
        zoom_start=zoom_start,
        min_zoom = zoom_start,
        control_scale=True,
        tiles= "CartoDB DarkMatter")
    
    # ---------------------------------
    # Add Data Information
    # ---------------------------------
    title_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 1000;
        background-color: rgba(0,0,0,0.6);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        font-family: Arial;
        font-size: 13px;
    ">
        <b>Wildfire Detections</b><br>
        Sensor: {wf.sensor}<br>
        Date: {wf.date}<br>
        Area: {wf.area_display}<br>
        Days: {wf.n_days}<br>
        Sampled: {wf.sampled}
    </div>
    """

    m.get_root().html.add_child(fm.Element(title_html))

    # ---------------------------------
    # area outline
    # ---------------------------------
    if wf.geometry is not None:
        outline_group = fm.FeatureGroup(name="Area outline", show=True)
        fm.GeoJson(wf.geometry,
                style_function=lambda x: {
                    "color": "white",
                    "weight": 1,
                    "opacity": 0.7,
                    "fillOpacity": 0
                    }
                ).add_to(outline_group)
        outline_group.add_to(m)

    # --------------------------------------------------------------------------------------
    # Heatmap
    # ---------------------------------
    heat_data = wf.cleaned[["latitude", "longitude", "frp_density"]].values.tolist()
    heat_group = fm.FeatureGroup(name="Heatmap", show=True)
    plugins.HeatMap(
        heat_data,
        min_opacity=0.4,
        radius=8,
        blur=6,
        max_zoom=10
        ).add_to(heat_group)
    heat_group.add_to(m)

    # ---------------------------------
    # prepare helpers for clusters
    # ---------------------------------
    # style function
    max_pixel_count = cluster_gdf_plot['pixel_count'].max()
    def make_style_fn(color, min_opacity):
        def style_fn(feature):
            pixel_count = feature['properties']['pixel_count']
            return {
                'radius': max(3, pixel_count ** 0.7),
                'color': color,
                'weight': 1,
                'opacity': max(min_opacity, pixel_count / max_pixel_count)
            }
        return style_fn
    
    # tooltip
    def make_cluster_tooltip():
        return fm.GeoJsonTooltip(
            fields=["display_type", "pixel_count", "cluster_size_approx", "frp_mean", "frp_sum", "time_span"],
            aliases=["Object:", "# pixels in cluster", "~ cluster size [km^2]", "mean FRP [MW]", "FRP sum [MW]", "Time Span:"]
            )

    # ---------------------------------
    # fire clusters
    # ---------------------------------
    fire_clusters = fm.FeatureGroup(name="Fires", show=False)
    fm.GeoJson(
        cluster_gdf_plot[["geometry", "display_type", "pixel_count", "frp_sum", "frp_mean", "cluster_size_approx", "time_span"]],
        marker=fm.CircleMarker(
            fill=True,
            fill_opacity=0,
        ),
        tooltip=make_cluster_tooltip(),
        style_function=make_style_fn('cyan', 0.5),
    ).add_to(fire_clusters)
    fire_clusters.add_to(m)
    # ---------------------------------
    # severity score
    # ---------------------------------
    if wf.sensor in ['VIIRS_NOAA20_SP', 'VIIRS_SNPP_SP']:
        # define rendering order
        severity_gdf_plot = severity_gdf_plot.sort_values("severity_class", ascending=True)

        # create color ramp
        severity_colors = [
            "#3f007d", "#54278f", "#6a51a3", "#807dba", "#9e9ac8",
            "#bcbddc", "#dadaeb", "#f2f0f7", "#f8f4ff", "#ffffff"
        ]
        colormap_severity = cm.StepColormap(
                    colors = severity_colors,
                    vmin=1,
                    vmax=10
                    )
        colormap_severity.caption = "WFSS"

        # plot points
        severity_clusters = fm.FeatureGroup(name="WFSS", show=False)
        fm.GeoJson(
            severity_gdf_plot[["geometry", "display_type", "severity_class"]],
            marker=fm.CircleMarker(
                fill=True,
                fill_opacity=0.02,
                weight=1,
            ),
            tooltip=fm.GeoJsonTooltip(
                fields=["display_type", "severity_class"],
                aliases=["Object:", "WFSS"]
                ),
            style_function=lambda feature: {
                        "color": colormap_severity(feature["properties"]["severity_class"]),
                        "fillColor": colormap_severity(feature["properties"]["severity_class"]),
                        "radius": max(1, feature["properties"]["severity_class"] ** 1.9),
                    },
        ).add_to(severity_clusters)
        severity_clusters.add_to(m)

        # legend
        severity_legend_html = """
            <div style="
                position: fixed;
                bottom: 310px;
                right: 10px;
                z-index: 1000;
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 10px 15px;
                border-radius: 5px;
                font-family: Arial;
                font-size: 12px;
            ">
                <b>WFSS</b><br>
            """
        for i, color in enumerate(severity_colors):
            label = "> 10" if i == len(severity_colors) - 1 else i + 1
            severity_legend_html += f"""
                <div style="display:flex; align-items:center; margin-top:4px">
                    <div style="background:{color}; width:20px; height:20px; margin-right:8px; border-radius:3px; border:1px solid rgba(255,255,255,0.2)"></div>
                    {label}
                </div>
                """
        severity_legend_html += "</div>"
        m.get_root().html.add_child(fm.Element(severity_legend_html))


    # --------------------------------------------------------------------------------------
    # prepare helpers for point layers
    # ---------------------------------
    def make_point_tooltip():
        return fm.GeoJsonTooltip(
            fields=["display_type", "frp", "datetime"],
            aliases=["Object:", "FRP [MW]:", "Time:"]
            )

    # ---------------------------------
    # Fire pixels by FRP -> ranked
    # ---------------------------------
    if wf.instrument != 'LANDSAT':
        quantiles = [0, 0.2, 0.4, 0.6, 0.8, 1.0]  # 5 equal classes
        breaks = wf.cleaned["frp"].quantile(quantiles).values

        colormap_frp = cm.StepColormap(
            colors=["#bd0026", "#f03b20", "#fd8d3c", "#fecc5c", "#ffffb2"],
            index=breaks,
            vmin=breaks[0],
            vmax=breaks[-1]
            )
        
        colormap_frp.caption = "FRP [MW]"

        # plot
        frp_points_group2 = fm.FeatureGroup(name="Fire Pixels by FRP", show=False)
        fm.GeoJson(
            gdf_plot[["geometry", "display_type", "frp", "datetime"]].sort_values("frp", ascending=True),
            marker=fm.CircleMarker(radius=2,
                                fill=True,
                                fill_opacity=0.7,
                                weight=0
                                ),
            style_function=lambda feature: {
                "color": colormap_frp(feature["properties"]["frp"]),
                "fillColor": colormap_frp(feature["properties"]["frp"])
            },
            tooltip=make_point_tooltip()
        ).add_to(frp_points_group2)
        frp_points_group2.add_to(m)

        # html legend
        frp_html = """
        <div style="
            position: fixed;
            bottom: 150px;
            right: 10px;
            z-index: 1000;
            background-color: rgba(0,0,0,0.7);
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-family: Arial;
            font-size: 12px;
        ">
            <b>Fire Radiative Ppower [MW]</b><br>
        """

        colors = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
        for i in range(len(colors)):
            frp_html += f"""
            <div style="display:flex; align-items:center; margin-top:4px">
                <div style="background:{colors[i]}; width:20px; height:20px; margin-right:8px; border-radius:3px"></div>
                {breaks[i]:.2f} – {breaks[i+1]:.2f}
            </div>
            """

        frp_html += "</div>"
        m.get_root().html.add_child(fm.Element(frp_html))

    # ---------------------------------
    # Fire pixels by detection datetime
    # ---------------------------------
    date_min = gdf_plot["datetime_num"].min()
    date_max = gdf_plot["datetime_num"].max()

    colors = cm.linear.YlOrRd_09.colors[::-1]

    colormap_time = cm.LinearColormap(
        colors=colors,
        vmin=date_min,
        vmax=date_max
    )

    # plot
    time_points_group = fm.FeatureGroup(name="Fire Pixels by detection time", show=False)
    fm.GeoJson(
        gdf_plot[["geometry", "display_type", "frp", "datetime", "datetime_num"]],
        marker=fm.CircleMarker(radius=2,
                            fill=True,
                            fill_opacity=0.7,
                            weight=0
                            ),
        style_function=lambda feature:{
            "color": colormap_time(feature["properties"]["datetime_num"]),
            "fillColor": colormap_time(feature["properties"]["datetime_num"])
        },
        tooltip=make_point_tooltip()
    ).add_to(time_points_group)
    time_points_group.add_to(m)

    # html legend
    time_start = wf.cleaned["datetime"].min().strftime("%Y-%m-%d %H:%M UTC")
    time_end = wf.cleaned["datetime"].max().strftime("%Y-%m-%d %H:%M UTC")

    time_legend_html = f"""
    <div style="
        position: fixed;
        bottom: 30px;
        right: 10px;
        z-index: 1000;
        background-color: rgba(0,0,0,0.7);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        font-family: Arial;
        font-size: 12px;
    ">
        <b>Detection Time</b><br><br>
        <div style="
            width: 150px;
            height: 15px;
            background: linear-gradient(to right, #ffffb2, #bd0026);
            border-radius: 3px;
            margin-bottom: 4px;
        "></div>
        <div style="display:flex; justify-content:space-between; width:150px">
            <span>{time_start}</span>
            <span>{time_end}</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(fm.Element(time_legend_html))

    # ---------------------------------
    # Volcano pixels
    # ---------------------------------
    if "type" in wf.cleaned.columns:
        volcanoes_points = gdf_plot[gdf_plot["type"] == 1][
            ["geometry", "display_type", "frp", "datetime"]
            ]
        if len(volcanoes_points) < MAX_ROWS and len(volcanoes_points) > 0:
            volcano_pixels_group = fm.FeatureGroup(name="Volcano Pixels", show=False)
            fm.GeoJson(
                volcanoes_points,
                marker=fm.CircleMarker(radius=2,
                                    fill=True,
                                    fill_color="lime",
                                    fill_opacity=1,
                                    weight=0
                                    ),
                tooltip=make_point_tooltip()
            ).add_to(volcano_pixels_group)
            volcano_pixels_group.add_to(m)
        volcanoes_clusters = cluster_gdf_plot[cluster_gdf_plot["type"] == 1][
            ["geometry", "display_type", "pixel_count", "frp_sum", "frp_mean", "cluster_size_approx", "time_span"]
            ]
        if len(volcanoes_clusters) < MAX_ROWS and len(volcanoes_clusters) > 0:
            volcano_clusters_group = fm.FeatureGroup(name="Volcano Clusters", show=False)
            fm.GeoJson(
                volcanoes_clusters,
                marker=fm.CircleMarker(
                    fill=True,
                    fill_opacity=0,
                ),
                tooltip=make_cluster_tooltip(),
                style_function=make_style_fn('lime', 1),
            ).add_to(volcano_clusters_group)
            volcano_clusters_group.add_to(m)

    # ---------------------------------
    # Offshore pixels
    # ---------------------------------
    if "type" in wf.cleaned.columns:
        offshore_points = gdf_plot[gdf_plot["type"] == 3][
            ["geometry", "display_type", "frp", "datetime"]
            ]
        if len(offshore_points) < MAX_ROWS and len(offshore_points) > 0:
            offshore_pixels_group = fm.FeatureGroup(name="Offshore Pixels", show=False)
            fm.GeoJson(
                offshore_points,
                marker=fm.CircleMarker(radius=2,
                                    fill=True,
                                    fill_color="yellow",
                                    fill_opacity=1,
                                    weight=0
                                    ),
                tooltip=make_point_tooltip()
            ).add_to(offshore_pixels_group)
            offshore_pixels_group.add_to(m)
        offshore_clusters = cluster_gdf_plot[cluster_gdf_plot["type"] == 3][
            ["geometry", "display_type", "pixel_count", "frp_sum", "frp_mean", "cluster_size_approx", "time_span"]
            ]
        if len(offshore_clusters) < MAX_ROWS and len(offshore_clusters) > 0:
            offshore_clusters_group = fm.FeatureGroup(name="Offshore Clusters", show=False)
            fm.GeoJson(
                offshore_clusters,
                marker=fm.CircleMarker(
                    fill=True,
                    fill_opacity=0,
                ),
                tooltip=make_cluster_tooltip(),
                style_function=make_style_fn('yellow', 1),
            ).add_to(offshore_clusters_group)
            offshore_clusters_group.add_to(m)

    # ---------------------------------
    # other landsource pixels
    # ---------------------------------
    if "type" in wf.cleaned.columns:
        other_land_points = gdf_plot[gdf_plot["type"] == 2][
            ["geometry", "display_type", "frp", "datetime"]
            ]
        if len(other_land_points) < MAX_ROWS and len(other_land_points) > 0:
            other_land_pixels_group = fm.FeatureGroup(name="Other Land Source Pixels", show=False)
            fm.GeoJson(
                other_land_points,
                marker=fm.CircleMarker(radius=2,
                                    fill=True,
                                    fill_color="magenta",
                                    fill_opacity=1,
                                    weight=0
                                    ),
                tooltip=make_point_tooltip()
            ).add_to(other_land_pixels_group)
            other_land_pixels_group.add_to(m)
        other_land_clusters = cluster_gdf_plot[cluster_gdf_plot["type"] == 2][
            ["geometry", "display_type", "pixel_count", "frp_sum", "frp_mean", "cluster_size_approx", "time_span"]
            ]
        if len(other_land_clusters) < MAX_ROWS and len(other_land_clusters) > 0:
            other_land_clusters_group = fm.FeatureGroup(name="Other Land Source Clusters", show=False)
            fm.GeoJson(
                other_land_clusters,
                marker=fm.CircleMarker(
                    fill=True,
                    fill_opacity=0,
                ),
                tooltip=make_cluster_tooltip(),
                style_function=make_style_fn('magenta', 1),
            ).add_to(other_land_clusters_group)
            other_land_clusters_group.add_to(m)

    fm.LayerControl(collapsed=False,
                    position="topleft").add_to(m)
    plugins.MeasureControl(
        position="bottomleft",
        primary_length_unit="kilometers",
        secondary_length_unit="miles",
        primary_area_unit="sqmeters",
        secondary_area_unit="acres",
    ).add_to(m)
        
    return m