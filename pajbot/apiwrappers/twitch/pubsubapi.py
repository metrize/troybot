import json
import threading
import logging
import websocket

from pajbot.managers.handler import HandlerManager
from pajbot.managers.schedule import ScheduleManager
from pajbot.managers.db import DBManager
from pajbot.models.user import User

log = logging.getLogger(__name__)


class PubSubAPI:
    def __init__(self, bot, token):
        self.bot = bot
        self.token = token
        self.sent_ping = False
        self.websocket = None
        ScheduleManager.execute_now(self.check_connection)
        self.check_connection_schedule = ScheduleManager.execute_every(30, self.check_connection)
        self.ping_schedule = ScheduleManager.execute_every(60, self.ping_server)

    def initialize_socket(self):
        self.websocket = websocket.WebSocketApp(
            "wss://pubsub-edge.twitch.tv",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open,
        )

        thread = threading.Thread(target=self._receiveEventsThread)
        thread.daemon = True
        thread.start()

    def _receiveEventsThread(self):
        self.websocket.run_forever()

    def on_message(self, ws, message):
        msg = json.loads(message)
        if msg["type"].lower() == "pong":
            self.sent_ping = False
        elif msg["type"].lower() == "reconnect":
            self.reset()
        elif msg["type"].lower() == "message":
            if msg["data"]["topic"] == "channel-bits-events-v2." + self.bot.streamer_user_id:
                messageR = json.loads(msg["data"]["message"])
                user_id_of_cheer = str(messageR["data"]["user_id"])
                bits_cheered = str(messageR["data"]["bits_used"])
                with DBManager.create_session_scope() as db_session:
                    user = User.find_by_id(db_session, user_id_of_cheer)
                    if user is not None:
                        HandlerManager.trigger("on_cheer", True, user=user, bits_cheered=bits_cheered)

    def on_error(self, ws, error):
        log.error(f"pubsubapi : {error}")

    def on_close(self, ws):
        log.error("Pubsub stopped")
        self.reset()

    def on_open(self, ws):
        log.info("Pubsub Started!")
        self.sendData(
            {
                "type": "LISTEN",
                "data": {
                    "topics": ["channel-bits-events-v2." + self.bot.streamer_user_id],
                    "auth_token": self.token.token.access_token,
                },
            }
        )

    def ping_server(self):
        if self.sent_ping:
            return

        self.sendData({"type": "PONG"})
        self.sent_ping = True
        ScheduleManager.execute_delayed(10, self.check_ping)

    def check_connection(self):
        if self.websocket is None:
            self.initialize_socket()

    def check_ping(self):
        if self.sent_ping:
            log.error("Pubsub connection timed out")
            self.reset()

    def sendData(self, message):
        try:
            self.websocket.send(json.dumps(message))
        except Exception as e:
            log.error(e)

    def reset(self):
        self.schedule.pause()
        try:
            self.websocket.close()
        except:
            pass
        self.websocket = None
