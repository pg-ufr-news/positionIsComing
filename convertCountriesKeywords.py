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

# pip3 install deep-translator
from deep_translator import GoogleTranslator
from difflib import SequenceMatcher

DATA_PATH = Path.cwd()

columns = ['keyword','language','topic','topicColor','keywordColor','limitPages','ratioNew']

origDf = pd.read_csv(DATA_PATH / 'csv' / 'countryInfo.csv', delimiter=',')
randomColors = []
for i in range(len(origDf)):
    randomColors.append('#%06X' % random.randint(0, 0xFFFFFF))


countriesDf = origDf.copy()
countriesDf['keyword'] = ""
for index, column in countriesDf.iterrows():
  countryDe = GoogleTranslator(source='en', target='de').translate(text=str(column['Country']).strip())
  countriesDf.loc[index,'keyword'] = "'"+countryDe+"'"
  time.sleep(1)
countriesDf['language'] = 'en'
countriesDf['topic'] = countriesDf['Country']
countriesDf['topicColor'] = randomColors
countriesDf['keywordColor'] = randomColors
countriesDf['limitPages'] = 2
countriesDf['ratioNew'] = 1000/countriesDf['Population']
countriesDf[countriesDf['ratioNew']>0.89]['ratioNew'] = 0.89
countriesDf = countriesDf.replace([np.inf], 0.9)
countriesDf['ratioNew'] += 0.1


capitalsDf = countriesDf.copy() 
for index, column in capitalsDf.iterrows():
  capitalDe = GoogleTranslator(source='en', target='de').translate(text=str(column['Capital']).strip())
  capitalsDf.loc[index,'keyword'] = "'"+capitalDe+"'"
  time.sleep(1)

print(capitalsDf)
print(capitalsDf)

bothDf = pd.concat([countriesDf,capitalsDf])
bothDf = bothDf.sort_values(['ratioNew'])
bothDf = bothDf[columns]
##bothDf = bothDf[bothDf[not 'keyword']=="'nan'"]
#
print(bothDf)

bothDf.to_csv(DATA_PATH / 'csv' / 'keywords.csv', index=False, columns=columns)

