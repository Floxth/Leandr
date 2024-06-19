from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import sqlite3
from contextlib import closing
import re

def initialize_database():
    conn = sqlite3.connect('apartment_database.db')
    with conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS apartments (user_id INTEGER PRIMARY KEY, apartment_number INTEGER)')
        cursor.execute("PRAGMA table_info(apartments)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'phone_number' not in columns:
            cursor.execute('ALTER TABLE apartments ADD COLUMN phone_number TEXT')
    return conn
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Привет! Для начала введите /home')
def ask_apartment(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Введите номер вашей квартиры:')
    context.user_data['waiting_for_apartment'] = True
def save_apartment(update: Update, context: CallbackContext) -> None:
    try:
        apartment_number = int(update.message.text)
        user_id = update.message.from_user.id

        update.message.reply_text('Пожалуйста, введите ваш номер телефона:')
        context.user_data['apartment_number'] = apartment_number
        context.user_data['waiting_for_phone'] = True
        context.user_data.pop('waiting_for_apartment', None)
    except ValueError:
        update.message.reply_text('Пожалуйста, введите корректный номер квартиры.')

def save_phone_number(update: Update, context: CallbackContext) -> None:
    phone_number = update.message.text
    if not re.match(r'^(\+?\d{10,15}|\d{10,15})$', phone_number):
        update.message.reply_text('Пожалуйста, введите корректный номер телефона (от 10 до 15 цифр, может начинаться с +).')
        return

    try:
        user_id = update.message.from_user.id
        apartment_number = context.user_data['apartment_number']

        with closing(initialize_database()) as conn:
            with conn:
                conn.execute(
                    'INSERT OR REPLACE INTO apartments (user_id, apartment_number, phone_number) VALUES (?, ?, ?)',
                    (user_id, apartment_number, phone_number))

        update.message.reply_text(f'Квартира {apartment_number} и телефон {phone_number} успешно записаны!')
        context.user_data.pop('waiting_for_phone', None)
        context.user_data.pop('apartment_number', None)
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        update.message.reply_text(
            'Произошла ошибка при сохранении номера телефона в базе данных. Пожалуйста, повторите попытку.')
    except Exception as e:
        print(f"Unexpected error: {e}")
        update.message.reply_text(
            'Произошла неожиданная ошибка при сохранении номера телефона. Пожалуйста, повторите попытку.')

def list_residents(update: Update, context: CallbackContext) -> None:
    with closing(initialize_database()) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, apartment_number, phone_number FROM apartments ORDER BY apartment_number ASC')
        residents = cursor.fetchall()

    if residents:
        residents_text = '\n'.join(
            [f'@{get_username(update, context.bot, user_id)}: Квартира {apartment_number}, Телефон {phone_number}' for
             user_id, apartment_number, phone_number in residents])
        update.message.reply_text(f'Все зарегистрированные жильцы:\n{residents_text}')
    else:
        update.message.reply_text('Нет зарегистрированных жильцов.')

def who_lives(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Введите номер квартиры, чтобы узнать, кто в ней живет:')
    context.user_data['waiting_for_apartment_who_lives'] = True

def handle_apartment_who_lives(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('waiting_for_apartment_who_lives'):
        try:
            target_apartment = int(update.message.text)
            with closing(initialize_database()) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, apartment_number, phone_number FROM apartments WHERE apartment_number = ?', (target_apartment,))
                residents = cursor.fetchall()

            if residents:
                residents_text = '\n'.join(
                    [f'@{get_username(update, context.bot, user_id)}: Квартира {apartment_number}, Телефон {phone_number}' for
                     user_id, apartment_number, phone_number in residents])
                update.message.reply_text(f'Живут в квартире {target_apartment}:\n{residents_text}')
            else:
                update.message.reply_text(f'В квартире {target_apartment} никто не зарегистрирован.')

            context.user_data.pop('waiting_for_apartment_who_lives', None)
        except ValueError:
            update.message.reply_text('Пожалуйста, введите корректный номер квартиры.')

def get_username(update: Update, bot: Bot, user_id: int) -> str:
    try:
        user = bot.get_chat_member(update.message.chat_id, user_id).user
        return user.username if user.username else str(user_id)
    except Exception as e:
        print(f"Error getting username: {e}")
        return str(user_id)

def handle_non_command(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('waiting_for_apartment'):
        save_apartment(update, context)
    elif context.user_data.get('waiting_for_phone'):
        save_phone_number(update, context)
    elif context.user_data.get('waiting_for_apartment_who_lives'):
        handle_apartment_who_lives(update, context)

def main() -> None:
    updater = Updater("7447031449:AAHpD9CbTUHxIoJ9LyZRW4mDyGisklwDAbQ")

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("home", ask_apartment))
    dp.add_handler(CommandHandler("who_lives", who_lives))
    dp.add_handler(CommandHandler("list_residents", list_residents))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_non_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
