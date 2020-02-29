import logging
import random

from pajbot.managers.db import DBManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.songrequest_queue_manager import SongRequestQueueManager

from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory, SongRequestSongInfo
from pajbot.models.user import User

import pajbot.utils as utils

log = logging.getLogger("pajbot")

WIDGET_ID = 4


class SongrequestManager:
    def __init__(self, bot):
        self.bot = bot

        self.current_song_id = None
        self.youtube = None
        self.settings = None

        self.previously_playing_spotify = False
        self.is_video_showing = False
        self.previous_queue = 0

        self.current_song_schedule = None
        self.schedule_job_id = None

        self.module_state = {
            "paused": False,
            "video_showing": False,
            "enabled": False,
            "requests_open": False,
            "use_backup_playlist": False
        }
        self.volume = 0

    def enable(self, settings, youtube):
        self.current_song_id = None
        self.youtube = youtube
        self.settings = settings

        self.previously_playing_spotify = False
        self.is_video_showing = False
        self.previous_queue = 0

        self.current_song_schedule = None
        self.schedule_job_id = None

        self.module_state["enabled"] = True
        self.volume = 0

    @property
    def volume_val(self):
        return int(self.volume * (100 / int(self.settings["volume_multiplier"])))

    def to_true_volume(self, multiplied_volume):
        return int(multiplied_volume * int(self.settings["volume_multiplier"]) / 100)

    def disable(self):
        self.module_state["enabled"] = False
        self.module_state["paused"] = False
        self.module_state["requests_open"] = False
        self.module_state["video_showing"] = False
        self.previously_playing_spotify = False
        self.is_video_showing = False
        self.settings = None
        self.youtube = None
        self.current_song_id = None

    def open_module_function(self):
        if not self.module_state["enabled"]:
            return False
        if not self.module_state["requests_open"]:
            self.module_state["requests_open"] = True
            self.module_state["paused"] = False
            if not self.current_song_id:
                self.load_song()
            return True
        return False

    def close_module_function(self):
        if not self.module_state["enabled"]:
            return False
        if self.module_state["requests_open"]:
            self.module_state["requests_open"] = False
            return True
        return False

    def skip_function(self, skipped_by):
        with DBManager.create_session_scope() as db_session:
            skipped_by = User.find_by_user_input(db_session, skipped_by)
            if not skipped_by:
                return
            skipped_by_id = skipped_by.id
        if not self.module_state["enabled"] and self.current_song_id:
            return False
        self.load_song(skipped_by_id)
        self.remove_schedule()
        return True

    def remove_schedule(self):
        try:
            if self.current_song_schedule is not None:
                self.current_song_schedule.remove()
        except:
            pass
        self.current_song_schedule = None
        self.schedule_job_id = None

    def previous_function(self, requested_by):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            requested_by = User.find_by_user_input(db_session, requested_by)
            if not requested_by:
                return
            requested_by_id = requested_by.id
            SongrequestHistory._insert_previous(db_session, requested_by_id, self.previous_queue)
            db_session.commit()
        self.previous_queue += 1
        self.remove_schedule()
        self.load_song(requested_by_id)
        return True

    def pause_function(self):
        if not self.module_state["enabled"] or not self.current_song_id:
            return False
        if not self.module_state["paused"]:
            self.module_state["paused"] = True
            self._pause()
            self.remove_schedule()
            if self.current_song_id:
                return True

            with DBManager.create_session_scope() as db_session:
                song = SongrequestQueue._from_id(db_session, self.current_song_id)
                song.date_resumed = None
                song.played_for = (utils.now() - song.date_resumed).total_seconds()
            return True

        return False

    def resume_function(self):
        if not self.module_state["enabled"] or not self.current_song_id:
            return False
        if self.module_state["paused"]:
            self.module_state["paused"] = False
            self._resume()
            with DBManager.create_session_scope() as db_session:
                song = SongrequestQueue._from_id(db_session, self.current_song_id)
                song.date_resumed = utils.now()
                self.schedule_job_id = random.randint(1, 100000)
                self.current_song_schedule = ScheduleManager.execute_delayed(song.time_left + 10, self.load_song_schedule, args=[self.schedule_job_id])

            return True
        return False

    def seek_function(self, _time): #TODO
        if not self.module_state["enabled"]:
            return False
        if self.current_song_id:
            with DBManager.create_session_scope() as db_session:
                current_song = SongrequestQueue._from_id(db_session, self.current_song_id)
                current_song.current_song_time = _time
                self._seek(_time)
            return True
        return False

    def volume_function(self, volume):
        if not self.module_state["enabled"]:
            return False
        try:
            self.volume = self.to_true_volume(volume)
        except ValueError:
            return False

        self._volume()
        return True

    def play_function(self, database_id, skipped_by):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            skipped_by = User.find_by_user_input(db_session, skipped_by)
            if not skipped_by:
                return
            skipped_by_id = skipped_by.id
            song = SongrequestQueue._from_id(db_session, database_id)
            song._move_song(db_session, 1)
            db_session.commit()
        self.load_song(skipped_by_id)
        return True

    def move_function(self, database_id, to_id):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            song = SongrequestQueue._from_id(db_session, database_id)
            song._move_song(db_session, to_id)
            db_session.commit()
        self._playlist()
        return True

    def request_function(self, video_id, requested_by, queue=None):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            requested_by = User.find_by_user_input(db_session, requested_by)
            if not requested_by:
                return False
            requested_by_id = requested_by.id
            song_info = SongRequestSongInfo._create_or_get(db_session, video_id, self.youtube)
            if not song_info:
                log.error("There was an error!")
                return False
            skip_after = (
                self.settings["max_song_length"] if song_info.duration > self.settings["max_song_length"] else None
            )
            song = SongrequestQueue._create(db_session, video_id, skip_after, requested_by_id)
            if queue:
                song._move_song(queue)
            db_session.commit()
            current_song = SongrequestQueue._from_id(db_session, self.current_song_id)
            if not current_song or not current_song.requested_by:
                self.load_song()
        return True

    def requeue_function(self, database_id, requested_by):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            requested_by = User.find_by_user_input(db_session, requested_by)
            if not requested_by:
                return False
            requested_by_id = requested_by.id
            SongrequestHistory._from_id(db_session, database_id).requeue(db_session, requested_by_id)
            db_session.commit()
            current_song = SongrequestQueue._from_id(db_session, self.current_song_id)
            if not current_song or not current_song.requested_by:
                self.load_song()
        self._playlist()
        return True

    def show_function(self):
        if not self.module_state["enabled"]:
            return False
        if not self.module_state["video_showing"]:
            self.module_state["video_showing"] = True
            if not self.module_state["paused"]:
                self._show()
            return True
        return False

    def hide_function(self):
        if not self.module_state["enabled"]:
            return False
        if self.module_state["video_showing"]:
            self.module_state["video_showing"] = False
            self._hide()
            return True
        return False

    def remove_function(self, database_id):
        if not self.module_state["enabled"]:
            return False
        with DBManager.create_session_scope() as db_session:
            song = SongrequestQueue._from_id(db_session, database_id)
            song._remove(db_session)
            db_session.commit()
        self._playlist()
        return True

    def load_song_schedule(self, *args):
        if not self.current_song_schedule or self.schedule_job_id != args[0]:
            return
        self.load_song()

    def load_song(self, skipped_by_id=None):
        if not self.module_state["enabled"]:
            return False
        if self.current_song_id:
            with DBManager.create_session_scope() as db_session:
                current_song = SongrequestQueue._from_id(db_session, self.current_song_id)
                if current_song:
                    if current_song.current_song_time > 5:
                        self.previous_queue = 0
                        histroy = current_song._to_histroy(db_session, skipped_by_id)
                        if not histroy:
                            log.info("History not added because stream is offline!")
                    else:
                        current_song._remove(db_session)
                self._stop_video()
                self._hide()
                db_session.commit()
            self._playlist_history()

        self.current_song_id = None
        self.schedule_job_id = None
        self.module_state["paused"] = False
        self.remove_schedule()

        if not self.module_state["requests_open"]:
            return False

        with DBManager.create_session_scope() as db_session:
            current_song = SongrequestQueue._get_current_song(db_session)
            if not current_song:
                current_song = SongrequestQueue._pop_next_song(db_session)
            if current_song:
                SongRequestQueueManager.update_song_playing_id(current_song.id)
                self.current_song_id = current_song.id
                self._play(
                    current_song.video_id,
                    current_song.song_info.title,
                    current_song.requested_by.username_raw if current_song.requested_by else "Backup list",
                )
                current_song.date_resumed = utils.now()
                self.schedule_job_id = random.randint(1, 100000)
                self.current_song_schedule = ScheduleManager.execute_delayed(current_song.time_left + 10, self.load_song_schedule, args=[self.schedule_job_id])
                if self.settings["use_spotify"]:
                    is_playing, song_name, artistsArr = self.bot.spotify_api.state(self.bot.spotify_token_manager)
                    if is_playing:
                        self.bot.spotify_api.pause(self.bot.spotify_token_manager)
                        self.previously_playing_spotify = True
                if not current_song.requested_by_id:
                    SongrequestQueue._create(
                        db_session,
                        current_song.video_id,
                        current_song.skip_after,
                        None,
                        backup=True
                    )
                db_session.commit()
                self._playlist()
                return True
            if not current_song:
                SongRequestQueueManager.update_song_playing_id("")
            if self.settings["use_spotify"]:
                if self.previously_playing_spotify:
                    self.bot.spotify_api.play(self.bot.spotify_token_manager)
                    self.previously_playing_spotify = False
            if self.is_video_showing:
                self._hide()
        return False

    def _play(self, video_id, video_title, requested_by_name):
        self.bot.songrequest_websocket_manager.emit(
            "play", {"video_id": video_id, "video_title": video_title, "requested_by": requested_by_name}
        )
        self.bot.websocket_manager.emit("songrequest_play", WIDGET_ID, {"video_id": video_id})
        self.module_state["paused"] = True
        if self.module_state["video_showing"]:
            self._show()
        self._playlist()

    def ready(self):
        self.resume_function()
        ScheduleManager.execute_delayed(2, self._volume)

    def _pause(self):
        self.bot.songrequest_websocket_manager.emit("pause", {})
        self.bot.websocket_manager.emit("songrequest_pause", WIDGET_ID, {})
        self._hide()

    def _resume(self):
        self.bot.songrequest_websocket_manager.emit("resume", {})
        self.bot.websocket_manager.emit("songrequest_resume", WIDGET_ID, {"volume": self.volume})
        self.module_state["paused"] = False
        if self.module_state["video_showing"]:
            self._show()

    def _volume(self):
        self.bot.songrequest_websocket_manager.emit("volume", {"volume": self.volume_val})
        self.bot.websocket_manager.emit("songrequest_volume", WIDGET_ID, {"volume": self.volume})

    def _seek(self, _time):
        self.bot.songrequest_websocket_manager.emit("seek", {"seek_time": _time})
        self.bot.websocket_manager.emit("songrequest_seek", WIDGET_ID, {"seek_time": _time})
        self.module_state["paused"] = True

    def _show(self):
        self.bot.websocket_manager.emit("songrequest_show", WIDGET_ID, {})
        self.is_video_showing = True

    def _hide(self):
        self.bot.websocket_manager.emit("songrequest_hide", WIDGET_ID, {})
        self.is_video_showing = False

    def _playlist(self):
        with DBManager.create_session_scope() as db_session:
            playlist = SongrequestQueue._get_playlist(db_session, 15)
            self.bot.songrequest_websocket_manager.emit("playlist", {"playlist": playlist})

    def _playlist_history(self):
        with DBManager.create_session_scope() as db_session:
            self.bot.songrequest_websocket_manager.emit(
                "history", {"history": SongrequestHistory._get_history(db_session, 15)}
            )

    def _stop_video(self):
        self.bot.songrequest_websocket_manager.emit("stop", {})
        self.bot.websocket_manager.emit("songrequest_stop", WIDGET_ID, {})
