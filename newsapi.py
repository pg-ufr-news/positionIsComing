import mysecrets
import os
import sys
import math

import pandas as pd

from pathlib import Path
import os.path
import glob

import aiohttp
import asyncio
import io
import requests
from urllib.parse import urlparse
import json
import time
import smtplib
import random
import hashlib
import glob
from difflib import SequenceMatcher


import datetime
#from datetime import timezone
from dateutil import parser
from datetime import date, timedelta, datetime, timezone

import nltk
import spacy
import de_core_news_md
from textblob_de import TextBlobDE
nlp = de_core_news_md.load()
nltk.download('punkt')

DATA_PATH = Path.cwd()

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

keywordsFields = ["keyword","language","topic","topicColor","keywordColor","limitPages","ratioNew",
                  "continent","gnd","geonames","latitude","longitude","geotype","country","ipcc"]

keywordsDF = pd.read_csv(DATA_PATH / 'keywords.csv', delimiter=',')  #,index_col='keyword'
keywordsDF['uniqueString'] = keywordsDF['keyword'] + "_" + keywordsDF['language'] + "_" + keywordsDF['topic']
keywordsDF['crc'] = keywordsDF['uniqueString'].apply(
    lambda x: 
        hashlib.sha256(x.encode()).hexdigest()
)
keywordsDF = keywordsDF.drop_duplicates(subset=['keyword'])
keywordsDF = keywordsDF.sort_values(by=['ratioNew'], ascending=False)  

def addNewLocations(urlNames, keyDF, newRatio=0.5,language='de', limitCount=9):
    stream=requests.get(urlNames).content
    newDF=pd.read_csv(io.StringIO(stream.decode('utf-8')), delimiter=',')
    newDF = newDF.dropna()
    if(not newDF.empty):
     newDF = newDF[(newDF['count'] > limitCount)]
     if(not newDF.empty):
      for index, column in newDF.iterrows():
        newPhrase = "'" + column['phrase'] + "'" 
        if(not newPhrase in keyDF['keyword'].unique()):
          newData = {'keyword':newPhrase, 'language':column['language'], 'topic':column['country'], 'topicColor':column['topicColor'], 'keywordColor':column['keywordColor'], 'limitPages':2, 'ratioNew':(newRatio+random.random()/10000+column['count']/1000), 'continent':column['continent'], 'gnd':column['gnd'], 'geonames':column['geonames'], 'latitude':column['latitude'], 'longitude':column['longitude'], 'geotype':column['geotype'], 'country':column['country'], 'ipcc':column['ipcc']}
          ##print(newData)  
          keyDF = pd.concat([keyDF, pd.DataFrame([newData])], ignore_index=True)
    return keyDF

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
    if(not newsDF.empty):
        newsDF = newsDF.sort_values(by=['published'], ascending=True)        
    return newsDF 

def getNewsDF():
    files = getNewsFiles()
    newsDF = getNewsDFbyList(files)
    return newsDF     

newsDf = getNewsDF()
newsDf['age'] = newsDf['published'].apply(
    lambda x: 
        getAge(x)
)
newsDf = newsDf[(newsDf.age>0) & (newsDf.age < 60)]

keywordsNewsDF = pd.DataFrame(None) 
if(not newsDf.empty):
  keywordsNewsDF = newsDf.groupby('keyword').count()
  keywordsNewsDF = keywordsNewsDF.drop(columns = ['language'])


keywordsNewsDF2 = pd.DataFrame(None) 
if(not keywordsNewsDF.empty):
  keywordsNewsDF2 = pd.merge(keywordsDF, keywordsNewsDF, how='left', left_on=['keyword'], right_on=['keyword'])
  keywordsNewsDF2['index'] = keywordsNewsDF2['index'].fillna(0)
  keywordsNewsDF2['index'] = keywordsNewsDF2['index'] - keywordsNewsDF2['ratioNew']
  keywordsNewsDF2 = keywordsNewsDF2.sort_values(by=['index'], ascending=True)  

rows20 = int(math.ceil(keywordsNewsDF2.shape[0]/5))
keywordsNewsDF2 = keywordsNewsDF2.head(rows20)
print(keywordsNewsDF2)   

