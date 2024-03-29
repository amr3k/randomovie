#!usr/bin/env python3
# -*- coding: utf-8; -*-
# TODO: split this file into two, with basic flask enabled
"""
MIT License
Copyright (c) 2019 Amr Khamis
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import TelegramError, ChatAction, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from randomovie.database import *
from data.sqlite_build import default_genres


def random_reply_markup(trailer, url):
    button_list = [
        [
            InlineKeyboardButton("👍 Get one more", callback_data="random"),
        ],
        [
            InlineKeyboardButton("📺 Official Trailer", url=trailer),
            InlineKeyboardButton("🎬 Watch or Download", url=url),
        ]
    ]
    return InlineKeyboardMarkup(button_list)


def create_markup(genre_index: int):
    button_list = [
        [
            InlineKeyboardButton(f"👍 Yes I like {default_genres[genre_index]}", callback_data="append"),
            InlineKeyboardButton(f"👎 No", callback_data='skip'),
        ],
        [
            InlineKeyboardButton("☑️ Add All genres", callback_data='add_all_genres'),
            InlineKeyboardButton("👌 I'm done", callback_data='finish_genres'),
        ]
    ]
    return InlineKeyboardMarkup(button_list)


def command_start(bot, update):
    bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
    user_create(update.effective_user.id)
    bot_description = 'This bot was created to provide you a random movie based on your preference including ' \
                      'movie genres, minimum rating and oldest release year.\n' \
                      'You can start creating your own filter using /create \n' \
                      'After you complete setting your filter, you can use /random to get a random movie based ' \
                      'on your preferences\n.' \
                      'Whenever you need help just send /help\n' \
                      'Have fun 😊'
    bot.send_message(chat_id=update.effective_message.chat_id, parse_mode=ParseMode.MARKDOWN,
                     text=f"Hello *{update.effective_user.full_name}*\n{bot_description}")


def command_create(bot, update):  # Create a new filter starting with oldest year, then minimum rating
    # and finally genres
    user_id = update.effective_user.id
    user_create(user_id)
    user_reset(user_id)
    create_year(bot, update, 'new')


def create_year(bot, update, step: str):
    """
    Prompt the user for setting the oldest release year that he would get movies newer than
    :param bot:
    :param update:
    :param step:
    :return:
    """
    if step == 'new':  # Send a simple message
        bot.send_message(chat_id=update.effective_message.chat_id,
                         text="So what is the minimum release year that all movies I suggest should be newer than?\n "
                              "Type a year in range of 1912 to 2017.",
                         )
        user_set_last_step(update.effective_user.id, 'create_year')
    elif step == 'set':  # Verify the received number and take the appropriate response
        user_update(update.effective_user.id, 'year', update.effective_message.text)


def create_rating(bot, update, step: str):
    """
        Prompt the user setting the oldest release year that he/she would get movies newer than
        :param bot:
        :param update:
        :param step:
        :return:
        """
    if step == 'new':  # Send a simple message
        bot.send_message(chat_id=update.effective_message.chat_id,
                         text="OK, Send me a number between 0-9 which represents the minimum movie rating you want!")
        user_set_last_step(update.effective_user.id, 'create_rating')
    elif step == 'set':  # Verify the received number and take the appropriate response
        user_update(update.effective_user.id, 'rating', update.effective_message.text)


def create_genres(bot, update, step, msg_id=0, qid=0):
    """
    Handles genres creation
    :param bot:
    :param update:
    :param step:
    :param msg_id:
    :param qid: Will be used to reply to incoming queries
    :return: None
    """
    user_id = update.effective_user.id
    chat_id = update.effective_message.chat_id
    user_create(user_id)
    if step == 'new':
        user_set_last_step(user_id, 'create_genres_0')
        bot.send_message(chat_id=chat_id, text="Now It's time to choose your favourite genres")
        bot.send_message(chat_id=chat_id, text=f"Do you like {default_genres[0]} movies ?",
                         reply_markup=create_markup(0))
    else:
        last_genre = user_get_last_step(user_id)
        next_index = int(last_genre[last_genre.rfind('_') + 1:]) + 1
        if next_index == len(default_genres):  # This is the last genre.
            user_set_last_step(user_id, 'ready')
            bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                  text="Ok, You are set, now you can start using /random")
        else:
            if step == 'skip':  # Just get the next genre
                try:
                    bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                          text=f"Do you like {default_genres[next_index]} movies ?",
                                          reply_markup=create_markup(next_index))
                except TelegramError as e:
                    print(e)
                finally:
                    user_set_last_step(user_id, f'create_genres_{next_index}')
            elif step == 'done':  # Finish
                if user_has_genres(user_id):
                    user_set_last_step(user_id, 'ready')
                    try:
                        bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                              text="Ok, You are set, now you can start using /random")
                    except TelegramError as e:
                        print(e)
            elif step == 'append':  # Append the current genre to user's database and Get the next genre and prompt user
                user_set_last_step(user_id, f'create_genres_{next_index}')
                user_update(user_id, 'genre', next_index)
                bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                      text=f"Do you like {default_genres[next_index]} movies ?",
                                      reply_markup=create_markup(next_index))
            elif step == 'all':  # Update user's genre cell with all default genres
                user_set_last_step(user_id, 'ready')
                user_update(user_id, 'all_genres', None)
                bot.edit_message_text(chat_id=chat_id, message_id=msg_id,
                                      text="Ok, You are set, now you can start using /random")


def command_reset(bot, update):
    user_reset(update.effective_user.id)
    bot.send_message(chat_id=update.effective_message.chat_id, text="Ok .. Your filters have been successfully reset!")


def command_random(bot, update, msg_id=None):
    chat_id = update.effective_message.chat_id
    bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    user_id = update.effective_user.id
    user_create(user_id)
    movie = fetch(user_id)
    if type(movie) is list:
        trailer = f"https://www.youtube.com/results?search_query={movie[1]} trailer"
        url = f"https://www.google.com/search?q=Download full movie {movie[1]}"
        msg = f"*Title:* {movie[1]}\n" \
              f"*Release year:* {movie[3]}\n" \
              f"*Genres:* {movie[2]}\n" \
              f"*Rating:* {movie[4]}\n" \
              f"*Votes:* {movie[5]}\n" \
              f"*IMDB:* {movie[0]}"
        if msg_id:
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg,
                                      reply_markup=random_reply_markup(trailer, url), parse_mode=ParseMode.MARKDOWN)
            except TelegramError as e:
                print(e)
        else:
            try:
                bot.send_message(chat_id=chat_id, text=msg,
                                 reply_markup=random_reply_markup(trailer, url), parse_mode=ParseMode.MARKDOWN)
            except TelegramError as e:
                print(e)
    else:  # Error message
        if movie == "No result":  # User has set strict rules
            msg = "Oops 😞 I found nothing matches your filter !!\nTry /create a new filter with " \
                  "more tolerant parameters like more genres, less rating and older release year"
            try:
                bot.send_message(chat_id=chat_id, text=msg)
            except TelegramError as e:
                print(e)
        else:  # User hasn't yet created a filter
            msg = "⛔ Looks like you haven't created a filter yet, so I can't suggest a movie unless you " \
                  "/create a new filter"
            try:
                bot.send_message(chat_id=chat_id, text=msg)
            except TelegramError as e:
                print(e)


def command_help(bot, update):
    bot.send_message(chat_id=update.effective_message.chat_id,
                     text="If you liked the bot please consider supporting my work using Patreon: "
                          "https://www.patreon.com/akkk33 \nIf your found any bug, or have issues "
                          "using this bot, please accept my apologies and kindly submit an issue "
                          "in Github's repository.\nhttps://github.com/akkk33/randomovie/issues/new")


def non_command_msg(bot, update):
    user_id = update.effective_user.id
    msg = update.effective_message.text
    chat_id = update.effective_message.chat_id
    user_create(user_id)
    if msg.isdigit():  # Check the previous message that was sent by bot
        if user_get_last_step(user_id) == 'create_year':  # Check if user is responding to create_year() function
            if 1911 < int(msg) < 2018:  # Minimum release year
                bot.send_message(chat_id=chat_id, text=f"Great, I'll only suggest movies that are newer than {msg}")
                create_year(bot, update, 'set')
                # Initialise the next /create step which is: minimum rating
                create_rating(bot, update, 'new')
            else:  # Wrong year
                bot.send_message(chat_id=chat_id,
                                 text="Sorry, You must send a year between 1912-2017 because all movies are in that "
                                      "range!")
        elif user_get_last_step(user_id) == 'create_rating':
            if int(msg) == 10:  # Maximum rating
                bot.send_message(chat_id=chat_id,
                                 text="Hey, there's no movie that has 10/10 rating\nSend another number below 10")
            elif 0 <= int(msg) < 10:  # Minimum rating
                bot.send_message(chat_id=chat_id,
                                 text=f"Ok, I'll only suggest movies that have a rating more than {msg}/10")
                create_rating(bot, update, 'set')
                # Initialise the next /create step which is: genres
                create_genres(bot, update, 'new')
            else:
                bot.send_message(chat_id=chat_id, text="Sorry, You must specify a minimum rating number between 0-9")
    else:
        if user_get_last_step(user_id) == 'create_year' or user_get_last_step(user_id) == 'create_rating':
            bot.send_message(chat_id=chat_id, text="I can only accept digit number 0-9")
        else:
            unknown_command(bot, update)


def unknown_command(bot, update):
    bot.send_message(chat_id=update.effective_message.chat_id,
                     text="Sorry, I couldn't understand that!!\nTry /help")


def query_handler(bot, update):
    btn = update.callback_query.data
    msg_id = update.callback_query.message.message_id
    query_id = update.callback_query.id
    if btn == 'random':  # Fetch a new movie
        command_random(bot, update, msg_id)
    else:
        if btn == 'append':  # User is creating a new filter
            create_genres(bot, update, 'append', msg_id, query_id)
        elif btn == 'skip':  # get the next genre
            create_genres(bot, update, 'skip', msg_id, query_id)
        elif btn == 'add_all_genres':  # Add all genres
            create_genres(bot, update, 'all', msg_id, query_id)
        elif btn == 'finish_genres':  # User has selected all genres he needs
            create_genres(bot, update, 'done', msg_id, query_id)


if __name__ == "__main__":

    # Secrets
    TOKEN = str(environ.get('telegram_token'))
    PORT = int(environ.get('PORT', '8443'))

    # Telegram connection
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Received messages Handlers
    dp.add_handler(CommandHandler('start', command_start))
    dp.add_handler(CommandHandler('create', command_create))
    dp.add_handler(CommandHandler('reset', command_reset))
    dp.add_handler(CommandHandler('random', command_random))
    dp.add_handler(CommandHandler('help', command_help))
    dp.add_handler(MessageHandler(Filters.text, non_command_msg))
    dp.add_handler(CallbackQueryHandler(query_handler))

    # Webhook Initialisation on heroku
    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=TOKEN)
    updater.bot.setWebhook(f"https://randomovie.herokuapp.com/{TOKEN}")

    # Simple home server
    # updater.start_polling()
    # updater.idle()
