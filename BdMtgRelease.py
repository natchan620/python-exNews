# coding:utf-8
from bs4 import BeautifulSoup, Comment
from cachecontrol import CacheControl
from tinydb import TinyDB, Query
from datetime import datetime
import requests
import re
import pandas as pd
import logging
import pytz


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


def BoardMeetingCheck():
    messagelist = []
    newsData = getBoardMeeting()
    ExNewsData = exScrapeResults()

    # sort date today / before today
    mytz = pytz.timezone('Asia/Hong_Kong')
    today = str(datetime.now(mytz).date())
    mask = (newsData['BM_Date'] <= today)
    # mask = (newsData['BM_Date'] <= '2018-02-21') #debug
    newsData = newsData.loc[mask]

    # find results and modified results
    mask = (ExNewsData['headline'].str.contains('Final Results')) | (ExNewsData['headline'].str.contains(
        'Interim Results')) | (ExNewsData['headline'].str.contains('Quarterly Results'))
    ExNewsDataResults = ExNewsData.loc[mask]
    mask = (ExNewsData['headline'].str.contains(
        'Qualified and/or Modified Audit Report'))
    ExNewsDataQualify = ExNewsData.loc[mask]

    # Start loop for each user
    subscribeList = db.search(Query().subscribe == True)
    for user in subscribeList:
        df = TeamDF[(TeamDF['team'] == int(user['teamID']))]
        # df = TeamDF[(TeamDF['team'] == 10)] #debug
        stocklist = []
        for index, row in df.iterrows():
            stocklist.append(str(row['code']).zfill(5))

        newsDataSorted = newsData[(newsData["stockcode"].isin(stocklist))]
        push_msg = ["Results due for Team " + str(user['teamID'])]
        for index, row in newsDataSorted.iterrows():
            push_msg.append("\n<b>" + datetime.strftime(
                row['BM_Date'], '%d/%m/%Y') + " " + row['stockcode'] + " " + row['stockname'] + "</b>")
            # search released
            SearchMatch = ExNewsDataResults[ExNewsDataResults['stockcode']
                                            == row['stockcode']]
            if SearchMatch.size > 0:
                push_msg.append(
                    "\n:bar_chart:<a href=\"" + SearchMatch['docurl'].iloc[0] + "\">" + SearchMatch['document'].iloc[0] + "</a>")
            else:
                push_msg.append("\n:question_mark:<i>(not yet published)</i>")
            # search qualified
            SearchMatch = ExNewsDataQualify[ExNewsDataQualify['stockcode']
                                            == row['stockcode']]
            if SearchMatch.size > 0:
                push_msg.append(
                    "\n:warning:<b>(Qualified and/or Modified Audit Report)</b>")

        if len(push_msg) < 2:
            push_msg.append(
                "\n:Japanese_free_of_charge_button:<i>(no results due)</i>")

        messagelist.append([user['chatID'], ''.join(push_msg)])

    # except (IndexError, ValueError):
    #     subscribeList = db.search(Query().subscribe == True)
    #     for user in subscribeList:
    #         messagelist.append([user['chatID'], "Get meeting dates error, will try again later."])

    return messagelist


def exScrapeResults():
    # Enable logging
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
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
    urls = [
        'http://www3.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_SEVEN.HTM',
        'http://www3.hkexnews.hk/listedco/listconews/gemindex/GEM_LISTEDCO_DATETIME_SEVEN.HTM']
    # urls = [
    # 'http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_SEVEN.HTM',
    # 'http://www.hkexnews.hk/listedco/listconews/gemindex/GEM_LISTEDCO_DATETIME_SEVEN.HTM'] #debug
    # load html

    for url in urls:
        r = cached_sess.get(url)
        r.encoding = 'utf-8'

        html = r.text
        soup = BeautifulSoup(html, "lxml")

        currTime = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
        logger.info("Updated: " + currTime)

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
            data['docurl'].append(
                "http://www3.hkexnews.hk" + cols[3].contents[1].attrs["href"])

    newsData = pd.DataFrame(data)
    newsData = newsData[['docID', 'time', 'stockcode',
                         'stockname', 'headline', 'document', 'docurl']]

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

    return newsData


def getBoardMeeting():
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
            data['stockcode'].append(code.zfill(5))
            data['purpose'].append(cols[4].get_text())
            data['period'].append(cols[5].get_text())

    newsData = pd.DataFrame(data)
    newsData = newsData[['BM_Date', 'stockname',
                         'stockcode', 'purpose', 'period']]
    # debug
    # newsData = newsData.append({'BM_Date': "01/01/2018",
    #             'stockname': "DYNASTY WINES", 'stockcode': "00828",
    #             'purpose': "FIN RES", 'period': "Y.E.31/12/17"}, ignore_index=True)
    newsData['BM_Date'] = newsData['BM_Date'].apply(
        lambda x: datetime.strptime(x, '%d/%m/%Y'))
    newsData = newsData.sort_values(['BM_Date'], ascending=True)

    return newsData


def main():
    initialise()
    msgList = BoardMeetingCheck()
    for message in msgList:
        print(message)


if __name__ == '__main__':
    main()
