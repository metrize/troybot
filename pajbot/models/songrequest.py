import logging

from sqlalchemy import Column, INT, TEXT, BOOLEAN, REAL
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utc import UtcDateTime
from sqlalchemy import func

from pajbot import utils
from pajbot.managers.db import Base
from pajbot.managers.db import DBManager
from pajbot.streamhelper import StreamHelper

log = logging.getLogger("pajbot")


class SongrequestQueue(Base):
    __tablename__ = "songrequest_queue"

    id = Column(INT, primary_key=True)
    queue = Column(INT, nullable=False)
    video_id = Column(TEXT, ForeignKey("songrequest_song_info.video_id", ondelete="CASCADE"), nullable=False)
    date_added = Column(UtcDateTime(), nullable=False)
    skip_after = Column(INT, nullable=True)  # skipped after
    playing = Column(BOOLEAN, nullable=True)
    requested_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    current_song_time = Column(REAL, nullable=False, default=0)
    song_info = relationship("SongRequestSongInfo", foreign_keys=[video_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])

    def __init__(self, **options):
        super().__init__(**options)
        if self.skip_after and self.skip_after < 0:
            # Make sure skip_after cannot be a negative number
            self.skip_after = None

    def jsonify(self):
        return {
            "id": self.id,
            "queue": self.queue,
            "video_id": self.video_id,
            "date_added": self.date_added,
            "skip_after": self.skip_after,
            "playing": self.playing,
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
        }

    def webjsonify(self):
        return {
            "video_id": self.video_id,
            "video_title": self.song_info.title,
            "video_length": self.duration,
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
            "database_id": self.id,
            "current_song_time": self.current_song_time,
            "link": f"http://www.youtube.com/watch?v={self.video_id}",
        }

    def playing_in(self, db_session):
        all_songs_before_current = (
            db_session.query(SongrequestQueue)
            .filter(SongrequestQueue.queue < self.queue)
            .filter(SongrequestQueue.requested_by_id is not None)
            .all()
        )
        time = 0
        for song in all_songs_before_current:
            if not song.playing:
                time += song.skip_after if song.skip_after else song.song_info.duration
            else:
                time += song.time_left
        return time

    @hybrid_property
    def time_left(self):
        if self.playing:
            return self.duration - self.current_song_time
        return self.duration

    @hybrid_property
    def duration(self):
        return self.skip_after if self.skip_after else self.song_info.duration

    def _remove(self, db_session):
        db_session.delete(self)

    def _to_histroy(self, db_session, skipped_by_id=None):
        stream_id = StreamHelper.get_current_stream_id()
        if not stream_id:
            self._remove(db_session)
            return None
        history = SongrequestHistory._create(
            db_session,
            stream_id,
            self.video_id,
            self.requested_by.id if self.requested_by else None,
            skipped_by_id,
            self.skip_after,
        )
        self._remove(db_session)
        return history

    def _move_song(self, db_session, queue_id):
        if self.queue > queue_id:
            SongrequestQueue._shift_songs(db_session, lower_bound=queue_id, upper_bound=self.queue, shift_by=+1)
        else:
            SongrequestQueue._shift_songs(db_session, lower_bound=self.queue, upper_bound=queue_id, shift_by=-1)
        self.queue = queue_id

    @hybrid_property
    def link(self):
        return f"youtu.be/{self.video_id}"

    @staticmethod
    def _from_id(db_session, id):
        return db_session.query(SongrequestQueue).filter_by(id=id).one_or_none()

    @staticmethod
    def _get_next_queue(db_session):
        current = db_session.query(func.max(SongrequestQueue.queue).label("max")).one().max
        return (current if current else 0) + 1

    @staticmethod
    def _create(db_session, video_id, skip_after, requested_by_id, queue=None):
        if not queue:
            if requested_by_id:
                queue_min_not_playing_backup = list(
                    db_session.query(SongrequestQueue)
                    .filter_by(playing=False)
                    .filter_by(requested_by_id=None)
                    .values(func.min(SongrequestQueue.queue))
                )[0][0]
                if queue_min_not_playing_backup:
                    return SongrequestQueue._insert_song(
                        db_session, video_id, skip_after, requested_by_id, queue_min_not_playing_backup
                    )
        if not queue:
            queue = SongrequestQueue._get_next_queue(db_session)
        songrequestqueue = SongrequestQueue(
            queue=queue,
            video_id=video_id,
            date_added=utils.now(),
            skip_after=skip_after,
            playing=False,
            requested_by_id=requested_by_id,
        )
        db_session.add(songrequestqueue)
        return songrequestqueue

    @staticmethod
    def _get_current_song(db_session):
        return db_session.query(SongrequestQueue).filter_by(playing=True).one_or_none()

    @staticmethod
    def _get_next_song(db_session):
        return db_session.query(SongrequestQueue).filter_by(queue=1).one_or_none()

    @staticmethod
    def _clear_backup_songs(db_session):
        returnExe = db_session.execute(SongrequestQueue.__table__.delete().where(not SongrequestQueue.requested_by))
        return returnExe

    @staticmethod
    def _update_queue():
        with DBManager.create_session_scope() as db_session:
            queued_songs = (
                db_session.query(SongrequestQueue).filter_by(playing=False).order_by(SongrequestQueue.queue).all()
            )
            pos = 1
            for song in queued_songs:
                song.queue = pos
                pos += 1

    @staticmethod
    def _load_backup_songs(db_session, songs, youtube, settings):
        for song in songs:
            song_info = SongRequestSongInfo._create_or_get(db_session, song, youtube)
            if song_info:
                SongrequestQueue._create(db_session, song, None, None)

    @staticmethod
    def _shift_songs(db_session, lower_bound=None, upper_bound=None, shift_by=1):
        if not lower_bound:
            lower_bound = 1
        if not upper_bound:
            upper_bound = SongrequestQueue._get_next_queue(db_session) - 1
        queued_songs = (
            db_session.query(SongrequestQueue)
            .order_by(SongrequestQueue.queue)
            .filter(SongrequestQueue.queue >= lower_bound)
            .filter(SongrequestQueue.queue <= upper_bound)
            .all()
        )
        for song in queued_songs:
            song.queue += shift_by

    @staticmethod
    def _insert_song(db_session, video_id, skip_after, requested_by, queue_id):
        SongrequestQueue._shift_songs(db_session, lower_bound=queue_id)
        return SongrequestQueue._create(db_session, video_id, skip_after, requested_by, queue_id)

    @staticmethod
    def _get_playlist(db_session, limit=None):
        queued_songs = db_session.query(SongrequestQueue).filter_by(playing=False).order_by(SongrequestQueue.queue)
        if limit:
            queued_songs = queued_songs.limit(limit)
        queued_songs = queued_songs.all()
        songs = []
        for song in queued_songs:
            songs.append(
                {
                    "video_id": song.video_id,
                    "video_title": song.song_info.title,
                    "video_length": song.duration,
                    "requested_by": song.requested_by.username_raw if song.requested_by_id else None,
                    "database_id": song.id,
                }
            )
        return songs


