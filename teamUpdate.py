# coding:utf-8
from cachecontrol import CacheControl
from tinydb import TinyDB, Query
import requests
import logging
import email.utils as eut
import datetime

# https://www.hkex.com.hk/eng/listing/listreq_pro/listcontact/documents/listingone.xls
# Last-Modified: Tue, 09 May 2017 00:49:45 GMT

def initialise():
    # set HTML cache
    sess = requests.session()
    global cached_sess
    cached_sess = CacheControl(sess)
    # set up DB
    global db
    db = TinyDB('files/db.json')


def TeamUpdate():
    # Enable logging
    logging.basicConfig(filename='files/logfile.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    # initialise
    messagelist = []

    # load xls
    try:
        r = cached_sess.get("http://www.hkex.com.hk/-/media/HKEX-Market/Listing/Rules-and-Guidance/Other-Resources/Listed-Issuers/Contact-Persons-in-HKEX-Listing-Department-for-Listed-Companies/listingone.xls?la=en")
        lastModified = HTTPparsedate(r.headers['Last-Modified'])
        lastModified += datetime.timedelta(hours=8)
        lastModString = datetime.datetime.strftime(lastModified, '%d-%b-%Y %H:%M:%S')

        with open('files/listingone.xls', 'wb') as f:
            f.write(r.content)

        # Start loop for each user
        subscribeList = db.search(Query().subscribe == True)
        # avoid double send
        sentList = []
        for user in subscribeList:
            if user['chatID'] not in sentList:
                messagelist.append([user['chatID'], "<i>Updated Team List (File Last Modified):" +
                                    "\n" + lastModString +
                                   "</i>"])
                sentList.append(user['chatID'])

    except (IndexError, ValueError):
        logger.warn("Error Updating Team List")

    return messagelist


def HTTPparsedate(text):
    return datetime.datetime(*eut.parsedate(text)[:6])
