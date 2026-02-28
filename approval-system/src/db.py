"""SQLite DB helpers for the approval system."""
from typing import Iterator
import sqlite3


def get_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str) -> None:
    conn = get_conn(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            sender_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            current_step INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(sender_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            letter_id INTEGER NOT NULL,
            step_index INTEGER NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            actor_id INTEGER,
            comments TEXT,
            acted_at TEXT,
            FOREIGN KEY(letter_id) REFERENCES letters(id),
            FOREIGN KEY(actor_id) REFERENCES users(id)
        );
        """
    )
    conn.commit()
    conn.close()