# coding:utf-8
from bs4 import BeautifulSoup
from cachecontrol import CacheControl
from tinydb import TinyDB, Query
import requests
import re
import pandas as pd
import logging
import datetime
import json


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
    TeamDF = pd.read_excel(open('files/listingone.xls', 'rb'), sheet_name=0)
    TeamDF.columns = ['code', 'EName', 'CName', 'team']


def BoardMeeting():
    # Enable logging
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    # initialise
    data = {
        'BM_Date': [],
        'stockname': [],
        'stockcode': [],
        'purpose': [],
        'period': []
    }
    messagelist = []
    urls = [
        'http://www.hkexnews.hk/reports/bmn/ebmn.htm',
        'http://www.hkgem.com/prices/diaries/diaries2/ebmngem.htm']

    # load html

    for url in urls:
        r = cached_sess.get(url)
        r.encoding = 'utf-8'

        html = r.text
        soup = BeautifulSoup(html, "lxml")

        currTime = re.search(r'Date : ([0-9/]*)', html).group(1)
        logger.info("Updated: " + currTime)

        table = soup.find("table", {"class": "textfont"})
        rows = table.find_all('tr')

        for row in rows[2:]:
            cols = row.find_all('td')
            # fix date range error
            datestring = cols[0].get_text()
            datestring = re.sub(r"[0-9][0-9]-", "", datestring)
            data['BM_Date'].append(datestring)

            data['stockname'].append(cols[2].get_text())
            code = re.sub("[^0-9]", "", cols[3].get_text())
            data['stockcode'].append(code)
            data['purpose'].append(cols[4].get_text())
            data['period'].append(cols[5].get_text())

    newsData = pd.DataFrame(data)
    newsData = newsData[['BM_Date', 'stockname',
                         'stockcode', 'purpose', 'period']]
    newsData['BM_Date'] = newsData['BM_Date'].apply(
        lambda x: datetime.datetime.strptime(x, '%d/%m/%Y'))
    newsData = newsData.sort_values(['BM_Date'], ascending=True)

    # Start loop for each user
    subscribeList = db.search(Query().subscribe == True)
    for user in subscribeList:
        df = TeamDF[(TeamDF['team'] == int(user['teamID']))]
        stocklist = []
        for index, row in df.iterrows():
            stocklist.append(str(row['code']))

        newsDataSorted = newsData[(newsData["stockcode"].isin(stocklist))]
        push_msg = ["Coming Board Meeting Dates for Team " +
                    str(user['teamID'])]
        for index, row in newsDataSorted.iterrows():
            push_msg.append("\n:spiral_calendar:<b>" + datetime.datetime.strftime(row['BM_Date'], '%d/%m/%Y') +
                            "\n</b>" + row['stockcode'] + " " + row['stockname'] +
                            "\n" + row['purpose'] +
                            "\n" + row['period'])

        if len(push_msg) < 2:
            push_msg.append("\n<i>(no results coming)</i>")

        messagelist.append([user['chatID'], ''.join(push_msg)])

    # except (IndexError, ValueError):
    #     subscribeList = db.search(Query().subscribe == True)
    #     for user in subscribeList:
    #         messagelist.append([user['chatID'], "Get meeting dates error, will try again later."])

    return messagelist
