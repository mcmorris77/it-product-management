import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connections():
    # открывает соединение, строки результата приходят словарями
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def create_tables():
    conn = get_connections()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id SERIAL PRIMARY KEY,
            payer_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT,
            payment_info TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            check_id INTEGER NOT NULL REFERENCES checks(id),
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            type TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id SERIAL PRIMARY KEY,   
            item_id INTEGER NOT NULL REFERENCES items(id),
            user_id INTEGER NOT NULL REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()