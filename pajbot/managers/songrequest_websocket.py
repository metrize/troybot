import json
import logging
import threading
import urllib
import re
from pathlib import Path

from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol

from pajbot.models.songrequest import SongrequestQueue, SongrequestHistory, SongRequestSongInfo
from pajbot.managers.db import DBManager

import pajbot.utils as utils

log = logging.getLogger("pajbot")


def find_youtube_id_in_string(string):
    if len(string) < 11:
        # Too short to be a youtube ID
        return False

    if len(string) == 11:
        # Assume it's a straight up youtube ID
        return string

    if not (string.lower().startswith("http://") or string.lower().startswith("https://")):
        string = "http://" + string

    urldata = urllib.parse.urlparse(string)

    if urldata.netloc == "youtu.be":
        youtube_id = urldata.path[1:]
    elif urldata.netloc.endswith("youtube.com"):
        qs = urllib.parse.parse_qs(urldata.query)
        if "v" not in qs:
            return False
        youtube_id = qs["v"][0]
    else:
        return False

    return youtube_id


def find_youtube_video_by_search(search):
    try:
        query_string = urllib.parse.urlencode({"search_query": search})
        html_content = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
        return re.findall(r"href=\"\/watch\?v=(.{11})", html_content.read().decode())[0]
    except:
        return None


def isfloat(str):
    try:
        float(str)
    except ValueError:
        return False
    return True


def isint(str):
    try:
        int(str)
    except ValueError:
        return False
    return True


