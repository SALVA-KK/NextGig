import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "nextgig_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432")
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT pid, usename, application_name, client_addr FROM pg_stat_activity WHERE datname='test_nextgig_db';")
    rows = cur.fetchall()
    print(f"Active sessions on test_nextgig_db ({len(rows)}): {rows}")
    for row in rows:
        cur.execute(f"SELECT pg_terminate_backend({row[0]});")
    cur.execute("DROP DATABASE IF EXISTS test_nextgig_db;")
    print("Dropped database test_nextgig_db successfully")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
