import logging

from flask import render_template

from pajbot.managers.db import DBManager
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager
from pajbot.models.stream import StreamManager
from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory

log = logging.getLogger(__name__)


def init(app):
    @app.route("/songrequest")
    def songrequest():
        with DBManager.create_session_scope() as db_session:
            playing_in = 0
            track_number = 1
            songs_queue = []
            queue_ids = SongRequestQueueManager.get_next_songs(50)
            current_song = SongrequestQueue._get_current_song(db_session)
            queue = ([current_song] if current_song else []) + SongrequestQueue.sort(queue_ids, SongrequestQueue._from_list_id(db_session, queue_ids))
            for song in queue:
                if song.song_info is None:
                    continue
                jsonify = song.webjsonify()
                m, s = divmod(playing_in, 60)
                m = int(m)
                s = int(s)
                jsonify["playing_in"] = f"{m:02d}:{s:02d}" if playing_in != 0 else ("Currently playing" if song == current_song else "Song Request Closed")
                m, s = divmod(jsonify["video_length"], 60)
                m = int(m)
                s = int(s)
                jsonify["video_length"] = f"{m:02d}:{s:02d}"
                jsonify["track_number"] = track_number
                playing_in += song.time_left
                track_number += 1
                songs_queue.append(jsonify)

            history = (
                db_session.query(SongrequestHistory)
                .filter(SongrequestHistory.song_info.has(banned=False))
                .order_by(SongrequestHistory.id.desc())
                .limit(50)
                .all()
            )
            track_number = 1
            songs_history = []
            for song in history:
                if song.song_info.banned:
                    continue
                jsonify = song.webjsonify()
                jsonify["track_number"] = track_number
                m, s = divmod(jsonify["video_length"], 60)
                m = int(m)
                s = int(s)
                jsonify["video_length"] = f"{m:02d}:{s:02d}"
                track_number += 1
                songs_history.append(jsonify)

            return render_template(
                "songrequest.html", songs_queue=songs_queue, songs_history=songs_history, live=StreamManager.online
            )
