import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            shop_name TEXT,
            registration_date TEXT,
            expiry_date TEXT,
            status TEXT DEFAULT 'trial'
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, shop_name):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    reg_date = datetime.now()
    expiry_date = reg_date + timedelta(days=3)

    cursor.execute("SELECT user_id FROM subscribers WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO subscribers (user_id, username, shop_name, registration_date, expiry_date, status)
            VALUES (?, ?, ?, ?, ?, 'trial')
        ''', (user_id, username, shop_name, reg_date.strftime('%Y-%m-%d'), expiry_date.strftime('%Y-%m-%d')))
        conn.commit()
    conn.close()

def check_subscription(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date, status FROM subscribers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        expiry_date = datetime.strptime(row[0], '%Y-%m-%d')
        if datetime.now() > expiry_date:
            return "expired"
        return row[1]
    return "not_found"

def renew_subscription(user_id, months):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT expiry_date FROM subscribers WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        current_expiry = datetime.strptime(row[0], '%Y-%m-%d')
        start_date = max(datetime.now(), current_expiry)
        days_to_add = months * 30
        new_expiry = start_date + timedelta(days=days_to_add)
        cursor.execute('''
            UPDATE subscribers SET expiry_date = ?, status = 'active' WHERE user_id = ?
        ''', (new_expiry.strftime('%Y-%m-%d'), user_id))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()