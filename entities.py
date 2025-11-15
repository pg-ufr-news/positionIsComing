import pandas as pd

from pathlib import Path
import os.path
import io
#import requests
import glob

import time
from datetime import datetime
from dateutil import parser
from datetime import date, timedelta, datetime, timezone

# pip3 install spacy
# python3 -m spacy download de_core_news_md
#pip3 install textblob_de

import nltk
import spacy
import de_core_news_md
from textblob_de import TextBlobDE

nlp = de_core_news_md.load()
nltk.download('punkt')


DATA_PATH = Path.cwd()
if(not os.path.exists(DATA_PATH / 'csv')):
    os.mkdir(DATA_PATH / 'csv')

def getAge(dateString):
    today = datetime.now(timezone.utc)
    timeDate = -1
    pubDate = None
    try:
        pubDate = parser.parse(dateString)
    except:
        print('date parse error 1')
    if(not pubDate):
      try:
        pubDate = parser.isoparse(dateString)
      except:
        print('date parse error 2')   
    if(pubDate):
        timeDate = today - pubDate
        timeDate = timeDate.days 
    return timeDate

def getNewsFiles():
    fileName = './csv/news_????_??.csv'
    files = glob.glob(fileName)
    return files  

def getNewsDFbyList(files):    
    newsDF = pd.DataFrame(None)
    for file in files:
        df = pd.read_csv(file, delimiter=',')
        if(newsDF.empty):
            newsDF = df
        else:
            newsDF = pd.concat([newsDF, df])
    newsDF = newsDF.sort_values(by=['published'], ascending=True)        
    return newsDF 

def getNewsDF():
    files = getNewsFiles()
    newsDF = getNewsDFbyList(files)
    return newsDF         

keywordsDF = pd.read_csv(DATA_PATH / 'keywords.csv', delimiter=',')
keywordsDF = keywordsDF.drop(columns = ['language'])

newsDf = getNewsDF()
if(not newsDf.empty):
  newsDf['age'] = newsDf['published'].apply(
    lambda x: 
        getAge(x)
  )
  newsDf = newsDf[(newsDf.age>0) & (newsDf.age < 90)]
print(newsDf)   

keywordsNewsDF = pd.merge(keywordsDF, newsDf, how='left', left_on=['keyword'], right_on=['keyword'])
print(keywordsNewsDF)  

newsDf['subjectivity'] = 0.0
newsDf['sentiment'] = 0.0
newsDf['count'] = 1.0
newsDf['week'] = '0000-00'
newsDf['day'] = '000-00-00'

i=0
##topicWordsAbs = {'summaryOfAllWords': emptyTopics.copy()}
for index, column in newsDf.iterrows():
    i += 1
    if(i % 50 == 0):
        print(i)
    quote = str(column.title)+'. ' +str(column.description)+' '+str(column.content)
    #quote = str(column.title)+'. ' +str(column.description)
    blob = TextBlobDE(quote)
    newsDf.loc[newsDf['url'] == column['url'], 'subjectivity'] = blob.sentiment.subjectivity
    newsDf.loc[newsDf['url'] == column['url'], 'sentiment'] = blob.sentiment.polarity
    try:
      pubDate = parser.parse(column['published'])
      newsDf.loc[newsDf['url'] == column['url'], 'week'] = pubDate.strftime('%Y-%W')
      newsDf.loc[newsDf['url'] == column['url'], 'day'] = pubDate.strftime('%Y-%m-%d')
    except:
      print('date parse error')

##keywordsNewsDF = newsDf.groupby('keyword').mean()

def groupSentiments(df, aggColumn):
	cols = [aggColumn,'sentiment_mean','sentiment_std','subjectivity_mean','subjectivity_std','counting']
	groupDF = df.groupby([aggColumn], as_index=False).agg(
		              {'sentiment':['mean','std'],'subjectivity':['mean','std'],'count':'sum'})
	groupDF.columns = cols
	groupDF.reindex(columns=sorted(groupDF.columns))
	groupDF = groupDF.sort_values(by=['counting'], ascending=False)
	groupDF['sentiment_std'] = groupDF['sentiment_std'].fillna(1)
	groupDF['subjectivity_std'] = groupDF['subjectivity_std'].fillna(1)
	return groupDF 

domainDF = groupSentiments(newsDf, 'domain')
domainDF.loc[domainDF['counting'] < 2, 'sentiment_mean'] = 0.0
domainDF.loc[domainDF['counting'] < 2, 'subjectivity_mean'] = 0.0
print(domainDF)
cols = ['domain','sentiment_mean','sentiment_std','subjectivity_mean','subjectivity_std','counting']
domainDF.to_csv(DATA_PATH / 'csv' / 'sentiments_domains.csv', columns=cols,index=False) 