rows20 = int(math.ceil(keywordsDF.shape[0]/5))
keywordsDF3 = keywordsDF.head(rows20)
print(keywordsDF3)


searchWords = dict(zip(keywordsDF.keyword.values, keywordsDF.language.values))

#print(keywordsDF)
#print(searchWords)
#print(keywordsDF.sample() )


stopDomains = ["www.mydealz.de", "www.techstage.de", "www.nachdenkseiten.de", "www.amazon.de", "www.4players.de", "www.netzwelt.de", "www.nextpit.de",
               "www.mein-deal.com", "www.sparbote.de", "www.xda-developers.com" "www.pcgames.de", "blog.google", "www.ingame.de", "playstation.com",
               "www.pcgameshardware.de", "9to5mac.com", "roanoke.com", "billingsgazette.com", "richmond.com", "www.rawstory.com", "slate.com",
               "www.computerbild.de", "www.giga.de", "www.heise.de", "www.chip.de", "consent.google.com"
                ]


#https://github.com/theSoenke/news-crawler/blob/master/data/feeds_de.txt

                  
def dataIsNotBlocked(data):
    for blocked in stopDomains: 
        if blocked in data['domain']:
            return False
    return True         

#replace/drop: "https://www.zeit.de/zustimmung?url="  

#get url data (inq)  -> check if keyword in title|description    and url equal
#see 'https://www.stern.de/panorama/weltgeschehen/news-heute---ocean-viking--rettet-mehr-als-40-menschen-aus-dem-mittelmeer-30598826.html'

def personInSearchCrc(person):
    for index, column in keywordsDF.iterrows():
        if((person in column['keyword']) or (column['keyword'].strip("'") in person)):
             return column['crc']
    return None

def strangeCharacters(testString, testCharacters):
     count = 0
     for oneCharacter in testCharacters:
          count += testString.count(oneCharacter)
     return count

def incrementLocationsInKeywords(data):
    #global keywordsDF
    #print(['incrementLocationsInKeywords data',data]) 
    quote = str(data['title'])+'. ' +str(data['description'])+' '+str(data['content'])
    #lang = data['language'] 
    blob = TextBlobDE(quote)
    locationsDone = []
    for sentence in blob.sentences:
        #sentence.sentiment.polarity
        doc = nlp(str(sentence))
        for entity in doc.ents:
          #print(entity) 
          if(entity.label_ in ['LOC','GPE']):
           locationText = entity.text
           locationText = locationText.strip(" .,!?;:'…/-").strip('"')
           if(strangeCharacters(locationText,".,!?;:'…<>/\n\r")==0):
               #if(personText.count(' ')>0):
               if(not locationText in locationsDone):
                crc = personInSearchCrc(locationText)
                if(crc):
                  oldRatio = float(keywordsDF.loc[keywordsDF['crc'] == crc, 'ratioNew'].iloc[0])
                  newRatio = math.atan(math.tan(oldRatio*math.pi/2) + 1/500)*2/math.pi
                  print(['incrementLocationsInKeywords ratio',locationText,oldRatio,newRatio])
                  keywordsDF.loc[keywordsDF['crc'] == crc, 'ratioNew'] = newRatio
                  locationsDone.append(locationText) 
    return True


collectedNews = {}

def addNewsToCollection(data):
    global collectedNews
    pubDate = parser.parse(data['published'])
    fileDate = 'news_'+pubDate.strftime('%Y_%m')+'.csv'
    if(fileDate in collectedNews):
      if(not data['url'] in collectedNews[fileDate]):
        incrementLocationsInKeywords(data)
        if(not 'archive' in data):
           data = archiveUrl(data)
        collectedNews[fileDate][data['url']] = data
        return True
    return False

def storeCollection():
    global collectedNews
    print("Inside store")
    cols = ['url','valid','domain','title','description','image','published','archive','content','quote','language','keyword']
    for dateFile in collectedNews:
        df = pd.DataFrame.from_dict(collectedNews[dateFile], orient='index', columns=cols)
        df = removeDuplicates(df)
        #df.to_csv(DATA_PATH / dateFile, index=True) 
        if(not os.path.exists(DATA_PATH / 'csv')):
            os.mkdir(DATA_PATH / 'csv')
        print(["store file: ", dateFile])    
        df.to_csv(DATA_PATH / 'csv' / dateFile, index_label='index') 
    collectedNews = {}

