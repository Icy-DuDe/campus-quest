import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).with_name("campus_quest.sqlite3")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def create_game(player_name):
    game_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    state = {
        "game_id": game_id,
        "player_name": player_name,
        "phase": "NOT_STARTED",
        "reached": [],
        "boosts": {},
        "deadline": None,
        "message_queue": [],
        "last_location": None,
        "started_at": None,
    }

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO games
            (id, player_name, state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, player_name, json.dumps(state), now, now),
        )
        conn.commit()

    return game_id


def get_game(game_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT state_json FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()

    if row is None:
        return None

    return json.loads(row["state_json"])


def save_game(game):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE games
            SET state_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(game), now, game["game_id"]),
        )
        conn.commit()