objNewsDF = pd.merge(newsDf, domainDF, how='left', left_on=['domain'], right_on=['domain'])
objNewsDF['subjectivity'] = (objNewsDF['subjectivity'] - objNewsDF['subjectivity_mean'])/objNewsDF['subjectivity_std']
objNewsDF['sentiment'] = (objNewsDF['sentiment'] - objNewsDF['sentiment_mean'])/objNewsDF['sentiment_std']
print(objNewsDF)  

weeksDF =  groupSentiments(objNewsDF, 'week')
weeksDF = weeksDF.sort_values(by=['week'], ascending=True)
weeksDF.to_csv(DATA_PATH / 'csv' / 'sentiments_weeks.csv',index=False) 

daysDF =  groupSentiments(objNewsDF, 'day')
daysDF = daysDF.sort_values(by=['day'], ascending=True)
daysDF.to_csv(DATA_PATH / 'csv' / 'sentiments_days.csv',index=False) 

keywordsSentimentDF =  groupSentiments(objNewsDF, 'keyword')
keywordsSentimentDF = keywordsSentimentDF.sort_values(by=['keyword'], ascending=True)
keywordsSentimentDF.to_csv(DATA_PATH / 'csv' / 'sentiments_keywords.csv',index=False) 


print(list(newsDf.columns))
print(list(objNewsDF.columns))
print(list(keywordsDF.columns))
topicNewsDF = pd.merge(objNewsDF, keywordsDF, how='left', left_on=['keyword'], right_on=['keyword'])
print(list(topicNewsDF.columns))
topicsDF =  groupSentiments(topicNewsDF, 'topic')
topicsDF = topicsDF.sort_values(by=['topic'], ascending=True)
topicsDF.to_csv(DATA_PATH / 'csv' / 'sentiments_topics.csv',index=False) 


emptyDict = {'count':0,'sentiment':0,'subjectivity':0}
indexLocations = {}
indexOrganizations = {}
indexPersons = {}
indexNewLocations = {}
indexMisc = {}
indexMissing = {}

def locationInSearch(location):
    for keyword in keywordsDF['keyword']:
        if((location in keyword) or (keyword.strip("'") in location)):
             return True
    return False

def strangeCharacters(testString, testCharacters):
     count = 0
     for oneCharacter in testCharacters:
          count += testString.count(oneCharacter)
     return count

i=0
##topicWordsAbs = {'summaryOfAllWords': emptyTopics.copy()}
for index, column in objNewsDF.iterrows():
    i += 1
    if(i % 50 == 0):
        print(i)
    quote = str(column.title)+'. ' +str(column.description)+' '+str(column.content)
    lang = column.language 
    #quote = str(column.title)+'. ' +str(column.description)
    blob = TextBlobDE(quote)
    for sentence in blob.sentences:
        #sentence.sentiment.polarity
        doc = nlp(str(sentence))
        for entity in doc.ents:

            if(entity.label_ in ['LOC','GPE']):
                if(entity.text in indexLocations):
                    indexLocations[entity.text]['count'] += 1
                    indexLocations[entity.text]['sentiment'] += sentence.sentiment.polarity
                    indexLocations[entity.text]['subjectivity'] += sentence.sentiment.subjectivity
                else:      
                    indexLocations[entity.text] = {'phrase':entity.text, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                                   'subjectivity':sentence.sentiment.subjectivity, 'language':lang,'count':1}

                if(not locationInSearch(entity.text) and (column.age < 60)):
                  if(entity.text in indexNewLocations):
                    indexNewLocations[entity.text]['count'] += 1
                    indexNewLocations[entity.text]['sentiment'] += sentence.sentiment.polarity
                    indexNewLocations[entity.text]['subjectivity'] += sentence.sentiment.subjectivity
                  else:    
                    indexNewLocations[entity.text] = {'phrase':entity.text, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                                 'subjectivity':sentence.sentiment.subjectivity, 'language':lang, 'count':1}  

            elif(entity.label_ in ['PER','PERSON']):
             personText = entity.text
             personText = personText.strip(" .,!?;:'…/-").strip('"')
             if(strangeCharacters(personText,".,!?;:'…<>/\n\r")==0):
               if(personText.count(' ')>0):
                if(personText in indexPersons):
                    indexPersons[personText]['count'] += 1
                    indexPersons[personText]['sentiment'] += sentence.sentiment.polarity
                    indexPersons[personText]['subjectivity'] += sentence.sentiment.subjectivity
                else:    
                    indexPersons[personText] = {'phrase':personText, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                                 'subjectivity':sentence.sentiment.subjectivity, 'language':lang, 'count':1} 
 
            elif('ORG' == entity.label_):
                if(entity.text in indexOrganizations):
                    indexOrganizations[entity.text]['count'] += 1
                    indexOrganizations[entity.text]['sentiment'] += sentence.sentiment.polarity
                    indexOrganizations[entity.text]['subjectivity'] += sentence.sentiment.subjectivity
                else:    
                    indexOrganizations[entity.text] = {'phrase':entity.text, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                                       'subjectivity':0, 'language':lang, 'count':1} 
            elif('MISC' == entity.label_):
                if(entity.text in indexMisc):
                    indexMisc[entity.text]['count'] += 1
                    indexMisc[entity.text]['sentiment'] += sentence.sentiment.polarity
                    indexMisc[entity.text]['subjectivity'] += sentence.sentiment.subjectivity
                else:         
                    indexMisc[entity.text] = {'phrase':entity.text, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                              'subjectivity':sentence.sentiment.subjectivity, 'language':lang, 'count':1} 
            else:
                if(entity.text in indexMissing):
                    indexMissing[entity.text]['count'] += 1
                    indexMissing[entity.text]['sentiment'] += sentence.sentiment.polarity
                    indexMissing[entity.text]['subjectivity'] += sentence.sentiment.subjectivity
                else:
                    indexMissing[entity.text] = {'phrase':entity.text, 'label':entity.label_, 'sentiment':sentence.sentiment.polarity,
                                                 'subjectivity':sentence.sentiment.subjectivity, 'language':lang, 'count':1}  

