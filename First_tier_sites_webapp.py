# -*- coding: utf-8 -*-
"""
Created on Tue Dec 21 07:19:36 2021

@author: ekonyag
"""

import streamlit as st
import geopandas as gpd
from shapely.ops import unary_union
from geovoronoi import voronoi_regions_from_coords
import pandas as pd
from math import sin, cos, sqrt, atan2, radians


st.title("First Tier Sites webapp")
st.subheader("This application will calculate first tier locations of required lat long")
file = st.file_uploader("Upload Planar physical data 'Physical_location_list_with_remote.xlsx'")
exclude = st.checkbox("Exclude IBC sites")

@st.cache
def load_database(file):
    df = pd.read_excel(file,usecols=['U21_STATUS','U21_SITETYPE','LOCATION_ID','LATITUDE','LONGITUDE'])
    if exclude:
        df = df.loc[(df['U21_STATUS']=='On Air')&(df['U21_SITETYPE']!='IBC')][['LOCATION_ID','LATITUDE','LONGITUDE']]
    else:
        df = df.loc[(df['U21_STATUS']=='On Air')][['LOCATION_ID','LATITUDE','LONGITUDE']]
    return df
def distance(lat1,lon1,lat2,lon2):
    R = 6373.0

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance

choice = st.selectbox("Select mode",['Single','Bulk'])

if choice=='Single':
    col1,col2 = st.columns(2)
    Lat = col1.text_input("Latitude(degrees)")
    Long = col2.text_input("Longitude(degrees)")
    tempcode = pd.DataFrame.from_dict(
        {'LOCATION_ID':'Temp001',
         'LATITUDE':[Lat],
         'LONGITUDE':[Long]},orient='columns')
    st.dataframe(tempcode)
    
else:
    st.write("""Upload the tempcode .xlsx file with 3 columns only LOCATION_ID,LATITUDE,LONGITUDE""")
    file1=st.file_uploader('Upload here')
    if file1 is not None:
        tempcode = pd.read_excel(file1,usecols=['LOCATION_ID','LATITUDE','LONGITUDE'])

calc = st.button("Calculate")
if calc:
    existing = load_database(file)
    existing = pd.concat([existing,tempcode],axis=0,ignore_index = True)
    region = gpd.read_file(r'webapp\Region shape file\Region.tab')
    coords = existing[['LONGITUDE','LATITUDE']].to_numpy()
    boundary_shape = unary_union(region.geometry).buffer(0.5)
    poly_shapes, poly_to_pt_assignments = voronoi_regions_from_coords(coords,boundary_shape)
    voronoi_polygons = gpd.GeoDataFrame()
    voronoi_polygons['geometry'] = poly_shapes.values()
    voronoi_polygons['region_id'] = poly_to_pt_assignments
    for i in range(len(voronoi_polygons)):
        voronoi_polygons.loc[i,'region_id'] = poly_to_pt_assignments[i][0]
    voronoi_polygons = voronoi_polygons.set_index('region_id',drop = True)
    existing = pd.merge(existing,voronoi_polygons,how = 'inner',left_index = True,right_index = True)
    existing = gpd.GeoDataFrame(existing,geometry = 'geometry')
    first_tier = gpd.sjoin(existing,existing,how = 'inner',op = 'touches')
    first_tier = first_tier.loc[first_tier['LOCATION_ID_left']!=first_tier['LOCATION_ID_right']]
    first_tier = first_tier[['LOCATION_ID_left','LOCATION_ID_right','LATITUDE_right','LONGITUDE_right']].reset_index(drop = True)
    tempcode_firsttier = pd.merge(tempcode,first_tier,how = 'left',left_on = 'LOCATION_ID',right_on = 'LOCATION_ID_left')
    tempcode_firsttier['Distance'] = tempcode_firsttier.apply(lambda x:distance(x.LATITUDE,x.LONGITUDE,x.LATITUDE_right,x.LONGITUDE_right),axis=1)
    st.dataframe(tempcode_firsttier)
    st.download_button('Download CSV',tempcode_firsttier.to_csv(),'output.csv')

st.write("** Developer:Ankur Goyal**")
    
