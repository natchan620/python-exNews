# coding:utf-8
from bs4 import BeautifulSoup, Comment
from cachecontrol import CacheControl
from tinydb import TinyDB, Query
import requests
import re
import pandas as pd
import logging
from pathlib import Path


def initialise():
    # set HTML cache
    sess = requests.session()
    global cached_sess
    cached_sess = CacheControl(sess)
    # set up DB
    global db
    db = TinyDB('files/db.json')
    # load stocklist
    global TeamDF
    TeamDF = pd.read_excel(open('files/listingone.xls', 'rb'), sheetname=0)
    TeamDF.columns = ['code', 'EName', 'CName', 'team', 'x', 'y', 'z']


def addUser(chatIDno, teamIDno):
    if len(db.search(Query().chatID == chatIDno)) > 0:
        db.update({'subscribe': True, 'teamID': teamIDno}, Query().chatID == chatIDno)
    else:
        db.insert({'chatID': chatIDno,
                   'teamID': teamIDno,
                   'subscribe': True,
                   'lastDocID': 2762023})


def removeUser(chatIDno):
    if len(db.search(Query().chatID == chatIDno)) > 0:
        db.update({'subscribe': False}, Query().chatID == chatIDno)
        return True
    else:
        return False


def exScrape():
    # Enable logging
    logging.basicConfig(filename='files/logfile.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    # initialise    
    data = {
        'docID': [],
        'time': [],
        'stockcode': [],
        'stockname': [],
        'headline': [],
        'document': [],
        'docurl': []
    }
    messagelist = []
    urls = [
    'http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM',
    'http://www.hkexnews.hk/listedco/listconews/mainindex/sehk_listedco_datetime_today_c.htm',
    'http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today.htm',
    'http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today_c.htm']

    # load html
    try:
        for url in urls:
            r = cached_sess.get(url)
            r.encoding = 'utf-8'

            html = r.text
            soup = BeautifulSoup(html, "lxml")

            currTime = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
            logger.info("Update: " + currTime)

            comments = soup.find_all(text=lambda text: isinstance(text, Comment))
            rows = soup.find_all('tr', {'class': re.compile('row*')})

            for comment in comments:
                e = re.match(r'([0-9]*)', comment.string).group(1)
                if len(e) > 1:
                    data['docID'].append(int(e))

            for row in rows:
                cols = row.find_all('td')
                data['time'].append(cols[0].get_text())
                data['stockcode'].append(cols[1].get_text())
                data['stockname'].append(cols[2].get_text())
                data['headline'].append(cols[3].contents[0].contents[0])
                data['document'].append(cols[3].contents[1].contents[0])
                data['docurl'].append("http://www.hkexnews.hk" + cols[3].contents[1].attrs["href"])

        newsData = pd.DataFrame(data)
        newsData = newsData[['docID', 'time', 'stockcode', 'stockname', 'headline', 'document', 'docurl']]

        # duplicate row if more than one code
        newsDataDuplicate = newsData[newsData['stockcode'].str.len() > 5]
        for index, row in newsDataDuplicate.iterrows():
            stockcodes = re.findall('.....', row['stockcode'])
            for stockno in stockcodes:
                newsData = newsData.append({'docID': row['docID'],
                    'time': row['time'], 'stockcode': stockno,
                    'stockname': row['stockname'],
                    'headline': row['headline'], 'document': row['document'],
                    'docurl': row['docurl']}, ignore_index=True)

        # sortdata
        newsData = newsData.sort_values(['docID'], ascending=True)

        # Start loop for each user
        subscribeList = db.search(Query().subscribe == True)
        for user in subscribeList:
            df = TeamDF[(TeamDF['team'] == int(user['teamID']))]
            stocklist = []
            for index, row in df.iterrows():
                stocklist.append(str(row['code']).zfill(5))

            newsDataSorted = newsData[(newsData["docID"] > user['lastDocID']) & (newsData["stockcode"].isin(stocklist))]
            for index, row in newsDataSorted.iterrows():
                messagelist.append([user['chatID'], str(row['docID']) + " " + row['time'] +
                    "\n<b>" + row['stockcode'] + " " + row['stockname'] +
                    "</b>\n" + row['headline'] + "\n<a href=\"" + row['docurl'] + "\">" + row['document'] + "</a>"])

            # update next minID to list & save session
            db.update({'lastDocID': int(newsData['docID'].iloc[-1])}, Query().chatID == user['chatID'])

    except (IndexError, ValueError):
        subscribeList = db.search(Query().subscribe == True)
        for user in subscribeList:
            messagelist.append([user['chatID'], "Error, will try again later."])

    return messagelist
