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
# import BookCloseCal
import datetime
import configparser
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


def exScrape():
    # Enable logging
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    # initialise
    data = {
        'docID': [],
        'board': [],
        'time': [],
        'stockcode': [],
        'stockname': [],
        'headline': [],
        'document': [],
        'docurl': []
    }
    messagelist = []
    urls = [
        'https://www1.hkexnews.hk/ncms/json/eds/lcisehk1relsde_1.json',
        'https://www1.hkexnews.hk/ncms/json/eds/lcisehk1relsdc_1.json',
        'https://www1.hkexnews.hk/ncms/json/eds/lcigem1relsde_1.json',
        'https://www1.hkexnews.hk/ncms/json/eds/lcigem1relsdc_1.json']

    # load json
    try:
        for url in urls:
            r = cached_sess.get(url)
            r.encoding = 'utf-8'

            newsjson = json.loads(r.text)

            maxNumOfFile = newsjson["maxNumOfFile"]

            currTime = newsjson["genDate"]
            logger.info("Updated: " + currTime)

            for news in newsjson["newsInfoLst"]:
                # remove testing announcment ID
                if news["t1Code"] != "51500" and news["newsId"] < 9000000:
                    for stock in news["stock"]:
                        data['docID'].append(news["newsId"])
                        # classify MB and GEM
                        if int(stock["sc"]) >= 8000 and int(stock["sc"]) <= 8999:
                            data['board'].append("GEM")
                        else:
                            data['board'].append("MB")
                        data['time'].append(news["relTime"])
                        data['stockcode'].append(stock["sc"])
                        data['stockname'].append(stock["sn"])
                        data['headline'].append(news["lTxt"])
                        data['document'].append(news["title"])
                        data['docurl'].append(
                            "https://www1.hkexnews.hk" + news["webPath"])

            if maxNumOfFile > 1:
                for i in range(2, maxNumOfFile):
                    r = cached_sess.get(url.replace(
                        "_1.json", "_" + str(i) + ".json"))
                    r.encoding = 'utf-8'

                    newsjson = json.loads(r.text)

                    for news in newsjson["newsInfoLst"]:
                        # remove testing announcment ID
                        if news["t1Code"] != "51500" and news["newsId"] < 9000000:
                            for stock in news["stock"]:
                                data['docID'].append(news["newsId"])
                                # classify MB and GEM
                                if int(stock["sc"]) >= 8000 and int(stock["sc"]) <= 8999:
                                    data['board'].append("GEM")
                                else:
                                    data['board'].append("MB")
                                data['time'].append(news["relTime"])
                                data['stockcode'].append(stock["sc"])
                                data['stockname'].append(stock["sn"])
                                data['headline'].append(news["lTxt"])
                                data['document'].append(news["title"])
                                data['docurl'].append(
                                    "https://www1.hkexnews.hk" + news["webPath"])

        newsData = pd.DataFrame(data)
        newsData = newsData[['docID', 'board', 'time', 'stockcode',
                             'stockname', 'headline', 'document', 'docurl']]

        # sortdata
        newsData = newsData.sort_values(['docID'], ascending=True)

        # Start loop for each user
        subscribeList = db.search(Query().subscribe == True)
        for user in subscribeList:
            df = TeamDF[(TeamDF['team'] == int(user['teamID']))]
            stocklist = []
            for index, row in df.iterrows():
                stocklist.append(str(row['code']).zfill(5))

            newsDataSorted = newsData[((newsData["docID"] > user['MB_lastDocID']) & (
                newsData["stockcode"].isin(stocklist)) & (newsData['board'] == "MB")) | ((newsData["docID"] > user['GEM_lastDocID']) & (
                    newsData["stockcode"].isin(stocklist)) & (newsData['board'] == "GEM"))]
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
            db.update({'MB_lastDocID': int(
                newsData[(newsData["board"] == "MB")]['docID'].iloc[-1])}, Query().chatID == user['chatID'])
            db.update({'GEM_lastDocID': int(
                newsData[(newsData["board"] == "GEM")]['docID'].iloc[-1])}, Query().chatID == user['chatID'])

    except (IndexError, ValueError):
        # subscribeList = db.search(Query().subscribe == True)
        # for user in subscribeList:
        Config = configparser.ConfigParser()
        Config.read("config.ini")
        admin_id = Config.get('Telegram', 'Admin')
        messagelist.append(
            [admin_id, "Error, will try again later."])

    return messagelist


if __name__ == '__main__':
    initialise()
    messagelist = exScrape()
    print(messagelist)