class SongRequestWebSocketServer:
    clients = []
    manager_ext = None

    def __init__(self, manager, port, secure=False, key_path=None, crt_path=None, unix_socket_path=None):
        self.manager = manager_ext = manager

        class MyServerProtocol(WebSocketServerProtocol):
            def __init__(self):
                self.isAuthed = False
                self.user_id = None
                self.user_name = None
                self.login = None
                WebSocketServerProtocol.__init__(self)

            def onOpen(self):
                SongRequestWebSocketServer.clients.append(self)

            def onMessage(self, payload, isBinary):
                with DBManager.create_session_scope() as db_session:
                    if not isBinary:
                        try:
                            json_msg = json.loads(payload)
                        except:
                            self._close_conn()
                            return
                        if "event" not in json_msg:
                            self._close_conn()
                            return
                        switcher = {
                            "AUTH": self._auth,
                            "PAUSE": self._pause,
                            "RESUME": self._resume,
                            "NEXT": self._next,
                            "PREVIOUS": self._previous,
                            "SEEK": self._seek,
                            "VOLUME": self._volume,
                            "SHOWVIDEO": self._showvideo,
                            "HIDEVIDEO": self._hidevideo,
                            "CLOSESR": self._closesr,
                            "OPENSR": self._opensr,
                            "MOVE": self._move,
                            "FAVOURITE": self._favourite,
                            "UNFAVOURITE": self._unfavourite,
                            "BAN": self._ban,
                            "UNBAN": self._unban,
                            "DELETE": self._delete,
                        }
                        method = switcher.get(json_msg["event"], None)
                        if not manager_ext.bot.songrequest_manager.module_state["enabled"]:
                            return

                        if not method or not method(db_session, json_msg.get("data", None)):
                            self._close_conn()
                            return

            def onClose(self, wasClean, code, reason):
                try:
                    SongRequestWebSocketServer.clients.remove(self)
                except:
                    pass

            def _close_conn(self):
                self.sendClose()

            def _pause(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.pause_function()

            def _showvideo(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.show_function()

            def _hidevideo(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.hide_function()

            def _closesr(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.close_module_function()

            def _opensr(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.open_module_function()

            def _resume(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.resume_function()

            def _next(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.skip_function(self.login)

            def _previous(self, db_session, data):
                if not self.isAuthed:
                    return False

                return manager_ext.bot.songrequest_manager.previous_function(self.login)

            def _seek(self, db_session, data):
                if not self.isAuthed or not data.get("seek_time", False):
                    return False

                return manager_ext.bot.songrequest_manager.seek_function(data.get("seek_time"))

            def _volume(self, db_session, data):
                if not self.isAuthed or not data or not data.get("volume", False):
                    return False

                return manager_ext.bot.songrequest_manager.volume_function(data.get("volume"))

            def _move(self, db_session, data):
                if not self.isAuthed or not data or not data.get("database_id", False) or not data.get("to_id", False):
                    return False

                return manager_ext.bot.songrequest_manager.move_function(
                    int(data["database_id"]), int(data["to_id"]) - 1
                )

            def _favourite(self, db_session, data):
                if not self.isAuthed or not data or not data.get("database_id", data.get("hist_database_id", False)):
                    return False

                return manager_ext.bot.songrequest_manager.favourite_function(
                    database_id=data.get("database_id", None), hist_database_id=data.get("hist_database_id", None)
                )

            def _unfavourite(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or not data.get(
                        "database_id", data.get("songinfo_database_id", data.get("hist_database_id", False))
                    )
                ):
                    return False

                return manager_ext.bot.songrequest_manager.unfavourite_function(
                    database_id=data.get("database_id", None),
                    hist_database_id=data.get("hist_database_id", None),
                    songinfo_database_id=data.get("songinfo_database_id", None),
                )

            def _ban(self, db_session, data):
                if not self.isAuthed or not data or not data.get("database_id", data.get("hist_database_id", False)):
                    return False

                return manager_ext.bot.songrequest_manager.ban_function(
                    database_id=data.get("database_id", None), hist_database_id=data.get("hist_database_id", None)
                )

            def _unban(self, db_session, data):
                if (
                    not self.isAuthed
                    or not data
                    or not data.get(
                        "database_id", data.get("songinfo_database_id", data.get("hist_database_id", False))
                    )
                ):
                    return False

                return manager_ext.bot.songrequest_manager.unban_function(
                    database_id=data.get("database_id", None),
                    hist_database_id=data.get("hist_database_id", None),
                    songinfo_database_id=data.get("songinfo_database_id", None),
                )

            def _delete(self, db_session, data):
                if not self.isAuthed or not data or not data.get("database_id", False):
                    return False

                return manager_ext.bot.songrequest_manager.remove_function(int(data["database_id"]))

            def _auth(self, db_session, data):
                access_token = data["access_token"]
                user = manager_ext.bot.twitch_v5_api.user_from_access_token(
                    access_token, manager_ext.bot.twitch_helix_api, db_session
                )
                if not user or user.level < 500:
                    return False
                self.isAuthed = True
                self.login = user.login
                self._dump_state(db_session)
                return True

            def _dump_state(self, db_session):
                song = (
                    SongrequestQueue._from_id(db_session, manager_ext.bot.songrequest_manager.current_song_id)
                    if manager_ext.bot.songrequest_manager.current_song_id
                    else None
                )
                data = {
                    "volume": manager_ext.bot.songrequest_manager.volume_val,
                    "current_song": song.webjsonify() if song else {},
                    "module_state": manager_ext.bot.songrequest_manager.module_state,
                    "playlist": SongrequestQueue._get_playlist(db_session, limit=30),
                    "backup_playlist": SongrequestQueue._get_backup_playlist(db_session, limit=30),
                    "history_list": SongrequestHistory._get_history(db_session, limit=30),
                    "banned_list": SongRequestSongInfo._get_banned_list(db_session),
                    "favourite_list": SongRequestSongInfo._get_favourite_list(db_session),
                    "current_timestamp": str(utils.now().timestamp()),
                }
                payload = {"event": "initialize", "data": data}
                self.sendMessage(json.dumps(payload).encode("utf8"), False)

        factory = WebSocketServerFactory()
        factory.setProtocolOptions(autoPingInterval=15, autoPingTimeout=5)
        factory.protocol = MyServerProtocol

        def reactor_run(reactor, factory, port, context_factory=None, unix_socket_path=None):
            if unix_socket_path:
                sock_file = Path(unix_socket_path)
                if sock_file.exists():
                    sock_file.unlink()
                reactor.listenUNIX(unix_socket_path, factory)
            else:
                if context_factory:
                    log.info("wss secure")
                    reactor.listenSSL(port, factory, context_factory)
                else:
                    log.info("ws unsecure")
                    reactor.listenTCP(port, factory)
            reactor.run(installSignalHandlers=0)

        reactor_thread = threading.Thread(
            target=reactor_run,
            args=(reactor, factory, port, None, unix_socket_path),
            name="SongRequestWebSocketServerThread",
        )
        reactor_thread.daemon = True
        reactor_thread.start()


class SongRequestWebSocketManager:
    def __init__(self, bot):
        self.clients = []
        self.server = None
        self.bot = bot
        cfg = bot.config["songrequest-websocket"]
        try:
            if cfg["enabled"] == "1":
                try:
                    from twisted.python import log as twisted_log

                    twisted_log.addObserver(SongRequestWebSocketManager.on_log_message)
                except ImportError:
                    log.error("twisted is not installed, websocket cannot be initialized.")
                    return
                except:
                    log.exception("Uncaught exception")
                    return
                ssl = bool(cfg.get("ssl", "0") == "1")
                port = int(cfg.get("port", "443" if ssl else "80"))
                key_path = cfg.get("key_path", "")
                crt_path = cfg.get("crt_path", "")
                unix_socket_path = cfg.get("unix_socket", None)
                if ssl and (key_path == "" or crt_path == ""):
                    log.error("SSL enabled in config, but missing key_path or crt_path")
                    return
                self.server = SongRequestWebSocketServer(self, port, ssl, key_path, crt_path, unix_socket_path)
        except:
            log.exception("Uncaught exception in SongRequestWebSocketManager")

    def emit(self, event, data={}):
        if self.server:
            payload = json.dumps({"event": event, "data": data}).encode("utf8")
            for client in self.server.clients:
                if client.isAuthed:
                    client.sendMessage(payload, False)

    @staticmethod
    def on_log_message(message, isError=False, printed=False):
        if isError:
            log.error(message["message"])
        else:
            pass
