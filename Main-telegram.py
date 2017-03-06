from bs4 import BeautifulSoup, Comment
from telegram.ext import Updater, CommandHandler, Job
import logging
import requests
import re
import pandas as pd

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)



#telegram
def start(bot, update):
    update.message.reply_text('Hi! Use /set <seconds> to set a timer')

def alarm(bot, job):

	#initialise
	data = {
		'docID' : [],
	    'time' : [],
	    'stockcode' : [],
	    'stockname' : [],
	    'headline' : [],
	    'document' : [],
	    'docurl' : []
	}
	lastDocID = 0

	#urls = ['http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM','http://www.hkexnews.hk/listedco/listconews/mainindex/sehk_listedco_datetime_today_c.htm','http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today.htm','http://www.hkexnews.hk/listedco/listconews/gemindex/gem_listedco_datetime_today_c.htm']
	urls = ['http://www.hkexnews.hk/listedco/listconews/mainindex/SEHK_LISTEDCO_DATETIME_TODAY.HTM']

	with open('stocklist.txt') as f:
	    rawstocklist = f.read().splitlines()
	stocklist = []
	for stock in rawstocklist:
		stocklist.append(stock.zfill(5))
	#load html
	for url in urls:
		r = requests.get(url)
		html = r.text
		soup = BeautifulSoup(html, "lxml")


		currTime = re.search(r'Current Date Time: ([0-9]*)', html).group(1)
		print("Last update: "+currTime)

		comments = soup.find_all(text=lambda text:isinstance(text, Comment))
		rows = soup.find_all('tr', {'class': re.compile('row*')})

		for comment in comments:
		  e = re.match(r'([0-9]*)', comment.string).group(1)
		  if len(e) > 1:
		  	data['docID'].append( int(e) )

		for row in rows:
		    cols = row.find_all('td')
		    data['time'].append( cols[0].get_text() )
		    data['stockcode'].append( cols[1].get_text() )	
		    data['stockname'].append( cols[2].get_text() )
		    data['headline'].append( cols[3].contents[0].contents[0] )
		    data['document'].append( cols[3].contents[1].contents[0] )
		    data['docurl'].append( "http://www.hkexnews.hk"+cols[3].contents[1].attrs["href"] )


	newsData = pd.DataFrame( data )
	newsData = newsData[['docID', 'time', 'stockcode', 'stockname', 'headline', 'document', 'docurl']]

	#sortdata
	newsData = newsData.sort_values(['docID'], ascending=True)
	newsDataSorted = newsData[(newsData["docID"] > lastDocID) & (newsData["stockcode"].isin(stocklist))]
	for index, row in newsDataSorted.iterrows():
		bot.sendMessage(job.context, text=row['time']+row['stockcode']+row['stockname']+row['headline']+row['document']+row['docurl'])
	#newsDataSorted.to_csv("exNews_"+currTime+".csv")

	#update next minID to list
	newsData = newsData.sort_values(['docID'], ascending=False)
	lastDocID= newsData['docID'].iloc[0]
	bot.sendMessage(job.context, text=lastDocID)

def set(bot, update, args, job_queue, chat_data):
    """Adds a job to the queue"""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return

        # Add job to queue
        job = Job(alarm, due, repeat=False, context=chat_id)
        chat_data['job'] = job
        job_queue.put(job)

        update.message.reply_text('Timer successfully set!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(bot, update, chat_data):
    """Removes the job if the user changed their mind"""

    if 'job' not in chat_data:
        update.message.reply_text('You have no active timer')
        return

    job = chat_data['job']
    job.schedule_removal()
    del chat_data['job']

    update.message.reply_text('Timer successfully unset!')


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    updater = Updater("TOKEN HERE")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("set", set,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
