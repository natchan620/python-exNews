from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO
import pandas as pd
import datetime
import requests
import numpy as np
import re
from dateutil.parser import *


def convert_pdf_to_txt(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()
    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        interpreter.process_page(page)
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return str


def calc_noticeperiod(time, filename):
    pdf_text = convert_pdf_to_txt(filename).replace(
        '\n', ' ').replace('\r', '').replace(',', '').replace('.', '')
    # print(pdf_text)
    matches = re.findall(
        r'(\d{1,2}[\/ ]*(\d{2}|January|Jan|February|Feb|March|Mar|April|Apr|May|May|June|Jun|July|Jul|August|Aug|September|Sep|October|Oct|November|Nov|December|Dec)[\/ ]*\d{2,4})', pdf_text)

    # matches = datefinder.find_dates(pdf_text, source=True, strict=True)
    date_list = []
    for match in matches:
        print(match)
        date_list.append(parse(match[0]))
    bm_date = max(date_list)
    # now_date = datetime.datetime.now(
    #    pytz.timezone('Asia/Hong_Kong')).replace(tzinfo=None)
    now_date = datetime.datetime.strptime(time, '%d/%m/%Y %H:%M').date()
    # Count number of working days
    weekmask = 'Mon Tue Wed Thu Fri'
    # holidays = [datetime.datetime(2011, 1, 5), datetime.datetime(2011, 3, 14)]  # to read holidays
    dates = np.genfromtxt('files/HKHoliday.txt',
                          delimiter=";", usecols=(0), dtype=None)
    holidays = [datetime.datetime.strptime(
        date.decode('UTF-8'), '%Y-%m-%d').date() for date in dates]
    num_bdays = len(pd.bdate_range(now_date, bm_date, freq='C',
                                   weekmask=weekmask, holidays=holidays)) - 2
    if now_date in holidays or now_date.weekday() > 5:
        num_bdays = num_bdays + 1
    return bm_date, num_bdays


def downloadPDF(URL):
    r = requests.get(URL, stream=True)

    with open('files/TempAnnt.pdf', 'wb') as fd:
        for chunk in r.iter_content(2000):
            fd.write(chunk)


if __name__ == '__main__':
    downloadPDF(
        "https://www1.hkexnews.hk/listedco/listconews/sehk/2019/0822/ltn20190822381.pdf")
    bm_date, num_bdays = calc_noticeperiod(
        "22/08/2019 18:46", "files/TempAnnt.pdf")
    print(str(bm_date) + " " + str(num_bdays))
