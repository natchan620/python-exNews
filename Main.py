#coding:utf-8
from telegram.ext import Updater, CommandHandler, Job
import exScrape
import logging
import configparser


#telegram
def start(bot, update, args):
    Config = configparser.ConfigParser()
    Config.read("config.ini")
    due = int(Config.get('Settings', 'Due'))

    try:
        teamID = int(args[0])
        if teamID < 1 | teamID > 27:
            update.message.reply_text('Please check your teamID')
            return
        exScrape.addUser(update.message.chat_id, teamID)

        update.message.reply_text("exNews subscription for Team: " + str(teamID) + " set. I will refresh every " + str(due) + " seconds. Send /stop to stop.")

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /start <teamID>')


def alarm(bot, job):
    msgList = exScrape.exScrape()
    for message in msgList:
        bot.sendMessage(
            chat_id=message[0],
            text=message[1],
            parse_mode='HTML',
            disable_web_page_preview=True)


def stop(bot, update):
    """Removes the job if the user changed their mind"""
    result = exScrape.removeUser(update.message.chat_id)
    if result:
        update.message.reply_text('Successfully unsubscribed.')
    else:
        update.message.reply_text('No current subscription found.')


def error(bot, update, error):
    logging.basicConfig(filename='files/logfile.log',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # read config
    Config = configparser.ConfigParser()
    Config.read("config.ini")

    # Enable logging
    logging.basicConfig(filename='files/logfile.log',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    updater = Updater(Config.get('Telegram', 'token'))
    j = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start, pass_args=True))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("stop", stop))

    # log all errors
    dp.add_error_handler(error)

    # initialise scraper cache
    exScrape.initialise()

    # Set Refresh Job
    job_set = Job(alarm, int(Config.get('Settings', 'Due')))
    j.put(job_set, next_t=0.0)

    # Start the Bot
    updater.start_polling()

    logger.info("Bot started!")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
