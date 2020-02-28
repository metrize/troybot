import logging

log = logging.getLogger("pajbot")


def up(cursor, bot):
    cursor.execute(
        """
    CREATE TABLE songrequest_history
    (
    id integer NOT NULL GENERATED BY DEFAULT AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    video_id text COLLATE pg_catalog."default" NOT NULL,
    date_finished timestamp with time zone NOT NULL,
    requested_by text COLLATE pg_catalog."default",
    skipped_by text COLLATE pg_catalog."default",
    stream_id integer,
    skip_after integer,
    CONSTRAINT songrequest_history_pkey PRIMARY KEY (id)
    )"""
    )
    cursor.execute(
        """
    CREATE TABLE songrequest_queue
    (
    id integer NOT NULL GENERATED BY DEFAULT AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1 ),
    queue integer NOT NULL,
    video_id text COLLATE pg_catalog."default" NOT NULL,
    date_added timestamp with time zone NOT NULL DEFAULT now(),
    skip_after integer,
    playing boolean DEFAULT false,
    requested_by text COLLATE pg_catalog."default",
    current_song_time real NOT NULL DEFAULT 0,
    CONSTRAINT songrequest_queue_pkey PRIMARY KEY (id)
    )"""
    )
    cursor.execute(
        """
    CREATE TABLE songrequest_song_info
    (
    video_id text COLLATE pg_catalog."default" NOT NULL,
    title text COLLATE pg_catalog."default" NOT NULL,
    duration integer NOT NULL,
    default_thumbnail text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT songrequest_song_info_pkey PRIMARY KEY (video_id)
    )
    """
    )
    cursor.execute("DROP TABLE IF EXISTS pleblist_song")
    cursor.execute("DROP TABLE IF EXISTS pleblist_song_info")