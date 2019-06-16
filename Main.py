# coding:utf-8
from telegram.ext import Updater, CommandHandler, Job
from tinydb import TinyDB, Query
from emoji import emojize
import exScrape
import BdMtg
import BdMtgRelease
import teamUpdate
import logging
import configparser
import datetime

# telegram


def AboutMe(bot, update):
    update.message.reply_text("ExNews Push build 20190616" +
                              "\n" +
                              "\n" + "Fuction: " +
                              "\n" + "- Update ex news website every 90 seconds" +
                              "\n" + "- Check results release 11:10 PM every day" +
                              "\n" + "- Update board meeting dates (MB & GEM) 11:20 PM every day" +
                              "\n" + "- Update team Excel around 11:30 PM every day" +
                              "\n" +
                              "\n" + "Change log:" +
                              "\n" + "- 20170516: Auto update team Excel" +
                              "\n" + "- 20170516: Added board meeting dates" +
                              "\n" + "- 20170518: Support multiple team subscription" +
                              "\n" + "- 20170522: Added statistics" +
                              "\n" + "- 20170814: Fix meeting date error" +
                              "\n" + "- 20171002: Fix phrase Excel error" +
                              "\n" + "- 20171231: Fix user list error & message error" +
                              "\n" + "- 20180103: Fix message cannot sent to all users" +
                              "\n" + "- 20180215: Add function to check results released" +
                              "\n" + "- 20180518: Fix Telegram for Python update" +
                              "\n" + "- 20180720: Fix user list" +
                              "\n" + "- 20181016: Added board meeting date calculation" +
                              "\n" + "- 20181017: Added emoji" +
                              "\n" + "- 20181022: Fix date calculation for Sunday & holiday announcements" +
                              "\n" + "- 20181028: Fix url link for new website" +
                              "\n" + "- 20181030: Improved regular expression for board meeting date identification" +
                              "\n" + "- 20190108: Added book closure date check" +
                              "\n" + "- 20190321: Disabled closure date check" +
                              "\n" + "- 20190616: Fixed to read after news website revamp" +
                              "\n" +
                              "\n" + "Usage: " +
                              "\n" + "- Start subscription: /start <teamID> (eg: /start 10)" +
                              "\n" + "- Add one more team subscription: /start <teamID> (eg: /start 20)" +
                              "\n" + "- Stop all team subscription: /stop" +
                              "\n" +
                              "\n" + "Enjoy!")


def start(bot, update, args):
    Config = configparser.ConfigParser()
    Config.read("config.ini")
    due = int(Config.get('Settings', 'Due'))

    try:
        teamID = int(args[0])
        if teamID < 1 | teamID > 99:
            update.message.reply_text('Please check your teamID')
            return
        exScrape.addUser(update.message.chat_id, teamID)

        update.message.reply_text("exNews subscription for Team: " + str(
            teamID) + " set. I will refresh every " + str(due) + " seconds. Send /stop to stop.")

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /start <teamID> (eg: /start 30)')