# self.randomWordsDF = pd.DataFrame.from_dict(self.randomWords, orient='index', columns=self.randomBase.keys())  
# self.randomWordsDF.to_csv(DATA_PATH / self.category / "csv" / ("words_random_"+str(self.randomSize)+".csv"), index=True)


#https://web.archive.org/save/https://translate.google.com/translate?sl=de&tl=en&u=
#https://web.archive.org/save/https://translate.google.com/translate?sl=de&tl=en&u=https://www.nikos-weinwelten.de/beitrag/weinbau_reagiert_auf_den_klimawandel_abschied_vom_oechsle_hin_zur_nachhaltigkeit/


# https://docs.aiohttp.org/en/stable/client_reference.html
# 
async def saveArchive(saveUrl):
    async with aiohttp.ClientSession() as session:
      async with session.get(saveUrl, timeout=20) as response:
        print("x")   

async def getArchives(urlList):
    async with aiohttp.ClientSession() as session:
      async with session.get(saveUrl) as response:
        print("x")   

def findArchives(articles):
    foundArticles = []
    for article in articles:
        data = extractData(article, language, keyWord) 
        if (dataIsNotBlocked(data)):
            a=1

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def checkDuplicates(dict1, data2):
    quote2 = str(data2['domain']) + ' ' + str(data2['title']) + ' ' + str(data2['description'])
    md52 = hashlib.md5(quote2.encode('utf-8')).hexdigest() 
    for url1 in dict1:
        data1 = dict1[url1]
        quote1 = str(data1['domain']) + ' ' + str(data1['title']) + ' ' + str(data1['description'])   
        md51 = hashlib.md5(quote1.encode('utf-8')).hexdigest()
        if(md52 == md51):
            return True 
        day1 = '1970-01-01'
        if(len(str(data1['published']))>5):
          pubDate1 = parser.parse(data1['published'])
          day1 = pubDate1.strftime('%Y-%m-%d')
        groupTxt1 = str(data1['domain']) +  ' ' + day1
        group1 = hashlib.md5(groupTxt1.encode('utf-8')).hexdigest()  

        day2 = '1970-01-01'
        if(len(str(data2['published']))>5):
          pubDate2 = parser.parse(data2['published'])
          day2 = pubDate2.strftime('%Y-%m-%d')
        groupTxt2 = str(data2['domain']) +  ' ' + day2
        group2 = hashlib.md5(groupTxt2.encode('utf-8')).hexdigest()  
        if(group1 == group2):
          quote1 = str(data1['title']) + ' ' + str(data1['description'])
          quote2 = str(data2['title']) + ' ' + str(data2['description'])
          similarity = similar(quote1,quote2)
          if(similarity>0.8):
            return True
    return False


def removeDuplicates(df1):
    df1['md5'] = ''
    df1['group'] = ''
    df1['similarity'] = 0.0
    df1 = df1.sort_values(by=['published'], ascending=True)

    for index, column in df1.iterrows():
        quote = str(column['domain']) + ' ' + str(column['title']) + ' ' + str(column['description'])
        md5 = hashlib.md5(quote.encode('utf-8')).hexdigest()
        df1.loc[index,'md5'] = md5
        day = '1970-01-01'
        if(len(str(column['published']))>5):
          pubDate = parser.parse(column['published'])
          day = pubDate.strftime('%Y-%m-%d')
         
        groupTxt = str(column['domain']) +  ' ' + day
        group = hashlib.md5(groupTxt.encode('utf-8')).hexdigest()  
        df1.loc[index,'group'] = group

    df1 = df1[~df1.md5.duplicated(keep='first')]  

    for index1, column1 in df1.iterrows():
        quote1 = str(column1['title']) + ' ' + str(column1['description']) 
        df2 = df1[df1['group']==column1['group']]
        for index2, column2 in df2.iterrows():
            if(column1['md5']>column2['md5']):
                quote2 = str(column2['title']) + ' ' + str(column2['description'])
                similarity = similar(quote1,quote2)
                if(similarity > df1.loc[index1,'similarity']):
                    df1.loc[index1,'similarity'] = similarity

    df3 = df1[df1['similarity']<0.8]
    df3 = df3.drop(columns=['md5', 'group', 'similarity'])
    df3 = df3.sort_values(by=['published'], ascending=True)
    return df3

