import pandas as pd
import numpy as np
import csv
import io
import requests
import json

from pathlib import Path
import os.path
import io
#import requests
import glob
import hashlib
import random

#import datetime
import time
from dateutil import parser
from datetime import date, timedelta, datetime, timezone

DATA_PATH = Path.cwd()

keywordsDF = pd.read_csv(DATA_PATH / 'keywords.csv', delimiter=',')


def searchGndByGeonamesId(geonamesId):
    gndurl = 'https://lobid.org/gnd/search?q='+str(geonamesId)+'&filter=type%3APlaceOrGeographicName&format=json'   #hasGeometry
    page = requests.get(gndurl, timeout=60)
    if page.status_code == 200:
      content = page.content
      #print(content)
      if(content):
        #print(content)
        jsonData = json.loads(content)
        print(jsonData)      #'variantName' !
        if('member' in jsonData):
          for member in jsonData['member']:
           if('sameAs' in member):
             for same in member['sameAs']:
               print(25*"##")
               print(same)
               if('id' in same):
                 if(same['id']=="https://sws.geonames.org/"+str(geonamesId)):
                   if('gndIdentifier' in member):
                     result = {'gndId':member['gndIdentifier']} 
                     #print(member['gndIdentifier']) 
                     #print(25*"=*")
                     #print(member)  
                     if('hasGeometry' in member):
                       #print(member['hasGeometry']) 
                       latitude = None
                       longitude = None
                       for geo in member['hasGeometry']:  
                         if('asWKT' in geo and 'type' in geo and geo['type']=='Point'):
                            point = geo['asWKT'][0]
                            point = point.replace('Point ','').strip().strip('()').strip()
                            print(point)
                            coords = point.split(" ")
                            print(coords)
                            result['longitude'] = float(coords[0])
                            result['latitude'] = float(coords[1])
                     if('variantName' in member):
                       #print(member['variantName']) 
                       result['variantNames'] = member['variantName']  
                     if('preferredName' in member):
                       #print(member['preferredName'])
                       result['preferredName'] = member['preferredName']
                     return result
    return None

def searchGndByNameAndGeo(locationName, latitude, longitude):
    gndUrl = 'https://explore.gnd.network/search?term='+locationName+'&f.satzart=Geografikum&rows=1'
    gndurl = 'https://lobid.org/gnd/search?q='+locationName+'&filter=type%3APlaceOrGeographicName&format=json'   #hasGeometry
    page = requests.get(gndurl, timeout=60)
    if page.status_code == 200:
      content = page.content
      #print(content)
      if(content):
        #print(content)
        jsonData = json.loads(content)
        #print(jsonData)      #'variantName' !
        if('member' in jsonData):
          minDistance2 = 10E9
          result = None
          for member in jsonData['member']:
           #print(25*"=*")
           #print(member)  
           if('hasGeometry' in member):
            #print(member['hasGeometry']) 
            for geo in member['hasGeometry']: 
             if('asWKT' in geo and 'type' in geo and geo['type']=='Point'):
               point = geo['asWKT'][0]
               point = point.replace('Point ','').strip().strip('()').strip()
               #print(point)
               coords = point.split(" ")
               #print(coords)
               currLongitude = float(coords[0])
               currLatitude = float(coords[1])
               distance2 = (currLongitude-longitude)**2+(currLatitude-latitude)**2
               if(distance2<minDistance2):
                 minDistance = distance2 
                 if('gndIdentifier' in member):
                   #print(member['gndIdentifier']) 
                   result = {'longitude':currLongitude, 'latitude':currLatitude, 'distance':distance2**0.5}
                   result['gndId'] = member['gndIdentifier']
                   if('preferredName' in member):
                     #print(member['preferredName']) 
                     result['preferredName'] = member['preferredName']
          return result
        return None                   

def searchGndByName(locationName):
    gndUrl = 'https://explore.gnd.network/search?term='+locationName+'&f.satzart=Geografikum&rows=1'
    gndurl = 'https://lobid.org/gnd/search?q='+locationName+'&filter=type%3APlaceOrGeographicName&format=json'   #hasGeometry
    page = requests.get(gndurl, timeout=60)
    if page.status_code == 200:
      content = page.content
      #print(content)
      if(content):
        #print(content)
        jsonData = json.loads(content)
        #print(jsonData)      #'variantName' !
        if('member' in jsonData):
          for member in jsonData['member']:
           print(25*"=*")
           #print(member)  
           if('gndIdentifier' in member):
             print(member['gndIdentifier']) 
             result = {'gndId':member['gndIdentifier']} 
             if('hasGeometry' in member):
               #print(member['hasGeometry']) 
               latitude = None
               longitude = None
               for geo in member['hasGeometry']:  
                 if('asWKT' in geo and 'type' in geo and geo['type']=='Point'):
                    point = geo['asWKT'][0]
                    point = point.replace('Point ','').strip().strip('()').strip()
                    print(point)
                    coords = point.split(" ")
                    print(coords)
                    result['longitude'] = float(coords[0])
                    result['latitude'] = float(coords[1])
             if('variantName' in member):
               #print(member['variantName']) 
               result['variantNames'] = member['variantName']  
             if('preferredName' in member):
               #print(member['preferredName'])
               result['preferredName'] = member['preferredName']
             return result
    return None
  

##searchGndByName('Deutschland')
##print(searchGndByGeonamesId(2643743))
print(searchGndByNameAndGeo('Alofi', -19.05294,-169.91957))
print(searchGndByName('Alofi'))

keywordsDF['gnd'] = ''
for index, column in keywordsDF.iterrows():
    found = False 
    gnd = searchGndByGeonamesId(column['geonames'])
    if(gnd and 'gndId' in gnd):
      keywordsDF.loc[index,'gnd'] = gnd['gndId']
      found = True
    if(not found):
      gnd = searchGndByNameAndGeo(column['keyword'], column['latitude'], column['longitude'])
      if(gnd and 'gndId' in gnd):
        keywordsDF.loc[index,'gnd'] = gnd['gndId']
        found = True
    if(not found):
      gnd = searchGndByName(column['keyword'])
      if(gnd and 'gndId' in gnd):
        keywordsDF.loc[index,'gnd'] = gnd['gndId']
        found = True

print(keywordsDF)
keywordsDF.to_csv(DATA_PATH / 'csv'/ 'keywords.csv',index=False)

