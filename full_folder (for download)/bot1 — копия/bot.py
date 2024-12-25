import telebot
from telebot import types
import sqlite3

# Ініціалізація бота
bot = telebot.TeleBot('7000409399:AAG1xPV4drfoPwEtZi9v8p8wmTilXI2Js64')  

# Підключення до БД
def connect_db():
    """Підключення до БД SQLite."""
    conn = sqlite3.connect('database1') 
    return conn

user_selection = {}

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Переглянути архів 🔂')
    btn2 = types.KeyboardButton('Допомога ⁉️')
    btn3 = types.KeyboardButton('Обрати ТЗ 🗂')
    markup.row(btn3, btn2)
    markup.add(btn1)

    bot.send_message(message.chat.id, f"Вітаю, {message.from_user.first_name}. \nОберіть дію нижче 👇", reply_markup=markup)

# Обробник "Зверни ТЗ"
@bot.message_handler(func=lambda message: message.text == 'Обрати ТЗ 🗂')
def select_tz(message):
    markup = types.InlineKeyboardMarkup()
    btn_add = types.InlineKeyboardButton('Додати', callback_data='add_data')
    btn_delete = types.InlineKeyboardButton('Видалити', callback_data='delete_data')
    markup.add(btn_add, btn_delete)

    bot.send_message(message.chat.id, 'Оберіть дію:', reply_markup=markup)

# Обробка кнопки "Додати"
@bot.callback_query_handler(func=lambda call: call.data == 'add_data')
def handle_add_data(call):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for table in tables:
        table_name = table[0]
        btn = types.InlineKeyboardButton(table_name, callback_data=f"table|{table_name}")
        markup.add(btn)

    bot.send_message(call.message.chat.id, "Оберіть таблицю ТЗ з наступного списку:", reply_markup=markup)

