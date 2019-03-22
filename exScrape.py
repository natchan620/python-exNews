# coding:utf-8
from bs4 import BeautifulSoup, Comment
from cachecontrol import CacheControl
from tinydb import TinyDB, Query
import requests
import re
import pandas as pd
import logging
from pathlib import Path
import BdMtgCal
import BookCloseCal
import datetime


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


def addUser(chatIDno, teamIDno):
    if len(db.search((Query().chatID == chatIDno) & (Query().teamID == teamIDno))) > 0:
        db.update({'subscribe': True}, ((Query().chatID == chatIDno)
                                        & (Query().teamID == teamIDno)))
    else:
        lastDocID = 2809759
        if len(db) > 0:
            lastDocID = db.all()[0]['lastDocID']
        db.insert({'chatID': chatIDno,
                   'teamID': teamIDno,
                   'subscribe': True,
                   'lastDocID': lastDocID})


def removeUser(chatIDno):
    if len(db.search(Query().chatID == chatIDno)) > 0:
        db.update({'subscribe': False}, Query().chatID == chatIDno)
        return True
    else:
        return False


def exScrape():
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
    messagelist = []
    urls = [
        'http://www3.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM',
        'http://www3.hkexnews.hk/listedco/listconews/mainindex/sehk_listedco_datetime_today_c.htm',
        'http://www3.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today.htm',
        'http://www3.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today_c.htm']

    # load html
    try:
        for url in urls:
            r = cached_sess.get(url)
            r.encoding = 'utf-8'

            html = r.text
            soup = BeautifulSoup(html, "lxml")

            currTime = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
            logger.info("Updated: " + currTime)

            comments = soup.find_all(
                text=lambda text: isinstance(text, Comment))
            rows = soup.find_all('tr', {'class': re.compile('row*')})

            for comment in comments:
                e = re.match(r'([0-9]*)', comment.string).group(1)
                if len(e) > 1:
                    data['docID'].append(int(e))

            for row in rows:
                cols = row.find_all('td')
                data['time'].append(cols[0].get_text()[
                                    :10] + " " + cols[0].get_text()[-5:])
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
                newsData = newsData.append({'docID': row['docID'], 'time': row['time'], 'stockcode': stockno,
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

            newsDataSorted = newsData[(newsData["docID"] > user['lastDocID']) & (
                newsData["stockcode"].isin(stocklist))]
            for index, row in newsDataSorted.iterrows():
                messagelist.append([user['chatID'], ":newspaper: Team " + str(user['teamID']) + " " + row['time'] + " #" + str(row['docID']) + "\n<b>" + row['stockcode'] + " " + row['stockname'] +
                                    "</b>\n" + row['headline'] + "\n<a href=\"" + row['docurl'] + "\">" + row['document'] + "</a>"])

                # add notice period calculation for board meeting notice
                # if "Closure of Books or Change of Book Closure Period" in str(row['headline']):
                #     try:
                #         # download as "files/TempAnnt.pdf"
                #         BookCloseCal.downloadPDF(row['docurl'])
                #         bc_start_date, bc_end_date, num_bdays = BookCloseCal.calc_noticeperiod(
                #             row['time'], "files/TempAnnt.pdf")
                #         if "Rights Issue" in str(row['headline']) and num_bdays >= 6:
                #             messagelist.append([user['chatID'], "Book Close Date Calcuation (Rights Issue) " + "\n:tear-off_calendar: From: " +
                #                                 datetime.datetime.strftime(bc_start_date, '%d-%b-%Y') + "\n:spiral_calendar_pad: To: " +
                #                                 datetime.datetime.strftime(bc_end_date, '%d-%b-%Y') + "\n:heavy_large_circle: (" + str(num_bdays) + " business days)"])
                #         elif num_bdays >= 10:
                #             messagelist.append([user['chatID'], "Book Close Calcuation (testing) " + "\n:tear-off_calendar: From: " +
                #                                 datetime.datetime.strftime(bc_start_date, '%d-%b-%Y') + "\n:spiral_calendar_pad: To: " +
                #                                 datetime.datetime.strftime(bc_end_date, '%d-%b-%Y') + "\n:heavy_large_circle: (" + str(num_bdays) + " business days)"])
                #         else:
                #             messagelist.append([user['chatID'], "Book Close Calcuation (testing) " + "\n:tear-off_calendar: From: " +
                #                                 datetime.datetime.strftime(bc_start_date, '%d-%b-%Y') + "\n:spiral_calendar_pad: To: " +
                #                                 datetime.datetime.strftime(bc_end_date, '%d-%b-%Y') + "\n:cross_mark:<b> (" + str(num_bdays) + " business days)</b>    "])

                #     except:
                #         pass

                # add notice period calculation for bookclosure period
                if "Date of Board Meeting" in str(row['headline']):
                    try:
                        # download as "files/TempAnnt.pdf"
                        BdMtgCal.downloadPDF(row['docurl'])
                        bm_date, num_bdays = BdMtgCal.calc_noticeperiod(
                            row['time'], "files/TempAnnt.pdf")
                        if num_bdays >= 7:
                            messagelist.append([user['chatID'], "Board Meeting Date Calcuation (testing) " + "\n:tear-off_calendar: Board meeting date: " +
                                                datetime.datetime.strftime(bm_date, '%d-%b-%Y') + "\n:heavy_large_circle: (" + str(num_bdays) + " clear business days)"])
                        else:
                            messagelist.append([user['chatID'], "Board Meeting Date Calcuation (testing) " + "\n:tear-off_calendar: Board meeting date: " +
                                                datetime.datetime.strftime(bm_date, '%d-%b-%Y') + "\n:cross_mark:<b> (" + str(num_bdays) + " clear business days)</b>    "])

                    except:
                        pass
            # update next minID to list & save session
            db.update({'lastDocID': int(
                newsData['docID'].iloc[-1])}, Query().chatID == user['chatID'])

    except (IndexError, ValueError):
        subscribeList = db.search(Query().subscribe == True)
        for user in subscribeList:
            messagelist.append(
                [user['chatID'], "Error, will try again later."])

    return messagelist


if __name__ == '__main__':
    messagelist = exScrape()
    print(messagelist)