def archiveUrl(data):
    #timetravelDate = datetime.datetime.strptime(data['published'], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')
    #pubDate = datetime.datetime.fromisoformat(data['published'])
    #pubDate = parser.isoparse(data['published'])
    timetravelDate = '19700101'
    pubDate = None
    try:
        pubDate = parser.parse(data['published'])
    except:
        print('date parse error 1')
    if(not pubDate):
      try:
        pubDate = parser.isoparse(data['published'])
      except:
        print('date parse error 2')   
    if(pubDate):
        timetravelDate = pubDate.strftime('%Y%m%d')
    #timetravelUrl = 'http://timetravel.mementoweb.org/api/json/'+timetravelDate+'/'+data['url']
    timetravelUrl = 'http://archive.org/wayback/available?url='+data['url']+'&timestamp='+timetravelDate
    try:
        print(["try request", timetravelUrl])
        page = requests.get(timetravelUrl, timeout=60)
        if page.status_code == 200:
            content = page.content
            print(content)
            if(content):
                #print(content)
                jsonData = json.loads(content)
                if(jsonData and ('archived_snapshots' in jsonData)):
                  snapshots = jsonData['archived_snapshots']
                  if('closest' in snapshots):
                    closest = snapshots['closest']
                    if('200'==closest['status']):
                      data['archive'] = closest['url']
                      if('1970-01-01T00:00:00' == data['published']):
                        ts = closest['timestamp']
                        tsNew = ts[0:4]+'-'+ts[4:6]+'-'+ts[6:8]+'T'+ts[8:10]+':'+ts[10:12]+':'+ts[12:14]
                        print(['new ts',ts,tsNew])
                        data['published'] = tsNew
    except:
#    except Exception as e:    
#    except json.decoder.JSONDecodeError as e:    
#    except requests.exceptions.RequestException as e:  
        e = sys.exc_info()[0]
        print("not archived yet")
        saveUrl = 'https://web.archive.org/save/' + data['url'] # archive.org
        #saveUrl = 'https://archive.is/submit/'
        #saveUrl = 'https://archive.ph/submit/'

        ##  pip3 install aiohttp
        try:
           loop = asyncio.get_event_loop()
           loop.run_until_complete(saveArchive(saveUrl))
        except:
           e2 = sys.exc_info()[0]
           print("something more went wrong (timeout/redirect/...)")            

        #async with aiohttp.ClientSession() as session:
        #    async with session.get(saveUrl) as response:
        #        print(await response.status())        
        '''
        try:
            page = requests.get(saveUrl, timeout=240)  # archive.org
            #page = requests.post(saveUrl, data = {'url':data['url']}, timeout=240)
            if page.status_code == 200:
                print('archived!')
        except requests.exceptions.RequestException as e2:
            print("not archivable: " + data['url'])
        '''    
    return data 

def extractData(article, language, keyWord):
    title = article['title']
    description = article['description']
    url = article['url']
    domain = None
    if(url):   
     #later use list...
     url = url.replace('https://www.zeit.de/zustimmung?url=', '')
     url = url.replace('%3A', ':')
     url = url.replace('%2F', '/')                
     domain = urlparse(url).netloc
    else:
     print(['no url', article])
    image = None
    if('urlToImage' in article): 
        image = article['urlToImage']

    published = '1970-01-01T00:00:00'
    if('publishedAt' in article):    
        published = article['publishedAt']
    content = article['content']
    data = {'url':url, 'valid':0, 'domain':domain,'published':published, 'description':description, 'title':title, 
            'image':image, 'content':content, 'quote':'', 'language': language, 'keyword':keyWord}
    return data  