# Обробка вибору таблиці
@bot.callback_query_handler(func=lambda call: call.data.startswith("table"))
def handle_table(call):
    table_name = call.data.split('|')[1]
    user_selection[call.message.chat.id] = {'table': table_name, 'columns': []}

    # Отримуємо колонки таблиці
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    markup = types.InlineKeyboardMarkup()

    for col in columns:
        if col not in ['Дата', 'Пробіг_(км)']:
            if col in user_selection[call.message.chat.id]['columns']:
                btn = types.InlineKeyboardButton(f"✅ {col}", callback_data=f"col|{col}")
            else:
                btn = types.InlineKeyboardButton(f"⬜ {col}", callback_data=f"col|{col}")
            markup.add(btn)

    markup.add(types.InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_columns"))
    bot.edit_message_text("Оберіть дії:", 
                          chat_id=call.message.chat.id, 
                          message_id=call.message.message_id, 
                          reply_markup=markup)

# Оновлення обраних колонок
@bot.callback_query_handler(func=lambda call: call.data.startswith("col"))
def toggle_column(call):
    column_name = call.data.split('|')[1]
    user_data = user_selection[call.message.chat.id]
    columns = user_data['columns']

    # Додаємо або видаляємо колонку зі списку вибору
    if column_name in columns:
        columns.remove(column_name)
    else:
        columns.append(column_name)

    markup = types.InlineKeyboardMarkup()
    for col in columns:
        btn = types.InlineKeyboardButton(f"✅ {col}", callback_data=f"col|{col}")
        markup.add(btn)

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({user_data['table']});")
    columns_list = [col[1] for col in cursor.fetchall()]
    conn.close()

    for col in columns_list:
        if col not in columns and col not in ['Дата', 'Пробіг_(км)']:
            btn = types.InlineKeyboardButton(f"⬜ {col}", callback_data=f"col|{col}")
            markup.add(btn)

    markup.add(types.InlineKeyboardButton("✅ Підтвердити", callback_data="confirm_columns"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

# Підтвердження стовпців
@bot.callback_query_handler(func=lambda call: call.data == "confirm_columns")
def confirm_columns(call):
    bot.send_message(call.message.chat.id, "Введіть дату (формат: ДД.ММ.РРРР):")
    bot.register_next_step_handler(call.message, get_date)

# Отримання дати
def get_date(message):
    user_selection[message.chat.id]['date'] = message.text
    bot.send_message(message.chat.id, "Введіть пробіг (км):")
    bot.register_next_step_handler(message, get_mileage)

# Отримання пробігу
def get_mileage(message):
    user_selection[message.chat.id]['mileage'] = message.text
    save_data(message)

# Збереження даних у БД
def save_data(message):
    try:
        user_data = user_selection.pop(message.chat.id)
        table_name = user_data['table']
        selected_columns = user_data['columns']
        date = user_data['date']
        mileage = user_data['mileage']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(f"SELECT * FROM `{table_name}` WHERE `Дата` = ? AND `Пробіг_(км)` = ?", (date, mileage))
        existing_row = cursor.fetchone()

        if existing_row:
            for col in selected_columns:
                cursor.execute(f"UPDATE `{table_name}` SET `{col}` = '+' WHERE `Дата` = ? AND `Пробіг_(км)` = ?", (date, mileage))
        else:
            cursor.execute(f"INSERT INTO `{table_name}` (`Дата`, `Пробіг_(км)`) VALUES (?, ?)", (date, mileage))
            for col in selected_columns:
                cursor.execute(f"UPDATE `{table_name}` SET `{col}` = '+' WHERE `Дата` = ? AND `Пробіг_(км)` = ?", (date, mileage))

        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, "✅ Дані успішно оновлено!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Сталася помилка: {e}")

user_selection = {}

user_selection = {}

# Обробник "Видалити"
@bot.callback_query_handler(func=lambda call: call.data == 'delete_data')
def handle_delete_data(call):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for table in tables:
        table_name = table[0]
        btn = types.InlineKeyboardButton(table_name, callback_data=f"delete_table|{table_name}")
        markup.add(btn)

    bot.edit_message_text("⚠️УВАГА⚠️ \n ВИДАЛЯТИ ВАРТО ЛИШЕ ТОДІ, ЯКЩО ПРИ ЗАПИСІ БУЛИ ЗАЗНАЧЕНІ НЕКОРЕКТНІ ДАНІ  \n\n Оберіть ТЗ для видалення даних:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# Обробка вибору таблиці для видалення
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_table"))
def select_table_for_deletion(call):
    table_name = call.data.split('|')[1]
    user_selection[call.message.chat.id] = {'table': table_name}

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT Дата FROM {table_name} ORDER BY Дата ASC;")
    dates = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for date in dates:
        btn = types.InlineKeyboardButton(date[0], callback_data=f"select_date_to_delete|{date[0]}|{table_name}")
        markup.add(btn)

    bot.send_message(call.message.chat.id, "Оберіть дату для видалення:", reply_markup=markup)

# Обробка вибору дати видалення
@bot.callback_query_handler(func=lambda call: call.data.startswith("select_date_to_delete"))
def select_date_for_deletion(call):
    date, table_name = call.data.split('|')[1], call.data.split('|')[2]
    user_selection[call.message.chat.id]['date'] = date
    user_selection[call.message.chat.id]['table'] = table_name

    conn = connect_db()
    cursor = conn.cursor()

    # Отримуємо дані для обраної дати
    cursor.execute(f"SELECT * FROM {table_name} WHERE Дата = ?", (date,))
    rows = cursor.fetchall()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    # Формуємо текст з інформацією про дії
    result = f"Таблиця: {table_name}\n\nДата: {date}\n"
    for row in rows:
        mileage = row[columns.index('Пробіг_(км)')]  # Находим значение пробега
        result += f"Пробіг: {mileage} км\n"
        result += "\nДії:\n"
        result += "\n".join(columns[i] for i in range(len(row)) if row[i] == '+')  # Выводим только названия столбцов
        result += "\n\n"

    bot.send_message(call.message.chat.id, result)

    # Створюємо кнопки для видалення чи повернення
    markup = types.InlineKeyboardMarkup()
    btn_delete = types.InlineKeyboardButton('Видалити', callback_data=f"confirm_delete|{table_name}|{date}")
    btn_back = types.InlineKeyboardButton('Повернутись', callback_data="back_to_main_menu")
    markup.add(btn_delete, btn_back)

    bot.send_message(call.message.chat.id, "Виберіть дію:", reply_markup=markup)

# Підтвердження видалення даних
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete"))
def confirm_delete(call):
    table_name, date = call.data.split('|')[1], call.data.split('|')[2]
    
    conn = connect_db()
    cursor = conn.cursor()

    # Видалення даних
    cursor.execute(f"DELETE FROM `{table_name}` WHERE `Дата` = ?", (date,))
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, "✅ Дані успішно видалено!")

# Повернення до вибору дії
@bot.callback_query_handler(func=lambda call: call.data == "back_to_main_menu")
def back_to_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    btn_add = types.InlineKeyboardButton('Додати', callback_data='add_data')
    btn_delete = types.InlineKeyboardButton('Видалити', callback_data='delete_data')
    markup.add(btn_add, btn_delete)

    bot.send_message(call.message.chat.id, 'Оберіть дію:', reply_markup=markup)



    # Обробник "Переглянути архів"
@bot.message_handler(func=lambda message: message.text == 'Переглянути архів 🔂')
def view_archive(message):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for table in tables:
        table_name = table[0]
        btn = types.InlineKeyboardButton(table_name, callback_data=f"archive_table|{table_name}")
        markup.add(btn)

    bot.send_message(message.chat.id, "Оберіть ТЗ для перегляду архіву:", reply_markup=markup)

# Вибір таблиці для перегляду архіву
@bot.callback_query_handler(func=lambda call: call.data.startswith("archive_table"))
def select_archive_table(call):
    table_name = call.data.split('|')[1]
    user_selection[call.message.chat.id] = {'table': table_name}

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT Дата FROM {table_name} ORDER BY Дата ASC;")
    dates = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    for date in dates:
        btn = types.InlineKeyboardButton(date[0], callback_data=f"archive_date|{table_name}|{date[0]}")
        markup.add(btn)

    bot.edit_message_text("Оберіть дату з архіву:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

# Вибір дати для перегляду архіву
@bot.callback_query_handler(func=lambda call: call.data.startswith("archive_date"))
def select_archive_date(call):
    _, table_name, date = call.data.split('|')
    conn = connect_db()
    cursor = conn.cursor()

    # Отримуємо дані для обраної дати
    cursor.execute(f"SELECT * FROM {table_name} WHERE Дата = ?", (date,))
    rows = cursor.fetchall()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    # Формуємо текст відповіді з даними
    result = f"{table_name}\n \nДата: {date}\n"
    for row in rows:
        mileage = row[columns.index('Пробіг_(км)')]  
        result += f"Пробіг: {mileage} км\n"
        result += "\nДії:\n"
        result += "\n".join(columns[i] for i in range(len(row)) if row[i] == '+') 
        result += "\n\n"

    bot.send_message(call.message.chat.id, result if rows else "Дані за вибрану дату відсутні.")


# Обробник кнопки "Допомога ⁉️"
@bot.message_handler(func=lambda message: message.text == 'Допомога ⁉️')
def send_help(message):
    try:
        help_text = """
<b>ІНСТРУКЦІЯ КОРИСТУВАННЯ</b>

<b>Вибір ТЗ:</b>
1. Клік на «Обрати ТЗ»  
2. Із бази даних обираємо необхідний ТЗ за держ номером  
3. Обираємо необхідні роботи з наступної бази робіт  
4. Вносимо дату проведення робіт  
5. Вносимо показники одометра (пробіг на даний момент)  
6. Зберігаємо внесену інформацію  

<b>Робота з архівом:</b>
1. Клік на «Переглянути архів»  
2. Із бази даних обираємо необхідний ТЗ за держ номером  
3. Обираємо дату на яку нас цікавить інформація  
4. Отримуємо результат
        """
        bot.send_message(message.chat.id, help_text, parse_mode="HTML")
    except Exception as e:
        bot.send_message(message.chat.id, f"Помилка при відправці допомоги: {e}")


# Запуск бота
if __name__ == "__main__":
    bot.polling(non_stop=True)