class SongrequestHistory(Base):
    __tablename__ = "songrequest_history"

    id = Column(INT, primary_key=True)
    stream_id = Column(INT, nullable=False)
    video_id = Column(TEXT, ForeignKey("songrequest_song_info.video_id"), nullable=False)
    date_finished = Column(UtcDateTime(), nullable=False)
    requested_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    skipped_by_id = Column(INT, ForeignKey("user.id"), nullable=True)
    skip_after = Column(INT, nullable=True)
    song_info = relationship("SongRequestSongInfo", foreign_keys=[video_id])
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    skipped_by = relationship("User", foreign_keys=[skipped_by_id])

    def __init__(self, **options):
        super().__init__(**options)

    def jsonify(self):
        return {
            "id": self.id,
            "stream_id": self.stream_id,
            "video_id": self.video_id,
            "date_finished": self.date_finished,
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
            "skipped_by": self.skipped_by.username_raw if self.skipped_by_id else None,
            "skip_after": self.skip_after,
        }

    def webjsonify(self):
        return {
            "video_id": self.video_id,
            "stream_id": self.stream_id,
            "video_title": self.song_info.title,
            "video_length": self.duration,
            "requested_by": self.requested_by.username_raw if self.requested_by_id else None,
            "date_finished": self.date_finished,
            "database_id": self.id,
            "link": f"http://www.youtube.com/watch?v={self.video_id}",
        }

    @hybrid_property
    def link(self):
        return f"youtu.be/{self.video_id}"

    @hybrid_property
    def duration(self):
        return self.skip_after if self.skip_after else self.song_info.duration

    def _remove(self, db_session):
        db_session.delete(self)

    def requeue(self, db_session, requested_by):
        return SongrequestQueue._create(db_session, self.video_id, self.skip_after, requested_by)

    @staticmethod
    def _create(db_session, stream_id, video_id, requested_by_id, skipped_by_id, skip_after):
        songrequesthistory = SongrequestHistory(
            stream_id=stream_id,
            video_id=video_id,
            date_finished=utils.now(),
            requested_by_id=requested_by_id,
            skipped_by_id=skipped_by_id,
            skip_after=skip_after,
        )
        db_session.add(songrequesthistory)
        return songrequesthistory

    @staticmethod
    def _get_previous(db_session, position):
        songs = db_session.query(SongrequestHistory).order_by(SongrequestHistory.id.desc()).limit(position + 1).all()
        if len(songs) == position + 1:
            return songs[position]

    @staticmethod
    def _insert_previous(db_session, requested_by_id, position=0):
        previous = SongrequestHistory._get_previous(db_session, position)
        if not previous:
            return False
        return SongrequestQueue._insert_song(db_session, previous.video_id, previous.skip_after, requested_by_id, 1)

    @staticmethod
    def _get_list(db_session, size):
        return db_session.query(SongrequestHistory).order_by(SongrequestHistory.id.desc()).limit(size).all()

    @staticmethod
    def _from_id(db_session, id):
        return db_session.query(SongrequestHistory).filter_by(id=id).one_or_none()

    @staticmethod
    def _get_history(db_session, limit):
        played_songs = (
            db_session.query(SongrequestHistory)
            .filter(SongrequestHistory.song_info.has(banned=False))
            .order_by(SongrequestHistory.id.desc())
            .limit(limit)
            .all()
        )
        songs = []
        for song in played_songs:
            songs.append(
                {
                    "video_id": song.video_id,
                    "video_title": song.song_info.title,
                    "video_length": song.duration,
                    "requested_by": song.requested_by.username_raw if song.requested_by_id else None,
                    "database_id": song.id,
                }
            )
        return songs


