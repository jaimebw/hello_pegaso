import streamlit as st
import pandas as pd
from datetime import datetime
from shapely.geometry import Polygon
import plotly.express as px
import h3
import geopandas


#
#
# 1. Functions
#
#

@st.cache_data
def load_data():
    df = pd.read_csv("aircraftinformation.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"],format = "mixed")
    return df

def h3_boundaries(row):
    """
    Transform h3 values to poligons
    """
    points = h3.h3_to_geo_boundary(row,True)
    return Polygon(points)

def extract_geojson(geo,h3_id):
    """
    Extracts geojson to plot heatmap
    """
    geodict =  geopandas.GeoSeries(geo).__geo_interface__
    geodict["features"][0]["id"] = h3_id
    return geodict["features"][0]

def geo_process(data,h3_resolution=6):
    """
    Add h3 data to the dataframe and return the geojson for plotting
    """
    data = data.dropna()
    #data["h3"] = data.apply(lambda row:\
    #        h3.geo_to_h3(row["lat"], row["lon"], h3_resolution), axis=1)
    data["boundaries"] = data.h3.apply(lambda row: h3_boundaries(row))
    data["geojson"] = data.apply(lambda row: extract_geojson(row["boundaries"],row["h3"]),axis = 1)

    return data 

def get_geodict(data):
    """
    Geodict for plotting utils
    """
    return  {
    "type": "FeatureCollection",
    "features": data['geojson'].tolist()
}



@st.cache_data
def get_stats(data):
    """
    Get stats for the dashboard.

    TODO: Añadir stats de número de muestras de la última hora, día, semana, mes

    """
    regis_vals = data.dropna().count().values[0]
    last_update=pd.to_datetime(data.timestamp.values[-1]).strftime('%d/%m/%Y %H:%M') 
    n_helicopters = data.dropna().registration.nunique()
    unique_helicopters = data.dropna().registration.unique().tolist()
    n_days = data.dropna().date.nunique()
    last_day_activity = data.dropna().date.values[-1]


    return {
            "regis_vals":regis_vals,
            "last_update": last_update,
            "n_helicopters":n_helicopters,
            "unique_helicopters":unique_helicopters,
            "n_days":n_days,# registered days with activity
            "last_day_activity":last_day_activity
            }

def h3_heatmap(data,geojson_dict):
    """
    Plot for the heatmap of the helicopter routes
    """
    return px.choropleth_mapbox(
    data, 
    geojson=geojson_dict,#h3_vals.geo_json.apply(lambda x: str(x)), 
    locations='h3', 
    color='count',
    color_continuous_scale="Viridis",
    range_color=(0, data["count"].mean()),
    mapbox_style='carto-positron',
    zoom=7,
    center={"lat": 40.4168, "lon": -3.7038},  # Madrid coordinates
    opacity=0.7
)
def trajectory_map(data,date):
    plotdata = data.loc[data.date == date].dropna()
    fig = px.line_mapbox(plotdata, lat="lat", lon="lon", color="registration", zoom=7,
                         center={"lat": 40.4168, "lon": -3.7038},
                         mapbox_style="carto-positron")
    return fig


#
#
# 2. Data prep
#
#
#

data = load_data()
data["h3"] = data.apply(lambda row:h3.geo_to_h3(row["lat"], row["lon"], 6), axis=1)
data["date"] = data.timestamp.dt.strftime("%d-%m-%y")
data["date"] = data.date.apply(lambda x: datetime.strptime(x,"%d-%m-%y"))
agg_data = data.copy()
agg_data = agg_data.dropna()

agg_data = agg_data.h3.value_counts().to_frame().reset_index()
agg_data = geo_process(agg_data)

geodict = get_geodict(agg_data)
stats = get_stats(data)


#
#
# 3. Dashboard
#
#
#

st.title("Pegaso helicopter stats dashboard")
st.subheader("General stats")
col1, col2= st.columns(2)

with col1:
    st.metric("Number of samples", stats["regis_vals"])
    st.markdown("Registered helicopters")
    for heli in stats["unique_helicopters"]:
        st.write(heli)
with col2:
    st.metric("Last updated", stats["last_update"])

st.subheader("Heatmap")
st.markdown("The heatmap shows the number of time a helicopter has been registered in that cell")
st.plotly_chart(h3_heatmap(agg_data,geodict))
av_dates = data.dropna().date.unique().tolist()
st.subheader("Helicopter routes")
date = st.date_input("Select the day you want to visualize",
                     min_value = av_dates[0],
                     max_value = av_dates[-1],
                     value=av_dates[-1])
date = datetime.strptime(str(date),"%Y-%m-%d")
st.plotly_chart(trajectory_map(data,date))
