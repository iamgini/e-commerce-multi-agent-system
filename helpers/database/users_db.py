from typing import Optional, Tuple

import bcrypt
import psycopg
# from psycopg.rows import dict_row

from config import USERS_DB_DSN


def encrypt_password(plaintext_password: str) -> str:
    password_bytes = plaintext_password.encode('utf-8')
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    return password_hash.decode('utf-8')


def verify_password(entered_password: str, stored_hash_str: str) -> bool:
    password_bytes = entered_password.encode('utf-8')
    hash_bytes = stored_hash_str.encode('utf-8')

    return bcrypt.checkpw(password_bytes, hash_bytes)


def _connect() -> psycopg.Connection:
    """Connect to returns database."""
    return psycopg.connect(USERS_DB_DSN)


def get_user(username: str) -> Optional[Tuple]:
    sql = """
        SELECT username, password_hash
        FROM users
        WHERE username = %s
        """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (username,))
            row = cur.fetchone()
            return row if row else None
