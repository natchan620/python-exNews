# coding:utf-8
from bs4 import BeautifulSoup, Comment
import requests
import re
import pandas as pd
from pathlib import Path


def exScrape(teamID, chatID, slientMode):
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

    # load last DocID
    lastDocID = 0
    my_file = Path("session/" + str(chatID))
    if my_file.is_file():
        with open("session/" + str(chatID)) as f:
            lastDocID = int(f.read())

    messagelist = []
    if not slientMode:
        messagelist.append("Updating from: " + str(lastDocID))

    urls = [
    'http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM',
    'http://www.hkexnews.hk/listedco/listconews/mainindex/sehk_listedco_datetime_today_c.htm',
    'http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today.htm',
    'http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today_c.htm']

    # load stocklist
    df = pd.read_excel(open('listingone.xls', 'rb'), sheetname=0)
    df.columns = ['code', 'EName', 'CName', 'team', 'x', 'y', 'z']
    df = df[(df['team'] == int(teamID))]
    stocklist = []
    for index, row in df.iterrows():
        stocklist.append(str(row['code']).zfill(5))

    # load html
    try:
        for url in urls:
            r = requests.get(url)
            r.encoding = 'utf-8'

            html = r.text
            soup = BeautifulSoup(html, "lxml")

            currTime = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
            print("Last update: " + currTime)

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
       # newsDataDuplicate = newsData[newsData["stockcode"] .str.len() > 5]
       # for index, row in newsDataDuplicate.iterrows():
       #     stockcodes = re.findall('.....', row['stockcode'])
       #     for stockno in stockcodes:
       #         print(stockno)
       #         newsDataToadd = pd.DataFrame([row['docID'], row['time'], stockno, row['stockname'], row['headline'], row['document']], columns = ['docID', 'time', 'stockcode', 'stockname', 'headline', 'document', 'docurl'])
       #         newsData = newsData.concat(newsData, newsDataToadd)

        # sortdata and match to team
        newsData = newsData.sort_values(['docID'], ascending=True)
        newsDataSorted = newsData[(newsData["docID"] > lastDocID) & (newsData["stockcode"].isin(stocklist))]
        for index, row in newsDataSorted.iterrows():
            messagelist.append(str(row['docID'])+" "+row['time']+"\n"+row['stockcode']+" "+row['stockname']+"\n"+row['headline']+"\n"+row['document']+"\n"+row['docurl'])

        # update next minID to list & save session
        lastDocID = newsData['docID'].iloc[-1]
        lastDocTime = newsData['time'].iloc[-1]
        if not slientMode:
            messagelist.append("Updated to: " + str(lastDocID) + " " + str(lastDocTime))
        wr = open("session/" + str(chatID), "w+")
        wr.write(str(lastDocID))
        # newsData.to_csv("exNews_" + str(lastDocID) + ".csv")
    except:
        messagelist.append("Error, please try again later")

    return messagelist
