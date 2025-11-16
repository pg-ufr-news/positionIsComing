import mysecrets
import pandas as pd

from pathlib import Path
import os.path

#import requests
#from urllib.parse import urlparse
#import json
#import time
#import smtplib
#import random

import time
#import datetime
#from dateutil import parser

import geocoder
import geopandas
import colorsys


#1000 per hour! 10000 per day.

DATA_PATH = Path.cwd()
  
keywordsDF = pd.read_csv(DATA_PATH / 'keywords.csv', delimiter=',')
if (not 'continent' in keywordsDF.columns):
  keywordsDF['continent'] = ''
  keywordsDF['geonames'] = -1
  keywordsDF['latitude'] = None
  keywordsDF['longitude'] = None
  keywordsDF['geotype'] = ''
  keywordsDF['country'] = ''
  keywordsDF['ipcc'] = ''

ipccRegions = geopandas.read_file('https://github.com/creDocker/creAssets/blob/main/cre/versions/u24.04/assets/public/ipcc/IPCC-WGI-reference-regions-v4.geojson?raw=true')

geonamesKey = 'GEONAMES_KEY'
geonamesKey = os.getenv('GEONAMES_KEY')
if(geonamesKey == '1a2b3c4d5'): 
    print('Please set geonames.org key in file: secrets.py');
    exit()

imax = 550
for index, column in keywordsDF.iterrows():
    if(imax>0):
        lang = str(column.language)
        phrase = str(column.keyword)
        if(str(column.geonames) == '-1'):
          gn = geocoder.geonames(phrase, lang=lang, key=geonamesKey)
          print([phrase,gn,gn.geonames_id]) 
          if(gn.geonames_id):  
            keywordsDF.loc[index,'geonames'] = int(gn.geonames_id)
            keywordsDF.loc[index,'latitude'] = float(gn.lat)
            keywordsDF.loc[index,'longitude'] = float(gn.lng)
            keywordsDF.loc[index,'geotype'] = gn.feature_class
            keywordsDF.loc[index,'country'] = gn.country

            print(['geo',gn.lat,gn.lng, gn])
            (r, g, b) = colorsys.hls_to_rgb((float(gn.lng)+180)/360, (0.8*float(gn.lat)+90)/180, 0.8)
            hexColor = "#{:02x}{:02x}{:02x}".format(int(255*r),int(255*g),int(255*b))
            keywordsDF.loc[index,'topicColor'] = hexColor
            keywordsDF.loc[index,'keywordColor'] = hexColor

            #(get country) get ipcc
            coordinates = geopandas.points_from_xy([float(gn.lng)], [float(gn.lat)])
            Coords = geopandas.GeoDataFrame({
              'geometry': coordinates,
              'name': [phrase]
             }, crs={'init': 'epsg:4326', 'no_defs': True})
            whichIpcc = geopandas.sjoin(ipccRegions, Coords, how='inner', op='intersects')
            print(whichIpcc)
            if(not whichIpcc.empty):
                keywordsDF.loc[index,'ipcc'] = list(whichIpcc['Acronym'])[0]
                keywordsDF.loc[index,'continent'] = list(whichIpcc['Continent'])[0]


            imax -= 1
            time.sleep(1) 
    else:
        print("daily geonames limit has been reached, please re-run later.")

print(keywordsDF)
keywordsDF.to_csv(DATA_PATH / 'csv'/ 'keywords.csv',index=False)