def checkArticlesForKeywords(articles, keywordsDF, seldomDF, language, keyWord, inclContent=False):
    keywordsLangDF = keywordsDF[keywordsDF['language']==language]
    foundArticles = []
    for article in articles:
      data = extractData(article, language, keyWord)
      searchQuote = str(data['title']) + " " + str(data['description']) 
      if (inclContent):
         searchQuote += " " + str(data['content'])
      foundKeywords = []
      found = False
      for index2, column2 in keywordsLangDF.iterrows(): 
         keyword = column2['keyword']
         allFound = True
         keywords = keyword.strip("'").split(" ")
         for keyw in keywords:
            allFound = allFound and (keyw in searchQuote)
         if(allFound):
             foundKeywords.append(keyword) 
             found = True
      # add seldom keywords twice if
      for index2, column2 in seldomDF.iterrows(): 
         keyword = column2['keyword']
         allFound = True
         keywords = keyword.strip("'").split(" ")
         for keyw in keywords:
            allFound = allFound and (keyw in searchQuote)
         if(allFound):
             foundKeywords.append(keyword) 
             found = True
      if(not data['url']):
        found = False
      if(found):
        foundKeywords.append(keyWord) 
        data['keyword'] = random.choice(foundKeywords)
        foundArticles.append(data)

    return foundArticles

def filterNewAndArchive(articles, language, keyWord):
    global collectedNews
    newArticles = []
    startTime = time.time()
    for data in articles:
        ##data = extractData(article, language, keyWord) 
        if (dataIsNotBlocked(data)):
            pubDate = parser.parse(data['published'])
            fileDate = 'news_'+pubDate.strftime('%Y_%m')+'.csv'
            if(not fileDate in collectedNews):
                if(os.path.isfile(DATA_PATH / 'csv' / fileDate)):
                    df = pd.read_csv(DATA_PATH / 'csv' / fileDate, delimiter=',',index_col='index')
                    collectedNews[fileDate] = df.to_dict('index')
                else:
                    collectedNews[fileDate] = {}
            if(not data['url'] in collectedNews[fileDate]):
              if(not checkDuplicates(collectedNews[fileDate], data)):
                data = archiveUrl(data)
                newArticles.append(data)
        if((time.time() - startTime) > 60*10):
            return newArticles        
    return newArticles

def getNewsFiles(state='harvest'):
    fileName = './csv/news_????_??.csv'
    if(state):
        fileName = './csv/news_'+state+'_????_??.csv'
    files = glob.glob(fileName)
    return files  

def getLatestFileAge():
    minAge = 1E6
    now = time.time()
    for fileName in getNewsFiles(state=None):
        print([os.path.getatime(fileName),os.path.getctime(fileName),os.path.getmtime(fileName)])
        modifyDate = os.path.getmtime(fileName)
        fileAge = now-modifyDate
        print(fileAge)
        if(fileAge<minAge):
            minAge = fileAge
    return minAge        


