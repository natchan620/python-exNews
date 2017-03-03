from bs4 import BeautifulSoup
import requests
import re

url = "http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM"
r = requests.get(url)
html = r.text
soup = BeautifulSoup(html)

rows = soup.find_all('tr', {'class': re.compile('row*')})

for row in rows:
        print(row.get_text())

data = {
    'time' : [],
    'stockcode' : [],
    'stockname' : [],
    'headline' : [],
    'document' : [],
    'docurl' : []
}

for row in rows:
    cols = row.find_all('td')
    data['time'].append( cols[0].get_text() )
    data['stockcode'].append( cols[1].get_text() )
    data['stockname'].append( cols[2].get_text() )
    data['rank2008'].append( cols[3].get_text() )
    data['rank2003'].append( cols[4].get_text() )

newsData = pd.DataFrame( data )
newsData.to_csv("exNews.csv")
