import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute("ALTER TABLE songrequest_queue DROP COLUMN queue;")
    cursor.execute("ALTER TABLE songrequest_queue DROP COLUMN playing;")
    cursor.execute("ALTER TABLE songrequest_queue DROP COLUMN current_song_time;")
    cursor.execute("ALTER TABLE songrequest_queue ADD COLUMN date_resumed timestamp with time zone;")
    cursor.execute("ALTER TABLE songrequest_queue ADD COLUMN played_for REAL NOT NULL DEFAULT 0;")