colSent = ['phrase', 'label', 'sentiment', 'subjectivity', 'language', 'count']
indexLocationsDF = pd.DataFrame.from_dict(indexLocations, orient='index', columns=colSent)
indexLocationsDF['sentiment'] = indexLocationsDF['sentiment']/indexLocationsDF['count']
indexLocationsDF['subjectivity'] = indexLocationsDF['subjectivity']/indexLocationsDF['count']
indexLocationsDF = indexLocationsDF.sort_values(by=['count'], ascending=False)
indexLocationsDF.to_csv(DATA_PATH / 'csv' / "sentiments_locations.csv", index=True)   
 
indexPersonsDF = pd.DataFrame.from_dict(indexPersons, orient='index', columns=colSent)
indexPersonsDF['sentiment'] = indexPersonsDF['sentiment']/indexPersonsDF['count']
indexPersonsDF['subjectivity'] = indexPersonsDF['subjectivity']/indexPersonsDF['count']
indexPersonsDF = indexPersonsDF.sort_values(by=['count'], ascending=False)
indexPersonsDF.to_csv(DATA_PATH / 'csv' / "sentiments_persons.csv", index=True)

indexNewLocationsDF = pd.DataFrame.from_dict(indexNewLocations, orient='index', columns=colSent)
indexNewLocationsDF['sentiment'] = indexNewLocationsDF['sentiment']/indexNewLocationsDF['count']
indexNewLocationsDF['subjectivity'] = indexNewLocationsDF['subjectivity']/indexNewLocationsDF['count']
indexNewLocationsDF = indexNewLocationsDF.sort_values(by=['count'], ascending=False)
indexNewLocationsDF.to_csv(DATA_PATH / 'csv' / "sentiments_new_locations.csv", index=True)

indexOrganizationsDF = pd.DataFrame.from_dict(indexOrganizations, orient='index', columns=colSent)
indexOrganizationsDF['sentiment'] = indexOrganizationsDF['sentiment']/indexOrganizationsDF['count']
indexOrganizationsDF['subjectivity'] = indexOrganizationsDF['subjectivity']/indexOrganizationsDF['count']
indexOrganizationsDF = indexOrganizationsDF.sort_values(by=['count'], ascending=False)
indexOrganizationsDF.to_csv(DATA_PATH / 'csv' / "sentiments_organizations.csv", index=True)

indexMiscDF = pd.DataFrame.from_dict(indexMisc, orient='index', columns=colSent)
indexMiscDF['sentiment'] = indexMiscDF['sentiment']/indexLocationsDF['count']
indexMiscDF['subjectivity'] = indexMiscDF['subjectivity']/indexLocationsDF['count']
indexMiscDF = indexMiscDF.sort_values(by=['count'], ascending=False)
indexMiscDF.to_csv(DATA_PATH / 'csv' / "sentiments_misc.csv", index=True)

indexMissingDF = pd.DataFrame.from_dict(indexMissing, orient='index', columns=colSent)
indexMissingDF['sentiment'] = indexMissingDF['sentiment']/indexLocationsDF['count']
indexMissingDF['subjectivity'] = indexMissingDF['subjectivity']/indexLocationsDF['count']
indexMissingDF = indexMissingDF.sort_values(by=['count'], ascending=False)
indexMissingDF.to_csv(DATA_PATH / 'csv' / "sentiments_missing.csv", index=True)



