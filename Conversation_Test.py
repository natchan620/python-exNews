from telegram import ReplyKeyboardMarkup
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY, TYPING_CHOICE, CONFIRMING = range(4)

reply_keyboard = [['Get User Info'],
                  ['Send Public Announcement'],
                  ['Done']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

confrim_keyboard = [['Confirm'], ['Cancel']]
confrim_markup = ReplyKeyboardMarkup(confrim_keyboard, one_time_keyboard=True)


def start(bot, update):
    update.message.reply_text(
        "Welcome to the admin panel, please choose your option:",
        reply_markup=markup)

    return CHOOSING


def regular_choice(bot, update, user_data):
    # text = update.message.text
    # user_data['choice'] = text
    update.message.reply_text(
        "Print out user stats...")

    done(bot, update, user_data)


def custom_choice(bot, update):
    update.message.reply_text("Okay, please send me the public announcment:")

    return TYPING_REPLY


def received_information(bot, update, user_data):
    text = update.message.text
    if 'message' in user_data:
        del user_data['message']
    user_data['message'] = text

    update.message.reply_text("Neat! Just so you know, this is what you told me:"
                              "\n\n{}"
                              "\n\nConfirm?"
                              .format(
                                  user_data['message']), reply_markup=confrim_markup, disable_web_page_preview=True)

    return CONFIRMING


def sendout_pa(bot, update, user_data):
    update.message.reply_text("Sending out message..."
                              "\n{}"
                              "\nDone."
                              .format(user_data['message']), disable_web_page_preview=True)

    done(bot, update, user_data)


def done(bot, update, user_data):
    if 'message' in user_data:
        del user_data['message']

    update.message.reply_text("Until next time!")

    user_data.clear()
    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("363930604:AAGKIIRspwOP7lAJFCLK8UYTD29ehjtaEsM")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [RegexHandler('^Get User Info$',
                                    regular_choice,
                                    pass_user_data=True),
                       RegexHandler('^Send Public Announcement$',
                                    custom_choice),
                       ],

            TYPING_CHOICE: [MessageHandler(Filters.text,
                                           regular_choice,
                                           pass_user_data=True),
                            ],

            TYPING_REPLY: [MessageHandler(Filters.text,
                                          received_information,
                                          pass_user_data=True),
                           ],

            CONFIRMING: [RegexHandler('^Confirm$',
                                      sendout_pa,
                                      pass_user_data=True),

                         ],
        },

        fallbacks=[RegexHandler('^(Done|Cancel)$', done, pass_user_data=True)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
