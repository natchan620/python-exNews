# coding:utf-8
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler, CallbackQueryHandler, Job)
from tinydb import TinyDB, Query
from emoji import emojize
import pandas as pd
import logging
import configparser
import datetime
import exScrape
import BdMtg
import BdMtgRelease
import teamUpdate

# change log
change_log = """ExNews Push build 20190616
Fuction: 
- Update ex news website every 90 seconds
- Check results release 11:10 PM every day
- Update board meeting dates (MB & GEM) 11:20 PM every day
- Update team Excel around 11:30 PM every day

Change log:
- 20170516: Auto update team Excel
- 20170516: Added board meeting dates
- 20170518: Support multiple team subscription
- 20170522: Added statistics
- 20170814: Fix meeting date error
- 20171002: Fix phrase Excel error
- 20171231: Fix user list error & message error
- 20180103: Fix message cannot sent to all users
- 20180215: Add function to check results released
- 20180518: Fix Telegram for Python update
- 20180720: Fix user list
- 20181016: Added board meeting date calculation
- 20181017: Added emoji
- 20181022: Fix date calculation for Sunday & holiday announcements
- 20181028: Fix url link for new website
- 20181030: Improved regular expression for board meeting date identification
- 20190108: Added book closure date check
- 20190321: Disabled closure date check
- 20190616: Fixed to read after news website revamp
"""

# Enable logging
logging.basicConfig(filename = 'files/logfile.log',
                    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level = logging.INFO)
logger=logging.getLogger(__name__)

# telegram
MENU, ADMIN_MENU, REPEAT_MSG, CONFIRM=range(4)

menu_keyboard=[['Cancel Subscriptions', 'View Subscriptions',
    'Statistics'], ['About this bot', 'Subscribe to team']]
markup=ReplyKeyboardMarkup(
    menu_keyboard, one_time_keyboard = False, resize_keyboard = True)

admin_keyboard=[['Get User Info', 'Send Public Announcement'], ['Done']]
admin_markup=ReplyKeyboardMarkup(
    admin_keyboard, one_time_keyboard = True, resize_keyboard = True)

confrim_keyboard=[['Confirm', 'Cancel']]
confrim_markup=ReplyKeyboardMarkup(
    confrim_keyboard, one_time_keyboard = True, resize_keyboard = True)

# functions
def start(bot, update):
    update.message.reply_text(
            "Welcome to ExNews Push, please choose your option below:", reply_markup=markup)
    return MENU

def add_subs(bot, update):
    # read Excel and generate buttons
    TeamDF=pd.read_excel(open('files/listingone.xls', 'rb'), sheet_name = 0)
    TeamDF.columns=['code', 'EName', 'CName', 'team']
    team_array=TeamDF.team.unique()
    team_array.sort()
    button_array=[]
    button_row=[]
    for teamno in team_array:
        button_row.append(InlineKeyboardButton(
            str(teamno), callback_data="add_" + str(teamno)))
        if len(button_row) >= 5:  # 5 button per row
            button_array.append(button_row)
            button_row=[]

    reply_markup=InlineKeyboardMarkup(button_array)

    update.message.reply_text(
        'Please choose the subscription you want to add:', reply_markup = reply_markup)

def cancel_subs(bot, update):
    db=TinyDB('files/db.json')
    if len(db.search((Query().chatID == update.message.chat_id) & (Query().subscribe == True))) > 0:
        subscribedList=db.search(
            (Query().chatID == update.message.chat_id) & (Query().subscribe == True))
        button_array=[]
        for subsciption in subscribedList:
            button_array.append(InlineKeyboardButton(
                "Team " + str(subsciption['teamID']), callback_data="cancel_" + str(subsciption['teamID'])))

        keyboard= [[InlineKeyboardButton("Cancel all", callback_data = 'cancel_all')],
                button_array]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose the subscription you want to cancel:', reply_markup=reply_markup)

    else:
        update.message.reply_text("No active subscription found.")


