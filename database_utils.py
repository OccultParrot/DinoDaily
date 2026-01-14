import os
import random
from datetime import time
from zoneinfo import ZoneInfo
import psycopg2
import dotenv

from rich import print as print

dotenv.load()


def get_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def get_servers():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM servers;")
            rows = cur.fetchall()

            return [{
                "guild_id": guild_id,
                "channel_id": channel_id,
                "scheduled_time": scheduled_time,
                "time_zone": time_zone,
                "added_at": added_at,
                "edited_at": edited_at
            } for
                guild_id,
                channel_id,
                scheduled_time,
                time_zone,
                added_at,
                edited_at in rows]


def add_server(guild_id: int, scheduled_time: time, time_zone: ZoneInfo, channel_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            insert_query = """
            INSERT INTO servers (id, channel_id, scheduled_time, time_zone)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """
            try:
                cur.execute(insert_query, (guild_id, channel_id, scheduled_time, str(time_zone)))
                conn.commit()
            except Exception as e:
                print(e)


def edit_server(guild_id: int):
    pass


def remove_server(guild_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM servers WHERE id = %s", (guild_id,))
            conn.commit()


def get_random_dino():
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT * FROM dino_refs;")
                rows = cur.fetchall()
                dino_raw = random.choice(rows)
                print(dino_raw)
                return {
                    "id": dino_raw[0],
                    "name": dino_raw[1],
                    "href": dino_raw[2],
                    "page_name": dino_raw[3],
                    "scraped_date": dino_raw[4],
                }
            except Exception as e:
                print(e)