def alarm(bot, job):
    msgList = exScrape.exScrape()
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    for message in msgList:
        try:
            bot.sendMessage(
                chat_id=message[0],
                text=emojize(message[1], use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)
            if(is_ascii(message[1])):
                logger.info(
                    "Pushed ID#" + str(message[0]) + ": " + message[1].replace('\n', ''))

        except BaseException as e:
            logger.error("Pushed ID#" + str(message[0]) + ": " + str(e))


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


def meeting(bot, job):
    msgList = BdMtg.BoardMeeting()
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    for message in msgList:
        try:
            bot.sendMessage(
                chat_id=message[0],
                text=emojize(message[1], use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)
            if(is_ascii(message[1])):
                logger.info(
                    "Meeting ID#" + str(message[0]) + ": " + message[1].replace('\n', ''))

        except BaseException as e:
            logger.error("Meeting ID#" + str(message[0]) + ": " + str(e))


def checkresultsJob(bot, job):
    msgList = BdMtgRelease.BoardMeetingCheck()
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    for message in msgList:
        try:
            bot.sendMessage(
                chat_id=message[0],
                text=emojize(message[1], use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)
            if(is_ascii(message[1])):
                logger.info("Results check ID#" +
                            str(message[0]) + ": " + message[1].replace('\n', ''))

        except BaseException as e:
            logger.error("Results check ID#" + str(message[0]) + ": " + str(e))


def teamUpdateJob(bot, job):
    msgList = teamUpdate.TeamUpdate()
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    for message in msgList:
        try:
            bot.sendMessage(
                chat_id=message[0],
                text=emojize(message[1], use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)
            if(is_ascii(message[1])):
                logger.info("Team Excel Update ID#" +
                            str(message[0]) + ": " + message[1].replace('\n', ''))

        except BaseException as e:
            logger.error("Team Excel Update ID#" +
                         str(message[0]) + ": " + str(e))


def stop(bot, update):
    """Removes the job if the user changed their mind"""
    result = exScrape.removeUser(update.message.chat_id)
    if result:
        update.message.reply_text('Successfully unsubscribed ALL teams')
    else:
        update.message.reply_text('No current subscription found.')


def stat_admin(bot, update):
    # read config
    Config = configparser.ConfigParser()
    Config.read("config.ini")
    admin_id = Config.get('Telegram', 'Admin')
    if(str(update.message.chat_id) == admin_id):
        db = TinyDB('files/db.json')
        subscribeList = db.all()
        for user in subscribeList:

            TelegramChat = bot.getChat(user['chatID'])

            push_msg = "<b>" + str(user['chatID']) + \
                "\n</b>Team " + str(user['teamID']) + ": " + str(user['subscribe']) + \
                "\nName: " + str(TelegramChat.first_name) + " " + str(TelegramChat.last_name) + \
                "\nUsername: " + str(TelegramChat.username) + \
                "\nTitle: " + str(TelegramChat.title)

            bot.sendMessage(
                chat_id=update.message.chat_id,
                text=push_msg,
                parse_mode='HTML',
                disable_web_page_preview=True)
    else:
        update.message.reply_text("Sorry, you're not authorised.")


def error(bot, update, error):
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # read config
    Config = configparser.ConfigParser()
    Config.read("config.ini")

    # Enable logging
    logging.basicConfig(filename='files/logfile.log',
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    updater = Updater(Config.get('Telegram', 'token'))
    j = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start, pass_args=True))
    dp.add_handler(CommandHandler("add", start, pass_args=True))
    dp.add_handler(CommandHandler("help", AboutMe))
    dp.add_handler(CommandHandler("about", AboutMe))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("stat", stat_admin))

    # log all errors
    dp.add_error_handler(error)

    # initialise scraper cache
    exScrape.initialise()
    BdMtg.initialise()
    BdMtgRelease.initialise()
    teamUpdate.initialise()

    # 1-Set Refresh Job
    # job_set = Job(alarm, int(Config.get('Settings', 'Due')))
    # j.put(job_set, next_t=0.0)
    j.run_repeating(alarm, int(Config.get('Settings', 'Due')), first=0.0)

    # 2-Set Refresh Meeting
    meeting_time = datetime.datetime.strptime(
        Config.get('Settings', 'MeetingTime'), '%H:%M').time()
    # next_datetime = datetime.datetime.combine(datetime.date.today(), meeting_time)

    # # if time passed, then do tomorrow
    # if datetime.datetime.now().time() > meeting_time:
    #     next_datetime += datetime.timedelta(days=1)

    # next_t_mjob = (next_datetime - datetime.datetime.now()).total_seconds()
    # meeting_set = Job(meeting, int(Config.get('Settings', 'Meeting')))
    # logger.info("Seconds to get Board Meeting List:" + str(next_t_mjob))
    # j.put(meeting_set, next_t=next_t_mjob)
    j.run_daily(meeting, meeting_time)
    # j.run_once(meeting, 0)  # debug use

    # 3-Set Refresh Team
    teamupdate_time = datetime.datetime.strptime(
        Config.get('Settings', 'Update_TeamTime'), '%H:%M').time()
    # nextTeam_datetime = datetime.datetime.combine(datetime.date.today(), teamupdate_time)

    # # if time passed, then do tomorrow
    # if datetime.datetime.now().time() > teamupdate_time:
    #     nextTeam_datetime += datetime.timedelta(days=1)

    # next_updateteam_mjob = (nextTeam_datetime - datetime.datetime.now()).total_seconds()
    # teamUpdate_set = Job(teamUpdateJob, int(Config.get('Settings', 'Update_Team')))
    # logger.info("Seconds to get Excel List:" + str(next_updateteam_mjob))
    # j.put(teamUpdate_set, next_t=next_updateteam_mjob)
    j.run_daily(teamUpdateJob, teamupdate_time)
    # j.run_once(teamUpdateJob, 0)  # debug use

    # 4-Set Check results
    checkresults_time = datetime.datetime.strptime(
        Config.get('Settings', 'CheckResultsTime'), '%H:%M').time()
    # nextcheckresults_datetime = datetime.datetime.combine(datetime.date.today(), checkresults_time)

    # # if time passed, then do tomorrow
    # if datetime.datetime.now().time() > nextcheckresults_datetime.time():
    #     nextcheckresults_datetime += datetime.timedelta(days=1)

    # next_checkresults_mjob = (nextcheckresults_datetime - datetime.datetime.now()).total_seconds()
    # checkresults_set = Job(checkresultsJob, int(Config.get('Settings', 'CheckResults')))
    # logger.info("Seconds to check results:" + str(next_checkresults_mjob))
    # j.put(checkresults_set, next_t=next_checkresults_mjob)
    j.run_daily(checkresultsJob, checkresults_time)
    # j.run_once(checkresultsJob, 0)  # debug use

    # Start the Bot
    updater.start_polling()

    logger.info("!Bot started!")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
