import json
import psycopg2
import psycopg2.extras
from config import DATABASE_URL


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id   BIGINT PRIMARY KEY,
                    username  TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    id         SERIAL PRIMARY KEY,
                    user_id    BIGINT REFERENCES users(user_id),
                    word       TEXT NOT NULL,
                    word_data  JSONB,
                    sent_at    TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id           SERIAL PRIMARY KEY,
                    user_id      BIGINT REFERENCES users(user_id),
                    quiz_type    TEXT,
                    score        INTEGER DEFAULT 0,
                    total        INTEGER DEFAULT 0,
                    started_at   TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quiz_answers (
                    id             SERIAL PRIMARY KEY,
                    quiz_id        INTEGER REFERENCES quizzes(id),
                    word           TEXT,
                    correct_answer TEXT,
                    user_answer    TEXT,
                    is_correct     BOOLEAN
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id           SERIAL PRIMARY KEY,
                    user_id      BIGINT REFERENCES users(user_id),
                    session_type TEXT,
                    level        TEXT,
                    scenario     TEXT,
                    messages     JSONB DEFAULT '[]',
                    evaluation   JSONB,
                    started_at   TIMESTAMP DEFAULT NOW(),
                    completed_at TIMESTAMP
                )
            """)
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS level TEXT DEFAULT 'B1'")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_session_id INTEGER")
        conn.commit()


def ensure_user(user_id: int, username: str | None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
            """, (user_id, username))
        conn.commit()


def get_all_user_ids() -> list[int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users")
            return [row[0] for row in cur.fetchall()]


def get_sent_words(user_id: int) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT word FROM user_words WHERE user_id = %s",
                (user_id,)
            )
            return [row[0] for row in cur.fetchall()]


def save_word(user_id: int, word: str, word_data: dict):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_words (user_id, word, word_data) VALUES (%s, %s, %s)",
                (user_id, word, json.dumps(word_data, ensure_ascii=False))
            )
        conn.commit()


def get_words_for_quiz(user_id: int, count: int, days: int | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if days:
                cur.execute("""
                    SELECT word, word_data FROM user_words
                    WHERE user_id = %s
                      AND sent_at >= NOW() - INTERVAL '%s days'
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (user_id, days, count))
            else:
                cur.execute("""
                    SELECT word, word_data FROM user_words
                    WHERE user_id = %s
                    ORDER BY RANDOM()
                    LIMIT %s
                """, (user_id, count))
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def get_word_count(user_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_words WHERE user_id = %s",
                (user_id,)
            )
            return cur.fetchone()[0]


def create_quiz(user_id: int, quiz_type: str, total: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quizzes (user_id, quiz_type, total)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (user_id, quiz_type, total))
            quiz_id = cur.fetchone()[0]
        conn.commit()
        return quiz_id


def save_quiz_answer(quiz_id: int, word: str, correct: str, given: str, is_correct: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quiz_answers (quiz_id, word, correct_answer, user_answer, is_correct)
                VALUES (%s, %s, %s, %s, %s)
            """, (quiz_id, word, correct, given, is_correct))
        conn.commit()


def finish_quiz(quiz_id: int, score: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE quizzes
                SET score = %s, completed_at = NOW()
                WHERE id = %s
            """, (score, quiz_id))
        conn.commit()


def get_quiz_history(user_id: int, limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT quiz_type, score, total, started_at
                FROM quizzes
                WHERE user_id = %s AND completed_at IS NOT NULL
                ORDER BY started_at DESC
                LIMIT %s
            """, (user_id, limit))
            return [dict(r) for r in cur.fetchall()]


def get_wrong_answers(quiz_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT word, correct_answer, user_answer
                FROM quiz_answers
                WHERE quiz_id = %s AND is_correct = FALSE
            """, (quiz_id,))
            return [dict(r) for r in cur.fetchall()]


# ── Practice sessions ────────────────────────────────────────────────────────

def create_practice_session(user_id: int, session_type: str, level: str, scenario: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO practice_sessions (user_id, session_type, level, scenario)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (user_id, session_type, level, scenario))
            session_id = cur.fetchone()[0]
            cur.execute("UPDATE users SET active_session_id = %s WHERE user_id = %s",
                        (session_id, user_id))
        conn.commit()
        return session_id


def get_active_session(user_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT ps.* FROM practice_sessions ps
                JOIN users u ON u.active_session_id = ps.id
                WHERE u.user_id = %s AND ps.completed_at IS NULL
            """, (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def append_practice_message(session_id: int, role: str, text: str, feedback: str = ""):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE practice_sessions
                SET messages = messages || %s::jsonb
                WHERE id = %s
            """, (json.dumps([{"role": role, "text": text, "feedback": feedback}],
                              ensure_ascii=False), session_id))
        conn.commit()


def finish_practice_session(session_id: int, user_id: int, evaluation: dict):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE practice_sessions
                SET completed_at = NOW(), evaluation = %s
                WHERE id = %s
            """, (json.dumps(evaluation, ensure_ascii=False), session_id))
            cur.execute("UPDATE users SET active_session_id = NULL WHERE user_id = %s",
                        (user_id,))
        conn.commit()


def get_practice_history(user_id: int, limit: int = 5) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT session_type, level, scenario, evaluation, started_at
                FROM practice_sessions
                WHERE user_id = %s AND completed_at IS NOT NULL
                ORDER BY started_at DESC LIMIT %s
            """, (user_id, limit))
            return [dict(r) for r in cur.fetchall()]


# ── User level ───────────────────────────────────────────────────────────────

def set_user_level(user_id: int, level: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET level = %s WHERE user_id = %s", (level, user_id))
        conn.commit()


def get_user_level(user_id: int) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT level FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else "B1"


