from bs4 import BeautifulSoup, Comment
import requests
import re
import pandas as pd

url = "http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM"
r = requests.get(url)
html = r.text
soup = BeautifulSoup(html, "lxml")


e = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
print(e)

comments = soup.find_all(text=lambda text:isinstance(text, Comment))
rows = soup.find_all('tr', {'class': re.compile('row*')})

data = {
	'docID' : [],
    'time' : [],
    'stockcode' : [],
    'stockname' : [],
    'headline' : [],
    'document' : [],
    'docurl' : []
}

for comment in comments:
  e = re.match(r'([0-9]*)', comment.string).group(1)
  if len(e) > 1:
  	data['docID'].append( e )

for row in rows:
    cols = row.find_all('td')
    data['time'].append( cols[0].get_text() )
    data['stockcode'].append( cols[1].get_text() )	
    data['stockname'].append( cols[2].get_text() )
    data['headline'].append( cols[3].contents[0].contents[0] )
    data['document'].append( cols[3].contents[1].contents[0] )
    data['docurl'].append( cols[3].contents[1].attrs["href"] )

newsData = pd.DataFrame( data )
newsData.to_csv("exNews.csv")
