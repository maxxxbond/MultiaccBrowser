import sqlite3
import json
from pathlib import Path
from app.models.profile import Profile

USER_DATA_PATH = Path(__file__).parent.parent.parent / 'user_data'
DB_PATH = USER_DATA_PATH / 'profiles.db'


def create_db():
    """Створює SQLite базу, якщо її немає"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            name TEXT PRIMARY KEY,
            fingerprint TEXT,
            proxy TEXT,
            page_urls TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def get_profile(profile_name: str) -> Profile | None:
    """Отримує профіль з бази"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT fingerprint, proxy, page_urls FROM profiles WHERE name = ?", (profile_name,))
    row = cursor.fetchone()
    conn.close()
    return Profile.from_json(profile_name, *row) if row else None


def save_profile(profile: Profile):
    """Зберігає профіль у базу"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO profiles (name, fingerprint, proxy, page_urls) VALUES (?, ?, ?, ?)",
        (profile.name, *profile.to_json())
    )
    conn.commit()
    conn.close()


def update_profile_pages(profile_name: str, urls: list[str]):
    """Оновлює список відкритих сторінок у профілі"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE profiles SET page_urls = ? WHERE name = ?",
        (json.dumps(urls), profile_name)
    )
    conn.commit()
    conn.close()


def get_all_profiles() -> list[str]:
    """Отримує список всіх профілів"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM profiles")
    profiles = [row[0] for row in cursor.fetchall()]
    conn.close()
    return profiles
