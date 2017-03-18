#coding:utf-8
from telegram.ext import Updater, CommandHandler, Job
import exScrape
import logging
import configparser

#telegram
def start(bot, update, args):
    try:
        teamID = int(args[0])
        if teamID < 1 | teamID > 27:
            update.message.reply_text('Please check your teamID')
            return
        msgList = exScrape.exScrape(teamID, update.message.chat_id, False)
        for message in msgList:
            bot.sendMessage(
                chat_id=update.message.chat_id,
                text=message,
                parse_mode='HTML')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /start <teamID>')


def alarm(bot, job):
    msgList = exScrape.exScrape(job.context[1], job.context[0], True)
    for message in msgList:
        bot.sendMessage(
            chat_id=job.context[0],
            text=message,
            parse_mode='HTML')


def set(bot, update, args, job_queue, chat_data):
    """Adds a job to the queue"""
    chat_id = update.message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        teamid = int(args[1])
        if due < 0:
            update.message.reply_text('Sorry we can not go back to future!')
            return
        if teamid < 1 | teamid > 27:
            update.message.reply_text('Please check your teamID')
            return

        # Add job to queue
        job = Job(alarm, due, repeat=True, context=[chat_id, teamid])
        chat_data['job'] = job
        job_queue.put(job)

        update.message.reply_text('Timer successfully set!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds> <teamID>')


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
    # read config
    Config = configparser.ConfigParser()
    Config.read("config.ini")

    # Enable logging
    logging.basicConfig(filename='logfile.log',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    updater = Updater(Config.get('Telegram', 'token'))

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start, pass_args=True))
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