def subs_callback(bot, update):
    db = TinyDB('files/db.json')
    query = update.callback_query
    query_data = query.data.split('_')
    if query_data[0] == "cancel" and query_data[1] == "all":
        bot.edit_message_text(text="Selected: Cancel all team subscriptions",
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
        if len(db.search(Query().chatID == update.message.chat_id)) > 0:
            db.update({'subscribe': False}, Query().chatID == update.message.chat_id)
            bot.sendMessage(
                chat_id=query.message.chat_id,
                text=emojize("Subscription for all teams cancelled successfully.", use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)

    elif query_data[0] == "cancel":
        bot.edit_message_text(text="Selected: Cancel Team {} subscription".format(query_data[1]),
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
        if len(db.search(Query().chatID == update.message.chat_id) & (Query().teamID == query_data[1])) > 0:
            db.update({'subscribe': False}, (Query().chatID == update.message.chat_id) & (Query().teamID == int(query[1])))           
            bot.sendMessage(
                chat_id=query.message.chat_id,
                text=emojize("Subscription for Team: " + str(query_data[1]) + " cancelled.", use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)

    elif query_data[0] == "add":
        bot.edit_message_text(text="Selected: Add Team {} subscription".format(query_data[1]),
                          chat_id=query.message.chat_id,
                          message_id=query.message.message_id)
        addUser(query.message.chat_id, int(query_data[1]))
        bot.sendMessage(
                chat_id=query.message.chat_id,
                text=emojize("Subscription for Team: " + str(query_data[1]) + " set successfully.", use_aliases=True),
                parse_mode='HTML',
                disable_web_page_preview=True)


def view_subs(bot, update):
    db = TinyDB('files/db.json')
    if len(db.search((Query().chatID == update.message.chat_id) & (Query().subscribe == True))) > 0:
        subscribedList = db.search((Query().chatID == update.message.chat_id) & (Query().subscribe == True))
        message = "Your active subscription(s):"
        for subsciption in subscribedList:
            message = message + "\n" + "<b>Team {}</b>".format(subsciption['teamID'])
        update.message.reply_text(message)
    else:
        update.message.reply_text("No active subscription found.")
    return ConversationHandler.END

def user_stats(bot, update):
    db = TinyDB('files/db.json')
    # number of active team subscriptions
    sub_no = len(db.search(Query().subscribe == True))

    # number of active individual users/groups
    subscribedList = db.search(Query().subscribe == True)
    userlist = []
    for subsciption in subscribedList:
        userlist.append(subsciption['chatID'])
    uniqueuserlist = set(userlist)

    update.message.reply_text("Thank you for your support!"
                            "\n" + "Number of active team subscriptions: " + str(sub_no) +
                            "\n" + "Number of active unique users/groups: " + str(len(uniqueuserlist)))
    return ConversationHandler.END

def about(bot, update):
    update.message.reply_text(change_log)
    return ConversationHandler.END

# jobs
def checknews(bot, job):
    msgList = exScrape.exScrape()
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

def meeting(bot, job):
    msgList = BdMtg.BoardMeeting()
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

# Admin functions below
def admin(bot, update):
    Config = configparser.ConfigParser()
    Config.read("config.ini")
    admin_id = Config.get('Telegram', 'Admin')
    if(str(update.message.chat_id) == admin_id):
        update.message.reply_text(
            "Welcome to the admin panel, please choose your option:",
        reply_markup=admin_markup)
        return ADMIN_MENU
    else:
        update.message.reply_text("Sorry, you're not authorised.")
        return ConversationHandler.END

def admin_getinfo(bot, update):
    db = TinyDB('files/db.json')
    subscribeList = db.all()
    for user in subscribeList:
        TelegramChat = bot.getChat(user['chatID'])
        push_msg = "<b>" + str(user['chatID']) + \
                "\n</b>Team " + str(user['teamID']) + ": " + str(user['subscribe']) + \
                "\nName: " + str(TelegramChat.first_name) + " " + str(TelegramChat.last_name) + \
                "\nUsername: " + str(TelegramChat.username) + \
                "\nTitle: " + str(TelegramChat.title)
        update.message.reply_text(push_msg)
    return ConversationHandler.END


def admin_pa(bot, update):
    update.message.reply_text("Okay, please type in the public announcment:")

    return CONFIRM


def admin_confirm_pa(bot, update, user_data):
    text = update.message.text
    if 'message' in user_data:
        del user_data['message']
    user_data['message'] = text

    update.message.reply_text("OK, this is the public announcment:"
                              "\n\n{}"
                              "\n\nConfirm?"
                              .format(
                                  user_data['message']), reply_markup=confrim_markup, disable_web_page_preview=True)

    return CONFIRM


def admin_sendout_pa(bot, update, user_data):
    update.message.reply_text("Sending out public announcment...")
    # Start loop for each user
    db = TinyDB('files/db.json')
    subscribeList = db.search(Query().subscribe == True)
    for user in subscribeList:
        bot.sendMessage(
                chat_id=user['chatID'],
                text=user_data['message'],
                disable_web_page_preview=False)

    update.message.reply_text("Public announcment sent.")
    return ConversationHandler.END


def cancel(bot, update, user_data):
    if 'message' in user_data:
        del user_data['message']

    update.message.reply_text("Operation cancelled.")

    user_data.clear()
    return ConversationHandler.END


# helpers
def addUser(chatIDno, teamIDno):
    db = TinyDB('files/db.json')
    if len(db.search((Query().chatID == chatIDno) & (Query().teamID == teamIDno))) > 0:
        db.update({'subscribe': True}, ((Query().chatID == chatIDno)
                                        & (Query().teamID == teamIDno)))
    else:
        lastDocID = 2809759
        if len(db) > 0:
            lastDocID = db.all()[0]['lastDocID']
        db.insert({'chatID': chatIDno,
                   'teamID': teamIDno,
                   'subscribe': True,
                   'lastDocID': lastDocID})


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def is_ascii(s):
    return all(ord(c) < 128 for c in s)


# main
def main():
    # read config
    Config = configparser.ConfigParser()
    Config.read("config.ini")

    updater = Updater(Config.get('Telegram', 'token'))
    j = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    # Add conversation handler and callback
    dp.add_handler(CallbackQueryHandler(subs_callback))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            MENU: [RegexHandler('^Subscribe to team$',
                                    add_subs),
                   RegexHandler('^About this bot$',
                                    about),
                   RegexHandler('^Statistics$',
                                    user_stats),
                   RegexHandler('^View Subscriptions$',
                                    view_subs),
                   RegexHandler('^Cancel Subscriptions$',
                                    cancel_subs),
                       ],
        },

        fallbacks=[RegexHandler('^(Done|Cancel)$', cancel, pass_user_data=True)]
    )
    dp.add_handler(conv_handler)
    # Add conversation handler with the states
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin)],

        states={
            ADMIN_MENU: [RegexHandler('^Get User Info$',
                                    admin_getinfo),
                        RegexHandler('^Send Public Announcement$',
                                    admin_pa),
                       ],

            REPEAT_MSG: [MessageHandler(Filters.text,
                        admin_confirm_pa,
                        pass_user_data=True),
                        ],

            CONFIRM: [RegexHandler('^Confirm$',
                                      admin_sendout_pa,
                                      pass_user_data=True),
                         ],
        },

        fallbacks=[RegexHandler('^(Done|Cancel)$', cancel, pass_user_data=True)]
    )
    dp.add_handler(admin_conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # 0-initialise scraper cache
    exScrape.initialise()
    BdMtg.initialise()
    BdMtgRelease.initialise()
    teamUpdate.initialise()

    # 1-Set Refresh Job
    j.run_repeating(checknews, int(Config.get('Settings', 'Due')), first=0.0)

    # 2-Set Refresh Meeting
    meeting_time = datetime.datetime.strptime(
        Config.get('Settings', 'MeetingTime'), '%H:%M').time()
    j.run_daily(meeting, meeting_time)
    # j.run_once(meeting, 0)  # debug use

    # 3-Set Refresh Team
    teamupdate_time = datetime.datetime.strptime(
        Config.get('Settings', 'Update_TeamTime'), '%H:%M').time()
    j.run_daily(teamUpdateJob, teamupdate_time)
    # j.run_once(teamUpdateJob, 0)  # debug use

    # 4-Set Check results
    checkresults_time = datetime.datetime.strptime(
        Config.get('Settings', 'CheckResultsTime'), '%H:%M').time()
    j.run_daily(checkresultsJob, checkresults_time)
    # j.run_once(checkresultsJob, 0)  # debug use

    # Start the Bot
    updater.start_polling()
    logger.info("Bot started!")

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
