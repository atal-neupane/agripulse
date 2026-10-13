
import os
import psycopg
from dotenv import load_dotenv

#load the environment variables from the .env file  
load_dotenv()

connection_string = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "agripulse"),
    "user": os.getenv("DB_USER", "agripulse_app"),
    "password": os.getenv("DB_PASSWORD"),
}

with psycopg.connect(**connection_string) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT current_database(), current_user, version();"
        )
        database, user, version = cur.fetchone()

        print(f"Database: {database}")
        print(f"User: {user}")
        print(f"PostgreSQL: {version.split(',')[0]}")
        print("Connection successful!")
