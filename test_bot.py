import unittest
from unittest.mock import patch, MagicMock
import sqlite3
from bot import connect_db, handle_add_data, user_selection

class TestTelegramBot(unittest.TestCase):
    def setUp(self):
        """Подготовка перед каждым тестом."""
        self.test_db = 'test_database.db'
        self.conn = sqlite3.connect(self.test_db)
        self.cursor = self.conn.cursor()
        # Удаляем таблицу, если она уже существует (для чистоты тестов)
        self.cursor.execute("DROP TABLE IF EXISTS test_table;")
        self.cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, column1 TEXT);")
        self.conn.commit()

    def tearDown(self):
        """Очистка после каждого теста."""
        # Проверяем, открыто ли соединение
        if hasattr(self, 'cursor') and self.cursor:
            try:
                self.cursor.execute("DROP TABLE IF EXISTS test_table;")
                self.conn.commit()
            except sqlite3.ProgrammingError:
                pass  # Игнорируем, если соединение уже закрыто
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
            except sqlite3.ProgrammingError:
                pass  # Игнорируем, если соединение уже закрыто

    def test_connect_db(self):
        """Проверяем подключение к базе данных."""
        conn = connect_db()
        self.assertIsInstance(conn, sqlite3.Connection)
        conn.close()

    @patch('bot.bot')  # Подмена объекта bot
    def test_handle_add_data(self, mock_bot):
        """Тест обработчика add_data."""
        mock_call = MagicMock()
        mock_call.data = 'add_data'
        mock_call.message.chat.id = 12345

        with patch('bot.connect_db', return_value=self.conn):
            handle_add_data(mock_call)

        # Проверка, что бот отправил сообщение
        mock_bot.send_message.assert_called()

    def test_user_selection(self):
        """Тестируем работу с user_selection."""
        chat_id = 12345
        user_selection[chat_id] = {'table': 'test_table', 'columns': ['column1']}
        self.assertIn(chat_id, user_selection)
        self.assertEqual(user_selection[chat_id]['table'], 'test_table')

if __name__ == '__main__':
    unittest.main()
