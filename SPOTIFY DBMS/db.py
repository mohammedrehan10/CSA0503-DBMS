"""
Database Abstraction & Connection Management
Spotify Audio Features & Popularity Explorer (DBMS Capstone)
Supports primary MySQL connection with resilient SQLite automatic mirror/fallback.
"""

import os
import sqlite3
import re
from pathlib import Path
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "spotify_explorer")
ALLOW_SQLITE_FALLBACK = os.getenv("ALLOW_SQLITE_FALLBACK", "True").lower() in ("true", "1", "yes")

SQLITE_DB_PATH = Path(__file__).resolve().parent / "spotify_explorer.db"
SQL_FILE_PATH = Path(__file__).resolve().parent / "database.sql"

# Global connection state tracking
db_status = {
    "engine": "unknown",          # "mysql" or "sqlite"
    "connected": False,
    "message": "Initializing...",
    "database": DB_NAME,
    "host": DB_HOST,
    "user": DB_USER,
    "error": None
}

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    HAS_MYSQL_CONNECTOR = True
except ImportError:
    HAS_MYSQL_CONNECTOR = False
    MySQLError = Exception


import time

# Cache MySQL connection health check to avoid repeated TCP socket wait times when offline
_mysql_available = None
_last_mysql_check = 0
MYSQL_CHECK_CACHE_SECONDS = 15

def try_connect_mysql(force_check=False):
    """Attempt connecting to the target MySQL database with timeout and caching."""
    global _mysql_available, _last_mysql_check
    
    if not HAS_MYSQL_CONNECTOR:
        return None, "mysql-connector-python is not installed."
        
    now = time.time()
    if not force_check and _mysql_available is False and (now - _last_mysql_check < MYSQL_CHECK_CACHE_SECONDS):
        return None, db_status.get("error", "MySQL offline (cached)")
    
    _last_mysql_check = now
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            connection_timeout=2,
            autocommit=False
        )
        _mysql_available = True
        return conn, None
    except MySQLError as err:
        # If database does not exist, try to connect to server and create it
        if err.errno == 1049:  # ER_BAD_DB_ERROR
            try:
                server_conn = mysql.connector.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    charset="utf8mb4",
                    connection_timeout=2
                )
                cursor = server_conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4;")
                server_conn.commit()
                cursor.close()
                server_conn.close()

                # Reconnect and run schema
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    charset="utf8mb4",
                    connection_timeout=2
                )
                initialize_mysql_schema(conn)
                _mysql_available = True
                return conn, None
            except Exception as creation_err:
                _mysql_available = False
                return None, f"Could not create database '{DB_NAME}': {creation_err}"
        _mysql_available = False
        return None, str(err)


def initialize_mysql_schema(conn):
    """Seed MySQL database from database.sql file."""
    if not SQL_FILE_PATH.exists():
        return
    with open(SQL_FILE_PATH, "r", encoding="utf-8") as f:
        sql_commands = f.read()

    # Split into statements, skipping comments and delimiters
    cursor = conn.cursor()
    # Remove comment-only lines and empty blocks
    clean_sql = re.sub(r"--.*?\n", "\n", sql_commands)
    statements = clean_sql.split(";")
    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith("USE") and not stmt.upper().startswith("CREATE DATABASE"):
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"[MySQL Init Warning] {e}")
    conn.commit()
    cursor.close()


def get_sqlite_conn():
    """Connect to SQLite database and ensure schema is present."""
    existed = SQLITE_DB_PATH.exists()
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if not existed:
        initialize_sqlite_schema(conn)
    else:
        # Check if tables exist
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks';")
        if not cur.fetchone():
            initialize_sqlite_schema(conn)
        cur.close()
    return conn