def inqRandomNews():
    apiKey = os.getenv('NEWSAPI_KEY')
    if(apiKey == '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7'): 
        print('Please set newsapi.org key in file: mysecrets.py');
        return None


    rndKey = keywordsDF.sample()
    randomNumber = random.random()
    if(keywordsDF3.ratioNew.max()>0.49):
      randomNumber = 0.05    
    #randomNumber = 0.95

    print(['randomNumber: ',randomNumber])
    if(not keywordsNewsDF2.empty):
      if(randomNumber>0.8):
        print("DF2 seldoms")
        rndKey = keywordsNewsDF2.sample()
      if(randomNumber>0.9):
        print("DF2 last")
        rndKey = keywordsNewsDF2.head(1).sample()
    if(not keywordsDF3.empty):
      if(randomNumber<0.4): 
        print("DF3 successors")
        rndKey = keywordsDF3.sample()
      if(randomNumber<0.2): 
        print("DF loosers")
        rndKey = keywordsDF.tail(1).sample()
      if(randomNumber<0.1):
        print("DF3 first")
        rndKey = keywordsDF3.head(1).sample()
    #if FoundAny: newLimit = minimum(currPage+1,limitPage)
    #if foundNothing:  newLimit = maximum(1,random.choice(range(currPage-1,limitPage-1)))

    ## cheat for now!     
    ## keywordEmptyDF = keywordsDF[keywordsDF['keyword']=="'Jewgeni Prigoschin'"]
    ## rndKey = keywordEmptyDF.sample()
    ## rm in final version
    ### rndKey = keywordsDF3.head(1).sample()

    #keyWord = random.choice(searchWords)
    #language = 'de'
    #language = 'en'   
    #language = 'fr' 
    crc = rndKey['crc'].iloc[0]
    keyWord = rndKey['keyword'].iloc[0]
    language = rndKey['language'].iloc[0]
    limitPages = rndKey['limitPages'].iloc[0]
    ratioNew = rndKey['ratioNew'].iloc[0]
    currPage = random.choice(range(1,limitPages+1))  
    newLimit = max(1,random.choice(range(currPage-1,limitPages)))
    currRatio = ratioNew
          
    print([keyWord, language])
    if(not 'xx'==language):
        sort = random.choice(['relevancy', 'popularity', 'publishedAt'])
        pageSize = 33
        print('keyword: '+keyWord+'; Page: '+str(currPage))
        # https://newsapi.org/docs/endpoints/everything
        url = ('https://newsapi.org/v2/everything?'+
            #'q="'+keyWord+'"&'
            'q='+keyWord+'&'
            'pageSize='+str(pageSize)+'&'
            'language='+language+'&'
            'page='+str(currPage)+'&'
            'sortBy='+sort+'&'
            'apiKey='+apiKey
            #'excludeDomains=www.zeit.de,www.reuters.com'
            )
            
            # sortBy=relevancy   : relevancy, popularity, publishedAt
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        
        foundNew = False
        if(response.text):
            jsonData = json.loads(response.text)
            if ('ok'==jsonData['status']):
             currRatio = 0
             if(jsonData['totalResults']>0):
              currRatio = jsonData['totalResults']/1E7
              if(len(jsonData['articles']) > 0):
                currRatio += len(jsonData['articles'])/1E3
                deltaLimit = 0
                #newLimit = limitPages
                if(len(jsonData['articles']) > 20):
                  deltaLimit += 1  
                  #newLimit = max(currPage+1,limitPages)                
                print('#found Articles: '+str(len(jsonData['articles'])))
                checkedArticles = checkArticlesForKeywords(jsonData['articles'], keywordsDF, keywordsNewsDF2,language, keyWord)
                print('#checked Articles: '+str(len(checkedArticles)))
                print("archive first")
                newArticles = filterNewAndArchive(checkedArticles, language, keyWord)
                if(len(newArticles)<1):
                    checkedArticles = checkArticlesForKeywords(jsonData['articles'], keywordsDF, keywordsNewsDF2,language, keyWord, True)
                    newArticles = filterNewAndArchive(checkedArticles, language, keyWord)  
                print('#new Articles: '+str(len(newArticles)))
                 
                if(len(newArticles) in [1,2]):     
                    print("sleep")   
                    time.sleep(60)
                print("add to collection")


                currRatio += len(newArticles)/len(jsonData['articles'])
                if(currRatio>0.5):
                    deltaLimit += 1
                    #newLimit = max(currPage+2,limitPages)
                newLimit =  min(3,max(currPage+deltaLimit,limitPages))
                print(['currRatio',currRatio,'currPage: ',currPage,' limitPages: ',limitPages,' deltaLimit: ',deltaLimit,' new Limit: ', newLimit])  

                for data in newArticles:
                    if (dataIsNotBlocked(data)):                    
                        #print(str(keyWord)+': '+str(title)+' '+str(url))
                        print(["addNewsToCollection: ",data])
                        if(addNewsToCollection(data)):
                            foundNew = True
                            print(["+++added"])  
                        else:
                            print(["---not added"])    
                #print(["collectedNews: ",collectedNews])            
                if(foundNew):         
                    storeCollection()
            else:
              print(response.text)
              if(jsonData['code'] == 'maximumResultsReached'):
                deltaLimit = -1
                newLimit =  max(1,currPage+deltaLimit)
              # {"status":"error","code":"maximumResultsReached","message":"You have requested too many results. Developer accounts are limited to a max of 100 results. You are trying to request results 100 to 150. Please upgrade to a paid plan if you need more results."}
    #print(rndKey.index)
    #keywordsDF.at[rndKey.index, 'limitPages'] = newLimit    
    keywordsDF.loc[keywordsDF['crc'] == crc, 'limitPages'] = newLimit 
    keywordsDF.loc[keywordsDF['crc'] == crc, 'ratioNew'] = currRatio*0.15+ratioNew*0.85
        
      