class SongRequestSongInfo(Base):
    __tablename__ = "songrequest_song_info"

    video_id = Column(TEXT, primary_key=True, autoincrement=False)
    title = Column(TEXT, nullable=False)
    duration = Column(INT, nullable=False)
    default_thumbnail = Column(TEXT, nullable=False)
    banned = Column(BOOLEAN, default=False)
    favourite = Column(BOOLEAN, default=False)

    def jsonify(self):
        return {
            "video_id": self.video_id,
            "title": self.title,
            "duration": self.duration,
            "default_thumbnail": self.default_thumbnail,
            "banned": self.banned,
            "favourite": self.favourite,
        }

    @staticmethod
    def _create(db_session, video_id, title, duration, default_thumbnail):
        songinfo = SongRequestSongInfo(
            video_id=video_id, title=title, duration=duration, default_thumbnail=default_thumbnail
        )
        db_session.add(songinfo)
        return songinfo

    @staticmethod
    def _create_or_get(db_session, video_id, youtube):
        song_info = db_session.query(SongRequestSongInfo).filter_by(video_id=video_id).one_or_none()
        if song_info:
            return song_info

        import isodate
        from apiclient.errors import HttpError

        if youtube is None:
            log.warning("youtube was not initialized")
            return False

        try:
            video_response = youtube.videos().list(id=str(video_id), part="snippet,contentDetails").execute()
        except HttpError:
            return False
        except:
            return False

        if not video_response.get("items", []):
            log.warning(f"Got no valid responses for {video_id}")
            return False

        video = video_response["items"][0]

        title = video["snippet"]["title"]
        duration = int(isodate.parse_duration(video["contentDetails"]["duration"]).total_seconds())
        default_thumbnail = video["snippet"]["thumbnails"]["default"]["url"]

        return SongRequestSongInfo._create(db_session, video_id, title, duration, default_thumbnail)