def initialize_sqlite_schema(conn):
    """Create SQLite schema and seed sample data matching database.sql."""
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS artists (
        artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        artist_name TEXT NOT NULL UNIQUE,
        country TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS albums (
        album_id INTEGER PRIMARY KEY AUTOINCREMENT,
        album_name TEXT NOT NULL,
        release_date TEXT NOT NULL,
        artist_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (artist_id) REFERENCES artists(artist_id) ON DELETE CASCADE ON UPDATE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tracks (
        track_id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_name TEXT NOT NULL,
        album_id INTEGER NOT NULL,
        popularity INTEGER NOT NULL CHECK (popularity >= 0 AND popularity <= 100),
        duration_ms INTEGER NOT NULL CHECK (duration_ms > 0),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (album_id) REFERENCES albums(album_id) ON DELETE CASCADE ON UPDATE CASCADE
    );

    CREATE TABLE IF NOT EXISTS audio_features (
        track_id INTEGER PRIMARY KEY,
        danceability REAL NOT NULL CHECK (danceability >= 0.0 AND danceability <= 1.0),
        energy REAL NOT NULL CHECK (energy >= 0.0 AND energy <= 1.0),
        valence REAL NOT NULL CHECK (valence >= 0.0 AND valence <= 1.0),
        tempo REAL NOT NULL CHECK (tempo > 0.0),
        acousticness REAL NOT NULL CHECK (acousticness >= 0.0 AND acousticness <= 1.0),
        loudness REAL NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (track_id) REFERENCES tracks(track_id) ON DELETE CASCADE ON UPDATE CASCADE
    );

    INSERT OR IGNORE INTO artists (artist_id, artist_name, country) VALUES
    (1, 'The Weeknd', 'Canada'),
    (2, 'Taylor Swift', 'USA'),
    (3, 'Drake', 'Canada'),
    (4, 'Ed Sheeran', 'UK'),
    (5, 'Ariana Grande', 'USA'),
    (6, 'Coldplay', 'UK'),
    (7, 'Dua Lipa', 'UK'),
    (8, 'Billie Eilish', 'USA');

    INSERT OR IGNORE INTO albums (album_id, album_name, release_date, artist_id) VALUES
    (1, 'After Hours', '2020-03-20', 1),
    (2, 'Starboy', '2016-11-25', 1),
    (3, '1989', '2014-10-27', 2),
    (4, 'Midnights', '2022-10-21', 2),
    (5, 'Lover', '2019-08-23', 2),
    (6, 'Scorpion', '2018-06-29', 3),
    (7, 'Views', '2016-04-29', 3),
    (8, '÷ (Divide)', '2017-03-03', 4),
    (9, 'Positions', '2020-10-30', 5),
    (10, 'Music of the Spheres', '2021-10-15', 6),
    (11, 'Future Nostalgia', '2020-03-27', 7),
    (12, 'When We All Fall Asleep, Where Do We Go?', '2019-03-29', 8);

    INSERT OR IGNORE INTO tracks (track_id, track_name, album_id, popularity, duration_ms) VALUES
    (1, 'Blinding Lights', 1, 100, 200040),
    (2, 'Save Your Tears', 1, 92, 215626),
    (3, 'Starboy', 2, 94, 230453),
    (4, 'Die For You', 2, 88, 260253),
    (5, 'Blank Space', 3, 95, 231826),
    (6, 'Shake It Off', 3, 90, 219200),
    (7, 'Anti-Hero', 4, 94, 200690),
    (8, 'Lavender Haze', 4, 86, 202395),
    (9, 'Cruel Summer', 5, 96, 178426),
    (10, 'Lover', 5, 87, 221306),
    (11, 'God''s Plan', 6, 95, 198973),
    (12, 'In My Feelings', 6, 89, 217925),
    (13, 'One Dance', 7, 91, 173986),
    (14, 'Hotline Bling', 7, 84, 267066),
    (15, 'Shape of You', 8, 98, 233712),
    (16, 'Perfect', 8, 92, 263400),
    (17, 'Castle on the Hill', 8, 85, 261153),
    (18, 'Positions', 9, 93, 172324),
    (19, '34+35', 9, 87, 173710),
    (20, 'My Universe', 10, 89, 226342),
    (21, 'feelslikeimfalling', 10, 88, 220000),
    (22, 'Levitating', 11, 93, 203807),
    (23, 'Don''t Start Now', 11, 91, 183290),
    (24, 'bad guy', 12, 92, 194087),
    (25, 'bury a friend', 12, 84, 193246),
    (26, 'Someone Like You', 8, 89, 285000);

    INSERT OR IGNORE INTO audio_features (track_id, danceability, energy, valence, tempo, acousticness, loudness) VALUES
    (1, 0.514, 0.730, 0.334, 171.00, 0.001, -5.93),
    (2, 0.680, 0.826, 0.644, 118.05, 0.021, -5.48),
    (3, 0.679, 0.587, 0.486, 186.00, 0.141, -7.01),
    (4, 0.586, 0.525, 0.508, 133.62, 0.111, -7.16),
    (5, 0.760, 0.703, 0.570, 95.99, 0.103, -5.41),
    (6, 0.647, 0.785, 0.942, 160.01, 0.064, -5.41),
    (7, 0.637, 0.643, 0.533, 97.00, 0.204, -6.57),
    (8, 0.733, 0.436, 0.097, 96.98, 0.258, -10.48),
    (9, 0.552, 0.702, 0.564, 169.99, 0.117, -5.70),
    (10, 0.359, 0.543, 0.453, 68.53, 0.492, -7.58),
    (11, 0.754, 0.449, 0.357, 77.17, 0.033, -9.21),
    (12, 0.835, 0.626, 0.350, 91.03, 0.059, -5.83),
    (13, 0.792, 0.625, 0.551, 103.96, 0.007, -5.60),
    (14, 0.900, 0.623, 0.558, 134.98, 0.002, -8.19),
    (15, 0.825, 0.652, 0.931, 95.97, 0.581, -3.18),
    (16, 0.599, 0.448, 0.168, 95.05, 0.163, -6.31),
    (17, 0.461, 0.834, 0.471, 135.00, 0.023, -4.86),
    (18, 0.737, 0.802, 0.682, 144.01, 0.468, -4.77),
    (19, 0.798, 0.678, 0.737, 110.02, 0.237, -4.97),
    (20, 0.588, 0.701, 0.470, 105.01, 0.008, -6.39),
    (21, 0.620, 0.710, 0.590, 122.00, 0.080, -6.20),
    (22, 0.702, 0.825, 0.915, 103.01, 0.008, -3.78),
    (23, 0.794, 0.793, 0.679, 123.94, 0.012, -4.52),
    (24, 0.701, 0.425, 0.562, 135.12, 0.328, -10.96),
    (25, 0.905, 0.389, 0.196, 120.04, 0.040, -14.50),
    (26, 0.559, 0.430, 0.285, 135.10, 0.692, -7.05);
    """)
    conn.commit()


def check_and_get_connection(force_check=False):
    """Returns an active database connection and engine name ('mysql' or 'sqlite')."""
    global db_status
    
    # 1. Try MySQL
    mysql_conn, mysql_err = try_connect_mysql(force_check=force_check)
    if mysql_conn is not None:
        db_status["engine"] = "mysql"
        db_status["connected"] = True
        db_status["message"] = f"Connected to MySQL ({DB_HOST}:{DB_PORT}/{DB_NAME})"
        db_status["error"] = None
        return mysql_conn, "mysql"
    
    # 2. If MySQL fails, check fallback
    if ALLOW_SQLITE_FALLBACK:
        sqlite_conn = get_sqlite_conn()
        db_status["engine"] = "sqlite"
        db_status["connected"] = True
        db_status["message"] = f"Running on Local SQLite Mirror (MySQL offline: {mysql_err})"
        db_status["error"] = mysql_err
        return sqlite_conn, "sqlite"
    
    # If fallback disabled, report error
    db_status["engine"] = "mysql"
    db_status["connected"] = False
    db_status["message"] = f"MySQL Connection Failed: {mysql_err}"
    db_status["error"] = mysql_err
    raise ConnectionError(f"Cannot connect to MySQL database '{DB_NAME}' at {DB_HOST}:{DB_PORT}: {mysql_err}")


def execute_query(sql, params=(), fetch_one=False, fetch_all=True, commit=False):
    """
    Unified query runner. Works seamlessly across MySQL and SQLite.
    Automatically handles parameter placeholders (%s vs ?).
    Returns list of dicts or single dict.
    """
    conn, engine = check_and_get_connection()
    try:
        if engine == "mysql":
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, params)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                conn.close()
                return {"lastrowid": last_id, "rowcount": row_count}
            
            result = cursor.fetchone() if fetch_one else (cursor.fetchall() if fetch_all else None)
            cursor.close()
            conn.close()
            return result
        else: # sqlite
            # Adapt %s to ? for SQLite
            adapted_sql = sql.replace("%s", "?")
            # Replace MySQL specific functions if any
            adapted_sql = adapted_sql.replace("CONCAT(", "").replace("AUTO_INCREMENT", "AUTOINCREMENT")
            cursor = conn.cursor()
            cursor.execute(adapted_sql, params)
            if commit:
                conn.commit()
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
                cursor.close()
                conn.close()
                return {"lastrowid": last_id, "rowcount": row_count}

            rows = cursor.fetchone() if fetch_one else (cursor.fetchall() if fetch_all else None)
            cursor.close()
            conn.close()
            if rows is None:
                return None
            if fetch_one:
                return dict(rows)
            return [dict(r) for r in rows]
    except Exception as e:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        raise e


# ==============================================================================
# MODULE 1: CRUD OPERATIONS
# ==============================================================================

# --- ARTISTS ---
def get_all_artists(search=""):
    if search:
        return execute_query(
            "SELECT * FROM artists WHERE artist_name LIKE %s OR country LIKE %s ORDER BY artist_name ASC",
            (f"%{search}%", f"%{search}%")
        )
    return execute_query("SELECT * FROM artists ORDER BY artist_name ASC")

def get_artist_by_id(artist_id):
    return execute_query("SELECT * FROM artists WHERE artist_id = %s", (artist_id,), fetch_one=True)

def add_artist(artist_name, country):
    res = execute_query(
        "INSERT INTO artists (artist_name, country) VALUES (%s, %s)",
        (artist_name.strip(), country.strip()),
        commit=True
    )
    return res["lastrowid"]

def update_artist(artist_id, artist_name, country):
    res = execute_query(
        "UPDATE artists SET artist_name = %s, country = %s WHERE artist_id = %s",
        (artist_name.strip(), country.strip(), artist_id),
        commit=True
    )
    return res["rowcount"]

def delete_artist(artist_id):
    res = execute_query("DELETE FROM artists WHERE artist_id = %s", (artist_id,), commit=True)
    return res["rowcount"]


# --- ALBUMS ---
def get_all_albums(search=""):
    sql = """
        SELECT al.album_id, al.album_name, al.release_date, al.artist_id,
               ar.artist_name, ar.country,
               COUNT(t.track_id) AS track_count
        FROM albums al
        JOIN artists ar ON al.artist_id = ar.artist_id
        LEFT JOIN tracks t ON al.album_id = t.album_id
    """
    if search:
        sql += " WHERE al.album_name LIKE %s OR ar.artist_name LIKE %s "
        sql += " GROUP BY al.album_id, al.album_name, al.release_date, al.artist_id, ar.artist_name, ar.country ORDER BY al.release_date DESC"
        return execute_query(sql, (f"%{search}%", f"%{search}%"))
    sql += " GROUP BY al.album_id, al.album_name, al.release_date, al.artist_id, ar.artist_name, ar.country ORDER BY al.release_date DESC"
    return execute_query(sql)

def get_album_by_id(album_id):
    return execute_query("""
        SELECT al.*, ar.artist_name 
        FROM albums al 
        JOIN artists ar ON al.artist_id = ar.artist_id 
        WHERE al.album_id = %s
    """, (album_id,), fetch_one=True)

def add_album(album_name, release_date, artist_id):
    res = execute_query(
        "INSERT INTO albums (album_name, release_date, artist_id) VALUES (%s, %s, %s)",
        (album_name.strip(), release_date, artist_id),
        commit=True
    )
    return res["lastrowid"]

def update_album(album_id, album_name, release_date, artist_id):
    res = execute_query(
        "UPDATE albums SET album_name = %s, release_date = %s, artist_id = %s WHERE album_id = %s",
        (album_name.strip(), release_date, artist_id, album_id),
        commit=True
    )
    return res["rowcount"]

def delete_album(album_id):
    res = execute_query("DELETE FROM albums WHERE album_id = %s", (album_id,), commit=True)
    return res["rowcount"]


# --- TRACKS ---
def get_all_tracks(search="", order_by="t.popularity DESC"):
    allowed_order = {
        "popularity_desc": "t.popularity DESC",
        "popularity_asc": "t.popularity ASC",
        "track_name": "t.track_name ASC",
        "artist_name": "ar.artist_name ASC",
        "duration": "t.duration_ms DESC",
        "recent": "t.track_id DESC"
    }
    order_clause = allowed_order.get(order_by, "t.popularity DESC")
    
    sql = f"""
        SELECT t.track_id, t.track_name, t.album_id, t.popularity, t.duration_ms,
               al.album_name, ar.artist_id, ar.artist_name,
               CASE WHEN af.track_id IS NOT NULL THEN 1 ELSE 0 END as has_features
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        LEFT JOIN audio_features af ON t.track_id = af.track_id
    """
    if search:
        sql += " WHERE t.track_name LIKE %s OR ar.artist_name LIKE %s OR al.album_name LIKE %s "
        sql += f" ORDER BY {order_clause}"
        return execute_query(sql, (f"%{search}%", f"%{search}%", f"%{search}%"))
    sql += f" ORDER BY {order_clause}"
    return execute_query(sql)

def get_track_by_id(track_id):
    return execute_query("""
        SELECT t.*, al.album_name, ar.artist_name, ar.artist_id
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        WHERE t.track_id = %s
    """, (track_id,), fetch_one=True)

def add_track(track_name, album_id, popularity, duration_ms):
    res = execute_query(
        "INSERT INTO tracks (track_name, album_id, popularity, duration_ms) VALUES (%s, %s, %s, %s)",
        (track_name.strip(), album_id, int(popularity), int(duration_ms)),
        commit=True
    )
    return res["lastrowid"]

def update_track(track_id, track_name, album_id, popularity, duration_ms):
    res = execute_query(
        "UPDATE tracks SET track_name = %s, album_id = %s, popularity = %s, duration_ms = %s WHERE track_id = %s",
        (track_name.strip(), album_id, int(popularity), int(duration_ms), track_id),
        commit=True
    )
    return res["rowcount"]

def delete_track(track_id):
    res = execute_query("DELETE FROM tracks WHERE track_id = %s", (track_id,), commit=True)
    return res["rowcount"]


# --- AUDIO FEATURES ---
def get_all_audio_features(search=""):
    sql = """
        SELECT af.*, t.track_name, t.popularity, al.album_name, ar.artist_name
        FROM audio_features af
        JOIN tracks t ON af.track_id = t.track_id
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
    """
    if search:
        sql += " WHERE t.track_name LIKE %s OR ar.artist_name LIKE %s ORDER BY af.danceability DESC"
        return execute_query(sql, (f"%{search}%", f"%{search}%"))
    sql += " ORDER BY af.danceability DESC"
    return execute_query(sql)

def get_audio_feature_by_track(track_id):
    return execute_query("""
        SELECT af.*, t.track_name, ar.artist_name, al.album_name
        FROM audio_features af
        JOIN tracks t ON af.track_id = t.track_id
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        WHERE af.track_id = %s
    """, (track_id,), fetch_one=True)

def save_audio_features(track_id, danceability, energy, valence, tempo, acousticness, loudness):
    # Upsert query
    existing = execute_query("SELECT track_id FROM audio_features WHERE track_id = %s", (track_id,), fetch_one=True)
    if existing:
        res = execute_query("""
            UPDATE audio_features
            SET danceability = %s, energy = %s, valence = %s, tempo = %s, acousticness = %s, loudness = %s
            WHERE track_id = %s
        """, (float(danceability), float(energy), float(valence), float(tempo), float(acousticness), float(loudness), track_id), commit=True)
    else:
        res = execute_query("""
            INSERT INTO audio_features (track_id, danceability, energy, valence, tempo, acousticness, loudness)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (track_id, float(danceability), float(energy), float(valence), float(tempo), float(acousticness), float(loudness)), commit=True)
    return res


# ==============================================================================
# MODULE 2: SQL-BASED ANALYTICS
# ==============================================================================

def query_top_10_popular_tracks():
    sql = """
        SELECT t.track_id, t.track_name, ar.artist_name, al.album_name, t.popularity, t.duration_ms
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        ORDER BY t.popularity DESC
        LIMIT 10
    """
    return {
        "title": "Top 10 Popular Tracks",
        "description": "Extracts the top 10 most popular songs in the catalogue sorted in descending order of Spotify popularity score.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }

def query_average_popularity():
    sql = """
        SELECT COUNT(track_id) AS total_tracks,
               ROUND(AVG(popularity), 2) AS avg_popularity,
               MIN(popularity) AS min_popularity,
               MAX(popularity) AS max_popularity
        FROM tracks
    """
    return {
        "title": "Overall Track Popularity Aggregate Statistics",
        "description": "Calculates statistical summaries (Count, Average, Minimum, Maximum) across all registered tracks using SQL aggregate functions.",
        "sql": sql.strip(),
        "data": execute_query(sql, fetch_one=True)
    }

def query_artist_wise_popularity():
    sql = """
        SELECT ar.artist_id, ar.artist_name, ar.country,
               COUNT(t.track_id) AS track_count,
               ROUND(AVG(t.popularity), 2) AS avg_popularity,
               MAX(t.popularity) AS peak_popularity
        FROM artists ar
        JOIN albums al ON ar.artist_id = al.artist_id
        JOIN tracks t ON al.album_id = t.album_id
        GROUP BY ar.artist_id, ar.artist_name, ar.country
        ORDER BY avg_popularity DESC
    """
    return {
        "title": "Artist-Wise Average Popularity",
        "description": "Aggregates track performance grouped by artist to rank artist catalog popularity alongside track volume.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }

def query_album_wise_analysis():
    sql = """
        SELECT al.album_id, al.album_name, ar.artist_name, al.release_date,
               COUNT(t.track_id) AS track_count,
               ROUND(AVG(t.popularity), 2) AS avg_popularity,
               ROUND(AVG(t.duration_ms) / 1000, 1) AS avg_duration_seconds
        FROM albums al
        JOIN artists ar ON al.artist_id = ar.artist_id
        LEFT JOIN tracks t ON al.album_id = t.album_id
        GROUP BY al.album_id, al.album_name, ar.artist_name, al.release_date
        ORDER BY track_count DESC, avg_popularity DESC
    """
    return {
        "title": "Album-Wise Track Analysis",
        "description": "Evaluates album catalogue performance, track yield, and average runtime using relational JOIN and GROUP BY.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }

def query_tracks_popularity_above_70():
    sql = """
        SELECT t.track_name, ar.artist_name, al.album_name, t.popularity,
               ROUND(t.duration_ms / 60000.0, 2) AS duration_minutes
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        WHERE t.popularity >= 70
        ORDER BY t.popularity DESC
    """
    return {
        "title": "High-Popularity Tracks (Score >= 70)",
        "description": "Filters tracks meeting the blockbuster popularity threshold using SQL WHERE and ORDER BY clauses.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }

def query_most_popular_artist():
    sql = """
        SELECT ar.artist_name, ar.country,
               COUNT(t.track_id) AS total_tracks,
               ROUND(AVG(t.popularity), 2) AS avg_popularity
        FROM artists ar
        JOIN albums al ON ar.artist_id = al.artist_id
        JOIN tracks t ON al.album_id = t.album_id
        GROUP BY ar.artist_id, ar.artist_name, ar.country
        ORDER BY avg_popularity DESC
        LIMIT 1
    """
    return {
        "title": "Most Popular Artist Overall",
        "description": "Finds the single highest-rated music artist based on collective track popularity score.",
        "sql": sql.strip(),
        "data": execute_query(sql, fetch_one=True)
    }

def query_audio_features_comparison():
    sql = """
        SELECT ar.artist_name,
               ROUND(AVG(af.danceability), 3) AS avg_danceability,
               ROUND(AVG(af.energy), 3) AS avg_energy,
               ROUND(AVG(af.valence), 3) AS avg_valence,
               ROUND(AVG(af.acousticness), 3) AS avg_acousticness,
               ROUND(AVG(af.tempo), 1) AS avg_tempo
        FROM artists ar
        JOIN albums al ON ar.artist_id = al.artist_id
        JOIN tracks t ON al.album_id = t.album_id
        JOIN audio_features af ON t.track_id = af.track_id
        GROUP BY ar.artist_id, ar.artist_name
        ORDER BY avg_danceability DESC
    """
    return {
        "title": "Audio Feature Fingerprint Comparison by Artist",
        "description": "Compares multidimensional audio DSP metrics (danceability, energy, valence, acousticness, tempo) across artists.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }

def query_danceability_energy_analysis():
    sql = """
        SELECT t.track_name, ar.artist_name,
               af.danceability, af.energy,
               ROUND((af.danceability + af.energy) / 2.0, 3) AS party_index,
               af.tempo, af.loudness
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        JOIN audio_features af ON t.track_id = af.track_id
        ORDER BY party_index DESC
    """
    return {
        "title": "Danceability & Energy Analysis (Party Index)",
        "description": "Computes composite party & danceability index using arithmetic expressions across joined DSP feature tables.",
        "sql": sql.strip(),
        "data": execute_query(sql)
    }


# ==============================================================================
# MODULE 3: DASHBOARD STATS & REPORT GENERATION
# ==============================================================================

def get_dashboard_summary():
    """Returns 4 real KPI cards computed directly from database records."""
    counts = execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM tracks) AS total_tracks,
            (SELECT COUNT(*) FROM artists) AS total_artists,
            (SELECT COUNT(*) FROM albums) AS total_albums,
            (SELECT ROUND(AVG(popularity), 1) FROM tracks) AS avg_popularity
    """, fetch_one=True)
    
    if not counts:
        return {"total_tracks": 0, "total_artists": 0, "total_albums": 0, "avg_popularity": 0.0}
    return {
        "total_tracks": counts.get("total_tracks") or 0,
        "total_artists": counts.get("total_artists") or 0,
        "total_albums": counts.get("total_albums") or 0,
        "avg_popularity": float(counts.get("avg_popularity") or 0.0)
    }

def get_all_tracks_joined():
    """Returns all tracks joined with albums, artists, and audio_features for Pandas analytics."""
    return execute_query("""
        SELECT t.track_id, t.track_name, ar.artist_name, ar.country,
               al.album_name, al.release_date, t.popularity, t.duration_ms,
               ROUND(t.duration_ms / 1000.0, 1) AS duration_seconds,
               af.danceability, af.energy, af.valence, af.tempo, af.acousticness, af.loudness
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        LEFT JOIN audio_features af ON t.track_id = af.track_id
        ORDER BY t.popularity DESC
    """)

def get_dashboard_chart_data():
    """Returns real dataset for the Overview line chart and Features doughnut chart with dynamic filters."""
    # Top 12 tracks for popularity curve
    tracks = execute_query("""
        SELECT t.track_name, t.popularity, ar.artist_name
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        ORDER BY t.popularity DESC
        LIMIT 14
    """)

    # High popularity tracks (>= 90)
    high_pop_tracks = execute_query("""
        SELECT t.track_name, t.popularity, ar.artist_name
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        WHERE t.popularity >= 90
        ORDER BY t.popularity DESC
        LIMIT 14
    """)

    # High danceability tracks (danceability >= 0.70)
    dance_tracks = execute_query("""
        SELECT t.track_name, t.popularity, af.danceability, ar.artist_name
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        JOIN audio_features af ON t.track_id = af.track_id
        WHERE af.danceability >= 0.70
        ORDER BY af.danceability DESC
        LIMIT 14
    """)

    # High energy tracks (energy >= 0.70)
    energy_tracks = execute_query("""
        SELECT t.track_name, t.popularity, af.energy, ar.artist_name
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        JOIN audio_features af ON t.track_id = af.track_id
        WHERE af.energy >= 0.70
        ORDER BY af.energy DESC
        LIMIT 14
    """)

    # Acoustic tracks (acousticness >= 0.15)
    acoustic_tracks = execute_query("""
        SELECT t.track_name, t.popularity, af.acousticness, ar.artist_name
        FROM tracks t
        JOIN albums al ON t.album_id = al.album_id
        JOIN artists ar ON al.artist_id = ar.artist_id
        JOIN audio_features af ON t.track_id = af.track_id
        WHERE af.acousticness >= 0.15
        ORDER BY af.acousticness DESC
        LIMIT 14
    """)
    
    # Average audio features across whole database
    features = execute_query("""
        SELECT 
            ROUND(AVG(danceability) * 100, 1) AS avg_danceability,
            ROUND(AVG(energy) * 100, 1) AS avg_energy,
            ROUND(AVG(valence) * 100, 1) AS avg_valence,
            ROUND(AVG(acousticness) * 100, 1) AS avg_acousticness
        FROM audio_features
    """, fetch_one=True)
    
    return {
        "line_labels": [t["track_name"] for t in tracks] if tracks else [],
        "line_values": [t["popularity"] for t in tracks] if tracks else [],
        "filters": {
            "all": {
                "labels": [t["track_name"] for t in tracks] if tracks else [],
                "values": [t["popularity"] for t in tracks] if tracks else [],
                "title": "All Top Tracks (Popularity)"
            },
            "high_pop": {
                "labels": [t["track_name"] for t in high_pop_tracks] if high_pop_tracks else [],
                "values": [t["popularity"] for t in high_pop_tracks] if high_pop_tracks else [],
                "title": "Blockbuster Hits (Score ≥ 90)"
            },
            "dance": {
                "labels": [t["track_name"] for t in dance_tracks] if dance_tracks else [],
                "values": [t["popularity"] for t in dance_tracks] if dance_tracks else [],
                "title": "High Danceability Tracks (Score ≥ 0.70)"
            },
            "energy": {
                "labels": [t["track_name"] for t in energy_tracks] if energy_tracks else [],
                "values": [t["popularity"] for t in energy_tracks] if energy_tracks else [],
                "title": "High Energy Tracks (Score ≥ 0.70)"
            },
            "acoustic": {
                "labels": [t["track_name"] for t in acoustic_tracks] if acoustic_tracks else [],
                "values": [t["popularity"] for t in acoustic_tracks] if acoustic_tracks else [],
                "title": "Acoustic Tracks (Acousticness ≥ 0.15)"
            }
        },
        "feature_labels": ["Danceability", "Energy", "Valence", "Acousticness"],
        "feature_values": [
            float(features["avg_danceability"]) if features and features["avg_danceability"] else 70.0,
            float(features["avg_energy"]) if features and features["avg_energy"] else 68.0,
            float(features["avg_valence"]) if features and features["avg_valence"] else 52.0,
            float(features["avg_acousticness"]) if features and features["avg_acousticness"] else 15.0
        ]
    }