#b'{"status":"ok","totalResults":1504,
# "articles":[{"source":{"id":null,"name":"heise online"},
#              "author":"Stefan Krempl",
#              "title":"Wissenschaftler: Klimawandel tr\xc3\xa4gt zum Starkregen bei\xe2\x80\x8b",
#              "description":"Die Wolkenbr\xc3\xbcche mit katastrophalen Folgen geh\xc3\xb6ren so nicht mehr zur \xc3\xbcblichen Wetter-Varianz, meinen Wissenschaftler. Sie fordern einen Umbau der Infrastruktur.",
#              "url":"https://www.heise.de/news/Wissenschaftler-Klimawandel-traegt-zum-Starkregen-bei-6140856.html",
#              "urlToImage":"https://heise.cloudimg.io/bound/1200x1200/q85.png-lossy-85.webp-lossy-85.foil1/_www-heise-de_/imgs/18/3/1/3/9/7/8/0/Ueberschwemmung-c06f751f2932e14b.jpeg",
#              "publishedAt":"2021-07-16T15:06:00Z",
#              "content":"Nach den langen und heftigen Regenf\xc3\xa4llen Mitte der Woche treten immer mehr katastrophale Folgen zutage: Die Zahl der Toten w\xc3\xa4chst, allein in Rheinland-Pfalz und Nordrhein-Westfalen sind \xc3\xbcber 100 Mens\xe2\x80\xa6 [+4840 chars]"}

'''
#time.sleep(80000)
i=1
while True:
###while (i<50):    
  print(i)  
  inqRandomNews()
  i += 1
  #time.sleep(200) # unless drop none-french
  #time.sleep(20)
  time.sleep(1000)

age = getLatestFileAge()
print(age)
if(age>60*60*5*0):
    inqRandomNews()
'''
inqRandomNews()

'''
##TODO decomment
keywordsDF = addNewNames('https://raw.githubusercontent.com/pg-ufr-news/gensChuchoter/main/csv/sentiments_new_persons.csv', keywordsDF, 0.5, 'de', 9)
keywordsDF = addNewNames('https://raw.githubusercontent.com/pg-ufr-news/winterIsComing/main/csv/sentiments_new_persons.csv', keywordsDF, 0.6, 'de', 9)
keywordsDF = addNewNames('https://raw.githubusercontent.com/pg-ufr-news/personWhisperer/main/csv/sentiments_new_persons.csv', keywordsDF, 0.5, 'de', 9)
'''
keywordsDF = addNewLocations('https://raw.githubusercontent.com/pg-ufr-news/positionIsComming/main/csv/sentiments_new_locations.csv', keywordsDF, 0.5, 'de', 9)

#keywordsDF = keywordsDF.sort_values(by=['topic','keyword'])
keywordsDF['geonames'] = keywordsDF['geonames'].astype(int)
keywordsDF = keywordsDF[(keywordsDF.ratioNew > 0.05)]
keywordsDF = keywordsDF.sort_values(by=['ratioNew'], ascending=False)
keywordsDF.to_csv(DATA_PATH / 'keywords.csv', columns=keywordsFields,index=False, float_format='%.12f')  

'''
i=1
while True:
###while (i<50):    
  print(i)  
  inqRandomNews()
  i += 1
  #time.sleep(200) # unless drop none-french
  #time.sleep(20)
  keywordsDF = keywordsDF.sort_values(by=['ratioNew'], ascending=False)
  keywordsDF.to_csv(DATA_PATH / 'keywords.csv', columns=keywordsFields,index=False) 
  time.sleep(1000)
'''    
