import sqlite3

DATABASE_NAME = "vyntra.db"


def create_table():
    """Create tables to track customer questions."""

    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answered INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def record_question(question, answered):
    """Save each customer question and whether it was answered."""

    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO customer_questions (question, answered)
        VALUES (?, ?)
        """,
        (question, answered)
    )

    connection.commit()
    connection.close()


def get_question_stats():
    """Get totals for answered and unanswered questions."""

    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            COUNT(*),
            SUM(CASE WHEN answered = 1 THEN 1 ELSE 0 END),
            SUM(CASE WHEN answered = 0 THEN 1 ELSE 0 END)
        FROM customer_questions
    """)

    result = cursor.fetchone()
    connection.close()

    return result


def get_frequent_questions(answered):
    """Get frequently asked questions by answer status."""

    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT question, COUNT(*) AS frequency
        FROM customer_questions
        WHERE answered = ?
        GROUP BY LOWER(TRIM(question))
        ORDER BY frequency DESC
        LIMIT 10
    """, (answered,))

    questions = cursor.fetchall()
    connection.close()

    return questions