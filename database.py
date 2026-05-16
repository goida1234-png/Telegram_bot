import aiosqlite
from config import DB_NAME


async def init_db():
    """Создаёт все таблицы при первом запуске"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER UNIQUE NOT NULL,
                username    TEXT,
                first_name  TEXT,
                joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                chapter     TEXT NOT NULL,
                score       INTEGER DEFAULT 0,
                total       INTEGER DEFAULT 0,
                started_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                finished_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS answers (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     INTEGER NOT NULL,
                question_index INTEGER NOT NULL,
                question_text  TEXT NOT NULL,
                chosen_option  TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                is_correct     INTEGER NOT NULL,
                FOREIGN KEY (session_id) REFERENCES quiz_sessions(id)
            )
        """)

        await db.commit()


# ───────────── USERS ─────────────

async def get_or_create_user(tg_id: int, username: str, first_name: str) -> int:
    """Возвращает id пользователя, создаёт если не существует"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id FROM users WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row:
            return row[0]

        async with db.execute(
            "INSERT INTO users (tg_id, username, first_name) VALUES (?, ?, ?)",
            (tg_id, username, first_name)
        ) as cursor:
            user_id = cursor.lastrowid

        await db.commit()
        return user_id


# ───────────── SESSIONS ─────────────

async def create_session(user_id: int, chapter: str, total: int) -> int:
    """Создаёт новую сессию викторины, возвращает её id"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "INSERT INTO quiz_sessions (user_id, chapter, total) VALUES (?, ?, ?)",
            (user_id, chapter, total)
        ) as cursor:
            session_id = cursor.lastrowid
        await db.commit()
        return session_id


async def finish_session(session_id: int, score: int):
    """Закрывает сессию, записывает финальный счёт"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE quiz_sessions
            SET score = ?, finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (score, session_id))
        await db.commit()


async def get_user_stats(tg_id: int) -> dict:
    """Статистика пользователя по всем главам"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("""
            SELECT
                qs.chapter,
                COUNT(qs.id)        AS games,
                MAX(qs.score)       AS best,
                ROUND(AVG(qs.score * 100.0 / qs.total), 1) AS avg_pct
            FROM quiz_sessions qs
            JOIN users u ON u.id = qs.user_id
            WHERE u.tg_id = ? AND qs.finished_at IS NOT NULL
            GROUP BY qs.chapter
        """, (tg_id,)) as cursor:
            rows = await cursor.fetchall()

    return {row[0]: {"games": row[1], "best": row[2], "avg_pct": row[3]} for row in rows}


# ───────────── ANSWERS ─────────────

async def save_answer(
    session_id: int,
    question_index: int,
    question_text: str,
    chosen_option: str,
    correct_option: str,
    is_correct: bool
):
    """Сохраняет один ответ пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO answers
                (session_id, question_index, question_text, chosen_option, correct_option, is_correct)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, question_index, question_text, chosen_option, correct_option, int(is_correct)))
        await db.commit()

# ───────────── XML EXPORT / IMPORT ─────────────

async def get_all_sessions_for_export(tg_id: int) -> dict:
    """Выгружает все данные пользователя для XML экспорта"""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        # Данные пользователя
        async with db.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ) as cursor:
            user = await cursor.fetchone()

        if not user:
            return {}

        # Все завершённые сессии
        async with db.execute("""
            SELECT * FROM quiz_sessions
            WHERE user_id = ? AND finished_at IS NOT NULL
            ORDER BY started_at DESC
        """, (user["id"],)) as cursor:
            sessions = await cursor.fetchall()

        result = {
            "user": dict(user),
            "sessions": []
        }

        # Ответы для каждой сессии
        for session in sessions:
            async with db.execute("""
                SELECT * FROM answers
                WHERE session_id = ?
                ORDER BY question_index
            """, (session["id"],)) as cursor:
                answers = await cursor.fetchall()

            result["sessions"].append({
                "session": dict(session),
                "answers": [dict(a) for a in answers]
            })

        return result


async def import_session_from_xml(
    tg_id: int,
    username: str,
    first_name: str,
    chapter: str,
    score: int,
    total: int,
    started_at: str,
    finished_at: str,
    answers: list
) -> bool:
    """Импортирует одну сессию из XML в БД"""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            # Получаем или создаём пользователя
            async with db.execute(
                "SELECT id FROM users WHERE tg_id = ?", (tg_id,)
            ) as cursor:
                user_row = await cursor.fetchone()

            if user_row:
                user_id = user_row[0]
            else:
                async with db.execute(
                    "INSERT INTO users (tg_id, username, first_name) VALUES (?, ?, ?)",
                    (tg_id, username, first_name)
                ) as cursor:
                    user_id = cursor.lastrowid

            # Создаём сессию
            async with db.execute("""
                INSERT INTO quiz_sessions
                    (user_id, chapter, score, total, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, chapter, score, total, started_at, finished_at)) as cursor:
                session_id = cursor.lastrowid

            # Сохраняем ответы
            for answer in answers:
                await db.execute("""
                    INSERT INTO answers
                        (session_id, question_index, question_text,
                         chosen_option, correct_option, is_correct)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    answer["question_index"],
                    answer["question_text"],
                    answer["chosen_option"],
                    answer["correct_option"],
                    answer["is_correct"]
                ))

            await db.commit()
            return True

    except Exception:
        return False