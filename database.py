import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Establishes and returns a database connection."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    # Neon and Render PostgreSQL databases require SSL.
    # The connection string usually has ?sslmode=require, but we make sure here.
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Initializes the database schema if tables do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id BIGINT PRIMARY KEY,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create announcements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id VARCHAR(64) PRIMARY KEY,
                position VARCHAR(255) NOT NULL,
                location VARCHAR(255),
                announcement_type VARCHAR(255),
                is_matching BOOLEAN DEFAULT FALSE,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

def add_user(chat_id):
    """Subscribes a user by saving their Telegram chat ID."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (chat_id) VALUES (%s) ON CONFLICT (chat_id) DO NOTHING",
            (chat_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error adding user {chat_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def remove_user(chat_id):
    """Unsubscribes a user by deleting their Telegram chat ID."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE chat_id = %s", (chat_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error removing user {chat_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def is_user_subscribed(chat_id):
    """Checks if a user is currently subscribed."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM users WHERE chat_id = %s", (chat_id,))
        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Error checking subscription for user {chat_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_all_users():
    """Retrieves all subscribed chat IDs."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT chat_id FROM users")
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def is_announcement_new(announcement_id):
    """Checks if an announcement hash has already been scraped and processed."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM announcements WHERE id = %s", (announcement_id,))
        return cursor.fetchone() is None
    except Exception as e:
        print(f"Error checking announcement {announcement_id}: {e}")
        return False  # Treat as not new if we hit db error (safeguard against spam)
    finally:
        cursor.close()
        conn.close()

# Fetch all announcement IDs at once
def get_existing_announcement_ids():
    """Returns a set containing all announcement IDs."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM announcements")
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error fetching announcement IDs: {e}")
        return set()
    finally:
        cursor.close()
        conn.close()

def add_announcement(announcement_id, position, location, announcement_type, is_matching):
    """Adds a new announcement to the tracking database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO announcements (id, position, location, announcement_type, is_matching)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (announcement_id, position, location, announcement_type, is_matching)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error adding announcement {announcement_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_announcements_summary(limit=50):
    """Gets the list of latest scraped announcements."""
    conn = get_connection()
    # Use RealDictCursor to return results as dictionaries
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT id, position, location, announcement_type, is_matching, scraped_at FROM announcements ORDER BY scraped_at DESC LIMIT %s",
            (limit,)
        )
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching announcements: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_stats():
    """Gets quick stats for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM announcements")
        total_announcements = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM announcements WHERE is_matching = TRUE")
        matching_announcements = cursor.fetchone()[0]
        
        return {
            "subscribers": user_count,
            "total_announcements": total_announcements,
            "matching_announcements": matching_announcements
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {"subscribers": 0, "total_announcements": 0, "matching_announcements": 0}
    finally:
        cursor.close()
        conn.close()
